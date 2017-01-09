# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import os
import threading
import functools

import sgtk


class AdobeEngine(sgtk.platform.Engine):
    """
    An Adobe CC engine for Shotgun Toolkit.
    """

    SHOTGUN_ADOBE_PORT = os.environ.get("SHOTGUN_ADOBE_PORT")
    SHOTGUN_ADOBE_APPID = os.environ.get("SHOTGUN_ADOBE_APPID")

    # Backwards compatibility added to support tk-photoshop environment vars.
    # https://support.shotgunsoftware.com/hc/en-us/articles/219039748-Photoshop#If%20the%20engine%20does%20not%20start
    SHOTGUN_ADOBE_HEARTBEAT_INTERVAL = os.environ.get(
        "SHOTGUN_ADOBE_HEARTBEAT_INTERVAL",
        os.environ.get(
            "SGTK_PHOTOSHOP_HEARTBEAT_INTERVAL",
            1.0,
        )
    )
    SHOTGUN_ADOBE_HEARTBEAT_TOLERANCE = os.environ.get(
        "SHOTGUN_ADOBE_HEARTBEAT_TOLERANCE",
        os.environ.get(
            "SGTK_PHOTOSHOP_HEARTBEAT_TOLERANCE",
            2,
        ),
    )
    SHOTGUN_ADOBE_NETWORK_DEBUG = (
        "SGTK_PHOTOSHOP_NETWORK_DEBUG" in os.environ or
        "SHOTGUN_ADOBE_NETWORK_DEBUG" in os.environ
    )

    TEST_SCRIPT_BASENAME = "run_tests.py"

    _COMMAND_UID_COUNTER = 0
    _LOCK = threading.Lock()
    _FAILED_PINGS = 0
    _DIALOG_PARENT = None

    ##########################################################################################
    # context changing

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change has occurred. This will trigger the
        new state to be sent to the Adobe CC host application.

        :param old_context: The previous context.
        :param new_context: The current context.
        """
        self.__send_state()

    ##########################################################################################
    # engine initialization

    def pre_app_init(self):
        self.__tk_adobecc = self.import_module("tk_adobecc")

        # TODO: We need to pass across id,name,displayname and have a
        # property for each. Like this: AEFT,aftereffects,After Effects
        self._app_id = self.SHOTGUN_ADOBE_APPID

        # get the adobe instance. it may have been initialized already by a
        # previous instance of the engine. if not, initialize a new one.
        self._adobe = self.__tk_adobecc.AdobeBridge.get_or_create(
            identifier=self.instance_name,
            port=self.SHOTGUN_ADOBE_PORT,
            logger=self.logger,
            network_debug=self.SHOTGUN_ADOBE_NETWORK_DEBUG,
        )

        self.logger.debug("Network debug logging is %s" % self._adobe.network_debug)

        self.logger.debug("%s: Initializing..." % (self,))
        self.__qt_dialogs = []

        self.adobe.logging_received.connect(self._handle_logging)
        self.adobe.command_received.connect(self._handle_command)
        self.adobe.run_tests_request_received.connect(self._run_tests)
        self.adobe.state_requested.connect(self.__send_state)

        self.__qt_dialogs = []

    def post_app_init(self):

        # ---- register common engine commands

        # register the "Jump to Shotgun" command
        sg_icon = os.path.join(self.disk_location, "resources", "shotgun_logo.png")
        self.register_command(
            "Jump to Shotgun",
            self._jump_to_sg,
            {
                "description": "Open the current Shotgun context in your web browser.",
                "type": "context_menu",
                "short_name": "jump_to_sg",
                "icon": sg_icon,
            }
        )

        # register the "Jump to File System" command
        fs_icon = os.path.join(self.disk_location, "resources", "shotgun_folder.png")
        self.register_command(
            "Jump to File System",
            self._jump_to_fs,
            {
                "description": "Open the current Shotgun context in your file browser.",
                "type": "context_menu",
                "short_name": "jump_to_fs",
                "icon": fs_icon,
            }
        )

        # list the registered commands for debugging purposes
        self.logger.debug("Registered Commands:")
        for (command_name, value) in self.commands.iteritems():
            self.logger.debug(" %s: %s" % (command_name, value))

        # list the registered panels for debugging purposes
        self.logger.debug("Registered Panels:")
        for (panel_name, value) in self.panels.iteritems():
            self.logger.debug(" %s: %s" % (panel_name, value))

        # TODO: log user attribute metric

    def post_qt_init(self):
        from sgtk.platform.qt import QtCore

        # since this is running in our own Qt event loop, we'll use the bundled
        # dark look and feel. breaking encapsulation to do so.
        self.logger.debug("Initializing default styling...")
        self._initialize_dark_look_and_feel()

        # setup the check connection timer.
        self._check_connection_timer = QtCore.QTimer(
            parent=QtCore.QCoreApplication.instance(),
        )

        self._check_connection_timer.timeout.connect(self._check_connection)

        # The class variable is in seconds, so multiply to get milliseconds.
        self._check_connection_timer.start(
            self.SHOTGUN_ADOBE_HEARTBEAT_INTERVAL * 1000.0,
        )

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
        QtCore.QCoreApplication.instance().quit()

    def _check_connection(self):
        try:
            self.adobe.ping()
        except Exception:
            if self._FAILED_PINGS >= self.SHOTGUN_ADOBE_HEARTBEAT_TOLERANCE:
                self.disconnected()
            else:
                self._FAILED_PINGS += 1
        else:
            self._FAILED_PINGS = 0

            # Will allow queued up messages (like logging calls)
            # to be handled on the Python end.
            self.adobe.process_new_messages()

    def _emit_log_message(self, handler, record):
        """
        Called by the engine whenever a new log message is available.

        All log messages from the toolkit logging namespace will be passed to
        this method.

        :param handler: Log handler that this message was dispatched from
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Std python logging record
        :type record: :class:`~python.logging.LogRecord`
        """

        # we don't use the handler's format method here because the adobe side
        # expects a certain format.
        msg_str = "\n%s: [%s] %s\n" % (record.levelname, record.name, record.message)

        sys.stdout.write(msg_str)
        sys.stdout.flush()

    def _handle_command(self, uid):
        """
        Handles an RPC engine command execution request.

        :param int uid: The unique id of the engine command to run.
        """
        from sgtk.platform.qt import QtGui

        for command in self.commands.values():
            if command.get("properties", dict()).get("uid") == uid:
                result = command["callback"]()
                if isinstance(result, QtGui.QWidget):
                    self.__qt_dialogs.append(result)

    def _handle_logging(self, level, message):
        """
        Handles an RPC logging request.

        :param str level: One of "debug", "info", "warning", or "error".
        :param str message: The log message.
        """
        command_map = dict(
            debug=self.logger.debug,
            error=self.logger.error,
            info=self.logger.info,
            warn=self.logger.warning,
        )

        # TODO: figure out how to add this back in. this will end up back in
        #       _emit_log_message which will send back to js.
        #if level in command_map:
        #    # native logging from Python.
        #    command_map[level]("[ADOBE] %s" % message)

    def _run_tests(self):
        """
        Runs the test suite for the tk-adobecc bundle.
        """
        # If we don't know what the tests root directory path is
        # via the environment, then we shouldn't be here.
        try:
            tests_root = os.environ["SHOTGUN_ADOBECC_TESTS_ROOT"]
        except KeyError:
            self.logger.error(
                "The SHOTGUN_ADOBECC_TESTS_ROOT environment variable "
                "must be set to the root directory of the tests to be "
                "run. Not running tests!"
            )
            return
        else:
            # Make sure we can find the run_tests.py file within the root
            # that was specified in the environment.
            self.logger.debug("Test root path found. Looking for run_tests.py.")
            test_module = os.path.join(tests_root, self.TEST_SCRIPT_BASENAME)

            if not os.path.exists(test_module):
                self.logger.error(
                    "Unable to find run_tests.py in the directory "
                    "specified by the SHOTGUN_ADOBECC_TESTS_ROOT "
                    "environment variable. Not running tests!"
                )
                return

        self.logger.debug("Found run_tests.py. Importing to run tests.")

        try:
            # We need to prepend to sys.path. We'll set it back to
            # what it was before once we're done running the tests.
            original_sys_path = sys.path
            python_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "python")
            )

            sys.path = [tests_root, python_root] + sys.path
            import run_tests

            # The run_tests.py module should make available a run_tests
            # function. We need to run that, giving it the engine pointer
            # so that it can use that for logging purposes.
            run_tests.run_tests(self)
        except Exception as exc:
            # If we got an unhandled exception, then something went very
            # wrong in the test suite. We'll just trap that and print it
            # as an error without letting it bubble up any farther.
            import traceback
            self.logger.error(
                "Tests raised the following:\n%s" % traceback.format_exc(exc)
            )
        finally:
            # Reset sys.path back to what it was before we started.
            sys.path = original_sys_path

    ##########################################################################################
    # properties

    @property
    def adobe(self):
        """
        The handle to the Adobe RPC API.
        """
        return self._adobe

    @property
    def app_id(self):
        """
        The runtime app id. This will be a string -- something like
        PHSP for Photoshop, or AEFT for After Effect.
        """
        return self._app_id

    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed by the engine.
        """
        return True

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

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """
        from sgtk.platform.qt import QtGui, QtCore

        if not self._DIALOG_PARENT:
            self._DIALOG_PARENT = QtGui.QWidget(
                parent=QtGui.QApplication.activeWindow(),
            )
            self._DIALOG_PARENT.setWindowFlags(
                self._DIALOG_PARENT.windowFlags() | QtCore.Qt.WindowStaysOnTopHint,
            )

        return self._DIALOG_PARENT

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
            self.logger.error(
                "Sorry, this environment does not support UI display! Cannot "
                "show the requested window '%s'." % title
            )
            return None

        from tank.platform.qt import QtGui, QtCore

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(
            title,
            bundle,
            widget_class,
            *args, **kwargs
        )

        # Note - the base engine implementation will try to clean up
        # dialogs and widgets after they've been closed.  However this
        # can cause a crash in Photoshop as the system may try to send
        # an event after the dialog has been deleted.
        # Keeping track of all dialogs will ensure this doesn't happen
        self.__qt_dialogs.append(dialog)

        # show the dialog:
        dialog.show()

        # make sure the window raised so it doesn't
        # appear behind the main Photoshop window
        dialog.raise_()
        dialog.activateWindow()

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
        if not self.has_ui:
            self.logger.error("Sorry, this environment does not support UI display! Cannot show "
                           "the requested window '%s'." % title)
            return

        from tank.platform.qt import QtGui, QtCore

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(
            title,
            bundle,
            widget_class,
            *args,
            **kwargs
        )

        # Note - the base engine implementation will try to clean up
        # dialogs and widgets after they've been closed.  However this
        # can cause a crash in Photoshop as the system may try to send
        # an event after the dialog has been deleted.
        # Keeping track of all dialogs will ensure this doesn't happen
        self.__qt_dialogs.append(dialog)


        # TODO: we need to test modal app dialogs!
        # TODO: wf2 file open for example
        # TODO: make sure it shows up on top!
        # TODO: if current code doesn't work, try single shot timer to raise after exec_()
        #       confirmed. single shot timer will fire while dialog is shown.
        dialog.raise_()
        dialog.activateWindow()
        status = dialog.exec_()

        return status, widget

    ##########################################################################################
    # logging

    # TODO: logging

    ##########################################################################################
    # internal methods

    def __get_command_uid(self):
        with self._LOCK:
            self._COMMAND_UID_COUNTER += 1
            return self._COMMAND_UID_COUNTER

    def __get_sg_url(self, entity):

        return "%s/detail/%s/%d" % (
            self.sgtk.shotgun_url, entity["type"], entity["id"])

    def __send_state(self):

        # --- process the menu favorites setting

        fav_lookup = {}
        fav_index = 0

        # create a lookup of the combined app instance name with the display name.
        # that should be unique and provide an easy lookup to match against.
        # we'll remember the order processed in order to sort our favorites list
        # once all the registered commands are processed
        for fav_command in self.get_setting("shelf_favorites"):
            app_instance_name = fav_command["app_instance"]
            display_name = fav_command["name"]
            fav_id = app_instance_name + display_name
            fav_lookup[fav_id] = fav_index
            fav_index += 1

        # keep a list of each type of command since they'll be displayed
        # differently on the adobe side.
        favorites = []
        context_menu_cmds = []
        commands = []

        # iterate over all the registered commands and gather the necessary info
        # to display them in adobe
        for (command_name, command_info) in self.commands.iteritems():
            properties = command_info.get("properties", {})

            # ---- determine the app's instance name

            app_instance = properties.get("app", None)
            app_name = None

            # check this command's app against the engine's apps.
            if app_instance:
                for (app_instance_name, app_instance_obj) in self.apps.items():
                    if app_instance_obj == app_instance:
                        app_name = app_instance_name

            cmd_type = properties.get("type", "default")

            # create the command dict to hand over to adobe
            command = dict(
                uid=properties.get("uid"),
                display_name=command_name,
                icon_path=properties.get("icon"),
                description=properties.get("description"),
                type=properties.get("type", "default"),
            )

            # build the lookup string to see if this app is a favorite
            fav_name = str(app_name) + command_name

            if cmd_type == "context_menu":
                context_menu_cmds.append(command)
            elif fav_name in fav_lookup:
                # add the fav index to the command so that we can sort after
                # all favorites are identified.
                command["fav_index"] = fav_lookup[fav_name]
                favorites.append(command)
            else:
                commands.append(command)

        # sort the favorites based on their index
        favorites = sorted(favorites, key=lambda d: d["fav_index"])

        # sort the other commands alphabetically by display name
        commands = sorted(commands, key=lambda d: d["display_name"])

        # sort the context menu commands alphabetically by display name
        context_menu_cmds = sorted(context_menu_cmds, key=lambda d: d["display_name"])

        # ---- process the context for display

        context = self.context
        context_fields = [
            {
                "type": "Site",
                "display": str(context),
                "url": self.sgtk.shotgun_url,
            }
        ]

        # TODO: thumbnail path for current context
        thumbnail_entity = None

        for entity in [context.project, context.entity, context.task]:

            if not entity:
                continue

            entity_type = entity["type"]
            entity_name = entity["name"]
            context_fields.append({
                "type": entity_type,
                "display": entity_name,
                "url": self.__get_sg_url(entity),
            })
            thumbnail_entity = entity

        # ---- populate the state structure to hand over to adobe

        state = {
            "context_fields": context_fields,
            "favorites": favorites,
            "commands": commands,
            "context_menu_cmds": context_menu_cmds,
        }

        self.logger.debug("Sending state: %s" % str(state))
        self.adobe.send_state(state)

    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """

        from sgtk.platform.qt import QtGui, QtCore
        url = self.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


    def _jump_to_fs(self):
        """
        Jump from context to FS
        """

        # launch one window for each location on disk
        paths = self.context.filesystem_locations
        self.logger.debug("FS paths: %s" % (str(paths),))
        for disk_location in paths:

            # get the setting
            system = sys.platform

            # run the app
            if system == "linux2":
                cmd = 'xdg-open "%s"' % disk_location
            elif system == "darwin":
                cmd = 'open "%s"' % disk_location
            elif system == "win32":
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception("Platform '%s' is not supported." % system)

            exit_code = os.system(cmd)
            if exit_code != 0:
                self.logger.error("Failed to launch '%s'!" % cmd)
