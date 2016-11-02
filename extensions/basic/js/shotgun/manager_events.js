// Copyright (c) 2016 Shotgun Software Inc.
//
// CONFIDENTIAL AND PROPRIETARY
//
// This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
// Source Code License included in this distribution package. See LICENSE.
// By accessing, using, copying or modifying this work you indicate your
// agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
// not expressly granted therein are reserved by Shotgun Software Inc.

"use strict";

// namespace
var sg_manager = sg_manager || {};

// typically as an async response to a REQUEST_STATE event from the panel
sg_event.create_event(sg_manager, "UPDATE_STATE");

// emits critical errors whereby the manager is not or can not function properly
sg_event.create_event(sg_manager, "CRITICAL_ERROR");
