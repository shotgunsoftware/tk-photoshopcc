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
import sgtk

def bootstrap(engine_name, context, app_path, app_args, **kwargs):
    """
    Prepares the environment for a tk-photoshopcc bootstrap.

    :param str engine_name: The name of the engine being used -- "tk-photoshopcc"
    :param context: The context to use when bootstrapping.
    :param str app_path: The path to the host application being launched.
    :param str app_args: The arguments to be passed to the host application
                         on launch.

    :returns: The host application path and arguments.
    """
    os.environ["SHOTGUN_ADOBE_PYTHON"] = sys.executable

    # We're going to append all of this Python process's sys.path to the
    # PYTHONPATH environment variable. This will ensure that we have access
    # to all libraries available in this process in subprocesses like the
    # Python process that is spawned by the Shotgun CEP extension on launch
    # of an Adobe host application. We're appending instead of setting because
    # we don't want to stomp on any PYTHONPATH that might already exist that
    # we want to persist when the Python subprocess is spawned.
    sgtk.util.append_path_to_env_var(
        "PYTHONPATH",
        os.pathsep.join(sys.path),
    )

    return (app_path, app_args)

