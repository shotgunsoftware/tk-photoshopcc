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
                timer.start()
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
    Container QObject for Qt signals fired when messages requesting certain
    actions take place in Python arrive from the remote process.

    :signal logging_received(str, str): Fires when a logging call has been
        received. The first string is the logging level (debug, info, warning,
        or error) and the second string is the message.
    :signal command_received(int): Fires when an engine command has been
        received. The integer value is the unique id of the engine command
        that was requested to be executed.
    :signal run_tests_request_received: Fires when a request for unit tests to
        be run has been received.
    :signal state_requested: Fires when the remote process requests the current
        state.
    """
    logging_received = QtCore.Signal(str, str)
    command_received = QtCore.Signal(int)
    run_tests_request_received = QtCore.Signal()
    state_requested = QtCore.Signal()


class AdobeBridge(Communicator):
    """
    Bridge layer between the Adobe product and Shotgun Toolkit.
    """
    # Backwards compatibility added to support tk-photoshop environment vars.
    # https://support.shotgunsoftware.com/hc/en-us/articles/219039748-Photoshop#If%20the%20engine%20does%20not%20start
    SHOTGUN_ADOBE_RESPONSE_TIMEOUT = os.environ.get(
        "SHOTGUN_ADOBE_RESPONSE_TIMEOUT",
        os.environ.get(
            "SGTK_PHOTOSHOP_TIMEOUT",
            300.0,
        ),
    )
    SHOTGUN_ADOBE_HEARTBEAT_TIMEOUT = os.environ.get(
        "SHOTGUN_ADOBE_HEARTBEAT_TIMEOUT",
        os.environ.get(
            "SGTK_PHOTOSHOP_HEARTBEAT_TIMEOUT",
            0.5,
        ),
    )
    WAIT_TIMEOUT = 5.0

    def __init__(self, *args, **kwargs):
        super(AdobeBridge, self).__init__(*args, **kwargs)

        self._emitter = MessageEmitter()
        self._io.on("logging", self._forward_logging)
        self._io.on("command", self._forward_command)
        self._io.on("run_tests", self._forward_run_tests)
        self._io.on("state_requested", self._forward_state_request)

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

    @property
    def state_requested(self):
        """
        The QSignal that is emitted when the state is requested via RPC.
        """
        return self._emitter.state_requested

    ##########################################################################################
    # public methods

    @timeout(SHOTGUN_ADOBE_HEARTBEAT_TIMEOUT, "Ping timed out.")
    def ping(self):
        """

        """
        super(AdobeBridge, self).ping()

    def send_state(self, state):
        """
        Responsible for forwarding the current SG state to javascript.

        This method knows about the structure of the json that the js side
        expects. We provide display info and we also
        """
        # encode the python dict as json
        json_state = json.dumps(state)
        self._io.emit("set_state", json_state)

    @timeout(WAIT_TIMEOUT, "SocketIO wait timed out.")
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
        """
        Forwards the received command on as a Qt Signal.

        :param response: The data received with the message. This
                         will take the form of a JSON encoded integeter
                         that is the unique id of the command to be called.
        """
        self.command_received.emit(int(json.loads(response)))

    def _forward_logging(self, response):
        """
        Forwards the logging request received as a Qt Signal.

        :param response: The data received with the message. This will
                         take the form of a JSON encoded dictionary with
                         "level" and "message" keys containing the severity
                         level of the logging message, and the message itself,
                         respectively.
        """
        response = json.loads(response)
        self.logging_received.emit(
            response.get("level"),
            response.get("message"),
        )

    def _forward_run_tests(self, response):
        """
        Forwards the request for tests to be run as a Qt Signal.

        :param response: The data received with the message. This
                         is disregarded.
        """
        self.run_tests_request_received.emit()

    def _forward_state_request(self, response):
        """
        Forwards the request for state as a QtSignal.

        :param response: The data received with the message. This
                         is disregarded.
        """
        self.state_requested.emit()

    @timeout(SHOTGUN_ADOBE_RESPONSE_TIMEOUT, "Timed out waiting for response.")
    def _wait_for_response(self, uid):
        """
        Waits for the results of an RPC call. A timeout is attached to this
        operation equal to the number of seconds defined in the
        SHOTGUN_ADOBE_RESPONSE_TIMEOUT environment variable, or 300 seconds
        if that is not defined.

        :param int uid: The unique id of the RPC call to wait for.

        :returns: The raw returned results data.
        """
        return super(AdobeBridge, self)._wait_for_response(uid)

##########################################################################################
# exceptions

class RPCTimeoutError(Exception):
    """
    Raised when an RPC event times out.
    """
    pass


