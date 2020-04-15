# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import os
import sys


import sgtk
import sgtk.platform.framework


logger = sgtk.LogManager.get_logger(__name__)


class EngineConfigurationError(sgtk.TankError):
    pass


def bootstrap(engine_name, context, app_path, app_args, **kwargs):
    """
    Interface for older versions of tk-multi-launchapp.

    This is deprecated and now replaced with the ``startup.py`` file
    and ``SoftwareLauncher`` interface.

    Prepares the environment for a tk-photoshopcc bootstrap. This method
    is called directly from the tk-multi-launchapp.

    :param str engine_name: The name of the engine being used -- "tk-photoshopcc"
    :param context: The context to use when bootstrapping.
    :param str app_path: The path to the host application being launched.
    :param str app_args: The arguments to be passed to the host application
                         on launch.

    :returns: The host application path and arguments.
    """
    # get the necessary environment variable for launch
    env = compute_environment()
    # set the environment
    os.environ.update(env)

    # all good to go
    return (app_path, app_args)


def compute_environment():
    """
    Return the env vars needed to launch the photoshop plugin.

    This will generate a dictionary of environment variables
    needed in order to launch the photoshop plugin.

    :returns: dictionary of env var string key/value pairs.
    """
    env = {}

    framework_location = _get_adobe_framework_location()
    if framework_location is None:
        raise EngineConfigurationError(
            "The tk-framework-adobe could not be found in the current environment. Please check the log for more information."
        )

    _ensure_framework_is_installed(framework_location)

    # set the interpreter with which to launch the CC integration
    env["SHOTGUN_ADOBE_PYTHON"] = sys.executable
    env["SHOTGUN_ADOBE_FRAMEWORK_LOCATION"] = framework_location
    env["SHOTGUN_ENGINE"] = "tk-photoshopcc"
    env["PYTHONPATH"] = os.environ["PYTHONPATH"]

    return env


def _get_adobe_framework_location():
    """
    This helper method will query the current disc-location for the configured
    tk-adobe-framework.

    This is necessary, as the the framework relies on an environment variable
    to be set by the parent engine and also the CEP panel to be installed.

    TODO: When the following logic was implemented, there was no way of
        accessing the engine's frameworks at launch time. Once this is
        possible, this logic should be replaced.

    Returns (str or None): The tk-adobe-framework disc-location directory path
        configured under the tk-multi-launchapp
    """

    engine = sgtk.platform.current_engine()
    env_name = engine.environment.get("name")

    env = engine.tank.pipeline_configuration.get_environment(env_name)
    engine_desc = env.get_engine_descriptor("tk-photoshopcc")
    if env_name is None:
        logger.warn(
            (
                "The current environment {!r} "
                "is not configured to run the tk-photohopcc "
                "engine. Please add the engine to your env-file: "
                "{!r}"
            ).format(env, env.disk_location)
        )
        return

    framework_name = None
    for req_framework in engine_desc.get_required_frameworks():
        if req_framework.get("name") == "tk-framework-adobe":
            name_parts = [req_framework["name"]]
            if "version" in req_framework:
                name_parts.append(req_framework["version"])
            framework_name = "_".join(name_parts)
            break
    else:
        logger.warn(
            (
                "The engine tk-photoshopcc must have the "
                "tk-framework-adobe configured in order to run"
            )
        )
        return

    desc = env.get_framework_descriptor(framework_name)
    return desc.get_path()


def _ensure_framework_is_installed(framework_location):
    """
    This method calls the frameworks CEP extension installation
    logic.
    """

    # TODO: The following import should be replaced with
    # a more a call like import_framework, once one has
    # access to the configured frameworks at engine start.
    bootstrap_python_path = os.path.join(framework_location, "python")

    sys.path.insert(0, bootstrap_python_path)
    import tk_framework_adobe_utils.startup as startup_utils

    sys.path.remove(bootstrap_python_path)

    # installing the CEP extension.
    startup_utils.ensure_extension_up_to_date(logger)
