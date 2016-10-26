
import json
import threading
import pprint

from socketIO_client import SocketIO

class ProxyScope(object):
    def __init__(self, data, communicator):
        self._data = data
        self._communicator = communicator
        self.__registry = dict()
        self.__register_data()

    def __register_data(self):
        try:
            for item_name, item in self._data.iteritems():
                self.__registry[item_name] = ProxyWrapper(
                    item,
                    self._communicator,
                )
        except Exception:
            raise ValueError("Unable to interpret data: \"%s\"" % self._data)

    def __getattr__(self, name):
        try:
            return self.__registry[name]
        except KeyError:
            raise AttributeError("'%s' is not available in the requested scope." % name)


class ProxyWrapper(object):
    _LOCK = threading.Lock()
    _REGISTRY = dict()

    def __new__(cls, data, *args, **kwargs):
        # These wrappers are singletones based on the unique id of
        # the data being wrapped. We only wrap data that has a unique
        # id, so anything that doesn't pass the test defined by the
        # _needs_wrapping() class method is returned as is.
        with cls._LOCK:
            if not cls._needs_wrapping(data):
                try:
                    return json.loads(data)
                except Exception:
                    return data
            elif data["__uniqueid"] in cls._REGISTRY:
                # This data has already been wrapped, so we just need
                # to return the object we already have stored in the
                # registry.
                return cls._REGISTRY[data["__uniqueid"]]
            else:
                # New data, so we go ahead and instantiate a new wrapper
                # object.
                return object.__new__(cls, data, *args, **kwargs)

    def __init__(self, data, communicator, parent=None):
        # We have to use super here because I've implemented a
        # __setattr__ on this class. This will prevent infinite
        # recursion when setting these attributes.
        super(ProxyWrapper, self).__setattr__("_data", data)
        super(ProxyWrapper, self).__setattr__("_serialized", json.dumps(data))
        super(ProxyWrapper, self).__setattr__("_parent", parent)
        super(ProxyWrapper, self).__setattr__("_communicator", communicator)
        super(ProxyWrapper, self).__setattr__("_uid", data.get("__uniqueid"))

        # Everything is registered by unique id. This allows us get
        # JSON data back from CEP and map it to an existing ProxyWrapper.
        self._REGISTRY[self._uid] = self

    @property
    def data(self):
        return self._data

    @property
    def serialized(self):
        return self._serialized

    @property
    def uid(self):
        return self._uid

    @classmethod
    def _needs_wrapping(cls, data):
        # If it has a unique id, then it needs to be wrapped. If it
        # doesn't, then we don't really know what to do with it. Most
        # cases like this will be basic data types like ints and strings.
        if isinstance(data, dict) and "__uniqueid" in data:
            return True
        else:
            return False

    def __call__(self, *args): # TODO: support kwargs
        return self._communicator.rpc_call(
            self,
            list(args),
            parent=self._parent,
        )

    def __getattr__(self, name):
        remote_names = self.data["properties"] + self.data["methods"].keys()

        # TODO: Let's not hardcode this to Adobe-like behavior. We should
        # allow for type-specific handlers that can be registered with the
        # API in case higher-level code wants to customize how attribute
        # lookup via RPC works.
        if name in remote_names or self.data.get("instanceof") == "Enumerator":
            return self._communicator.rpc_get(self, name)
        else:
            raise AttributeError("Attribute %s does not exist!" % name)

    def __getitem__(self, key):
        return self._communicator.rpc_get_index(self, key)

    def __setattr__(self, name, value):
        remote_names = self.data["properties"] + self.data["methods"].keys()

        if name in remote_names:
            self._communicator.rpc_set(self, name, value)
        else:
            super(ProxyWrapper, self).__setattr__(name, value)


class ClassInstanceProxyWrapper(ProxyWrapper):
    def __call__(self, *args, **kwargs):
        # We don't actually call this. We're wrapping and returning
        # instance objects as is. This is just to allow for the typical
        # Python syntax of `adobe.SomeClassToInstantiate()`
        return self


