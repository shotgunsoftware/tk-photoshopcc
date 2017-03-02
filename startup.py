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

from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation

class PhotoshopLauncher(SoftwareLauncher):
    """
    Handles the launching of Photoshop. Contains the logic for
    scanning for installed versions of the software and
    how to correctly set up a launch environment for the tk-photoshopcc
    engine.
    """

    # Glob strings to insert into the executable template paths when globbing
    # for executables and bundles on disk. Globbing is admittedly limited in
    # terms of specific match strings, but if we need to introduce more precise
    # match strings later, we can do it in one place rather than each of the
    # template paths defined below.
    COMPONENT_GLOB_LOOKUP = {
        "version": "*",
        "version_back": "*",
    }

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    COMPONENT_REGEX_LOOKUP = {
        "version": "(?P<version>[\d.]+)",
        "version_back": "(?P=version)",  # backreference to ensure same version
    }

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string. As Adobe adds modifies the
    # install path on a given OS for a new release, a new template will need
    # to be added here.
    EXECUTABLE_MATCH_TEMPLATES = {
        "darwin": [
            # /Applications/Adobe Photoshop CC 2017/Adobe Photoshop CC 2017.app
            "/Applications/Adobe Photoshop CC {version}/Adobe Photoshop CC {version_back}.app"
        ],
        "win32": [
            # C:\program files\Adobe\Adobe Photoshop CC 2017\Photoshop.exe
            "C:/Program Files/Adobe/Adobe Photoshop CC {version}/Photoshop.exe",
        ],
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

    def _scan_software(self):
        """
        Scan the filesystem for all photoshop executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """

        self.logger.debug("Scanning for photoshop executables...")

        # use the bundled icon
        icon_path = os.path.join(
            self.disk_location,
            "resources",
            "ps_2017_icon_256.png"
        )
        self.logger.debug("Using icon path: %s" % (icon_path,))

        if sys.platform not in self.EXECUTABLE_MATCH_TEMPLATES:
            self.logger.debug("Photoshop not supported on this platform.")
            return []

        # all the executable templates for the current OS
        match_templates = self.EXECUTABLE_MATCH_TEMPLATES[sys.platform]

        # all the discovered executables
        all_sw_versions = []

        for match_template in match_templates:

            # build the glob pattern by formatting the template for globbing
            glob_pattern = match_template.format(**self.COMPONENT_GLOB_LOOKUP)
            self.logger.debug(
                "Globbing for executable matching: %s ..." % (glob_pattern,)
            )

            # now match against files on disk
            executable_paths = glob.glob(glob_pattern)

            self.logger.debug("Found %s matches" % (len(executable_paths),))

            if not executable_paths:
                # no matches. move on to the next template
                continue

            # construct the regex string to extract the components
            regex_pattern = match_template.format(**self.COMPONENT_REGEX_LOOKUP)

            # accumulate the software version objects to return. this will
            # include the head/tail anchors in the regex
            regex_pattern = "^%s$" % (regex_pattern,)

            self.logger.debug(
                "Matching components against regex: %s" % (regex_pattern,))

            # compile the regex
            executable_regex = re.compile(regex_pattern, re.IGNORECASE)

            # now that we have a list of matching executables on disk we can
            # extract the component pieces. iterate over each executable found
            # for the glob pattern and find matched components via the regex
            for executable_path in executable_paths:

                self.logger.debug("Processing path: %s" % (executable_path,))

                match = executable_regex.match(executable_path)

                if not match:
                    self.logger.debug("Path did not match regex.")
                    continue

                # extract the components (default to None if not included). but
                # version is in all templates, so should be there.
                executable_version = match.groupdict().get("version")

                sw_version = SoftwareVersion(
                    executable_version,
                    "Photoshop CC",
                    executable_path,
                    icon_path
                )
                all_sw_versions.append(sw_version)

        return all_sw_versions

