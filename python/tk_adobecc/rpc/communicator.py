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
    _RESULTS = dict()
    _UID = 0
    _LOCK = threading.Lock()
    _WAIT_INTERVAL = 0.01
    _RPC_EXECUTE_COMMAND = "execute_command"
    __REGISTRY = dict()

    def __init__(self, port=8090, host="localhost", disconnect_callback=None):
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
        if identifier in cls.__REGISTRY:
            instance = cls.__REGISTRY[identifier]
        else:
            instance = cls(*args, **kwargs)
            cls.__REGISTRY[identifier] = instance
        return instance

    ##########################################################################################
    # properties

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    ##########################################################################################
    # RPC

    def ping(self):
        self._io._ping()

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

    def wait(self, timeout=0.1):
        self._io.wait(float(timeout))

    ##########################################################################################
    # internal methods

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
                self._RESULTS[uid] = result.get("result")

    ##########################################################################################
    # private methods

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