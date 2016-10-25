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

// namespace. not to be confused with the Shotgun Panel app.
var sg_panel = sg_panel || {};

// ---------------------------------------------------------------------------
// Module level values

sg_panel.content_frame_id = "content_frame";

// ---------------------------------------------------------------------------
// Module level functions

sg_panel.get_content_document = function() {
    // Returns the document of the content frame of the main page (the iframe
    // where the content is displayed. Used by pages to update their contents
    // dynamically.
    return document.getElementById(sg_panel.content_frame_id).
        contentWindow.document;
};

// ---------------------------------------------------------------------------
// Pages displayed in the panel

sg_panel.AboutPage = new function() {
    // A singleton object representing the about page.

    // path to the page html
    this.path = "about.html";
};

sg_panel.CommandsPage = new function() {
    // A singleton object representing the commands page.

    // ---- private vars

    // The div id of the context section of the page
    var _context_section_id = "sg_context_section";

    // The div id of the commands section of the page
    var _command_section_id = "sg_commands_section";

    // ---- public vars

    // path to the page html
    this.path = "panel.html";

    this.set_context_display = function(context_display) {

        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_context_section_id).innerHTML =
            context_display;
    };

    this.set_commands = function(commands) {
        // Display the supplied commands on the page.

        // XXX Temp implementation for testing.
        var command_html = "";

        for(var i = 0; i < commands.length; i++) {
            var command = commands[i];
            if (command.hasOwnProperty("id") &&
                command.hasOwnProperty("display_name") &&
                command.hasOwnProperty("icon_path")) {
                    var command_id = command["id"];
                    var display_name = command["display_name"];
                    var icon_path = command["icon_path"];
                    var data = {"command_id": command_id};
                    command_html +=
                        "<a href='#' onclick='" +
                            "sg_panel.emit(" +
                                "sg_panel.REGISTERED_COMMAND_TRIGGERED, \"" +
                                encodeURI(JSON.stringify(data)) +
                            "\")" +
                        "'>" +
                        "<img src='" + icon_path + "' width='48'>" + display_name +
                        "</a><br><br>";
            }
        }

        command_html += "";

        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_command_section_id).innerHTML =
            command_html;
    };

};

sg_panel.StatusPage = new function() {
    // A singleton object representing the status page.

    // ---- public vars

    // path to the page html
    this.path = "status.html";

    // ---- private vars

    // keep a handle on the instance.
    var self = this;

    // div ids for the components of the status page
    var _title_div_id = "sg_status_title";
    var _message_div_id = "sg_status_message";
    var _progress_bar_div_id = "sg_status_progress_bar";
    var _progress_div_id = "sg_status_progress";

    // ---- public methods

    this.set_message = function(message) {
        // Set the display message for the status page.

        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_message_div_id).innerHTML = message;

        // log the message
        sg_logging.debug(message)
    };

    this.set_progress = function(percent, message) {
        // Set the percentage of the progress bar

        // make sure the progress bar is shown
        self.show_progress_bar(true);

        // set the progress percentage
        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_progress_div_id).style.width =
            Math.min(percent, 100) + "%";

        // message is optional. if supplied, set the message.
        if (typeof(message) !== "undefined") {
            self.set_message(message)
        }
    };

    this.set_title = function(title) {
        // Set the title for the status page.

        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_title_div_id).innerHTML =
            "<strong>" + title + "</strong>";
    };

    this.show_progress_bar = function(show) {
        // Show or hide the progress bar

        // determine the proper display style
        var display = "none";
        if (show) {
            display = "block";
        }

        // set the display style for the progress bar
        var content_document = sg_panel.get_content_document();
        content_document.getElementById(_progress_bar_div_id).style.display =
            display;
    };

};

// ---------------------------------------------------------------------------
// The panel

