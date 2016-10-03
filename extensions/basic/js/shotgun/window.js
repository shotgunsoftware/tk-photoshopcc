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

sg_window.AboutPage = new function() {
    // A singleton object representing the about page.

    // ---- public vars

    // path to the page html
    this.path = "about.html";
};

// ---------------------------------------------------------------------------

sg_window.CommandsPage = new function() {
    // A singleton object representing the commands page.

    // ---- public vars

    // path to the page html
    this.path = "commands.html";

    // TODO:
    //  * clear
    //  * set commands
};

// ---------------------------------------------------------------------------

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

        var content_frame = _get_frame_document();
        alert("CONTENT FRAME: " + content_frame)

        var msg_div = content_frame.getElementById(_message_div_id);
        msg_div.innerHTML = message;

        // log the message
        console.log(message)
    };

    this.set_progress = function(percent, message) {
        // Set the percentage of the progress bar

        // make sure the progress bar is shown
        self.show_progress_bar(true);

        var content_frame = _get_frame_document();

        // set the progress percentage
        var progress_div = content_frame.getElementById(_progress_div_id);
        progress_div.style.width = Math.min(percent, 100) + "%";

        // message is optional. if supplied, set the message.
        if (typeof(message) !== "undefined") {
            self.set_message(message)
        }
    };

    this.set_title = function(title) {
        // Set the title for the status page.

        var content_frame = _get_frame_document();

        var title_div = content_frame.getElementById(_title_div_id);
        title_div.innerHTML = "<strong>" + title + "</strong>";
    };

    this.show_progress_bar = function(show) {
        // Show or hide the progress bar

        // determine the proper display style
        var display = "none";
        if (show) {
            display = "inline";
        }

        var content_frame = _get_frame_document();

        // set the display style for the progress bar
        var progress_bar_div = content_frame.getElementById(
            _progress_bar_div_id);
        progress_bar_div.style.display = display;
    };

    // ---- private methods

    var _get_frame_document = function() {
        // Return the document in the content frame
        // TODO: promote to base class for other page classes to access.
        // TODO: path should be defined in base class as well
        return document.getElementById("content_frame").contentWindow.document;
    }
};

// ---------------------------------------------------------------------------

// panel singleton.
sg_window.PanelSingleton = new function() {
    // A singleton "class" to manage the state of the extension's panel display.

    // ---- private vars

    // keep a handle on the instance.
    var self = this;

    // adobe interface
    var _cs_interface = new CSInterface();

    // the current page
    var _current_page = sg_window.StatusPage;

    // the div id of the iframe on the main page where content is displayed
    var _content_frame_id = "content_frame";

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

        // TODO: different events based on the current app?
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
        // Runs when the extension is loaded.

        // build the flyout menu. always do this first so we can have access
        // to the debug console no matter what happens during bootstrap.
        self.build_flyout_menu();

        // make the panel persistent
        self.make_persistent(true);

        // show the status page with a loading message
        var status_page = sg_window.StatusPage;
        _set_page(status_page);
        status_page.set_title("Loading Shotgun");
        status_page.set_message("Shotgun will be ready in just a moment...");
        status_page.show_progress_bar(false);
        // TODO: show shotgun logo

        // ensure this app is supported by our extension
        if (!self.app_is_supported()) {

            // this version of the sw is not supported by the extension.
            // show an unsupported message.
            status_page.set_title("Application Unsupported");
            // TODO: link to support mail. link to engine docs?
            status_page.set_message(
                "Uh oh! The current version of this application is not " +
                "supported by Shotgun. Please contact Shotgun support at " +
                "support@shotgunsoftware.com if you have questions."
            );
            // TODO: show error icon.
            return
        }

        // the path to this extension
        var ext_dir = _cs_interface.getSystemPath(SystemPath.EXTENSION);

        // bootstrap toolkit and get a handle on the python process
        self.python_process = sg_bootstrap.bootstrap(ext_dir);

        // XXX begin temporary process communication

        // log stdout from python process
        self.python_process.stdout.on("data", function(data) {
            console.log("stdout: " + data);
        });

        // log stderr from python process
        self.python_process.stderr.on("data", function(data) {
            console.log("stderr: " + data);
        });

        // XXX end temporary process communication

        // python process streams disconnected
        self.python_process.on("close", function(code) {
            var status_page = sg_window.StatusPage;
            _set_page(status_page);
            // TODO: better messages here...
            //status_page.set_title("Uh Oh! Shotgun Python Process Terminated.");
            //status_page.set_message("Something happened... blah blah blah...");
            //status_page.show_progress_bar(false);

            // XXX begin testing
            //status_page.show_progress_bar(true);
            //var val = 10;
            //var progress_func = function() {
                //var currentdate = new Date();
                //var datetime = "Current Time: " + currentdate.getDate() + "/"
                    //+ (currentdate.getMonth()+1)  + "/"
                    //+ currentdate.getFullYear() + " @ "
                    //+ currentdate.getHours() + ":"
                    //+ currentdate.getMinutes() + ":"
                    //+ currentdate.getSeconds();
                //status_page.set_progress(val, datetime);
                //val += 10;
            //};
            //var progress_test = setInterval(progress_func, 1000);

            //status_page.show_progress_bar(false);
            // XXX end testing
        });

        // TODO: this page should be shown after the python process has
        //   communicated back the information about the commands to display.
        _set_page(sg_window.CommandsPage);

        console.log("Window finished loading.");
    };

    this.on_unload = function() {
        // code to run when the extension panel is unloaded

        // show the status page with a shut down message
        var status_page = sg_window.StatusPage;
        _set_page(status_page);
        status_page.set_title("Shutting down...");
        status_page.set_message("Bye for now!");
        status_page.show_progress_bar(false);
        // TODO: show processing icon

        // make sure the python process is shut down
        _shutdown_python();

        console.log("Window finished unloading.");
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

    // ---- private methods

    var _on_flyout_menu_clicked = function(event) {
        // Handles flyout menu clicks

        switch (event.data.menuId) {

            // debug console
            case "sg_dev_debug":
                // TODO: go directly to console page instead of link page.
                console.log("Opening debugger in default browser.");
                // the port should correspond to the port defined in .debug
                _cs_interface.openURLInDefaultBrowser(
                    "http://localhost:45217");
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

    var _set_page = function (page) {
        // Make the supplied page current.
        //
        // Args:
        //   page: The page to make current.

        // get a handle on the content frame within the main document.
        // then set the source of the content frame to the path of the
        // supplied page.
        var content_frame = document.getElementById(_content_frame_id);
        content_frame.src = page.path;

        console.log("Current page changed to: " + page.path);
        _current_page = page;
    };

    var _shutdown_python = function() {
        // attempt to terminate the child python process

        if (typeof self.python_process !== "undefined") {
            console.log("Terminating python process...");
            try {
                self.python_process.kill();
                console.log("terminated!");
            } catch(err) {
                console.log("Unable to terminate python process: " + err);
            }
        }

    };

};

