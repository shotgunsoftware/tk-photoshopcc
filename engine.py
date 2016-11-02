# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
A Adobe engine for Toolkit.
"""

import os

import sgtk

###############################################################################################
# The Toolkit Adobe engine
class AdobeEngine(sgtk.platform.Engine):

    ENV_COMMUNICATION_PORT_NAME = "SHOTGUN_ADOBE_PORT"

    HEARTBEAT_TIMEOUT = 1500

    def pre_app_init(self):

        tk_adobecc = self.import_module("tk_adobecc")

        # get the adobe instance. it may have been initialized already by a
        # previous instance of the engine. if not, initialize a new one.
        self._adobe = \
            tk_adobecc.AdobeBridge.get_instance(self.instance_name) or \
            tk_adobecc.AdobeBridge.initialize(
                self.instance_name,
                port=os.environ.get(self.ENV_COMMUNICATION_PORT_NAME),
            )

    def post_app_init(self):

        # list the registered commands for debugging purposes
        self.log_debug("Registered Commands:")
        for (command_name, value) in self.commands.iteritems():
            self.log_debug(" %s: %s" % (command_name, value))

        # list the registered panels for debugging purposes
        self.log_debug("Registered Panels:")
        for (panel_name, value) in self.panels.iteritems():
            self.log_debug(" %s: %s" % (panel_name, value))

        # TODO: signal back to js that python startup is almost done. do this by
        #       sending the current state. this should be a call to the engine.

        # TODO: initialize & populate the panel
        # TODO: get a handle on the remote CC instance and get the version
            # and any CC-specifics (ps vs premiere)
        # TODO: log user attribute metric

        from sgtk.platform.qt import QtCore

        # setup the heartbeat timer. this listens to the adobe bridge for
        # heartbeat events. if we haven't received a heartbeat from adobe in
        # a while, it has probably shut down.
        self._last_adobecc_heartbeat = -1
        self._adobecc_heartbeat_timer = QtCore.QTimer(parent=self)
        self._adobecc_heartbeat_timer.timeout.connect(self._check_heartbeat)
        self._adobecc_heartbeat_timer.start(self.HEARTBEAT_TIMEOUT)


    def destroy_engine(self):
        # TODO: log
        # TODO: destroy the panel
        pass

    ##########################################################################################
    # RPC

    def disconnected(self):
        # TODO: Implement real disconnection behavior. This may or may not
        # make sense to do here. This is just a tribute.
        self.log_info("Disconnected from Adobe product.")
        raise RuntimeError("DISCONNECTED")

    ##########################################################################################
    # properties

    @property
    def adobe(self):
        return self._adobe

    ##########################################################################################
    # UI

    def _define_qt_base(self):
        """
        This will be called at initialisation time and will allow
        a user to control various aspects of how QT is being used
        by Toolkit. The method should return a dictionary with a number
        of specific keys, outlined below.

        * qt_core - the QtCore module to use
        * qt_gui - the QtGui module to use
        * dialog_base - base class for to use for Toolkit's dialog factory

        :returns: dict
        """
        # TODO: require Desktop to use Adobe integration? Always launch with desktop's python?
        base = {}
        from PySide import QtCore, QtGui
        base["qt_core"] = QtCore
        base["qt_gui"] = QtGui
        base["dialog_base"] = QtGui.QDialog

        # tell QT to handle text strings as utf-8 by default
        utf8 = QtCore.QTextCodec.codecForName("utf-8")
        QtCore.QTextCodec.setCodecForCStrings(utf8)

        # TODO: ensure message boxes show up in front of CC
        return base

    # TODO: see tk-photoshop for handling windows-specific window parenting/display

    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine.
        The engine will attempt to parent the dialog nicely to the host application.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.

        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: the created widget_class instance
        """
        # TODO: ensure dialog is shown above CC
        super(AdobeEngine, self).show_dialog(title, bundle, widget_class, *args, **kwargs)

    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a modal dialog window in a way suitable for this engine. The engine will attempt to
        integrate it as seamlessly as possible into the host application. This call is blocking
        until the user closes the dialog.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.

        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: (a standard QT dialog status return code, the created widget_class instance)
        """
        # TODO: ensure the dialog is shown above CC
        super(AdobeEngine, self).show_modal(title, bundle, widget_class, *args, **kwargs)

    ##########################################################################################
    # logging

    # TODO: logging

    def _check_heartbeat(self):

        self.log_debug("Checking heartbeat...")
        current_heartbeat = self.adobe.last_heartbeat

        if current_heartbeat == self._last_adobecc_heartbeat:
            self.log_warning("Heartbeat not detected...")
            # TODO: shut down the qapplication
            #self.disconnected()
        else:
            self._last_adobecc_heartbeat = heartbeat