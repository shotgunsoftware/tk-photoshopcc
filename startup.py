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

from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


class PhotoshopLauncher(SoftwareLauncher):
    """
    Handles the launching of Photoshop. Contains the logic for
    scanning for installed versions of the software and
    how to correctly set up a launch environment for the tk-photoshopcc
    engine.
    """

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    COMPONENT_REGEX_LOOKUP = {
        "version": "[\d.]+",
        "version_back": "[\d.]+",  # backreference to ensure same version
    }

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string. As Adobe adds modifies the
    # install path on a given OS for a new release, a new template will need
    # to be added here.
    EXECUTABLE_MATCH_TEMPLATES = {
        # /Applications/Adobe Photoshop CC 2017/Adobe Photoshop CC 2017.app
        "darwin": "/Applications/Adobe Photoshop CC {version}/Adobe Photoshop CC {version_back}.app",
        # C:\program files\Adobe\Adobe Photoshop CC 2017\Photoshop.exe
        "win32": "C:/Program Files/Adobe/Adobe Photoshop CC {version}/Photoshop.exe"
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.
        """
        return "2015.5"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch Photoshop so that will automatically
        load Toolkit after startup.

        :param str exec_path: Path to Maya executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on launch.
        :returns: :class:`LaunchInformation` instance
        """
        # todo - add support for the file_to_open parameter.

        # find the bootstrap script and import it.
        # note: all the business logic for how to launch is
        #       located in the python/startup folder to be compatible
        #       with older versions of the launch workflow
        bootstrap_python_path = os.path.join(self.disk_location, "python", "startup")
        sys.path.insert(0, bootstrap_python_path)
        import bootstrap

        # determine all environment variables
        required_env = bootstrap.compute_environment()
        # copy the extension across to the deploy folder
        bootstrap.ensure_extension_up_to_date()

        # Add std context and site info to the env
        std_env = self.get_standard_plugin_environment()
        required_env.update(std_env)

        return LaunchInformation(exec_path, args, required_env)

    def scan_software(self):
        """
        Scan the filesystem for all photoshop executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """

        self.logger.debug("Scanning for photoshop executables...")

        # use the bundled icon
        icon_path = os.path.join(
            self.disk_location,
            "icon_256.png"
        )
        self.logger.debug("Using icon path: %s" % (icon_path,))

        if sys.platform not in self.EXECUTABLE_MATCH_TEMPLATES:
            self.logger.debug("Photoshop not supported on this platform.")
            return []

        all_sw_versions = []

        for executable_path, tokens in self._glob_and_match(
            self.EXECUTABLE_MATCH_TEMPLATES[sys.platform], self.COMPONENT_REGEX_LOOKUP
        ):
            self.logger.debug("Processing %s with tokens %s", executable_path, tokens)
            # extract the components (default to None if not included). but
            # version is in all templates, so should be there.
            executable_version = tokens.get("version")

            sw_version = SoftwareVersion(
                executable_version,
                "Photoshop CC",
                executable_path,
                icon_path
            )
            supported, reason = self._is_supported(sw_version)
            if supported:
                all_sw_versions.append(sw_version)
            else:
                self.logger.debug(reason)

        return all_sw_versions
