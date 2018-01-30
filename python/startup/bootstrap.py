# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import contextlib
import os
import shutil
import sys
import tempfile
import zipfile

import sgtk
from sgtk.util.filesystem import (
    backup_folder,
    ensure_folder_exists,
    move_folder,
)

logger = sgtk.LogManager.get_logger(__name__)


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
    # make sure the extension is properly installed
    ensure_extension_up_to_date()
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

    # set the interpreter with which to launch the CC integration
    env["SHOTGUN_ADOBE_PYTHON"] = sys.executable

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
    env["PYTHONPATH"] = os.environ["PYTHONPATH"]

    return env


def ensure_extension_up_to_date():
    """
    Carry out the necessary operations needed in order for the
    photoshop extension to be recognized.

    This inlcudes copying the extension from the engine location
    to a OS-specific location.
    """

    # the basic plugin needs to be installed in order to launch the adobe
    # engine. we need to make sure the plugin is installed and up-to-date.
    # will only run if SHOTGUN_ADOBE_DISABLE_AUTO_INSTALL is not set.
    if not "SHOTGUN_ADOBE_DISABLE_AUTO_INSTALL" in os.environ:
        logger.debug("Ensuring adobe extension is up-to-date...")
        try:
            _ensure_extension_up_to_date()
        except Exception, e:
            import traceback
            exc = traceback.format_exc()
            raise Exception(
                "There was a problem ensuring the Adobe integration extension "
                "was up-to-date with your toolkit engine. If this is a "
                "recurring issue please contact support@shotgunsoftware.com. "
                "The specific error message encountered was:\n'%s'." % (exc,)
            )




def _ensure_extension_up_to_date():
    """
    Ensure the basic adobe extension is installed in the OS-specific location
    and that it matches the extension bundled with the installed engine.
    """

    extension_name = "com.sg.basic.ps"

    # the CEP install directory is OS-specific
    if sys.platform == "win32":
        app_data = os.getenv("APPDATA")
    elif sys.platform == "darwin":
        app_data = os.path.expanduser("~/Library/Application Support")
    else:
        raise Exception("This engine only runs on OSX & Windows.")

    # the adobe CEP install directory. This is where the extension is stored.
    adobe_cep_dir = os.path.join(app_data, "Adobe", "CEP", "extensions")
    logger.debug("Adobe CEP extension dir: %s" % (adobe_cep_dir,))

    # make sure the directory exists. create it if not.
    if not os.path.exists(adobe_cep_dir):
        logger.debug("Extension folder does not exist. Creating it.")
        ensure_folder_exists(adobe_cep_dir)

    # get the path to the installed engine's .zxp file. the extension_name file i
    # is 3 levels up from this file.
    bundled_ext_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            "%s.zxp" % (extension_name,)
        )
    )

    if not os.path.exists(bundled_ext_path):
        raise Exception(
            "Could not find bundled extension. Expected: '%s'" %
            (bundled_ext_path,)
        )

    # now get the version of the bundled extension
    version_file = "%s.version" % (extension_name,)

    bundled_version_file_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            version_file
        )
    )

    if not os.path.exists(bundled_version_file_path):
        raise Exception(
            "Could not find bundled version file. Expected: '%s'" %
            (bundled_version_file_path,)
        )

    # get the bundled version from the version file
    with open(bundled_version_file_path, "r") as bundled_version_file:
        bundled_version = bundled_version_file.read().strip()

    # check to see if the extension is installed in the CEP extensions directory
    installed_ext_dir = os.path.join(adobe_cep_dir, extension_name)

    # if not installed, install it
    if not os.path.exists(installed_ext_dir):
        logger.debug("Extension not installed. Installing it!")
        _install_extension(bundled_ext_path, installed_ext_dir)
        return

    # ---- already installed, check for udpate

    logger.debug("Bundled extension's version is: %s" % (bundled_version,))

    # get the version from the installed extension's build_version.txt file
    installed_version_file_path = os.path.join(installed_ext_dir, version_file)

    logger.debug(
        "The installed version file path is: %s" %
        (installed_version_file_path,)
    )

    if not os.path.exists(installed_version_file_path):
        logger.debug(
           "Could not find installed version file '%s'. Reinstalling" %
           (installed_version_file_path,)
        )
        _install_extension(bundled_ext_path, installed_ext_dir)
        return

    # the version of the installed extension
    installed_version = None

    # get the installed version from the installed version info file
    with open(installed_version_file_path, "r") as installed_version_file:
        logger.debug("Extracting the version from the installed extension.")
        installed_version = installed_version_file.read().strip()

    if installed_version is None:
        logger.debug("Could not determine version for the installed extension. Reinstalling")
        _install_extension(bundled_ext_path, installed_ext_dir)
        return

    logger.debug("Installed extension's version is: %s" % (installed_version,))

    from sgtk.util.version import is_version_older
    if bundled_version != "dev" and installed_version != "dev":
        if (bundled_version == installed_version or
           is_version_older(bundled_version, installed_version)):

            # the bundled version is the same or older. or it is a 'dev' build
            # which means always install that one.
            logger.debug(
                "Installed extension is equal to or newer than the bundled "
                "build. Nothing to do!"
            )
            return

    # ---- extension in engine is newer. update!

    if bundled_version == "dev":
        logger.debug("Installing the bundled 'dev' version of the extension.")
    else:
        logger.debug(
            "Bundled extension build is newer than the installed extension " +
            "build! Updating..."
        )

    # install the bundled .zxp file
    _install_extension(bundled_ext_path, installed_ext_dir)


def _install_extension(ext_path, dest_dir):
    """
    Installs the supplied extension path by unzipping it directly into the
    supplied destination directory.

    :param ext_path: The path to the .zxp extension.
    :param dest_dir: The CEP extension's destination
    :return:
    """
   
    # move the installed extension to the backup directory
    backup_ext_dir = tempfile.mkdtemp()
    logger.debug("Backing up the installed extension to: %s" % (backup_ext_dir,))
    try:
        backup_folder(dest_dir, backup_ext_dir)
    except Exception:
        shutil.rmtree(backup_ext_dir)
        raise Exception("Unable to create backup during extension update.")

    # now remove the installed extension
    logger.debug("Removing the installed extension directory...")
    try:
        shutil.rmtree(dest_dir)
    except Exception:
        # try to restore the backup
        move_folder(backup_ext_dir, dest_dir)
        raise Exception("Unable to remove the old extension during update.")

    logger.debug(
        "Installing bundled extension: '%s' to '%s'" % (ext_path, dest_dir))

    # make sure the bundled extension exists
    if not os.path.exists(ext_path):
        # retrieve backup before aborting install
        move_folder(backup_ext_dir, dest_dir)
        raise Exception(
            "Expected CEP extension does not exist. Looking for %s" %
            (ext_path,)
        )

    # extract the .zxp file into the destination dir
    with contextlib.closing(zipfile.ZipFile(ext_path, 'r')) as ext_zxp:
        ext_zxp.extractall(dest_dir)

    # if we're here, the install was successful. remove the backup
    try:
        logger.debug("Install success. Removing the backed up extension.")
        shutil.rmtree(backup_ext_dir)
    except Exception:
        # can't remove temp dir. no biggie.
        pass

