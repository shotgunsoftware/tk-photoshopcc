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

import sgtk

from sgtk.platform.qt import QtCore, QtGui

# use api json to cover py 2.5
from tank_vendor import shotgun_api3
json = shotgun_api3.shotgun.json

from .rpc import Communicator

class MessageEmitter(QtCore.QObject):
    """
    Emits incoming socket.io messages as Qt signals.
    """
    logging_received = QtCore.Signal(str, str)
    command_received = QtCore.Signal(int)


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

    ##########################################################################################
    # properties

    @property
    def emitter(self):
        return self._emitter

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

    ##########################################################################################
    # internal methods

    def _forward_command(self, response):
        self.emitter.command_received.emit(int(json.loads(response)))

    def _forward_logging(self, response):
        response = json.loads(response)
        self.emitter.logging_received.emit(
            response.get("level"),
            response.get("message"),
        )

