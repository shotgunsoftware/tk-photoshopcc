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

import sgtk

# use api json to cover py 2.5
from tank_vendor import shotgun_api3
json = shotgun_api3.shotgun.json

from .rpc import Communicator


class AdobeBridge(Communicator):
    """
    Bridge layer between the adobe product and toolkit.

    This is where we put logic that allows the two ends to communicate.
    """

    def __init__(self, *args, **kwargs):

        super(AdobeBridge, self).__init__(*args, **kwargs)

        self._commands_by_id = {}

    def send_state(self):
        """
        Responsible for forwarding the current SG state to javascript.

        This method knows about the structure of the json that the js side
        expects. We provide display info and we also
        """

        # get the current engine
        engine = sgtk.platform.current_engine()

        # TODO: thumbnail path for current context? query & update if unavailable

        state = {
            "context": {
                "display": str(engine.context),
            },
            "commands": []
        }

        for (command_name, command_info) in engine.commands.iteritems():

            command_id = "command_%s" % (command_name,)

            properties = command_info.get("properties", {})

            command = {
                "id": command_id,
                "display_name": command_name,
                "icon_path": properties.get("icon"),
                "description": properties.get("description")
            }

            state["commands"].append(command)

            self._commands_by_id[command_id] = command_info

        engine.log_debug("Sending state: " + str(state))

        # encode the python dict as json
        json_state = json.dumps(state)

        # TODO: send to javascript
        self._io.emit("set_state", json_state)

