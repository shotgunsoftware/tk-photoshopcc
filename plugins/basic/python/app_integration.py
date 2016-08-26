# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# don't import this module until bootstrapped
import sgtk
from sgtk.platform.qt import QtGui

class AdobeCCPython(QtGui.QApplication):

    def __init__(self, port, title, logger, icon_path=None):

        super(AdobeCCPython, self).__init__([title])

        self.setApplicationName(title)
        if icon_path:
            self.setWindowIcon(QtGui.QIcon(icon_path))
        self.setQuitOnLastWindowClosed(False)

        # keep a handle on the engine
        engine = sgtk.platform.current_engine()

        adobecc = engine.import_module("adobecc")

        app_factory = adobecc.AdobeCCAppFactory()
        adobecc_app = app_factory.get_current_cc_app()

        logger.debug("Adobe CC App: %s" % (adobecc_app,))
        logger.debug("Adobe CC App's port: %s" % (port,))

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