sg_panel.Panel = new function() {
    // A singleton "class" to manage the state of the extension's panel display.

    // ---- private vars

    // keep a handle on the instance.
    var self = this;

    // adobe interface
    var _cs_interface = new CSInterface();

    // debug console urls. the ports should correspond to the ports defined in
    // the extension's .debug file for the supported CC applications.
    var _debug_console_urls = {
        // TODO: externalize?
        // Photoshop
        "PHSP": "http://localhost:45216",
        "PHXS": "http://localhost:45217",
        // After effects
        "AEFT": "http://localhost:45218"
    };

    // ---- public methods

    this.build_flyout_menu = function() {
        // Builds the flyout menu with the debug/reload options.

        // the xml that defines the flyout menu
        var flyout_xml =
            '<Menu> \
                <MenuItem Id="sg_about" \
                          Label="About..." \
                          Enabled="true" \
                          Checked="false"/> \
                <MenuItem Label="---" /> \
                <MenuItem Id="sg_dev_debug" \
                          Label="Debug Console..." \
                          Enabled="true" \
                          Checked="false"/> \
                <MenuItem Id="sg_dev_reload" \
                          Label="Reload" \
                          Enabled="true" \
                          Checked="false"/> \
            </Menu>';

        // build the menu
        _cs_interface.setPanelFlyoutMenu(flyout_xml);

        // Listen for the Flyout menu clicks
        _cs_interface.addEventListener(
            "com.adobe.csxs.events.flyoutMenuClicked",
            _on_flyout_menu_clicked
        );
    };

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        try {

            // build the flyout menu. always do this first so we can have access
            // to the debug console no matter what happens during bootstrap.
            self.build_flyout_menu();

            // setup event listeners first so that we can react to various events
            _setup_event_listeners();

            // request new state from the manager. if the python process hasn't
            // started up yet, this may not result in a response. however, the
            // python process should send the initial state anyway.
            _request_state();

        } catch(error) {
            sg_logging.error("Manager startup error: " + error.stack);
            alert("Manager startup error: " + error.stack);
            // TODO: display error in the panel
        }

    };

    this.on_unload = function() {
        // code to run when the extension panel is unloaded
        sg_logging.debug("Panel unloaded.");

        // TODO: do we need to remove event listeners? do they persist?
    };

    this.reload = function() {
        // Request reload of the manager.
        //
        // After requesting manager reload, simply shuts down this extension
        // since the manager will restart it.

        // request manager reload
        sg_panel.REQUEST_MANAGER_RELOAD.emit();

        // close this extension
        _cs_interface.closeExtension();
    };

    this.set_state = function(state) {

        // TODO: document required command object contents once settled.
        const context_display = state["context"]["display"];

        // XXX Temp implementation for testing.
        var commands_html = "";
        var commands = state["commands"];

        for(var i = 0; i < commands.length; i++) {
            var command = commands[i];
            if (command.hasOwnProperty("id") &&
                command.hasOwnProperty("display_name") &&
                command.hasOwnProperty("icon_path")) {
                    var command_id = command["id"];
                    var display_name = command["display_name"];
                    var icon_path = command["icon_path"];
                    commands_html +=
                        "<a href='#' onClick='sg_panel.REGISTERED_COMMAND_TRIGGERED.emit(\"" + command_id + "\")'>" +
                        "<img align='middle' src='" + icon_path + "' width='24'> " + display_name +
                        "</a><br><br>";
            }
        }

        commands_html += "";

        document.getElementById("sg_context_display").innerHTML = context_display
        document.getElementById("sg_commands_display").innerHTML = commands_html
    };

    // ---- private methods

    var _on_flyout_menu_clicked = function(event) {
        // Handles flyout menu clicks

        switch (event.data.menuId) {

            // debug console
            case "sg_dev_debug":
                sg_logging.debug("Opening debugger in default browser.");
                var app_name = _cs_interface.getHostEnvironment().appName;
                var debug_url = _debug_console_urls[app_name];
                _cs_interface.openURLInDefaultBrowser(debug_url);
                break;

            // reload extension
            case "sg_dev_reload":

                // turn off persistence so we can reload, then turn it back
                // on after the reload
                self.reload();

                break;

            // about the extension
            case "sg_about":

                // show the about menu
                //_set_page(sg_panel.AboutPage);
                alert("Show about info!");
                break;

            default:
                sg_logging.warn("Unhandled menu event '" + event.data.menuName + "' clicked.");
        }
    };

    var _on_load = function() {
        // The panel startup payload

        // make the panel persistent
        // self.make_persistent(true);

        // the status page is the default, so we know it is loaded.
        //var status_page = sg_panel.StatusPage;
        //status_page.set_title("Loading Shotgun");
        //status_page.set_message("Shotgun will be ready in just a moment...");
        //status_page.show_progress_bar(false);

        // python process streams disconnected

        sg_logging.debug("Panel finished loading.");
    };

    var _on_python_connection_lost = function(event) {
        // Handles unexpected python process shutdown.

        // TODO: show different page here?
        // TODO: prompt to try to reload the manager/panel?

        //var status_page = sg_panel.StatusPage;

        // set the page and display some values after it is loaded.
        //_set_page(status_page, function() {
        //    // TODO: better messages here...
        //    status_page.set_title("Python Disconnected");
        //    status_page.set_message("Something happened... ");
        //    status_page.show_progress_bar(false);
        //});

        alert("Python process connection lost.");
    };

    var _request_state = function() {
        // request panel state update
        sg_panel.REQUEST_STATE.emit();
    };

    var _set_page = function (page, on_load_function) {
        // Make the supplied page current.
        //
        // Args:
        //   page: The page to make current.

        // get a handle on the content frame within the main document.
        //var content_frame = document.getElementById(sg_panel.content_frame_id);

        // set the source of the content frame to the path of the supplied page.
        //content_frame.src = page.path;

        // if an onload function was supplied, set it up to be called when the
        // page is loaded.
        //if (typeof on_load_function !== "undefined") {
        //    content_frame.onload = on_load_function;
        //}

        sg_logging.debug("Set page called: " + page);
    };

    var _setup_event_listeners = function() {

        // Handle python process disconnected
        sg_manager.PYTHON_PROCESS_DISCONNECTED.connect(
            _on_python_connection_lost
        );

        // Updates the panel with the current state from python
        sg_manager.UPDATE_STATE.connect(
            function(event) {
                self.set_state(event.data);
            }
        );

        // Handle log messages from python process
        sg_logging.LOG_MESSAGE.connect(
            function(event) {
                const level = event.data.level;
                const msg = event.data.message;
                console[level](msg);
            }
        );
    };
};

