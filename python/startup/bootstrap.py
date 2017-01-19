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
import re
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
    Prepares the environment for a tk-adobecc bootstrap.

    :param str engine_name: The name of the engine being used -- "tk-adobecc"
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

    # the basic plugin needs to be installed in order to launch the adobe
    # engine. we need to make sure the plugin is installed and up-to-date.
    # only do this if the SHOTGUN_ADOBE_DEVELOP environment variable is not set.
    if "SHOTGUN_ADOBE_DEVELOP" not in os.environ:
        logger.debug("Ensuring adobe extension is up-to-date...")
        try:
            _ensure_extension_up_to_date(context)
        except Exception, e:
            import traceback
            exc = traceback.format_exc()
            raise Exception(
                "There was a problem ensuring the Adobe integration extension "
                "was up-to-date with your toolkit engine. If this is a "
                "recurring issue please contact support@shotgunsoftware.com. "
                "The specific error message encountered was:\n'%s'." % (exc,)
            )

    return (app_path, app_args)


def _ensure_extension_up_to_date(context):
    """
    Ensure the basic adobe extension is installed in the OS-specific location
    and that it matches the extension bundled with the installed engine.

    :param context:  The context to use when bootstrapping.
    """

    # TODO: will need to rename to photoshopcc probably
    extension_name = "com.shotgunsoftware.basic.adobecc"

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

    # get the path to the installed engine's .zxp file. the extension_name is
    # 3 levels up from this file.
    bundled_ext_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            "%s.zxp" % (extension_name,)
        )
    )

    # check to see if the extension is installed in the CEP extensions directory
    installed_ext_dir = os.path.join(adobe_cep_dir, extension_name)

    # if not installed, install it
    if not os.path.exists(installed_ext_dir):
        logger.debug("Extension not installed. Installing it!")
        _install_extension(bundled_ext_path, installed_ext_dir)
        return

    # ---- already installed, check for udpate

    # first, get the build date from the .zxp's manifest file.

    # note: this is the zip file member specification not a file path. the
    # slashes should work regardless of the current OS.
    bundled_manifest_member = "python/sgtk_plugin_basic_adobecc/manifest.py"

    # the date the bundled .zxp file was built
    bundled_build_date = None

    # access the files within the zxp
    with zipfile.ZipFile(bundled_ext_path, 'r') as ext_zxp:
        logger.debug("Extracting the build date from the bundled .zxp file.")
        # open the manifest file
        bundled_manifest_info = ext_zxp.getinfo(bundled_manifest_member)
        bundled_manifest_file = ext_zxp.open(bundled_manifest_info, "r")
        bundled_build_date = _get_build_date(bundled_manifest_file)

    if bundled_build_date is None:
        raise Exception(
            "Could not determine build date for bundled extension.")

    logger.debug("Bundled extension's build date is: %s" % (bundled_build_date,))

    # get the build date from the installed extension's manifest file
    installed_manifest_path = os.path.join(
        installed_ext_dir,
        "python",
        "sgtk_plugin_basic_adobecc",
        "manifest.py"
    )

    logger.debug("The installed manifest path is: %s" % (installed_manifest_path,))

    if not os.path.exists(installed_manifest_path):
        raise Exception(
            "Could not find installed manifest file '%s'" %
            (installed_manifest_path,)
        )

    # the date the installed extension was built
    installed_build_date = None

    # get the installed build date from the installed manifest file
    with open(installed_manifest_path, "r") as installed_manifest_file:
        logger.debug("Extracting the build date from the installed extension.")
        installed_build_date = _get_build_date(installed_manifest_file)

    if installed_build_date is None:
        raise Exception(
            "Could not determine build date for the installed extension.")

    logger.debug("Installed extension's build date is: %s" % (installed_build_date,))

    if bundled_build_date <= installed_build_date:
        # a newer version is installed. nothing to do here.
        logger.debug(
            "Installed extension is equal to or newer than the bundled build. "
            "Nothing to do!"
        )
        return

    # ---- extension in engine is newer. update!

    logger.debug(
        "Bundled extension build is newer than the installed "
        "extension build! Updating..."
    )

    # move the installed extension to the backup directory
    backup_ext_dir = tempfile.mkdtemp()
    logger.debug("Backing up the installed extension to: %s" % (backup_ext_dir,))
    try:
        backup_folder(installed_ext_dir, backup_ext_dir)
    except Exception:
        shutil.rmtree(backup_ext_dir)
        raise Exception("Unable to create backup during extension update.")

    # now remove the installed extension
    logger.debug("Removing the installed extension directory...")
    try:
        shutil.rmtree(installed_ext_dir)
    except Exception:
        # try to restore the backup
        move_folder(backup_ext_dir, installed_ext_dir)
        raise Exception("Unable to remove the old extension during update.")

    # install the bundled .zxp file
    _install_extension(bundled_ext_path, installed_ext_dir)

    # if we're here, the install was successful. remove the backup
    try:
        logger.debug("Install success. Removing the backed up extension.")
        shutil.rmtree(backup_ext_dir)
    except Exception:
        # can't remove temp dir. no biggie.
        pass

def _install_extension(ext_path, dest_dir):
    """
    Installs the supplied extension path by unzipping it directly into the
    supplied destination directory.

    :param ext_path: The path to the .zxp extension.
    :param dest_dir: The CEP extension's destination
    :return:
    """

    logger.debug(
        "Installing bundled extension: '%s' to '%s'" % (ext_path, dest_dir))

    # make sure the bundled extension exists
    if not os.path.exists(ext_path):
        raise Exception(
            "Expected CEP extension does not exist. Looking for %s" %
            (ext_path,)
        )

    # extract the .zxp file into the destination dir
    with zipfile.ZipFile(ext_path, 'r') as ext_zxp:
        ext_zxp.extractall(dest_dir)


def _get_build_date(manifest_file_object):
    """
    Find the build date within the supplied, open file object.

    :param manifest_file_object:  A file-like object that supports read().
    :return: str build date.
    """

    # The manifest file should include a line that looks like this:
    #   BUILD_DATE="20170118_143247"
    # Find the build date in the manifest file

    manifest_contents = manifest_file_object.read()
    matches = re.search('BUILD_DATE="([\d_]+)"', manifest_contents)
    if matches:
        return matches.group(1)
    else:
        return None
