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
import sys
import re
import glob

import sgtk
from sgtk import TankError
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation

class PhotoshopLauncher(SoftwareLauncher):
    """
    Handles launching Maya executables. Automatically starts up
    a tk-maya engine with the current context in the new session
    of Maya.
    """
    def scan_software(self, versions=None, display_name=None, icon=None):
        """
        Performs a scan for software installations.

        :param list versions: List of strings representing versions
                              to search for. If set to None, search
                              for all versions. A version string is
                              DCC-specific but could be something
                              like "2017", "6.3v7" or "1.2.3.52".
        :param str display_name : (optional) Name to use in graphical
                                  displays to describe the
                                  SoftwareVersions that were found.
        :param icon: (optional) Path to a 256x256 (or smaller) png file
                     to use in graphical displays for every SoftwareVersion
                     found.
        :returns: List of :class:`SoftwareVersion` instances
        """
        self.logger.debug(
            "Scanning for photoshop versions. Versions=%s. Override display name:%s, override icon: %s" % (versions, display_name, icon)
        )

        software_versions = []

        icon_path = os.path.join(self.disk_location, "resources", "ps_2017_icon_256.png")

        if sys.platform == "darwin":
            # /Applications/Adobe Photoshop CC 2017/Adobe Photoshop CC 2017.app
            glob_pattern = "/Applications/Adobe Photoshop CC [0-9][0-9][0-9][0-9]/Adobe Photoshop CC [0-9][0-9][0-9][0-9].app"
            version_regex = re.compile(
                "^/Applications/Adobe Photoshop CC ([0-9]{4})/Adobe Photoshop CC ([0-9]{4})\.app$"
            )

        elif sys.platform == "win32":
            # C:\program files\Adobe\Adobe Photoshop CC 2017\Photoshop.exe
            glob_pattern = "C:\\Program Files\\Adobe\\Adobe Photoshop CC [0-9][0-9][0-9][0-9]\\Photoshop.exe"
            version_regex = re.compile(
                "^C:\\\\Program Files\\\\Adobe\\\\Adobe Photoshop CC ([0-9]{4})\\\\Photoshop.exe$",
                re.IGNORECASE
            )

        else:
            self.logger.debug("Photoshop not supported on this platform.")
            return []

        self.logger.debug("Scanning for photoshop installations in '%s'..." % glob_pattern)
        paths = glob.glob(glob_pattern)

        for path in paths:
            # extract version number
            self.logger.debug("Found photoshop install in '%s'" % path)

            match = version_regex.match(path)
            if match:
                dcc_version = match.group(1)  # extract first group
                display_name = "CC %s" % dcc_version
                software_version = SoftwareVersion(dcc_version, display_name, path, icon_path)
                self.logger.debug("Generated %s" % software_version)
                software_versions.append(software_version)
            else:
                self.logger.warning("Could not extract version number from path '%s'" % path)

        return software_versions


    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch Maya in that will automatically
        load Toolkit and the tk-maya engine when Maya starts.

        :param str exec_path: Path to Maya executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on launch.
        :returns: :class:`LaunchInformation` instance
        """

        # todo - add support for the file_to_open parameter.

        # find the bootstrap script and import it
        bootstrap_python_path = os.path.join(self.disk_location, "python", "startup")
        sys.path.insert(0, bootstrap_python_path)
        import bootstrap

        required_env = bootstrap.compute_environment()
        bootstrap.ensure_extension_up_to_date()

        return LaunchInformation(exec_path, args, required_env)


# def _extract_entity_from_context(context):
#     """
#     Extract an entity type and id from the context.
#
#     :param context:
#     :returns: Tuple (entity_type_str, entity_id_int)
#     """
#     # Use the Project by default
#     entity_type = context.project["type"]
#     entity_id = context.project["id"]
#
#     # if there is an entity then that takes precedence
#     if context.entity:
#         entity_type = context.entity["type"]
#         entity_id = context.entity["id"]
#
#     # and if there is a Task that is even better
#     if context.task:
#         entity_type = context.task["type"]
#         entity_id = context.task["id"]
#
#     return (entity_type, entity_id)