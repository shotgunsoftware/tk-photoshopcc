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
sys.dont_write_bytecode = True

import logging
import os
import traceback

# NOTE: this module becomes available once the plugin is built
from sgtk_plugin_basic_photoshopcc import manifest

# exit status codes used when the python process dies. these are known by the
# js process that spawned python so they can be used as a primitive form of
# communication.
EXIT_STATUS_CLEAN = 0
EXIT_STATUS_ERROR = 100
EXIT_STATUS_NO_PYSIDE = 101

class _BootstrapLogHandler(logging.StreamHandler):
    """
    Manually flushes emitted records for js to pickup.
    """

    def emit(self, record):
        """
        Forwards the record back to to js via the engine communicator.

        :param record: The record to log.
        """
        super(_BootstrapLogHandler, self).emit(record)

        # always flush to ensure its seen by the js process
        self.flush()


def get_sgtk_logger(sgtk):
    """
    Sets up a log handler and logger.

    :param sgtk: An sgtk module reference.

    :returns: A logger and log handler.
    """

    # add a custom handler to the root logger so that all toolkit log messages
    # are forwarded back to python via the communicator
    bootstrap_log_formatter = logging.Formatter("%(levelname)s: %(message)s")
    bootstrap_log_handler = _BootstrapLogHandler()
    bootstrap_log_handler.setFormatter(bootstrap_log_formatter)

    if manifest.debug_logging:
        bootstrap_log_handler.setLevel(logging.DEBUG)
    else:
        bootstrap_log_handler.setLevel(logging.INFO)

    # now get a logger to use during bootstrap
    sgtk_logger = sgtk.LogManager.get_logger("%s.%s" % (engine_name, "bootstrap"))
    sgtk.LogManager().initialize_custom_handler(bootstrap_log_handler)

    # allows for debugging to be turned on by the plugin build process
    sgtk.LogManager().global_debug = manifest.debug_logging

    # initializes the file where logging output will go
    sgtk.LogManager().initialize_base_file_handler(engine_name)
    sgtk_logger.debug("Log dir: %s" % (sgtk.LogManager().log_folder))

    return sgtk_logger, bootstrap_log_handler


def progress_handler(value, message):
    """
    Writes the progress values in a special format that can be intercepted by
    the panel during load.

    :param value: A float (0-1) value representing startup progress percentage.
    :param message: A message that indicates what is happening during startup.
    """

    # A three part message separated by "|" to help indicate boundaries. The
    # panel will intercept logged strings of this format and translate them
    # to the display.
    sys.stdout.write("|PLUGIN_BOOTSTRAP_PROGRESS,%s,%s|" % (value, message))
    sys.stdout.flush()


def bootstrap(root_path, port, engine_name, app_id):

    # set the port in the env so that the engine can pick it up. this also
    # allows engine restarts to find the proper port.
    os.environ["SHOTGUN_ADOBE_PORT"] = port

    # set the application id in the environment. This will allow the engine
    # to know what host runtime it's in -- Photoshop, AE, etc.
    os.environ["SHOTGUN_ADOBE_APPID"] = app_id

    # do the toolkit bootstrapping. this will replace the core imported via the
    # sys path with the one specified via the resolved config. it will startup
    # the engine and make Qt available to us.
    if os.environ.get("TANK_CONTEXT") and os.environ.get("TANK_ENGINE"):
        toolkit_traditional_bootstrap()
    else:
        toolkit_plugin_bootstrap(root_path, engine_name)

    # core may have been swapped. import sgtk
    import sgtk

    # get a handle on the newly bootstrapped engine
    engine = sgtk.platform.current_engine()

    from sgtk.platform.qt import QtGui

    app_name = 'Shotgun Engine for Photoshop CC'

    # create and set up the Qt app. we don't want the app to close when the
    # last window is shut down since it's running in parallel to the CC product.
    # We'll manage shutdown
    app = QtGui.QApplication([app_name])

    # the icon that will display for the python process in the dock/task bar
    app_icon = QtGui.QIcon(os.path.join(root_path, "icon_256.png"))

    # set up the QApplication
    app.setApplicationName(app_name)
    app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(False)

    # some operations can't be done until a qapplication exists.
    engine.post_qt_init()

    # log metrics for the app name and version
    engine.log_user_attribute_metric(
        "%s Version" % engine.adobe.app.name,
        engine.adobe.app.version
    )

    # debug logging for the app name/version as well
    engine.logger.debug("Adobe CC Product: %s" % engine.adobe.app.name)
    engine.logger.debug("Adobe CC Version: %s" % engine.adobe.app.version)

    # log the build date of the plugin itself
    engine.logger.debug("Shotgun plugin build date: %s" % manifest.BUILD_DATE)

    # once the event loop starts, the bootstrap process is complete and
    # everything should be connected. this is a blocking call, so nothing else
    # can happen afterward.
    print "Starting Qt event loop..."
    sys.exit(app.exec_())


