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

var sg_constants = sg_constants || {};

// debug console urls. the ports should correspond to the ports defined in
// the extension's .debug file for the supported CC applications.
sg_constants.product_info = {

    // ---- key'd on app id which is what we have access to in the extensions

    // TODO: consider if this is the best approach...
    // tk_engine_name: translates the app id (like "PHSP") to the expected
    // engine block name (like "tk-photoshop") in a tk configuration.

    // Photoshop
    PHSP: {
        tk_engine_name: "tk-photoshop",
        debug_url: "http://localhost:45216",
    },

    // Photoshop alt
    PHXS: {
        tk_engine_name: "tk-photoshop",
        debug_url: "http://localhost:45217",
    },

    // After Effects

    AEFT: {
        tk_engine_name: "tk-aftereffects",
        debug_url: "http://localhost:45218",
    },

    // NOTE: the debug ports are defined in .debug manifest

};

// This is simply a lookup of panel div ids. The keys of this should never
// change.
sg_constants.panel_div_ids = {
    contents: "sg_panel_contents",
    footer: "sg_panel_footer",
    header: "sg_panel_header",
    progress: "sg_progress",
    progress_bar: "sg_progress_bar",
    progress_label: "sg_progress_label"
};
