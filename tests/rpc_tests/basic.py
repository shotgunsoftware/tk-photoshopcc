# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import unittest
import os

from tk_adobecc import AdobeBridge
from tk_adobecc.rpc import Communicator

class TestAdobeRPC(unittest.TestCase):

    def setUp(self):
        self.resources = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "resources",
            ),
        )

        # Since we're requiring that these tests be run from
        # within an Adobe product with Shotgun integration active,
        # we can assume that a bridge communicator is already available
        # and use that.
        if not AdobeBrige._REGISTRY:
            raise RuntimeError(
                "These tests must be run from within an Adobe product "
                "with Shotgun integration active."
            )

        identifier = AdobeBridge._REGISTRY.keys()[:1]
        self.adobe = AdobeBridge.get_or_create(identifier)
        self.assertTrue(isinstance(self.adobe, AdobeBridge))
        self.assertTrue(isinstance(self.adobe, Communicator))

    def test_simple_eval(self):
        result = self.adobe.rpc_eval("1 + 1")
        self.assertEqual(2, result)