def toolkit_plugin_bootstrap(root_path, engine_name):
    """
    Business logic for bootstrapping toolkit as a plugin.
    """
    # setup the path to make toolkit importable
    tk_core_path = manifest.get_sgtk_pythonpath(root_path)
    sys.path.append(tk_core_path)

    # once the path is setup, this should be valid
    import sgtk

    # ---- setup logging

    sgtk_logger, log_handler = get_sgtk_logger(sgtk)

    sgtk_logger.debug("Toolkit core path: %s" % (tk_core_path,))
    sgtk_logger.debug("Added bootstrap log hander to root logger...")

    # set up the toolkit boostrap manager
    toolkit_mgr = sgtk.bootstrap.ToolkitManager()
    toolkit_mgr.plugin_id = manifest.plugin_id
    toolkit_mgr.base_configuration = manifest.base_configuration
    toolkit_mgr.bundle_cache_fallback_paths = [os.path.join(root_path, "bundle_cache")]
    toolkit_mgr.progress_callback = progress_handler
    sgtk_logger.debug("Toolkit Manager: " + str(toolkit_mgr))

    # the engine name comes from the adobe side. it will be tk-<name> where
    # <name> is the name of the CC product in use. ex: tk-photoshop,
    # tk-aftereffects, etc. The manager uses the engine name to locate the
    # engine/app configuration to bootstrap into within the current context.
    sgtk_logger.info("Bootstrapping toolkit...")
    toolkit_mgr.bootstrap_engine(engine_name, entity=None)

    # ---- tear down logging

    sgtk.LogManager().root_logger.removeHandler(log_handler)
    sgtk_logger.debug("Removed bootstrap log handler from root logger...")

    sgtk_logger.info("Toolkit Bootstrapped!")


def toolkit_traditional_bootstrap():
    """
    Business logic for bootstrapping toolkit as a traditional setup..
    """
    import sgtk

    # ---- setup logging

    sgtk_logger, log_handler = get_sgtk_logger(sgtk)
    sgtk_logger.info("TANK_CONTEXT and TANK_ENGINE variables found.")

    # Deserialize the Context object and use that when starting
    # the engine.
    context = sgtk.context.deserialize(os.environ["TANK_CONTEXT"])
    engine_name = os.environ["TANK_ENGINE"]

    sgtk_logger.info(
        "Starting %s using context %s..." % (engine_name, context)
    )
    engine = sgtk.platform.start_engine(engine_name, context.tank, context)

    # ---- tear down logging

    sgtk.LogManager().root_logger.removeHandler(log_handler)
    sgtk_logger.debug("Removed bootstrap log handler from root logger...")

    sgtk_logger.info("Toolkit Bootstrapped!")


# executed from javascript
if __name__ == "__main__":

    # the communication port is supplied by javascript. the toolkit engine
    # env to bootstrap into is also supplied by javascript
    (port, engine_name, app_id) = sys.argv[1:4]

    try:
        # first, make sure we can import PySide. If not, there's no need to
        # continue.
        from PySide import QtCore, QtGui
    except ImportError:
        sys.stdout.write("ERROR: %s" % (traceback.format_exc(),))
        sys.stdout.flush()
        sys.exit(EXIT_STATUS_NO_PYSIDE)

    # wrap the entire plugin boostrap process so that we can respond to any
    # errors and display them in the panel.
    try:
        # root path is the 'sgtk' directory 2 levels up from this file
        root_path = os.path.dirname(os.path.dirname(__file__))

        # startup the plugin which includes setting up the socket io client,
        # bootstrapping the engine, and starting the Qt event loop
        bootstrap(root_path, port, engine_name, app_id)
    except Exception, e:
        sys.stdout.write("ERROR: %s" % (traceback.format_exc(),))
        sys.stdout.flush()
        sys.exit(EXIT_STATUS_ERROR)

