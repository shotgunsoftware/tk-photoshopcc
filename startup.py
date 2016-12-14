# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk import TankError
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation

class AdobeCCLauncher(SoftwareLauncher):
    """
    Handles launching Adobe CC executables.
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
        # Look for executables in paths formerly specified by the
        # default configuration paths.yml file.
        sw_versions = self._default_path_software_versions(
            versions,
            display_name,
            icon,
        )
        if not sw_versions:
            self.logger.info(
                "Unable to determine available SoftwareVersions for engine %s" %
                self.engine_name
            )
            return []

        return sw_versions

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch Maya in that will automatically
        load Toolkit and the tk-maya engine when Maya starts.

        :param str exec_path: Path to Maya executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on launch.
        :returns: :class:`LaunchInformation` instance
        """
        required_env = {}

        # Run the engine's userSetup.py file when Maya starts up
        # by appending it to the env PYTHONPATH.
        startup_path = os.path.join(self.disk_location, "startup")
        sgtk.util.append_path_to_env_var("PYTHONPATH", startup_path)
        required_env["PYTHONPATH"] = os.environ["PYTHONPATH"]

        # Check the engine settings to see whether any plugins have been
        # specified to load.
        load_plugins = self.get_setting("launch_builtin_plugin") or None
        if load_plugins:
            # Parse the specified comma-separated list of plugins
            find_plugins = [p.strip() for p in load_plugins.split(",") if p.strip()]
            self.logger.debug(
                "Plugins found from 'launch_builtin_plugins' string value "
                "split by ',': %s" % find_plugins
            )

            # Keep track of the specific list of Toolkit plugins to load when
            # launching Maya. This list is passed through the environment and
            # used by the startup/userSetup.py file.
            load_maya_plugins = []

            # Add Toolkit plugins to load to the MAYA_MODULE_PATH environment
            # variable so the Maya loadPlugin command can find them.
            maya_module_paths = os.environ.get("MAYA_MODULE_PATH") or []
            if maya_module_paths:
                maya_module_paths = maya_module_paths.split(os.pathsep)

            for find_plugin in find_plugins:
                load_plugin = os.path.join(
                    self.disk_location, "plugins", find_plugin
                )
                if os.path.exists(load_plugin):
                    # If the plugin path exists, add it to the list of MAYA_MODULE_PATHS
                    # so Maya can find it and to the list of SGTK_LOAD_MAYA_PLUGINS so
                    # the startup's userSetup.py file knows what plugins to load.
                    self.logger.info("Loading builtin plugin '%s'" % load_plugin)
                    load_maya_plugins.append(load_plugin)
                    if load_plugin not in maya_module_paths:
                        maya_module_paths.append(load_plugin)
                else:
                    # Report the missing plugin directory
                    self.logger.warning("Resolved plugin path '%s' does not exist!" %
                        load_plugin
                    )

            # Add MAYA_MODULE_PATH and SGTK_LOAD_MAYA_PLUGINS to the launch
            # environment.
            required_env["MAYA_MODULE_PATH"] = os.pathsep.join(maya_module_paths)
            required_env["SGTK_LOAD_MAYA_PLUGINS"] = os.pathsep.join(load_maya_plugins)

            # Add additional variables required by the plugins to the launch
            # environment
            (entity_type, entity_id) = _extract_entity_from_context(self.context)
            required_env["SHOTGUN_SITE"] = self.sgtk.shotgun_url
            required_env["SHOTGUN_ENTITY_TYPE"] = entity_type
            required_env["SHOTGUN_ENTITY_ID"] = str(entity_id)
        else:
            # Prepare the launch environment with variables required by the
            # classic bootstrap approach.
            self.logger.info("Preparing Maya Launch via Toolkit Classic methodology ...")
            required_env["SGTK_ENGINE"] = self.engine_name
            required_env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)

        if file_to_open:
            # Add the file name to open to the launch environment
            required_env["SGTK_FILE_TO_OPEN"] = file_to_open

        return LaunchInformation(exec_path, args, required_env)

    ##########################################################################################
    # private methods

    def _default_path_software_versions(self, versions=None, display_name=None, icon=None):
        """
        Creates SoftwareVersion instances based on the path values used
        in the default configuration paths.yml environment.

        :param list versions: (optional) List of strings representing
                              versions to search for. If set to None,
                              search for all versions. A version string
                              is DCC-specific but could be something
                              like "2017", "6.3v7" or "1.2.3.52"
        :param str display_name : (optional) Name to use in graphical
                                  displays to describe the
                                  SoftwareVersions that were found.
        :param icon: (optional) Path to a 256x256 (or smaller) png file
                     to use in graphical displays for every SoftwareVersion
                     found.
        :returns: List of :class:`SoftwareVersion` instances
        """
        adobe_app_name = self.settings.get("adobe_app_name", "Photoshop")

        # Determine a list of paths to search for Maya executables based
        # on default installation path(s) for the current platform
        search_paths = []
        exec_paths = []

        if sys.platform == "darwin":
            search_paths = glob.glob("/Applications/Adobe %s CC*" % adobe_app_name)
        elif sys.platform == "win32":
            search_paths = glob.glob(r"C:\Program Files\Adobe\%s CC*" % adobe_app_name)

        if search_paths:
            for search_path in search_paths:
                # Construct the expected executable name for this path.
                # If it exists, add it to the list of exec_paths to check.
                exec_path = None

                if sys.platform == "darwin":
                    name = os.path.split(search_path)[-1]
                    exec_path = os.path.join(search_path, "%s.app" % name)
                elif sys.platform == "win32":
                    exec_path = os.path.join(search_path, "%s.exe" % adobe_app_name)

                if exec_path and os.path.exists(exec_path):
                    exec_paths.append(exec_path)

        if not exec_paths:
            return []

        sw_versions = []
        pattern = re.compile(r"%s\sCC\s(\d+[.\d]*)" % adobe_app_name)

        for exec_path in exec_paths:
            match = re.search(pattern, exec_path)
            version_number = None

            if match:
                version_number = match.group(1)
            else:
                self.logger.warning(
                    "Unable to determine version number from path: %s" % exec_path
                )
                continue

            if versions and version_number not in versions:
                # If this version isn't in the list of requested versions, skip it.
                self.logger.debug("Skipping %s default version %s ..." %
                    (adobe_app_name, default_version)
                )
                continue

            default_display = "%s CC %s" % (adobe_app_name, version_number)

            # Create a SoftwareVersion using the information from executable
            # path(s) found in default locations.
            self.logger.debug("Creating SoftwareVersion for executable '%s'." %
                exec_path
            )
            sw_versions.append(
                SoftwareVersion(
                    version_number,
                    (display_name or default_display),
                    exec_path,
                    icon,
                )
            )

        return sw_versions
