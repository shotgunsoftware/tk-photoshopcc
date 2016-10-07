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
var sg_window = sg_window || {};

// ---------------------------------------------------------------------------
// Module level values

sg_window.content_frame_id = "content_frame";

// ---------------------------------------------------------------------------
// Module level functions

sg_window.get_content_document = function() {
    // Returns the document of the content frame of the main page (the iframe
    // where the content is displayed. Used by pages to update their contents
    // dynamically.
    return document.getElementById(sg_window.content_frame_id).
        contentWindow.document;
};

// ---------------------------------------------------------------------------
// Pages displayed in the panel

sg_window.AboutPage = new function() {
    // A singleton object representing the about page.

    // path to the page html
    this.path = "about.html";
};

sg_window.CommandsPage = new function() {
    // A singleton object representing the commands page.

    // ---- private vars

    // The div id of the commands section of the page
    var _command_section_id = "sg_commands_section";

    // ---- public vars

    // path to the page html
    this.path = "commands.html";


    this.set_commands = function(commands) {
        // Display the supplied commands on the page.

        var command_html = "<ul>";

        for(var i = 0; i < commands.length; i++) {
            var command = commands[i];
            if (command.hasOwnProperty("id") &&
                command.hasOwnProperty("display_name") &&
                command.hasOwnProperty("icon_path")) {
                    var command_id = command["id"];
                    var display_name = command["display_name"];
                    var icon_path = command["icon_path"];
                    command_html +=
                        "<li><a href='#' onclick='alert(\"" + command_id + "\")'>" +
                        "<img src='" + icon_path + "' width='48'>" +
                        display_name + "</a></li>";
            }
        }

        command_html += "</ul>";

        var content_document = sg_window.get_content_document();
        content_document.getElementById(_command_section_id).innerHTML =
            command_html;
    };
};

sg_window.StatusPage = new function(path) {
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

        var content_document = sg_window.get_content_document();
        content_document.getElementById(_message_div_id).innerHTML = message;

        // log the message
        console.log(message)
    };

    this.set_progress = function(percent, message) {
        // Set the percentage of the progress bar

        // make sure the progress bar is shown
        self.show_progress_bar(true);

        // set the progress percentage
        var content_document = sg_window.get_content_document();
        content_document.getElementById(_progress_div_id).style.width =
            Math.min(percent, 100) + "%";

        // message is optional. if supplied, set the message.
        if (typeof(message) !== "undefined") {
            self.set_message(message)
        }
    };

    this.set_title = function(title) {
        // Set the title for the status page.

        var content_document = sg_window.get_content_document();
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
        var content_document = sg_window.get_content_document();
        content_document.getElementById(_progress_bar_div_id).style.display =
            display;
    };

};

// ---------------------------------------------------------------------------
// The panel

