# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import traceback

# don't import this module until bootstrapped
import sgtk
from sgtk.platform.qt import QtGui, QtCore

class HeartbeatMonitor(QtCore.QObject):
    # Five second interval. The heartbeat should trigger every
    # second, but it isn't guaranteed because the interval fires
    # the function when there's room in the event loop for it.
    HEARTBEAT_TIMEOUT = 5000

    def __init__(self, engine, logger, parent=None):
        super(HeartbeatMonitor, self).__init__(parent=parent)

        self._logger = logger
        self._engine = engine
        self._last_heartbeat = -1
        self._timer = QtCore.QTimer(parent=self)
        self._timer.timeout.connect(self.check_heartbeat)
        self._timer.start(self.HEARTBEAT_TIMEOUT)

    def check_heartbeat(self):
        self._logger.debug("Checking heartbeat...")
        heartbeat = self._engine.adobe.get_last_heartbeat()

        if heartbeat == self._last_heartbeat:
            self._logger.warning("Heartbeat not detected.")
            self._engine.disconnected()
        else:
            self._last_heartbeat = heartbeat

class AdobeCCPython(QtGui.QApplication):

    def __init__(self, title, logger, icon_path=None):

        super(AdobeCCPython, self).__init__([title])

        self.setApplicationName(title)
        if icon_path:
            self.setWindowIcon(QtGui.QIcon(icon_path))
        self.setQuitOnLastWindowClosed(False)

        engine = sgtk.platform.current_engine()

        # give the application a dark look and feel
        try:
            engine._initialize_dark_look_and_feel()
        except Exception, e:
            logger.error("Failed to initialize dark look and feel!")
            logger.critical(traceback.format_exc())
        else:
            logger.debug("Initialized dark look and feel!")

        # list the registered commands for debugging purposes
        logger.debug("Registered Commands:")
        for (command_name, value) in engine.commands.iteritems():
            logger.debug(" %s: %s" % (command_name, value))

        # list the registered panels for debugging purposes
        logger.debug("Registered Panels:")
        for (panel_name, value) in engine.panels.iteritems():
            logger.debug(" %s: %s" % (panel_name, value))

        # Monitor the heartbeat to ensure that we know if we lose the Adobe
        # product's process and need to shut down.
        self._heartbeat = HeartbeatMonitor(engine, logger)

        # XXX manually create/show the sg panel as a test
        panel_widget = None
        try:
            panel_widget = engine.panels["tk_multi_shotgunpanel_main"]["callback"]()
        except Exception, e:
            logger.error("Failed to show the SG panel!")
            logger.critical(traceback.format_exc())
        else:
            logger.debug("Showing the SG panel...")

        if not panel_widget:
            panel_widget = QtGui.QLabel("Something happend bro. Your code is whack!")

        panel_widget.show()

        # TODO: can we force raise windows as needed?
        panel_widget.raise_()

        #adobecc = engine.import_module("adobecc")

        #app_factory = adobecc.AdobeCCAppFactory()
        #adobecc_app = app_factory.get_current_cc_app()

        #logger.debug("Adobe CC App: %s" % (adobecc_app,))

        # TODO:
        #   * setup communications here
        #   * set up local server running in a separate thread to handle
        #       communication from CC app.
        #          * handled requests should be processed and sent back
        #              to main thread if need be (GUI stuff).
        #          * event types:
        #              * CC shut down
        #              * panel interactions (button clicks, etc)
        #              * context changes via panel
        #   * given the port supplied on bootstrap command line, send
        #       message back to CC app telling it what port the local
        #       server is listening on.
        #   * startup another bg thread to send heartbeats back to
        #       adobe CC on a regular basis
