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

import sgtk

from . import TestAdobeRPC


class TestPhotoshopRPC(TestAdobeRPC):
    document = None

    @classmethod
    def setUpClass(cls):
        TestAdobeRPC.setUpClass()

        engine = sgtk.platform.current_engine()

        psd_path = os.path.join(cls.resources, "empty.psd")
        engine.logger.info(f"Loading PSD file: {psd_path}")

        file_obj = cls.adobe.File(psd_path)
        cls.document = cls.adobe.app.open(file_obj)

    @classmethod
    def tearDownClass(cls):
        TestAdobeRPC.tearDownClass()
        cls.document.close(
            cls.adobe.SaveOptions.DONOTSAVECHANGES,
        )

    def test_active_document(self):
        self.assertEqual(
            self.document.fullName.path,
            self.adobe.app.activeDocument.fullName.path,
        )

    def test_layer_create_and_delete(self):
        art_layers = self.document.artLayers
        current_layers = art_layers.length

        self.assertTrue(isinstance(current_layers, int))

        art_layers.add()
        self.assertTrue(art_layers.length > current_layers)

        art_layers[0].remove()
        self.assertEqual(art_layers.length, current_layers)
