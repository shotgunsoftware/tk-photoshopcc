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

from .. import TestAdobeRPC

class TestPhotoshopRPC(TestAdobeRPC):

    def setUp(self):
        super(TestPhotoshopRPC, self).setUp()
        self.document = self.adobe.app.open(
            self.adobe.File(os.path.join(self.resources,"empty.psd")),
        )
        self.assertEqual(self.document, self.adobe.activeDocument)

    def test_layer_create_and_delete(self):
        art_layers = self.adobe.activeDocument.artLayers
        current_layers = art_layers.length
        self.assertTrue(isinstance(current_layers, int))
        artLayers.add()
        self.assertTrue(artLayers.length > current_layers)
        artLayers[0].remove()
        self.assertEqual(artLayers.length, current_layers)
