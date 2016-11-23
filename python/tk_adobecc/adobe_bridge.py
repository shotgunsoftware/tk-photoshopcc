# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# TODO: expose direct CC DOM APIs here
# TODO: factory to return proper API based on current DCC (ps, premiere, etc)
    # TODO: module level log methods?
    # TODO: clear panel
    # TODO: set message in panel
    # TODO: get remote objects/classes
    # TODO: wrap save as

import os
import functools
import threading

import sgtk
from sgtk.platform.qt import QtCore

# use api json to cover py 2.5
from tank_vendor import shotgun_api3
json = shotgun_api3.shotgun.json

from .rpc import Communicator

##########################################################################################
# functions

def timeout(seconds=5.0, error_message="Timed out."):
    """
    A timeout decorator. When the given amount of time has passed
    after the decorated callable is called, if it has not completed
    an RPCTimeoutError is raised.

    :param float seconds: The timeout duration, in seconds.
    :param str error_message: The error message to raise once timed out.
    """
    def decorator(func):
        def _handle_timeout():
            raise RPCTimeoutError(error_message)

        def wrapper(*args, **kwargs):
            timer = threading.Timer(float(seconds), _handle_timeout)
            try:
                result = func(*args, **kwargs)
            finally:
                timer.cancel()
            return result

        return functools.wraps(func)(wrapper)
    return decorator

##########################################################################################
# classes

class MessageEmitter(QtCore.QObject):
    """
    Emits incoming socket.io messages as Qt signals.
    """
    logging_received = QtCore.Signal(str, str)
    command_received = QtCore.Signal(int)
    run_tests_request_received = QtCore.Signal()


class AdobeBridge(Communicator):
    """
    Bridge layer between the adobe product and toolkit.

    This is where we put logic that allows the two ends to communicate.
    """

    def __init__(self, *args, **kwargs):
        super(AdobeBridge, self).__init__(*args, **kwargs)

        self._emitter = MessageEmitter()
        self._io.on("logging", self._forward_logging)
        self._io.on("command", self._forward_command)
        self._io.on("run_tests", self._forward_run_tests)

    ##########################################################################################
    # properties

    @property
    def logging_received(self):
        """
        The signal that is emitted when a logging message has arrived
        via RPC.
        """
        return self._emitter.logging_received

    @property
    def command_received(self):
        """
        The signal that is emitted when a command message has arrived
        via RPC.
        """
        return self._emitter.command_received

    @property
    def run_tests_request_received(self):
        """
        The signal that is emitted when a run_tests message has arrived
        via RPC.
        """
        return self._emitter.run_tests_request_received

    ##########################################################################################
    # public methods

    def send_state(self, state):
        """
        Responsible for forwarding the current SG state to javascript.

        This method knows about the structure of the json that the js side
        expects. We provide display info and we also
        """
        # encode the python dict as json
        json_state = json.dumps(state)
        self._io.emit("set_state", json_state)

    @timeout()
    def wait(self, timeout=0.1):
        """
        Triggers a wait call in the underlying socket.io server. This wait
        can get hung up if the server is killed, so this methods breaks at
        5 seconds of duration and raises RPCTimeoutError if it does.

        :param float timeout: The wait duration, in seconds.
        """
        super(AdobeBridge, self).wait(timeout)

    ##########################################################################################
    # internal methods

    def _forward_command(self, response):
        self.command_received.emit(int(json.loads(response)))

    def _forward_logging(self, response):
        response = json.loads(response)
        self.logging_received.emit(
            response.get("level"),
            response.get("message"),
        )

    def _forward_run_tests(self, response):
        self.run_tests_request_received.emit()

##########################################################################################
# exceptions

class RPCTimeoutError(Exception):
    """
    Raised when an RPC event times out.
    """
    pass


