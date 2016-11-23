# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging
import os
import sys
import traceback

# NOTE: this module becomes available once the plugin is built
from sgtk_plugin_basic_adobecc import manifest

# TODO: move this into the engine?
class _PyToJsLogHandler(logging.StreamHandler):
    """
    Manually flushes emitted records for js to pickup.
    """

    # TODO: this needs to be replaced with direct communication with the socket io server.
    #       an instance of the engine name can be supplied and each emit() call can
    #       get the communicator singleton instance in order to forward to js.

    def __init__(self, engine_name):
        """
        Initializes the log handler.

        :param engine_name: The name of the engine being wrapped.
        """
        super(_PyToJsLogHandler, self).__init__()
        self._engine_name = engine_name

    # always flush to ensure its seen by the js process
    def emit(self, record):
        """
        Forwards the record back to to js via the engine communicator.

        :param record: The record to log.
        """
        # TODO: replace these two lines with a call go get the communictor
        #       singleton instance and make a call to its logging method
        super(_PyToJsLogHandler, self).emit(record)
        self.flush()

def plugin_bootstrap(root_path, port, engine_name, app_id):

    # set the port in the env so that the engine can pick it up. this also
    # allows engine restarts to find the proper port.
    os.environ["SHOTGUN_ADOBE_PORT"] = port

    # set the application id in the environment. This will allow the engine
    # to know what host runtime it's in -- Photoshop, AE, etc.
    os.environ["SHOTGUN_ADOBE_APPID"] = app_id

    # do the toolkit bootstrapping. this will replace the core imported via the
    # sys path with the one specified via the resolved config. it will startup
    # the engine and make Qt available to us.
    toolkit_bootstrap(root_path, engine_name)

    # core may have been swapped. import sgtk
    import sgtk

    # get a handle on the newly bootstrapped engine
    engine = sgtk.platform.current_engine()

    from sgtk.platform.qt import QtGui

    app_name = 'Shotgun Engine for Adobe CC'

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

    # once the event loop starts, the bootstrap process is complete and
    # everything should be connected. this is a blocking call, so nothing else
    # can happen afterward.
    print "Starting Qt event loop..."
    sys.exit(app.exec_())


def toolkit_bootstrap(root_path, engine_name):
    """
    Business logic for bootstrapping toolkit.
    """

    # setup the path to make toolkit importable
    tk_core_path = manifest.get_sgtk_pythonpath(root_path)
    sys.path.append(tk_core_path)

    # once the path is setup, this should be valid
    import sgtk

    # ---- setup logging

    # initializes the file where logging output will go
    sgtk.LogManager().initialize_base_file_handler("tk-adobecc")

    # allows for debugging to be turned on by the plugin build process
    sgtk.LogManager().global_debug = manifest.debug_logging

    # add a custom handler to the root logger so that all toolkit log messages
    # are forwarded back to python via the communicator
    py_to_js_formatter = logging.Formatter("%(levelname)s: %(message)s")
    py_to_js_handler = _PyToJsLogHandler(engine_name)
    py_to_js_handler.setFormatter(py_to_js_formatter)
    sgtk.LogManager().initialize_custom_handler(py_to_js_handler)

    # now get a logger use during bootstrap
    sgtk_logger = sgtk.LogManager.get_logger("extension_bootstrap")
    sgtk_logger.debug("Toolkit core path: %s" % (tk_core_path,))

    # set up the toolkit boostrap manager
    toolkit_mgr = sgtk.bootstrap.ToolkitManager()
    toolkit_mgr.plugin_id = manifest.plugin_id
    toolkit_mgr.base_configuration = manifest.base_configuration
    toolkit_mgr.bundle_cache_fallback_paths = [os.path.join(root_path, "bundle_cache")]
    sgtk_logger.debug("Toolkit Manager: " + str(toolkit_mgr))

    # the engine name comes from the adobe side. it will be tk-<name> where
    # <name> is the name of the CC product in use. ex: tk-photoshop,
    # tk-aftereffects, etc. The manager uses the engine name to locate the
    # engine/app configuration to bootstrap into within the current context.
    sgtk_logger.info("Bootstrapping toolkit...")
    toolkit_mgr.bootstrap_engine(engine_name, entity=None)
    sgtk_logger.info("Toolkit Bootstrapped!")


# executed from javascript
if __name__ == "__main__":

    # wrap the entire plugin boostrap process so that we can respond to any
    # errors and display them in the panel.
    try:
        # root path is the 'sgtk' directory 2 levels up from this file
        root_path = os.path.dirname(os.path.dirname(__file__))

        # the communication port is supplied by javascript. the toolkit engine
        # env to bootstrap into is also supplied by javascript
        (port, engine_name, app_id) = sys.argv[1:4]

        # startup the plugin which includes setting up the socket io client,
        # bootstrapping the engine, and starting the Qt event loop
        plugin_bootstrap(root_path, port, engine_name, app_id)
    except Exception, e:
        print "Shotgun Toolkit failed to bootstrap."

        # TODO: possible to communicate this back via socket.io client?
        #       try to get a handle on the instance. if can't just print trace
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)


