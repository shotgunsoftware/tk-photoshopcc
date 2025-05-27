# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import os

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCImagePublishPlugin(HookBaseClass):
    """
    Plugin for publishing an image exported from the current Photoshop document.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_document.py"

    """

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """
        Export the Photoshop document as an image and publish it to Shotgun.
        The image format will be setup using the Publish plugin settings.
        """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.
        A dictionary on the following form::
            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }
        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        # inherit the settings from the base publish plugin
        base_settings = super(PhotoshopCCImagePublishPlugin, self).settings or {}

        # settings specific to this class
        plugin_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Export Settings": {
                "type": "dict",
                "default": {},
                "description": "Photoshop export image options.",
            },
        }

        # update the base settings
        base_settings.update(plugin_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.
        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["photoshop.document.export"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.
        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:
            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: dictionary with boolean keys accepted, required and enabled
        """

        document = item.parent.properties.get("document")
        if not document:
            self.logger.warn("Could not determine the document for item")
            return {"accepted": False}

        # need to make sure we have access to the export method within tk-framework-adobe
        # this is an ugly way to do it but hasattr() return True in any case
        if "export_image" not in dir(self.parent.engine.adobe):
            self.logger.warning(
                "Couldn't find the export_image() method within tk-framework-adobe. "
                "Please update the framework if you want to use this functionality."
            )
            return {"accepted": False}

        return {"accepted": True, "checked": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        document = item.parent.properties["document"]
        path = _document_path(document)
        template_name = settings["Publish Template"].value

        # ---- ensure the Export settings contains at least a "format" key
        if (
            not settings["Export Settings"].value
            or "format" not in settings["Export Settings"].value.keys()
        ):
            self.logger.error(
                "The 'Export Settings' must not be empty and contain at least a 'format' key."
            )
            return False

        # ---- ensure the session has been saved

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The Photoshop session has not been saved."
            self.logger.error(error_msg, extra=_get_save_as_action())
            raise Exception(error_msg)

        # get the normalized path
        path = sgtk.util.ShotgunPath.normalize(path)

        if template_name:
            # ensure the publish template is defined and valid and that we also have
            publish_template = publisher.get_template_by_name(template_name)
            if not publish_template:
                self.logger.error(
                    "The valid publish template could not be determined for the "
                    "export image item."
                )
                return False

            item.local_properties.publish_template = publish_template

            # get the configured work file template
            work_template = item.parent.properties.get("work_template")
            if not work_template:
                self.logger.error(
                    "A work template is required for the session item in order "
                    "to publish document as image"
                )
                return False

            # get the current scene path and extract fields from it using the work
            # template:
            work_fields = work_template.get_fields(path)

            # ensure the fields work for the publish template
            missing_keys = publish_template.missing_keys(work_fields)
            if missing_keys:
                error_msg = (
                    "Work file '%s' missing keys required for the "
                    "publish template: %s" % (path, missing_keys)
                )
                self.logger.error(error_msg)
                raise Exception(error_msg)

            # create the publish path by applying the fields. store it in the item's
            # properties. This is the path we'll create and then publish in the base
            # publish plugin. Also set the publish_path to be explicit.
            # We need to store the data in the item properties in order for the base class validation to be run successfully
            item.local_properties["path"] = publish_template.apply_fields(work_fields)

            # use the work file's version number when publishing
            if "version" in work_fields:
                item.local_properties["publish_version"] = work_fields["version"]
        else:
            item.local_properties["path"] = _get_default_export_filename(
                path,
                settings["Export Settings"].value.get("format").lower(),
            )

        if os.path.exists(item.local_properties["path"]):
            self.logger.error(
                'The "{filename}" file already exists on disk'.format(
                    filename=os.path.basename(item.local_properties["path"]),
                )
            )
            return False

        item.local_properties["publish_path"] = item.local_properties["path"]

        # run the base class validation
        return super().validate(settings, item)

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent
        engine = publisher.engine
        document = item.parent.properties["document"]
        path = sgtk.util.ShotgunPath.normalize(_document_path(document))

        # as we cannot rely on properties to hold the publish path, build it from scratch
        template_name = settings["Publish Template"].value
        if template_name:
            publish_template = publisher.get_template_by_name(template_name)
            work_template = item.parent.properties.get("work_template")
            work_fields = work_template.get_fields(path)

            item.local_properties["path"] = publish_template.apply_fields(work_fields)
        else:
            item.local_properties["path"] = _get_default_export_filename(
                path,
                settings["Export Settings"].value.get("format").lower(),
            )

        item.local_properties["publish_path"] = item.local_properties["path"]

        # export the file as png
        engine.adobe.export_image(
            document, item.local_properties["path"], settings["Export Settings"].value
        )
        item.set_thumbnail_from_path(item.local_properties["path"])

        # Now that the path has been generated, hand it off to the
        super().publish(settings, item)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        img_format = settings["Export Settings"].value.get("format")
        self.logger.info(f"{img_format} Image exported and published to FPTR")


def _get_default_export_filename(filename, export_format):
    (basename, ext) = os.path.splitext(filename)

    ext = "jpg" if export_format == "jpeg" else export_format

    return f"{basename}.{ext}"


def _get_save_as_action(document):
    """
    Simple helper for returning a log action dict for saving the document
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = lambda: engine.save_as(document)

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current document",
            "callback": callback,
        }
    }


def _document_path(document):
    """
    Returns the path on disk to the supplied document. May be ``None`` if the
    document has not been saved.
    """

    try:
        path = document.fullName.fsName
    except Exception:
        path = None

    return path
