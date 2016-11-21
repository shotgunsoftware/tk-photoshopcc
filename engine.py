# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import threading

import sgtk


class AdobeEngine(sgtk.platform.Engine):
    """
    An Adobe CC engine for Shotgun Toolkit.
    """

    ENV_COMMUNICATION_PORT_NAME = "SHOTGUN_ADOBE_PORT"
    CHECK_CONNECTION_TIMEOUT = 1000
    _COMMAND_UID_COUNTER = 0
    _LOCK = threading.Lock()

    def pre_app_init(self):

        tk_adobecc = self.import_module("tk_adobecc")

        # get the adobe instance. it may have been initialized already by a
        # previous instance of the engine. if not, initialize a new one.
        self._adobe = tk_adobecc.AdobeBridge.get_or_create(
            identifier=self.instance_name,
            port=os.environ.get(self.ENV_COMMUNICATION_PORT_NAME),
        )

        self.adobe.logging_received.connect(self._handle_logging)
        self.adobe.command_received.connect(self._handle_command)

    def post_app_init(self):

        # list the registered commands for debugging purposes
        self.log_debug("Registered Commands:")
        for (command_name, value) in self.commands.iteritems():
            self.log_debug(" %s: %s" % (command_name, value))

        # list the registered panels for debugging purposes
        self.log_debug("Registered Panels:")
        for (panel_name, value) in self.panels.iteritems():
            self.log_debug(" %s: %s" % (panel_name, value))

        # TODO: log user attribute metric

    def post_qt_init(self):

        from sgtk.platform.qt import QtCore

        # since this is running in our own Qt event loop, we'll use the bundled
        # dark look and feel. breaking encapsulation to do so.
        self.log_debug("Initializing default styling...")
        self._initialize_dark_look_and_feel()

        # setup the check connection timer.
        self._check_connection_timer = QtCore.QTimer(
            parent=QtCore.QCoreApplication.instance())
        self._check_connection_timer.timeout.connect(self._check_connection)
        self._check_connection_timer.start(self.CHECK_CONNECTION_TIMEOUT)

        # now that qt is setup and the engine is ready to go, forward the
        # current state back to the adobe side.
        self.__send_state()

    def destroy_engine(self):
        # TODO: log
        # TODO: destroy the panel
        pass

    def register_command(self, name, callback, properties=None):
        """
        Registers a new command with the engine. For Adobe RPC purposes,
        a "uid" property is added to the command's properties.
        """
        properties = properties or dict()
        properties["uid"] = self.__get_command_uid()
        return super(AdobeEngine, self).register_command(
            name,
            callback,
            properties,
        )

    ##########################################################################################
    # RPC

    def disconnected(self):
        # TODO: Implement real disconnection behavior. This may or may not
        # make sense to do here. This is just a tribute.
        from sgtk.platform.qt import QtCore
        app = QtCore.QCoreApplication.instance()
        app.quit()

    def _check_connection(self):
        try:
            self.adobe.ping()
        except Exception:
            self.disconnected()
        else:
            tk_adobecc = self.import_module("tk_adobecc")
            # Will allow queued up messages (like logging calls)
            # to be handled on the Python end.
            try:
                self.adobe.wait(0.01)
            except tk_adobecc.RPCTimeoutError:
                self.disconnected()

    def _handle_command(self, uid):
        for command in self.commands.values():
            if command.get("properties", dict()).get("uid") == uid:
                command["callback"]()

    def _handle_logging(self, level, message):
        command_map = dict(
            debug=self.log_debug,
            error=self.log_error,
            info=self.log_info,
            warn=self.log_warning,
        )

        if level in command_map:
            # TODO: Figure out how to better identify RPC logging vs.
            # native logging from Python.
            command_map[level]("[ADOBE] %s" % message)

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
        if not self.has_ui:
            self.log_error("Sorry, this environment does not support UI display! Cannot show "
                           "the requested window '%s'." % title)
            return None

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(title, bundle, widget_class, *args, **kwargs)

        # show the dialog
        dialog.show()

        # raise the dialog to make sure it shows above CC product
        dialog.raise_()

        # lastly, return the instantiated widget
        return widget

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

    ##########################################################################################
    # internal methods

    def __get_command_uid(self):
        with self._LOCK:
            self._COMMAND_UID_COUNTER += 1
            return self._COMMAND_UID_COUNTER

    def __send_state(self):
        # TODO: thumbnail path for current context? query & update if unavailable
        state = dict(
            context=dict(
                display=str(self.context)
            ),
            commands=[],
        )

        for (command_name, command_info) in self.commands.iteritems():
            properties = command_info.get("properties", {})

            command = dict(
                uid=properties.get("uid"),
                display_name=command_name,
                icon_path=properties.get("icon"),
                description=properties.get("description"),
            )

            state["commands"].append(command)

        # TODO: send to javascript
        self.log_debug("Sending state: %s" % str(state))
        self.adobe.send_state(state)
        

