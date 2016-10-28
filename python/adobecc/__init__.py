# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# TODO: expose direct CC DOM APIs here
# TODO: factory to return proper API based on current DCC (ps, premiere, etc)
    # TODO: module level log methods?
    # TODO: clear panel
    # TODO: set message in panel
    # TODO: get remote objects/classes
    # TODO: wrap save as

from .rpc import Communicator

# MOCKUPS...
class AdobeCCApplication(object):

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return "<%s - %s>" % (self.__class__, self._name)

class AdobeCCAppFactory(object):

    def get_current_cc_app(self):
        return AdobeCCApplication("photoshop")