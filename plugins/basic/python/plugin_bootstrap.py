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
import time

from sgtk_plugin_basic import manifest

# toolkit logger
sgtk_logger = None

# TODO: switch to a SocketHandler?
class _BootstrapLogHandler(logging.StreamHandler):
    """
    Manually flushes emitted records for js to pickup.
    """

    # always flush to ensure its seen by the js process
    def emit(self, record):
        super(_BootstrapLogHandler, self).emit(record)
        self.flush()

def _add_bootstrap_log_handler(logger):
    """
    Adds a custom stream logger to the supplied logger.
    """

    # prefix messages with "python" and the level name.
    formatter = logging.Formatter("python %(levelname)s: %(message)s")

    # create and add the handler
    handler = _BootstrapLogHandler()
    handler.setLevel(logger.level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def bootstrap_toolkit(root_path):
    """
    Business logic for bootstrapping toolkit.
    """

    tk_core_path = manifest.get_sgtk_pythonpath(root_path)
    sys.path.append(tk_core_path)

    import sgtk

    # ---- setup logging

    sgtk.LogManager().initialize_base_file_handler("tk-adobecc")

    if manifest.debug_logging:
        sgtk.LogManager().global_debug = True

    global sgtk_logger
    sgtk_logger = sgtk.LogManager.get_logger("plugin")

    # add a bootstrap stream handler so that log messages make it back to the
    # js console. TODO: swith this to a socket handler
    _add_bootstrap_log_handler(sgtk_logger)

    sgtk_logger.debug("Toolkit core path: %s" % (tk_core_path,))
    sgtk_logger.debug("Booting up plugin with manifest %s" % manifest.BUILD_INFO)

    # create boostrap manager
    toolkit_mgr = sgtk.bootstrap.ToolkitManager()
    toolkit_mgr.entry_point = manifest.entry_point
    toolkit_mgr.base_configuration = manifest.base_configuration
    toolkit_mgr.bundle_cache_fallback_paths = [os.path.join(root_path, "bundle_cache")]
    sgtk_logger.debug("Toolkit Manager: " + str(toolkit_mgr))

    # bootstrap the engine!
    sgtk_logger.info("Starting the Adobe CC engine.")
    toolkit_mgr.bootstrap_engine("tk-adobecc", entity=None)


# TODO: need to setup server thread on this end to receive messages from the DCC.
#       once we have those, we can respond and shut down when PS closes.
def shutdown_toolkit():
    """
    Shutdown the Shotgun toolkit and its Photoshop engine.
    """
    import sgtk

    # Turn off your engine! Step away from the car!
    engine = sgtk.platform.current_engine()
    if engine:
        engine.destroy()


if __name__ == "__main__":

    # parse the port number from the command line args
    port = sys.argv[1]

    # ---- BOOTSTRAP!!!

    # root path is the 'sgtk' directory 2 levels up from this file
    root_path = os.path.dirname(os.path.dirname(__file__))

    try:
        bootstrap_toolkit(root_path)
    except Exception, e:
        # TODO: temporary communication back to js.
        print "CRITICAL: Shotgun Toolkit failed to bootstrap.\n Error: %s" % (e,)
        sys.stdout.flush()
        sys.exit(1)

    # if we're bootstrapped, this should work!
    import sgtk

    # list the registered commands for debugging purposes
    engine = sgtk.platform.current_engine()
    sgtk_logger.debug("Registered Commands:")
    for (command_name, value) in engine.commands.iteritems():
        sgtk_logger.debug(" %s: %s" % (command_name, value))

    # now that we've bootstrapped, we can import our Application
    from app_integration import AdobeCCPython

    # create global app
    try:
        from sgtk.platform.qt import QtGui
        app = AdobeCCPython(
            port,
            "Shotgun Engine for Adobe CC",
            logger=sgtk_logger,
            icon_path=os.path.join(root_path, "icon_256.png")
        )
    except Exception, e:
        # TODO: send message to display in console
        sgtk_logger.critical(
            "Could not create global PySide app instance."
            " Error: %s" % (e,)
        )
        sys.exit(1)

    sgtk_logger.info("Starting PySide event loop: %s", app)
    sys.exit(app.exec_())

