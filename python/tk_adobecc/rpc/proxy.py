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

