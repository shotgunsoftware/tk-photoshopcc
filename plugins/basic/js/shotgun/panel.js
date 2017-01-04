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

    var _show_tooltip_timeout_id = undefined;
    var _hide_tooltip_timeout_id = undefined;

    var _cur_mouse_pos = {
        x: undefined,
        y: undefined
    };

    // ---- public methods

    this.clear = function() {
        // Clears the panel's contents and resets it to its default state.
        //
        // Since we don't really want to stay in this state, the panel shows
        // a message to the user saying that the panel is loading.

        _set_bg_color("#222222");

        _show_header(false);
        _set_contents(
            "<br><br>" +
            "<center><img src='../images/sg_logo_loading.png'></center>"
        );

        _show_info(true);
        _set_info(
            "Loading Shotgun Integration..."
        );
    };

    this.show_command_help = function(title, help, favorite) {

        if (_hide_tooltip_timeout_id !== undefined) {
            clearTimeout(_hide_tooltip_timeout_id);
        }

        _show_tooltip_timeout_id = setTimeout(
            function(){_on_show_command_help_timeout(help)}, 1500);

        if (favorite) {
            const fav_header_div = document.getElementById("sg_panel_favorites_header");
            fav_header_div.innerHTML = title;
        }
    };

    const _on_show_command_help_timeout = function(help) {

        if (!help || help === "null") {
            help = "Could not find a description for this command. " +
                   "Please check with the author of the app to see about " +
                   "making a description available."
        }

        // mouse pos. always align left to right from mouse position.
        // if help div will go past right and/or bottom border, adjust accordingly.

        const mouse_x = _cur_mouse_pos.x;
        const mouse_y = _cur_mouse_pos.y;

        const command_div = document.elementFromPoint(mouse_x, mouse_y);

        const offset = 8;
        const margin = 8;


        const help_div_id = sg_constants.panel_div_ids["command_help"];
        const help_div = document.getElementById(help_div_id);

        // reset to the top left to allow it to grow as needed when contest set
        help_div.style.left = "0px";
        help_div.style.top = "0px";

        _set_command_help(help);

        const help_div_rect = help_div.getBoundingClientRect();

        const help_width = help_div_rect.width;
        const help_height = help_div_rect.height;

        const far_right = mouse_x + offset + margin + help_width;
        const far_bottom = mouse_y + offset + margin + help_height;

        const win_width = window.innerWidth;
        const win_height = window.innerHeight;

        const beyond_right = far_right - win_width + margin;
        const beyond_bottom = far_bottom - win_height + margin;

        var adjust_left = 0;
        var adjust_top = 0;

        if (beyond_right > 0) {
            adjust_left = -1 * beyond_right;
        }

        if (beyond_bottom > 0) {
            adjust_top = -1 * beyond_bottom;
        }

        const new_left = mouse_x + offset + adjust_left + window.scrollX;
        const new_top = mouse_y + offset + adjust_top + window.scrollY;

        help_div.style.left = new_left + "px";
        help_div.style.top = new_top + "px";

        const new_help_div_rect = help_div.getBoundingClientRect();

        if (_point_in_rect(_cur_mouse_pos, new_help_div_rect)) {
            // the mouse is now inside the help div. need to adjust more

            var additional_offset_y = 0;

            if (beyond_bottom > 0) {
                // we already adjusted up, keep going. we know we need to get
                // at least `offset` pixels past the mouse. then it's just the
                // difference
                additional_offset_y = -1 * (offset + new_help_div_rect.bottom - mouse_y);
            }

            help_div.style.top = new_top + additional_offset_y + "px";
        }

        _show_command_help(true);

        _hide_tooltip_timeout_id = setTimeout(
            function(){ self.hide_command_help()}, 5000);
    };

    const _point_in_rect = function(point, rect) {

        return ((point.x >= rect.left) && (point.x <= rect.right) &&
                (point.y >= rect.top)  && (point.y <= rect.bottom));
    };

    this.hide_command_help = function() {
        if (_show_tooltip_timeout_id !== undefined) {
            clearTimeout(_show_tooltip_timeout_id);
        }
        _show_command_help(false);

        const fav_header_div = document.getElementById("sg_panel_favorites_header");
        fav_header_div.innerHTML = "Run a Command";
    };

    this.email_support = function(subject, body) {

        const mailto_url = "mailto:support@shotgunsoftware.com?" +
                           "subject=" + subject +
                           "&body=" + body;

        sg_logging.debug("Emailing support: " + mailto_url);

        _clear_info();
        _set_progress_info(100, "Composing SG support email...");
        setTimeout(_clear_info, 2000);

        self.open_external_url(mailto_url);
    };

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        try {

            // ensure the panel is in its default state.
            self.clear();

            _override_console_logging();

            // build the flyout menu. always do this first so we can have access
            // to the debug console no matter what happens during bootstrap.
            _build_flyout_menu();

            // setup event listeners first so we can react to various events
            _setup_event_listeners();

            sg_logging.error("PANEL: test error");
            sg_logging.warn("PANEL: test warning");
            sg_logging.info("PANEL: test info");
            sg_logging.debug("PANEL: test debug");

            // If the current Adobe application is photoshop, turn on persistence.
            // This isn't required, but provides a better user experience by not
            // trying to reload the panel whenever it regains focus.
            const photoshop_ids = ["PHSP", "PHXS"];
            if (photoshop_ids.indexOf(_cs_interface.getApplicationID()) > -1) {
                sg_logging.debug("Making panel persistent.");
                _make_persistent(true);
            }

            // request new state from the manager. if the python process hasn't
            // started up yet, this may not result in a response. however, the
            // python process should send the initial state after loading
            // initially anyway.
            // TODO: handle case where manager or python don't respond
            // TODO: use setTimeout to display an error
            sg_panel.REQUEST_STATE.emit();

            // track the mouse
            document.onmousemove = _on_mouse_move;

        } catch(error) {
            sg_logging.error("Manager startup error: " + error.stack);
            alert("Manager startup error: " + error.stack);
            // TODO: display error in the panel
        }

    };

    this.on_unload = function() {
        // code to run when the extension panel is unloaded
        sg_logging.debug("Panel unloaded.");
    };

    this.open_external_url = function(url) {
        sg_logging.debug("Opening external url: " + url);
        _cs_interface.openURLInDefaultBrowser(url);
    };

    this.reload = function() {
        // Request reload of the manager.
        //
        // After requesting manager reload, simply shuts down this extension
        // since the manager will restart it.

        sg_logging.debug("Closing the panel.");

        // turn off persistence so we can close the panel
        _make_persistent(false);

        // close the panel
        self.on_unload();

        // request manager reload and close the panel
        sg_panel.REQUEST_MANAGER_RELOAD.emit();
        _cs_interface.closeExtension();
    };

    this.set_state = function(state) {

        // TODO: show actual header info
        // TODO: handle case where no icon is provided
        // TODO: document state object. make an object out of it?

        var fields_table = "<table width='100%'>";

        state["context_fields"].forEach(function(field_info) {

            const field = field_info["type"];
            const value = field_info["display"];
            const url = field_info["url"];

            fields_table +=
                "<tr>" +
                    "<td class='sg_field_name'>" +
                        field + ":&nbsp;" +
                    "</td>" +
                    "<td class='sg_field_value'>" +
                        "<a href='#' class='sg_field_value_link' " +
                            "onclick='sg_panel.Panel.open_external_url(\"" + url + "\")'>" +
                            value +
                        "</a>" +
                    "</td>" +
                "</tr>";
        });

        fields_table += "</table>";

        var header_html = "<table class='sg_context_header'>" +
                "<tr>" +
                    "<td align='right'>" +
                        "<img src='../images/sg_logo.png' height='64'>" +
                    "</td>" +
                    "<td>" +
                        "<strong>" +
                            fields_table +
                        "</strong>" +
                    "</td>" +
                "</tr>" +
            "</table>";

        _set_header(header_html);
        _show_header(true);

        // Favorite commands

        const favorites = state["favorites"];
        var favorites_html = "";

        if (favorites.length > 0) {

            favorites_html = "<div id='sg_panel_favorites'>" +
                "<div id='sg_panel_favorites_header'>Run a Command</div>";

            // loop over favorites here
            favorites.forEach(function(favorite) {
                if (favorite.hasOwnProperty("uid") &&
                    favorite.hasOwnProperty("display_name") &&
                    favorite.hasOwnProperty("icon_path")) {

                    const command_id = favorite["uid"];
                    const display_name = favorite["display_name"];
                    const icon_path = favorite["icon_path"];
                    const description = favorite["description"];

                    favorites_html +=
                        "<a href='#' "  +
                            "onClick='sg_panel.Panel.trigger_command(\"" + command_id + "\", \"" + display_name + "\")'" +
                        ">" +
                            "<div class='sg_command_button' " +
                                "onmouseover='sg_panel.Panel.show_command_help(\"" + display_name + "\", \"" +description + "\", true)' " +
                                "onmouseout='sg_panel.Panel.hide_command_help()' " +
                            ">" +
                                "<center>" +
                                    "<img class='sg_panel_command_img' src='" + icon_path + "'>" +
                                "</center>" +
                            "</div>" +
                        "</a>";
                }
                // TODO: if command is missing something, log it.
            });

            favorites_html += "</div>";
        }

        // Now process the non-favorite commands

        const commands = state["commands"];
        var commands_html = "";

        if (commands.length > 0) {

            commands_html = "<div id='sg_panel_commands'>";

            commands.forEach(function(command) {
                if (command.hasOwnProperty("uid") &&
                    command.hasOwnProperty("display_name") &&
                    command.hasOwnProperty("icon_path")) {

                    const command_id = command["uid"];
                    const display_name = command["display_name"];
                    const icon_path = command["icon_path"];
                    const description = command["description"];

                    commands_html +=
                        "<div class='sg_panel_command' " +
                            "onmouseover='sg_panel.Panel.show_command_help(\"\", \"" +description + "\", false)' " +
                        "onmouseout='sg_panel.Panel.hide_command_help()' " +
                        ">" +
                        "<table style='width:100%;'>" +
                            "<colgroup>" +
                                "<col width='0%' />" +
                                "<col width='100%' />" +
                            "</colgroup>" +
                            "<tr>" +
                                "<td align='left' width='30px' style='vertical-align:middle;'>" +
                                    "<a href='#' class='sg_command_link' "  +
                                        "onClick='sg_panel.Panel.trigger_command(\"" + command_id + "\", \"" + display_name + "\")'" +
                                    ">" +
                                    "<img class='sg_panel_command_img' src='" + icon_path + "'>" +
                                    "</a>" +
                                "</td>" +
                                "<td align='left' style='padding-left:10px; vertical-align:middle; white-space:nowrap;'>" +
                                    "<a href='#' class='sg_command_link' "  +
                                        "onClick='sg_panel.Panel.trigger_command(\"" + command_id + "\", \"" + display_name + "\")'" +
                                    ">" +
                                        display_name +
                                    "</a>" +
                                "</td>" +
                            "</tr>" +
                        "</table>" +
                    "</div>";
                }
            });

            commands_html += "</div>";
        }

        _set_bg_color("#4D4D4D");

        _set_contents(favorites_html + commands_html);
        _show_contents(true);

        // make sure the progress bar and info is hidden
        _show_progress(false);
        _show_info(false);
    };

    this.show_console = function(show) {
        // Show or hide the console.

        const console_div_id = sg_constants.panel_div_ids["console"];
        const console_log_div_id = sg_constants.panel_div_ids["console_log"];

        _show_div(console_div_id, show);

        if (show) {
            _scroll_to_log_bottom();
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'visible';
        }
    };

    this.trigger_command = function(command_id, command_display) {
        // Emits the signal to launch the supplied command id.
        // Also shows a tmp message in the footer to confirm user click

        // show the progress message temporarily
        _set_info("Launching: " + command_display);
        setTimeout(_clear_info, 3000);

        // trigger the command
        sg_panel.REGISTERED_COMMAND_TRIGGERED.emit(command_id);
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
                <MenuItem Id="sg_console" \
                          Label="Console" \
                          Enabled="true" \
                          Checked="false"/> \
                <MenuItem Label="---" /> \
                <MenuItem Id="sg_dev_debug" \
                          Label="Chrome Console..." \
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

    const _make_persistent = function(persistent) {
        // Provides a way to make the panel persistent.
        //
        // Only valid for Photoshop.

        var event_type = "com.adobe.PhotoshopUnPersistent";
        if (persistent) {
            event_type = "com.adobe.PhotoshopPersistent";
        }

        var event = new CSEvent(event_type, "APPLICATION");
         event.extensionId = _cs_interface.getExtensionID();
         _cs_interface.dispatchEvent(event);
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
                self.open_external_url(debug_url);
                break;

            // reload extension
            case "sg_dev_reload":
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

            // about the extension
            case "sg_console":
                self.show_console(true);
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

        _set_bg_color("#222222");
        _clear_messages();

        const message = event.data.message;

        const stack = event.data.stack;

        sg_logging.error("Critical: " + message);

        _show_header(false);

        var contents_html = "<div class='sg_error_message'>" +
            message +
            "</div>";

        contents_html +=
            "<br>You can try link below to attempt a full restart " +
            " of the Adobe integration.<br><br>" +
            "<center>" +
            "<a href='#' onclick='sg_panel.Panel.reload()'>" +
            "Restart Shotgun Integration" +
            "</a>" +
            "</center><br>";

        const subject = encodeURIComponent("Adobe Integration Error");
        const body = _format_email_error_message(event.data);

        if (typeof stack !== "undefined") {
            contents_html +=
                "<br>If you encounter this problem consistently or have any " +
                "other questions, please send the following error and a " +
                "description of the steps to reproduce the problem to: " +
                "<a href='#' onClick='sg_panel.Panel.email_support(\"" +
                    subject + "\", \"" + body + "\")'>" +
                    "Shotgun Support" +
                "</a>." +
                "<br><br>" +
                "<center>" +
                    "<div class='sg_error'>" +
                        "<pre>" + stack + "</pre>" +
                    "</div>" +
                "</center>";
        } else {
            contents_html +=
                "<br>If you encounter this problem consistently or have any " +
                "other questions, please send the steps to reproduce to: " +
                "<a href='#' onClick='sg_panel.Panel.email_support(\"" +
                    subject + "\", \"" + body + "\")'>" +
                    "Shotgun Support" +
                "</a>.";
        }

        contents_html = "<div class='sg_container'>" + contents_html + "</div>";

        _set_contents(contents_html);
        _set_error(
            "Uh oh! Something went wrong."
        );
    };

    const _on_mouse_move = function(event) {
        _cur_mouse_pos = {
            x: event.clientX,
            y: event.clientY
        };
    };

    const _on_pyside_unavailable = function(event) {

        _set_bg_color("#222222");
        _clear_messages();

        sg_logging.error("Critical: PySide is unavailable");

        _show_header(false);

        var contents_html = "<div class='sg_error_message'>" +
            "The Shotgun integration failed to load because <samp>PySide" +
            "</samp> is not installed." +
            "</div>";

        contents_html +=
            "<br>In order for the Shotgun integration to work properly,  " +
            "<samp>PySide</samp> must be installed on your system.<br><br>" +
            "For information about <samp>PySide</samp> and how to install " +
            "it, please click the image below:<br><br><br>" +
            "<center>" +
            "<a href='#' onclick='sg_panel.Panel.open_external_url(\"" + sg_constants.pyside_url + "\")'>" +
                "<img src='../images/PySideLogo1.png' width='150px'>" +
            "</a>" +
            "</center><br>";

        const subject = encodeURIComponent("Adobe Integration Error");
        const body = encodeURIComponent(
            "Greetings Shotgun Support Team!\n\n" +
            "We have some questions about the Adobe CC Integration.\n\n" +
            "*** Please enter your questions here... ***\n\n"
        );

        contents_html +=
            "<br>Once you have <samp>PySide</samp> installed, restart this " +
            "application to load the Shotgun integration.<br><br> " +
            "If you believe the error is incorrect or you have any further " +
            "questions, please contact: " +
            "<a href='#' onClick='sg_panel.Panel.email_support(\"" +
            subject + "\", \"" + body + "\")'>" +
            "Shotgun Support" +
            "</a>.";

        contents_html = "<div class='sg_container'>" + contents_html + "</div>";

        _set_contents(contents_html);
        _set_error(
            "Uh Oh! Could not find <samp>PySide</samp>."
        );
    };

    const _on_logged_message = function(event) {
        // Handles incoming log messages
        var level = event.data.level;
        var msg = event.data.message;

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
            matches.forEach(function (match) {
                const single_regex = new RegExp(regex_str, "m");
                const msg_parts = match.match(single_regex);
                // the regex returns the progress value as a float at
                // position 1 of the match. position 3 is the message
                _set_progress_info(msg_parts[1] * 100, msg_parts[3]);
            });

            return;
        }

        // forward to the js console
        console[level](msg);
    };

    const _override_console_logging = function () {

        var console = window.console;
        if (!console) return;

        // keep a reference to the original console methods we want to intercept
        const original_methods = {
            debug: console.debug,
            info: console.info,
            error: console.error,
            warn: console.warn,
            log: console.log,
            python: console.log
        };

        const console_intercept = function(log_level) {
            // this function overrides the supplied log_level console method.

            console[log_level] = function () {
                // overriding log_level console method.

                // the original arguments
                var message = Array.prototype.slice.apply(arguments).join("\n");

                // keep track of where the log message came from. we display
                // python messages slightly different than js messages.
                var log_source = "js";
                if (log_level === "python") {
                    // This log message came from python. See if we can
                    // determine the real log level from the beginning
                    // of the message. This allows the messages to
                    // display properly in both the chrome debug console
                    // and our own console in the panel. NOTE: if the
                    // formatting of the python logs changes, this may
                    // not work.
                    log_source = "py";
                }

                // since messages can come across in bundles, if this portion is
                // not the same log level as the first one in the bundle, we
                // need to pass it over to the proper log method.
                const messages = message.split("\n");

                // if we're in a bundle of log messages, remember the previous
                // log level to use as a default for subsequent lines.
                var previous_log_level = log_level;

                // loop over the message lines and log them.
                messages.forEach(function(message) {

                    // next if nothing in the message
                    if (!message) { return; }

                    // use some hackery to determine the actual log level for
                    // this line in the message
                    const actual_log_level = _get_actual_log_level(message,
                        previous_log_level);

                    if (actual_log_level == "debug") {
                        message = message.replace("DEBUG: ", "");
                    } else if (actual_log_level == "warn") {
                        message = message.replace("WARNING: ", "");
                    } else if (actual_log_level == "error") {
                        message = message.replace("ERROR: ", "");
                    } else if (actual_log_level == "info") {
                        message = message.replace("INFO: ", "");
                    }

                    // forward the log message to the panel's console
                    _forward_to_panel_console(actual_log_level, message, log_source);

                    if (log_source == "py") {
                        // prefix the message with '[python]:` for chrome console
                        message = "[python]: " + message;
                    }

                    // call the original log method to log to the chrome console
                    original_methods[actual_log_level].apply(console, [message]);

                    // remember the current log level for use in next iteration
                    previous_log_level = actual_log_level;
                });
            }
        };

        // now call the intercept method on each of the console method names
        var log_levels = ["log", "warn", "error", "debug", "info", "python"];
        log_levels.forEach(function(log_level) {
            console_intercept(log_level)
        });
    };

    const _forward_to_panel_console = function(level, msg, log_source) {
        // make the message pretty and add it to the panel's console log

        // remove trailing newline
        msg = msg.replace(/\n$/, "");

        // figure out which div id to use for style/color
        var div_id = "sg_log_message";
        if (level == "debug") {
            div_id = "sg_log_message_debug"
        } else if (level == "warn") {
            div_id = "sg_log_message_warn"
        } else if (level == "error") {
            div_id = "sg_log_message_error"
        }

        // just a little indicator so that we know if the log message came from
        // (javascript or python) when looking in the panel console.
        if (log_source == "js") {
            msg = " > " + msg;
        } else {
            msg = ">> " + msg;
        }

        // create a <pre> element and insert the msg
        const node = document.createElement("pre");
        node.setAttribute("id", div_id);
        node.appendChild(document.createTextNode(msg));

        // append the <pre> element to the log div
        const log = document.getElementById("sg_panel_console_log");
        log.appendChild(node);
        log.appendChild(document.createElement("br"));

        // scroll to the bottom if an error occurs
        if (["error", "critical"].indexOf(level) >= 0) {
            _scroll_to_log_bottom();
        }
    };

    const _get_actual_log_level = function(msg, default_level) {
        // given a log message, do some inspection to see if we can deduce the
        // actual log level from the string. if not, fall back to the supplied
        // default value.

        var level = default_level;

        if (msg.startsWith("DEBUG:")) {
            level = "debug";
        } else if (msg.startsWith("INFO:")) {
            level = "info";
        } else if (msg.startsWith("WARNING:")) {
            level = "warn";
        } else if (msg.startsWith("ERROR:")) {
            level = "error";
        } else if (msg.startsWith("CRITICAL:")) {
            level = "error";
        }

        return level
    };

    const _scroll_to_log_bottom = function() {
        // scroll to the bottom of the div

        const console_log_div_id = sg_constants.panel_div_ids["console_log"];
        const log = document.getElementById(console_log_div_id);
        log.scrollTop = log.scrollHeight;
    };

    const _select_text = function(div_id) {
        // Select all the text within the provided div

        // TODO: add a button for this in the console

        if (document.selection) {
            const range = document.body.createTextRange();
            range.moveToElementText(document.getElementById(div_id));
            range.select();
        } else if (window.getSelection) {
            const range = document.createRange();
            range.selectNode(document.getElementById(div_id));
            window.getSelection().addRange(range);
        }
    };

    const _setup_event_listeners = function() {
        // Sets up all the event handling callbacks.

        // Handle python process disconnected
        sg_manager.CRITICAL_ERROR.connect(_on_critical_error);

        // Handle pyside not being installed
        sg_manager.PYSIDE_NOT_AVAILABLE.connect(_on_pyside_unavailable);

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

    // set html for div

    const _set_div_html = function(div_id, html) {
        // Updates the inner HTML of the supplied div with the supplied HTML
        _show_div(div_id, true);
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
    const _set_info = _set_div_html_by_id("info");
    const _set_error = _set_div_html_by_id("error");
    const _set_warning = _set_div_html_by_id("warning");
    const _set_command_help = _set_div_html_by_id("command_help");

    // ---- progress bar methods

    const _set_progress_info = function(progress, message) {
        // Update the progress section with a % and a message.
        _show_progress(true);
        _show_info(true);
        var elem = document.getElementById(
            sg_constants.panel_div_ids["progress_bar"]);
        elem.style.width = progress + '%';
        _set_info(message);
    };

    // show/hide divs

    const _show_div = function(div_id, show_or_hide) {
        // Show or hide a div
        var display = "none";  // hide
        if (show_or_hide) {
            display = "block"; // show
        }
        var elem = document.getElementById(div_id);
        elem.style.display = display;
    };

    const _show_div_by_id = function(div_id) {
        return function(show_or_hide) {
            // Convenience method for showing/hiding divs
            _show_div(sg_constants.panel_div_ids[div_id], show_or_hide);
        }
    };

    // convenience methods for showing/hiding status divs
    const _show_header = _show_div_by_id("header");
    const _show_contents = _show_div_by_id("contents");
    const _show_info = _show_div_by_id("info");
    const _show_error = _show_div_by_id("error");
    const _show_warning = _show_div_by_id("warning");
    const _show_progress = _show_div_by_id("progress");
    const _show_command_help = _show_div_by_id("command_help");

    const _set_bg_color = function(color) {
        document.body.style.background = color;
    };

    const _clear_messages = function() {
        _show_info(false);
        _show_error(false);
        _show_warning(false);
        _show_progress(false);
        _show_command_help(false);
    };

    const _clear_info = function() {
        _show_info(false);
        _show_progress(false);
    };

    const _format_email_error_message = function(error) {

        const message = error.message;
        const stack = error.stack;

        return encodeURIComponent(
            "Greetings Shotgun Support Team!\n\n" +
            "We are experiencing some difficulties with the Adobe CC Integration. " +
            "The details are included below.\n\n" +
            "Summary of the issue:\n\n" +
            "*** Please enter a summary of the issue here... ***\n\n" +
            "Steps to reproduce:\n\n" +
            "*** Please enter the steps you took to reach this error here. ***\n\n" +
            "Error displayed to the user:\n\n" +
            message + "\n\n" +
            "Stack trace:\n\n" +
            stack + "\n\n"
        );

        // TODO: include current version info of core, app, CC, etc.
    };
};

// TODO: state should provide header info
// TODO: mouse over icon should highlight text
