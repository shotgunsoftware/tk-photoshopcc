# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.platform.qt import QtCore, QtGui

class HeartbeatMonitor(QtCore.QObject):
    # Five second interval. The heartbeat should trigger every
    # second, but it isn't guaranteed because the interval fires
    # the function when there's room in the event loop for it.
    HEARTBEAT_TIMEOUT = 5

    def __init__(self, engine, parent=None):
        super(HeartbeatMonitor, self).__init__(parent=parent)

        self._engine = engine
        self._last_heartbeat = -1
        self._timer = QtCore.QTimer(parent=self)
        self._timer.timeout.connect(self.check_heartbeat)
        self._timer.start(self.HEARTBEAT_TIMEOUT)

    def check_heartbeat(self):
        raise Exception("WTF")
        self._engine.log_debug("Checking heartbeat...")
        heartbeat = self._engine.adobe.last_heartbeat

        if heartbeat == self._last_heartbeat:
            self._engine.log_warning("Heartbeat not detected.")
            self._engine.disconnected()
        else:
            self._last_heartbeat = heartbeat
