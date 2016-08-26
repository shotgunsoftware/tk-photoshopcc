# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# don't import this module until bootstrapped
import sgtk
from sgtk.platform.qt import QtGui

class AdobeCCPython(QtGui.QApplication):

    def __init__(self, title, icon_path=None):

        super(AdobeCCPython, self).__init__([title])

        self.setApplicationName(title)
        if icon_path:
            self.setWindowIcon(QtGui.QIcon(icon_path))
        self.setQuitOnLastWindowClosed(False)

        # TODO: setup communication connections here?

