# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import json
import threading
import sys
import os.path

# Add our third-party packages to sys.path.
sys.path.append(os.path.join(os.path.dirname(__file__), "packages"))

from socketIO_client import SocketIO, BaseNamespace
from .proxy import ProxyScope, ProxyWrapper, ClassInstanceProxyWrapper

class Communicator(object):
    """
    A communication manager that owns a socket.io client. The
    communicator offers access to a global scope provided by
    a server that the communicator connects to at instantiation
    time. Basic RPC calls are also implemented.
    """
    _RESULTS = dict()
    _UID = 0
    _LOCK = threading.Lock()
    _WAIT_INTERVAL = 0.01
    _RPC_EXECUTE_COMMAND = "execute_command"
    _REGISTRY = dict()

    def __init__(self, port=8090, host="localhost", disconnect_callback=None):
        """
        Constructor. Rather than instantiating the Communicator directly,
        it is advised to make use of the get_or_create() classmethod as
        a factory constructor.

        :param int port: The port num to connect to. Default is 8090.
        :param str host: The host to connect to. Default is localhost.
        :param disconnect_callback: A callback to call if a disconnect
                                    message is received from the host.
        """
        self._port = port
        self._host = host

        self._io = SocketIO(host, port)
        self._io.on("return", self._handle_response)

        self._global_scope = None
        self._disconnect_callback = disconnect_callback

        if disconnect_callback:
            self._io.on("disconnect", disconnect_callback)

        self._get_global_scope()

    ##########################################################################################
    # constructor

    @classmethod
    def get_or_create(cls, identifier, *args, **kwargs):
        """
        A factory constructor that provides singleton instantiation
        behavior based on a given unique identifier. If an instance
        exists with the given identifier it will be returned,
        otherwise a new instance is constructed and returned after
        being recorded by the given identifier.

        :param identifier: Some hashable identifier to associate
                           the instantiated communicator with.
        :param int port: The port to connect to. Default is 8090.
        :param str host: The host to connect to. Default is localhost.
        :param disconnect_callback: A callback to call if a disconnect
                                    message is received from the host. 
        """
        if identifier in cls._REGISTRY:
            instance = cls._REGISTRY[identifier]
        else:
            instance = cls(*args, **kwargs)
            cls._REGISTRY[identifier] = instance
        return instance

    ##########################################################################################
    # properties

    @property
    def host(self):
        """
        The host that was connected to.
        """
        return self._host

    @property
    def port(self):
        """
        The port number connected to.
        """
        return self._port

    ##########################################################################################
    # RPC

    def ping(self):
        """
        Pings the host, testing whether the connection is still live.
        """
        self._io._ping()

    def rpc_call(self, proxy_object, params=[], parent=None):
        """
        Executes a "call" RPC command.

        :param proxy_object: The proxy object to call via RPC.
        :param list params: The list of arguments to pass to the
                            callable when it is called.
        :param parent: The parent proxy object, if any. If given, the
                       callable will be called as a method of the
                       parent object. If a parent is not given, it
                       will be called as a function of the global
                       scope.

        :returns: The data returned by the callable when it is
                  called.
        """
        if parent:
            params.insert(0, parent.uid)
        else:
            params.insert(0, None)

        return self.__run_rpc_command(
            method="call",
            proxy_object=proxy_object,
            params=params,
            wrapper_class=ProxyWrapper,
        )

    def rpc_eval(self, command):
        """
        Evaluates the given string command via RPC.

        :param str command: The command to execute.

        :returns: The data returned by the evaluated command.
        """
        return self.__run_rpc_command(
            method="eval",
            proxy_object=None,
            params=[command],
            wrapper_class=ProxyWrapper,
        )

    def rpc_get(self, proxy_object, property_name):
        """
        Gets the value of the given property for the given proxy
        proxy object.

        :param proxy_object: The proxy object to get the property
                             value from.
        :param str property_name: The name of the property to get.

        :returns: The value of the property of the remote object.
        """
        return self.__run_rpc_command(
            method="get",
            proxy_object=proxy_object,
            params=[property_name],
            wrapper_class=ProxyWrapper,
            attach_parent=proxy_object,
        )

    def rpc_get_index(self, proxy_object, index):
        """
        Gets the value at the given index of the given proxy object.

        :param proxy_object: The proxy object to index into.
        :param int index: The index to get the value of.

        :returns: The value of the index of the remote object.
        """
        return self.__run_rpc_command(
            method="get_index",
            proxy_object=proxy_object,
            params=[index],
            wrapper_class=ProxyWrapper,
        )

    def rpc_new(self, class_name):
        """
        Instantiates a new remote object of the given class name.

        :param str class_name: The name of the class to instantiate.

        :returns: A proxy object pointing to the instantiated
                  remote object.
        """
        return self.__run_rpc_command(
            method="new",
            proxy_object=None,
            params=[class_name],
            wrapper_class=ClassInstanceProxyWrapper,
        )

    def rpc_set(self, proxy_object, property_name, value):
        """
        Sets the given property to the given value on the given proxy
        object.

        :param proxy_object: The proxy object to set the property of.
        :param str property_name: The name of the property to set.
        :param value: The value to set the property to.
        """
        return self.__run_rpc_command(
            method="set",
            proxy_object=proxy_object,
            params=[property_name, value],
            wrapper_class=ProxyWrapper,
        )

    def wait(self, timeout=0.1):
        """
        Triggers a wait and the processing of any messages already
        queued up or that arrive during the wait period.

        :param float timeout: The duration of time, in seconds, to
                              wait.
        """
        self._io.wait(float(timeout))

    ##########################################################################################
    # internal methods

    def _get_global_scope(self):
        """
        Emits a message requesting that the remote global scope be
        introspected, wrapped, and returned as JSON data.
        """
        payload = self._get_payload("get_global_scope")

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        uid = payload["id"]
        results = self._wait_for_response(uid)

        self._global_scope = ProxyScope(results, self)

    def _get_payload(self, method, proxy_object=None, params=[]):
        """
        Builds the payload dictionary to be sent via RPC.

        :param str method: The JSON-RPC method name to call.
        :param proxy_object: The proxy object to be included in the
                             payload.
        :param list params: The list of paramaters to be packaged.

        :returns: The payload dictionary, formatted for JSON-RPC
                  use.
        """
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
        """
        Handles the response to an already-emitted message.

        :param str response: The JSON encoded message response.

        :returns: The decoded result data.
        """
        with self._LOCK:
            result = json.loads(response)
            uid = result["id"]

            try:
                self._RESULTS[uid] = json.loads(result["result"])
            except (TypeError, ValueError):
                self._RESULTS[uid] = result.get("result")

    def _wait_for_response(self, uid):
        """
        Waits for the results of an RPC call.

        :param int uid: The unique id of the RPC call to wait for.

        :returns: The raw returned results data.
        """
        while uid not in self._RESULTS:
            self._io.wait(self._WAIT_INTERVAL)

        results = self._RESULTS[uid]
        del self._RESULTS[uid]
        return results

    ##########################################################################################
    # private methods

    def __get_uid(self):
        """
        Gets the next available unique id number.
        """
        with self._LOCK:
            self._UID += 1
            return self._UID

    def __prepare_params(self, params):
        """
        Prepares a list of paramaters to be emitted as part of an
        RPC call.

        :param list params: The list of paramaters to prepare.

        :returns: The list of prepared paramaters, fit for emission.
        """
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

    def __run_rpc_command(self, method, proxy_object, params, wrapper_class, attach_parent=None):
        """
        Emits the requested JSON-RPC method via socket.io and handles
        the returned result when it arrives.

        :param str method: The JSON-RPC method name to call.
        :param proxy_object: The proxy object to send.
        :param list params: The list of parameters to emit.
        :param wrapper_class: The class reference to use when
                              wrapping results.
        :param attach_parent: An optional parent object to associate
                              the returned data to.

        :returns: The wrapped results of the RPC call.
        """
        payload = self._get_payload(
            method=method,
            proxy_object=proxy_object,
            params=params,
        )

        self._io.emit(self._RPC_EXECUTE_COMMAND, payload)
        results = self._wait_for_response(payload["id"])

        return wrapper_class(results, self, parent=attach_parent)

    ##########################################################################################
    # magic methods

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