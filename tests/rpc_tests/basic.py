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

class TestAdobeRPC(unittest.TestCase):
    adobe = None
    resources = None

    @classmethod
    def setUpClass(cls):
        cls.resources = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "resources",
            ),
        )

    def test_simple_eval(self):
        result = self.adobe.rpc_eval("1 + 1")
        self.assertEqual(2, result)

