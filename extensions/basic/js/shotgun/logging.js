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
var sg_logging = sg_logging || {};

// ---- Events

// sent from non-panel extensions and received by the panel to log to the
// console available via the panel's flyout menu
sg_event.create_event(sg_logging, "LOG_MESSAGE");

// ---- Interface

sg_logging.debug = function(message) {
    // Debug logging
    sg_logging._log('debug', message);
};

sg_logging.error = function(message) {
    // Error logging
    sg_logging._log('error', message);
};

sg_logging.info = function(message) {
    // Info logging
    sg_logging._log('info', message);
};

sg_logging.log = function(message) {
    // Standard logging
    sg_logging._log('log', message);
};

sg_logging.warn = function(message) {
    // Warning logging
    sg_logging._log('warn', message);
};

sg_logging._log = function(level, message) {

    // send a log message. this should be received and processed by the
    // panel extension. that's where the user will have access to the
    // flyout menu where they can click and go to the console.
    sg_logging.LOG_MESSAGE.emit(
        {
            level: level,
            message: message
        }
    );
};
