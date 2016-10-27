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


sg_manager.Manager = new function() {
    // A singleton "class" to manage the Shotgun integration layers
    //   * python bootstrap
    //   * communication with the panel
    //   * communication with adobe api (extendscript) via socket.io

    // ---- private vars

    // keep a handle on the instance.
    var self = this;

    // adobe interface
    var _cs_interface = new CSInterface();

    // the name of the python process extension
    var _panel_extension_name = "com.shotgunsoftware.basic.adobecc.panel";

    // ---- public methods

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        // Execute the startup payload and catch *any* errors. If there are
        // errors, display them on the status page.
        try {

            // ensure this app is supported by our extension
            if (!_app_is_supported()) {
                // TODO: more information about why
                sg_logging.warning("This application does not support the Shotgun extension.");
                return;
            }

            // setup event listeners so that we can react to messages as they
            // come in.
            _setup_event_listeners();

            // start up the panel in the adobe product first. we can display
            // messages and information to the user while functions below are
            // running
            _panel_startup();

            // TODO: send the panel progress callback to the methods below

            // TODO: Figure out how to autogenerate a port number.
            var port = 8090;
            sg_socket_io.SocketManager.start_socket_server(port, _cs_interface);

            // TODO: python process should send context/state once bootstrapped

            // bootstrap the python process.
            _python_bootstrap();

        } catch (error) {
            sg_logging.error("Manager startup error: " + error.stack);
            alert("Manager startup error: " + error.stack); // XXX temp
            // TODO: send failure event with error data to display in panel if it is running.
        }
    };

    this.on_unload = function() {
        // code to run when the extension panel is unloaded

        // TODO: not sure this is ever called!

        _shutdown_py_process();

        // TODO: shut down socket.io server
        // TODO: close the panel extension
            // (send event to tell it to shut itself down since we can't do it from here)
    };

    var _shutdown_py_process = function() {

        // make sure the python process is shut down
        if (typeof self.python_process !== "undefined") {
            sg_logging.debug("Terminating python process...");
            try {
                self.python_process.kill();
                sg_logging.debug("Python process terminated successfully.");
            } catch(error) {
                sg_logging.warning("Unable to terminate python process: " + error.stack);
            }
        }
    };

    // ---- private methods

    var _app_is_supported = function() {
        // Tests whether the extension can run with the current application

        // supported if the panel menu and html extensions are available
        var host_capabilities = _cs_interface.getHostCapabilities();
        return host_capabilities.EXTENDED_PANEL_MENU &&
            host_capabilities.SUPPORT_HTML_EXTENSIONS;
    };

    var _panel_startup = function() {
        // Start up the panel

        sg_logging.debug("Launching the panel extension...");
        _cs_interface.requestOpenExtension(_panel_extension_name);
    };


    // TODO: add a progress callback
    var _python_bootstrap = function() {
        // Bootstrap the toolkit python process.
        //
        // Returns a `child_process.ChildProcess` object for the running
        // python process with a bootstrapped toolkit core.

        const child_process = require("child_process");
        const path = require('path');

        // the path to this extension
        var ext_dir = _cs_interface.getSystemPath(SystemPath.EXTENSION);

        // path to the python folder within the extension
        var plugin_python_path = path.join(ext_dir, "python");

        // get a copy of the current environment and append to PYTHONPATH.
        // we need to append the plugin's python path so that it can locate the
        // manifest and other files necessary for the bootstrap.
        var current_env = process.env;
        if (process.env["PYTHONPATH"]) {
            // append the plugin's python path to the existing env var
            process.env.PYTHONPATH += ":" + plugin_python_path;
        } else {
            // no PYTHONPATH set. set it to the plugin python path
            process.env.PYTHONPATH = plugin_python_path;
        }

        // get the bootstrap python script from the bootstrap python dir
        var plugin_bootstrap_py = path.join(plugin_python_path,
            "plugin_bootstrap.py");

        sg_logging.debug("Bootstrapping: " + plugin_bootstrap_py);

        // launch a separate process to bootstrap python with toolkit running...
        // > cd $ext_dir
        // > python /path/to/ext/bootstrap.py
        sg_logging.debug("Spawning child process... ");
        try {
            self.python_process = child_process.spawn(
                // TODO: which python to use
                "/Applications/Shotgun.app/Contents/Resources/Python/bin/python",
                [
                    // path to the python bootstrap script
                    plugin_bootstrap_py
                    // TODO: other args here (ex: port)
                ],
                {
                    // start the process from this dir
                    cwd: plugin_python_path,
                    // the environment to use for bootstrapping
                    env: process.env
                }
            );
            sg_logging.debug("Child process spawned! PID: " + self.python_process.pid)
        }
        catch (error) {
            sg_logging.error("Child process failed to spawn:  " + error);
            throw error;
        }

        // XXX begin temporary process communication

        // log stdout from python process
        self.python_process.stdout.on("data", function (data) {
            sg_logging.debug(data.toString());
        });

        // log stderr from python process
        self.python_process.stderr.on("data", function (data) {
            sg_logging.debug(data.toString());
        });

        // XXX end temporary process communication

        // handle python process disconnection
        self.python_process.on("close", _on_python_connection_lost);

    };

    var _on_python_connection_lost = function() {

        sg_manager.PYTHON_PROCESS_DISCONNECTED.emit();
    };



    var _reload = function(event) {

        // shutdown the python process
        _shutdown_py_process();

        // remember this extension id to reload it
        var extension_id = _cs_interface.getExtensionID();

        // close the extension
        self.on_unload();
        sg_logging.debug("Closing the python extension.");
        _cs_interface.closeExtension();

        // request relaunch
        sg_logging.debug("Relaunching the manager...");
        _cs_interface.requestOpenExtension(extension_id);
    };

    var _setup_event_listeners = function() {
        // setup listeners for any events that need to be processed by the
        // manager

        sg_panel.REQUEST_MANAGER_RELOAD.connect(_reload);

        // TODO:
        // until the socket.io layer is inserted, simply send
        // back some mock state info for the panel. eventually this
        // should post the request to the socket.io channel that the
        // python process is listening to. The python process should
        // process the request and send back to the server all the
        // state information (current context, registered commands, etc)
        sg_panel.REQUEST_STATE.connect(_tmp_send_state_info);

        // Handle python process disconnected
        sg_panel.REGISTERED_COMMAND_TRIGGERED.connect(
            // TODO: do the proper thing here...
            function(event) {
                alert("panel.js: Registered Command Triggered: " + event.data)
            }
        );

    };

    var _tmp_send_state_info = function(event) {

        // XXX This is temp sim of the state being sent from python
        var state = {
            context: {
                display: "Awesome Asset 01"
            },
            commands: [
                {
                    id: "command_id_1",
                    display_name: "Python Console",
                    icon_path: "../images/tmp/command1.png"
                },
                {
                    id: "command_id_2",
                    display_name: "Command B",
                    icon_path: "../images/tmp/command2.png"
                },
                {
                    id: "command_id_3",
                    display_name: "Command C",
                    icon_path: "../images/tmp/command3.png"
                },
                {
                    id: "command_id_4",
                    display_name: "Command D",
                    icon_path: "../images/tmp/command4.png"
                }
            ]
        };

        sg_manager.UPDATE_STATE.emit(state);
        // XXX End temporary simulation
    };
};

