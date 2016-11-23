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
// The panel

sg_panel.Panel = new function() {
    // A singleton "class" to manage the state of the extension's panel display.

    // ---- private vars

    // keep a handle on the instance.
    const self = this;

    // adobe interface
    const _cs_interface = new CSInterface();

    // ---- public methods

    this.clear = function() {
        // Clears the panel's contents and resets it to its default state.
        //
        // Since we don't really want to stay in this state, the panel shows
        // a message to the user saying that the panel is loading.

        _set_header("Shotgun integration is loading...");
        _set_contents("<img src='../images/sg_logo.png'>");
    };

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        try {

            // ensure the panel is in its default state.
            self.clear();

            // build the flyout menu. always do this first so we can have access
            // to the debug console no matter what happens during bootstrap.
            _build_flyout_menu();

            // setup event listeners first so we can react to various events
            _setup_event_listeners();

            // request new state from the manager. if the python process hasn't
            // started up yet, this may not result in a response. however, the
            // python process should send the initial state after loading
            // initially anyway.
            // TODO: handle case where manager or python don't respond
            // TODO: use setTimeout to display an error
            sg_panel.REQUEST_STATE.emit();

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
    };

    this.set_state = function(state) {

        // TODO: display the description as a tooltip or expandable content?
        // TODO: handle case where no icon is provided

        // TODO: document required command object contents once settled.
        _set_header(state["context"]["display"]);

        // XXX Temp implementation for testing.
        var commands_html = "";
        const commands = state["commands"];

        commands.forEach(function(command) {
            if (command.hasOwnProperty("uid") &&
                command.hasOwnProperty("display_name") &&
                command.hasOwnProperty("icon_path")) {

                const command_id = command["uid"];
                const display_name = command["display_name"];
                const icon_path = command["icon_path"];

                commands_html +=
                    "<a href='#' onClick='sg_panel.REGISTERED_COMMAND_TRIGGERED.emit(\"" + command_id + "\")'>" +
                        "<div id='sg_command_button'>" +
                            "<table>" +
                                "<tr>" +
                                    // icon
                                    "<td id='sg_command_button_icon'>" +
                                       "<img align='middle' src='" + icon_path + "' width='48'> " +
                                    "</td>" +
                                    // text
                                    "<td id='sg_command_button_text'>" +
                                       display_name +
                                    "</td>" +
                                "</tr>" +
                          "</table>" +
                        "</div>" +
                    "</a>";
            }
            // TODO: if command is missing something, log it.
        });

        _set_contents(commands_html);

        // make sure the progress bar is hidden
        _show_progress(false);
    };

    // ---- private methods

    const _build_flyout_menu = function() {
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
                          Label="Debug Console (Requires Chrome)..." \
                          Enabled="true" \
                          Checked="false"/> \
                <MenuItem Id="sg_dev_reload" \
                          Label="Reload" \
                          Enabled="true" \
                          Checked="false"/>'

        if (process.env["SHOTGUN_ADOBECC_TESTS_ROOT"]) {
            flyout_xml += '   <MenuItem Id="sg_dev_tests" \
                                        Label="Run Tests" \
                                        Enabled="true" \
                                        Checked="false"/>'
        }
        flyout_xml += '</Menu>';

        // build the menu
        _cs_interface.setPanelFlyoutMenu(flyout_xml);

        // Listen for the Flyout menu clicks
        _cs_interface.addEventListener(
            "com.adobe.csxs.events.flyoutMenuClicked",
            _on_flyout_menu_clicked
        );
    };

    const _on_flyout_menu_clicked = function(event) {
        // Handles flyout menu clicks

        switch (event.data.menuId) {

            // NOTE: Looks like you can't use `const` in the switch cases.
            // The panel won't even load if you do. Perhaps some type of failed
            // optimization when doing the menu callback? No obvious errors
            // are displayed. Leaving this here as a warning.

            // debug console
            case "sg_dev_debug":
                sg_logging.debug("Opening debugger in default browser.");
                var app_name = _cs_interface.getHostEnvironment().appName;
                var debug_url = sg_constants.product_info[app_name].debug_url;
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
                // TODO: show a Qt about dialog here.
                // Send information about the current CC product to python and
                // launch the about dialog from there. That will prevent us from
                // having to navigate away from the current panel and its contents.
                // Alternatively, display an overlay in the panel.
                alert("ABOUT dialog goes here.");
                break;

            // run test suite
            case "sg_dev_tests":
                sg_logging.debug("Emitting RUN_TESTS panel event.");
                sg_panel.RUN_TESTS.emit();
                break;

            default:
                sg_logging.warn("Unhandled menu event '" + event.data.menuName + "' clicked.");
        }
    };

    const _on_critical_error = function(event) {

        const message = event.data.message;

        // TODO: show the stack trace somewhere!
        const stack = event.data.stack;

        sg_logging.error("Critical: " + message);

        _set_header(
            "<img src='../images/error.png' align='bottom' width='24'>" +
            "&nbsp;&nbsp;Uh oh! Something went wrong..."
        );

        _set_contents(
            message +
            "<br>" +
            "If you encounter this problem consistently or have any other " +
            "problems, please contact: " +
            "<a href='mailto:support@shotgunsoftware.com'>Shotgun Support</a>" +
            "<br>" +
            "Click the button below to attempt to restart the integration." +
            "<br>" +
            "<button class='sg_button' onclick='sg_panel.Panel.reload()'>" +
            "Restart Shotgun Integration" +
            "</button>"
        );
    };

    const _on_logged_message = function(event) {
        // Handles incoming log messages
        const level = event.data.level;
        const msg = event.data.message;

        // Some things are sent via log signal because there's no other
        // way to get access to them. For example, during toolkit
        // bootstrap, we can only gain access to progress via stdio pipe
        // maintained between js process and the spawned python process.
        // So we intercept messages formatted to relay progress.
        if (msg.includes("PLUGIN_BOOTSTRAP_PROGRESS")) {
            // It is possible that the message contains multiple
            // progress messages packaged together. Identify all of them
            // and update the progress bar.
            var regex_str = "\\|PLUGIN_BOOTSTRAP_PROGRESS,(\\d+(\\.\\d+)?),([^|]+)\\|";
            const multi_regex = new RegExp(regex_str, "gm");
            var matches = msg.match(multi_regex);
            if (!matches) {
                return;
            }
            matches.forEach(function(match) {
                const single_regex = new RegExp(regex_str, "m");
                const msg_parts = match.match(single_regex);
                // the regex returns the progress value as a float at
                // position 1 of the match. position 3 is the message
                _set_progress(msg_parts[1] * 100, msg_parts[3]);
            });

        } else {
            // typical log message. forward to the console
            console[level](msg);
        }
    };

    const _setup_event_listeners = function() {
        // Sets up all the event handling callbacks.

        // Handle python process disconnected
        sg_manager.CRITICAL_ERROR.connect(_on_critical_error);

        // Updates the panel with the current state from python
        sg_manager.UPDATE_STATE.connect(
            function(event) {
                self.set_state(event.data);
            }
        );

        // Handle the manager shutting down.
        sg_manager.SHUTTING_DOWN.connect(
            function(event) {
                _cs_interface.closeExtension();
            }
        );

        // Handle log messages from python process
        sg_logging.LOG_MESSAGE.connect(_on_logged_message);

    };

    // ---- html update methods

    const _set_div_html = function(div_id, html) {
        // Updates the inner HTML of the supplied div with the supplied HTML
        document.getElementById(div_id).innerHTML = html;
    };

    const _set_div_html_by_id = function(div_id) {
        return function(html) {
            // Convenience method for updating panel contents with supplied html
            _set_div_html(sg_constants.panel_div_ids[div_id], html);
        };
    };

    // convenience methods for updating the various panel components
    const _set_contents = _set_div_html_by_id("contents");
    const _set_header = _set_div_html_by_id("header");
    const _set_footer = _set_div_html_by_id("footer");
    const _set_progress_message = _set_div_html_by_id("progress_label");

    const _set_progress = function(progress, message) {
        // Update the progress section with a % and a message.
        _show_progress(true);
        var elem = document.getElementById(
            sg_constants.panel_div_ids["progress_bar"]);
        elem.style.width = progress + '%';
        _set_progress_message(message);
    };

    const _show_progress = function(show_or_hide) {
        // Show or hide the progress bar.
        var display = "none";  // hide
        if (show_or_hide) {
            display = "block"; // show
        }
        var elem = document.getElementById(
            sg_constants.panel_div_ids["progress"]);
        elem.style.display = display;
    };
};


