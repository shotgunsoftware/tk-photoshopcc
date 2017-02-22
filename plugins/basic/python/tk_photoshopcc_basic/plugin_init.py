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
from . import log
from . import constants


def _progress_handler(value, message):
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


def _init_core(plugin_root_path):
    """
    Handles import of core for plugins that are either
    distributed with the engine itself and running as part of
    a larger workflow (basic configuration) where the toolkit core
    is located externally to the plugin, or alternatively workflows
    where the plugin has been built in a fully standalone mode
    where it has no external dependencies and comes bundled with all the things
    it needs.

    :param plugin_root_path: Path to the root of the plugin
    """

    # --- Import Core ---
    #
    # - If we are running the plugin built as a stand-alone unit,
    #   try to retrieve the path to sgtk core and add that to the pythonpath.
    #   When the plugin has been built, there is a sgtk_plugin_basic_photoshopcc
    #   module which we can use to retrieve the location of core and add it
    #   to the pythonpath.
    # - If we are running toolkit as part of a larger zero config workflow
    #   and not from a standalone workflow, we are running the plugin code
    #   directly from the engine folder without a bundle cache and with this
    #   configuration, core already exists in the pythonpath.

    try:
        from sgtk_plugin_basic_photoshopcc import manifest
        running_as_standalone_plugin = True
    except ImportError:
        running_as_standalone_plugin = False

    if running_as_standalone_plugin:
        # Retrieve the Shotgun toolkit core included with the plug-in and
        # prepend its python package path to the python module search path.
        tkcore_python_path = manifest.get_sgtk_pythonpath(plugin_root_path)
        sys.path.insert(0, tkcore_python_path)
        import sgtk

    else:
        # Running as part of the the launch process and as part of zero
        # config. The launch logic that started maya has already
        # added sgtk to the pythonpath.
        import sgtk


def _get_entity_from_environment():
    """
    Look for the standard environment variables SHOTGUN_ENTITY_TYPE
    and SHOTGUN_ENTITY_ID and attempt to extract and validate them.

    :returns: entity dictionary or None to indicate the site config
    """
    import sgtk
    logger = sgtk.LogManager.get_logger(__name__)

    # Retrieve the Shotgun entity type and id when they exist in the environment.
    entity_type = os.environ.get("SHOTGUN_ENTITY_TYPE")
    entity_id = os.environ.get("SHOTGUN_ENTITY_ID")

    if entity_type is None and entity_id is None:
        # nothing here - assume site context
        return None

    if (entity_type and not entity_id) or (not entity_type and entity_id):
        logger.error(
            "Both environment variables SHOTGUN_ENTITY_TYPE and SHOTGUN_ENTITY_ID must be provided "
            "to set a context entity. Shotgun will be initialized in site context."
        )
        return None

    # The entity id must be an integer number.
    try:
        entity_id = int(entity_id)
    except ValueError:
        logger.error("Environment variable SHOTGUN_ENTITY_ID value '%s' is not an integer number. "
                     "Shotgun will be initialized in site context." % entity_id)
        return None

    return {"type": entity_type, "id": entity_id}


def toolkit_plugin_bootstrap(plugin_root_path):
    """
    Business logic for bootstrapping toolkit as a plugin.

    :param plugin_root_path: Path to the root of the plugin
    """

    # import sgtk and handle cases both when the plugin
    # is running as part of a larger zero config workflow
    # and when it is running completely standalone
    _init_core(plugin_root_path)

    import sgtk
    logger = sgtk.LogManager.get_logger(__name__)

    # ---- setup logging
    log_handler = log.get_sgtk_logger(sgtk)
    logger.debug("Added bootstrap log hander to root logger...")

    # set up the toolkit bootstrap manager

    # todo: For standalone workflows, need to handle authentication here
    #       this includes workflows for logging in and out (see maya plugin).
    #       For now, assume that we are correctly authenticated.
    #       Also, need to check that the SHOTGUN_SITE env var matches
    #       the currently logged in site.

    toolkit_mgr = sgtk.bootstrap.ToolkitManager()
    toolkit_mgr.plugin_id = constants.PLUGIN_ID
    toolkit_mgr.base_configuration = constants.BASE_CONFIGURATION

    # when we have a plugin that was built for standalone use, it will contain
    # a complete set of apps in the bundle cache
    toolkit_mgr.bundle_cache_fallback_paths = [os.path.join(plugin_root_path, "bundle_cache")]

    toolkit_mgr.progress_callback = _progress_handler
    logger.debug("Toolkit Manager: %s" % toolkit_mgr)

    entity = _get_entity_from_environment()
    logger.debug("Will launch the engine with entity: %s" % entity)

    logger.info("Bootstrapping toolkit...")
    toolkit_mgr.bootstrap_engine("tk-photoshopcc", entity=entity)

    # ---- tear down logging
    sgtk.LogManager().root_logger.removeHandler(log_handler)
    logger.debug("Removed bootstrap log handler from root logger...")

    logger.info("Toolkit Bootstrapped!")