class Communicator(object):
    _RESULTS = dict()
    _UID = 0
    _LOCK = threading.Lock()
    _WAIT_INTERVAL = 0.01
    _RPC_EXECUTE_COMMAND = "execute_command"

    def __init__(self, port=8090, host='localhost'):
        self._port = port
        self._host = host
        self._io = SocketIO(host, port)
        self._io.on('return', self._handle_response)
        self._global_scope = None

        self._get_global_scope()

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    def rpc_call(self, proxy_object, params=[], parent=None):
        if parent:
            params.insert(0, parent.uid)
        else:
            params.insert(0, None)

        payload = self._get_payload(
            "call",
            proxy_object,
            params,
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self.__wait(payload["id"])

        return ProxyWrapper(results, self)

    def rpc_get(self, proxy_object, property_name):
        payload = self._get_payload(
            "get",
            proxy_object,
            [property_name],
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self.__wait(payload["id"])

        return ProxyWrapper(results, self, parent=proxy_object)

    def rpc_get_index(self, proxy_object, index):
        payload = self._get_payload(
            "get_index",
            proxy_object,
            [index],
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self.__wait(payload["id"])

        return ProxyWrapper(results, self)

    def rpc_new(self, class_name):
        payload = self._get_payload(
            method="new",
            proxy_object=None,
            params=[class_name],
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self.__wait(payload["id"])

        return ClassInstanceProxyWrapper(results, self)

    def rpc_set(self, proxy_object, property_name, value):
        payload = self._get_payload(
            "set",
            proxy_object,
            [property_name, value],
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self.__wait(payload["id"])

        return ProxyWrapper(results, self)

    def _get_global_scope(self):
        payload = self._get_payload("get_global_scope")

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        uid = payload["id"]
        results = self.__wait(uid)

        self._global_scope = ProxyScope(results, self)

    def _get_payload(self, method, proxy_object=None, params=[]):
        payload = dict(
            id=self.__get_uid(),
            method=method,
            jsonrpc="2.0",
            params=[],
        )

        if proxy_object:
            payload["params"] = [proxy_object.serialized]

            if params:
                payload["params"].extend(self.__prepare_params(params))
        else:
            payload["params"] = self.__prepare_params(params)

        return payload

    def _handle_response(self, response, *args):
        with self._LOCK:
            result = json.loads(response)
            uid = result["id"]

            try:
                self._RESULTS[uid] = json.loads(result["result"])
            except ValueError:
                self._RESULTS[uid] = result["result"]

    def __get_uid(self):
        with self._LOCK:
            self._UID += 1
            return self._UID

    def __prepare_params(self, params):
        processed = []

        for param in params:
            # TODO: Probably handle all iterables.
            if isinstance(param, list):
                processed.extend(self.__prepare_params(param))
            elif isinstance(param, ProxyWrapper):
                processed.append(param.data)
            else:
                processed.append(param)

        return processed

    def __wait(self, uid):
        while uid not in self._RESULTS:
            self._io.wait(self._WAIT_INTERVAL)

        results = self._RESULTS[uid]
        del self._RESULTS[uid]
        return results

    def __getattr__(self, name):
        try:
            return getattr(self._global_scope, name)
        except AttributeError:
            # If we were asked for something that's not in the global
            # scope, it's possible that it's a class that needs to be
            # instantiated.

            # TODO: This needs to be behavior that's custom to the given
            # environment we're dealing with. Right now, this behavior here
            # is handling a situation that arises in ExtendScript, but might
            # not even be appropriate for other flavors/versions of JS.

            # NOTE: I'm thinking we can do this sort of thing just with a
            # subclass. The base Communicator class can define the simpler
            # getattr, which assumes anything requested is available from
            # the global scope object. For Adobe, we can implement an
            # AdobeCommunicator subclass that reimplements getattr and
            # adds the below logic.
            instance = self.rpc_new(name)
            if isinstance(instance, ProxyWrapper):
                return instance
            else:
                raise 








    