sg_window.PanelSingleton = new function() {
    // A singleton "class" to manage the state of the extension's panel display.

    // ---- private vars

    // keep a handle on the instance.
    var self = this;

    // adobe interface
    var _cs_interface = new CSInterface();

    // the current page
    var _current_page = sg_window.StatusPage;

    // debug console urls. the ports should correspond to the ports defined in
    // the extension's .debug file for the supported CC applications.
    var _debug_console_urls = {
        // Photoshop
        "PHSP": "http://localhost:45216",
        "PHXS": "http://localhost:45217",
        // After effects
        "AEFT": "http://localhost:45218"
    };

    // ---- public methods

    this.app_is_supported = function() {
        // Tests whether the extension can run with the current application

        // supported if the panel menu and html extensions are available
        var host_capabilities = _cs_interface.getHostCapabilities();
        return host_capabilities.EXTENDED_PANEL_MENU &&
               host_capabilities.SUPPORT_HTML_EXTENSIONS;
    };

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

    this.make_persistent = function(persistent) {
        // Turns on/off persistence for the panel.

        // Making the app persistent prevents it from reloading each time
        var event = undefined;
        if (persistent) {
            console.log("Making panel persistent (no reloading).");
            event = new CSEvent("com.adobe.PhotoshopPersistent",
                "APPLICATION");
        } else {
            event = new CSEvent("com.adobe.PhotoshopUnPersistent",
                "APPLICATION");
        }

        event.extensionId = _cs_interface.getExtensionID();
        _cs_interface.dispatchEvent(event);
    };

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        // Execute the startup payload and catch *any* errors. If there are
        // errors, display them on the status page.
        try {
            _on_load();
        } catch(err) {
            // show the error on the status page
            _set_page(sg_window.StatusPage, function() {
                sg_window.StatusPage.set_title("Error");
                sg_window.StatusPage.set_message(
                    "There was a problem loading the Adobe CC Shotgun " +
                    "Integration. The error: <br><br>" + err.stack
                );
                sg_window.StatusPage.show_progress_bar(false);
            });
        }

    };

    this.on_unload = function() {
        // code to run when the extension panel is unloaded

        // make sure the python process is shut down
        _shutdown_python();
    };

    this.reload = function() {
        // Reload the extension by closing it then requresting to reopen.

        // remember the extension id to reload it
        var extension_id = _cs_interface.getExtensionID();

        // make sure the python process is shut down
        _shutdown_python();

        // close the extension
        console.log("Reloading the extension.");
        console.log("Debug console will need to be restarted.");
        _cs_interface.closeExtension();

        // request relaunch
        console.log("Relaunching the extension...");
        _cs_interface.requestOpenExtension(extension_id);
    };

    this.set_commands = function(commands) {
        // Set the current page and populate the supplied commands.
        //
        // TODO: document required command object contents.

        _set_page(sg_window.CommandsPage, function () {
            // on page load, setup the commands
            sg_window.CommandsPage.set_commands(commands);
        });

    };

    // ---- private methods

    var _on_flyout_menu_clicked = function(event) {
        // Handles flyout menu clicks

        switch (event.data.menuId) {

            // debug console
            case "sg_dev_debug":
                console.log("Opening debugger in default browser.");
                var app_name = _cs_interface.getHostEnvironment().appName;
                var debug_url = _debug_console_urls[app_name];
                _cs_interface.openURLInDefaultBrowser(debug_url);
                break;

            // reload extension
            case "sg_dev_reload":

                // turn off persistence so we can reload, then turn it back
                // on after the reload
                self.make_persistent(false);
                self.reload();
                self.make_persistent(true);

                break;

            // about the extension
            case "sg_about":

                // show the about menu
                _set_page(sg_window.AboutPage);
                break;

            default:
                console.log("Unhandled menu event '" + event.data.menuName +
                    "' clicked.");
        }
    };

    var _on_load = function() {
        // The panel startup payload

        // build the flyout menu. always do this first so we can have access
        // to the debug console no matter what happens during bootstrap.
        self.build_flyout_menu();

        // make the panel persistent
        self.make_persistent(true);

        // the status page is the default, so we know it is loaded.
        var status_page = sg_window.StatusPage;
        status_page.set_title("Loading Shotgun");
        status_page.set_message("Shotgun will be ready in just a moment...");
        status_page.show_progress_bar(false);

        // ensure this app is supported by our extension
        if (!self.app_is_supported()) {

            // this version of the sw is not supported by the extension.
            // show an unsupported message.
            status_page.set_title("Application Unsupported");
            // TODO: link to engine docs?
            status_page.set_message(
                "Uh oh! The current version of this application is not " +
                "supported by Shotgun. Please contact " +
                "<a href='mailto:support@shotgunsoftware.com'>Shotgun " +
                "Support</a> support at if you have questions."
            );
            return
        }

        // the path to this extension
        var ext_dir = _cs_interface.getSystemPath(SystemPath.EXTENSION);

        // bootstrap toolkit and get a handle on the python process
        self.python_process = sg_bootstrap.bootstrap(ext_dir);

        // XXX begin temporary process communication

        // log stdout from python process
        self.python_process.stdout.on("data", function (data) {
            console.log("stdout: " + data);
        });

        // log stderr from python process
        self.python_process.stderr.on("data", function (data) {
            console.log("stderr: " + data);
        });

        // XXX end temporary process communication

        // python process streams disconnected
        self.python_process.on("close", _on_python_connection_lost);

        // XXX This is temp sim of the commands being sent from python
        var commands = [
            {
                "id": "command_id_1",
                "display_name": "Python Console",
                "icon_path": "../images/tmp/command1.png"
            },
            {
                "id": "command_id_2",
                "display_name": "Command B",
                "icon_path": "../images/tmp/command2.png"
            },
            {
                "id": "command_id_3",
                "display_name": "Command C",
                "icon_path": "../images/tmp/command3.png"
            },
            {
                "id": "command_id_4",
                "display_name": "Command D",
                "icon_path": "../images/tmp/command4.png"
            }
        ];
        self.set_commands(commands);
        // XXX End temporary simulation

        console.log("Panel finished loading.");
    };

    var _on_python_connection_lost = function(code) {
        // Handles unexpected python process shutdown.

        // TODO: show different page here? One specific to python shut down
        // that prompts to reload the integration?
        var status_page = sg_window.StatusPage;

        // set the page and display some values after it is loaded.
        _set_page(status_page, function() {
            // TODO: better messages here...
            status_page.set_title("Python Disconnected");
            status_page.set_message("Something happened... ");
            status_page.show_progress_bar(false);
        });
    };

    var _set_page = function (page, on_load_function) {
        // Make the supplied page current.
        //
        // Args:
        //   page: The page to make current.

        // get a handle on the content frame within the main document.
        var content_frame = document.getElementById(sg_window.content_frame_id);

        // set the source of the content frame to the path of the supplied page.
        content_frame.src = page.path;

        // if an onload function was supplied, set it up to be called when the
        // page is loaded.
        if (typeof on_load_function !== "undefined") {
            content_frame.onload = on_load_function;
        }

        console.log("Current page changed to: " + page.path);
        _current_page = page;
    };

    var _shutdown_python = function() {
        // attempt to terminate the child python process

        if (typeof self.python_process !== "undefined") {
            console.log("Terminating python process...");
            try {
                self.python_process.kill();
                console.log("Python process terminated successfully.");
            } catch(err) {
                console.log("Unable to terminate python process: " + err);
            }
        }

    };

};

