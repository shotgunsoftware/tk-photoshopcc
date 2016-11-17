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

    // ---- public data members

    // the port we'll be communicating over
    this.communication_port = undefined;

    // ---- private

    // keep a handle on the instance.
    const self = this;

    // adobe interface
    const _cs_interface = new CSInterface();

    // the name of the python process extension
    const _panel_extension_name = "com.shotgunsoftware.basic.adobecc.panel";

    // ---- public methods

    this.on_load = function() {
        // Setup the Shotgun integration within the app.

        // Execute the startup payload and catch *any* errors. If there are
        // errors, display them in the panel if possible.
        try {

            // ensure this app is supported by our extension
            if (!_app_is_supported()) {
                sg_logging.warning(
                    "This CC product does not meet the minimum requirements " +
                    "to run the Shotgun integration. The Shotgun integration " +
                    "requires support for HTML panels and the extended panel " +
                    "menu."
                );
                return;
            }

            // setup event listeners so that we can react to messages as they
            // come in.
            _setup_event_listeners();

            // start up the panel in the adobe product first. we can display
            // messages and information to the user while functions below are
            // running
            sg_logging.debug("Launching the panel extension...");
            _cs_interface.requestOpenExtension(_panel_extension_name);

            // Look for an open port to use for the server. Once a port has been
            // found, this method will directly call the supplied callback
            // method to start up the server and then bootstrap python.
            _get_open_port(_on_server_port_found);

        } catch (error) {
            const message = "There was an unexpected error startup of the " +
                "startup of the Shotgun integration. Please see the " +
                "attached stack trace.";

            // log the error in the event that the panel has started and the
            // user can click the console
            sg_logging.error(message);
            sg_logging.error(error.stack);

            // emit the critical error for any listeners to display
            sg_manager.CRITICAL_ERROR.emit({
                message: message,
                stack: error.stack
            });

            // There are no guarantees that the panel has started up, and
            // therefore no guarantees that the user has easy access to the
            // debug console. Go ahead and display an old school alert box here
            // to ensure that they get something. This may look like crap.
            alert(message + "\n\n" + error.stack);
        }
    };

    this.on_unload = function() {
        // Code to run when the manager extension is unloaded

        // This callback never seems to run. This could be because this is an
        // "invisible" extension, but it seems like even regular panels never
        // have their page "unload" callbacks called. Leaving this here for now
        // in the event that this becomes called at some point in the future.
        self.shutdown();
    };

    this.set_state = function(state) {
        // Sets the manager state.

        // emits the state update for listeners to respond to
        sg_manager.UPDATE_STATE.emit(state);
    };

    this.shutdown = function() {
        // Ensure all the manager's components are shutdown properly
        //
        // Also emits an event for listeners to respond to manager shutdown.

        // shut down socket.io server
        sg_socket_io.SocketManager.stop_socket_server();

        // alert listeners that the manager is shutting down
        sg_manager.SHUTTING_DOWN.emit();

        // ensure the python process is shut down
        if (typeof self.python_process !== "undefined") {
            sg_logging.debug("Terminating python process...");
            try {
                self.python_process.kill();
                sg_logging.debug("Python process terminated successfully.");
            } catch(error) {
                sg_logging.warning(
                    "Unable to terminate python process: " + error.stack);
            }
        }
    };

    // ---- private methods

    const _app_is_supported = function() {
        // Tests whether the extension can run with the current application

        // supported if the panel menu and html extensions are available
        const host_capabilities = _cs_interface.getHostCapabilities();
        return host_capabilities.EXTENDED_PANEL_MENU &&
            host_capabilities.SUPPORT_HTML_EXTENSIONS;
    };

    // TODO: add a progress callback
    const _bootstrap_python = function(port) {
        // Bootstrap the toolkit python process.
        //
        // Returns a `child_process.ChildProcess` object for the running
        // python process with a bootstrapped toolkit core.

        const app_id = _cs_interface.hostEnvironment.appId;
        const child_process = require("child_process");
        const path = require('path');
        const engine_name = sg_constants.product_info[app_id].tk_engine_name;

        // the path to this extension
        const ext_dir = _cs_interface.getSystemPath(SystemPath.EXTENSION);

        // path to the python folder within the extension
        const plugin_python_path = path.join(ext_dir, "python");

        // get a copy of the current environment and append to PYTHONPATH.
        // we need to append the plugin's python path so that it can locate the
        // manifest and other files necessary for the bootstrap.
        if (process.env.PYTHONPATH) {
            // append the plugin's python path to the existing env var
            process.env.PYTHONPATH += ":" + plugin_python_path;
        } else {
            // no PYTHONPATH set. set it to the plugin python path
            process.env.PYTHONPATH = plugin_python_path;
        }

        // Set the port in the environment. The engine will use this when
        // establishing a socket client connection.
        process.env.SHOTGUN_ADOBE_PORT = port;

        // get the bootstrap python script from the bootstrap python dir
        const plugin_bootstrap_py = path.join(plugin_python_path,
            "plugin_bootstrap.py");

        sg_logging.debug("Bootstrapping: " + plugin_bootstrap_py);

        // TODO: proper python executable discovery

        // launch a separate process to bootstrap python with toolkit running...
        // > cd $ext_dir
        // > python /path/to/ext/bootstrap.py
        var python_exe_path = "/Applications/Shotgun.app/Contents/Resources/Python/bin/python";

        if (process.env["SHOTGUN_ADOBECC_PYTHON"]) {
            python_exe_path = process.env.SHOTGUN_ADOBECC_PYTHON;
        }

        sg_logging.debug("Spawning child process... ");
        sg_logging.debug("Using Python: " + python_exe_path);

        try {
            self.python_process = child_process.spawn(
                // TODO: which python to use
                python_exe_path,
                [
                    // path to the python bootstrap script
                    plugin_bootstrap_py,
                    port,
                    engine_name
                ],
                {
                    // start the process from this dir
                    cwd: plugin_python_path,
                    // the environment to use for bootstrapping
                    env: process.env,
                }
            );
        }
        catch (error) {
            sg_logging.error("Child process failed to spawn:  " + error);
            throw error;
        }

        sg_logging.debug("Child process spawned! PID: " + self.python_process.pid)

        // XXX begin temporary process communication

        // log stdout from python process
        self.python_process.stdout.on("data", function (data) {
            sg_logging.log(data.toString());
        });

        // log stderr from python process
        self.python_process.stderr.on("data", function (data) {
            sg_logging.log(data.toString());
        });

        // XXX end temporary process communication

        // handle python process disconnection
        self.python_process.on(
            "close",
            function() {
                sg_manager.CRITICAL_ERROR.emit({
                    message: "The Shotgun integration has unexpectedly shut " +
                             "down. Specifically, the python process that " +
                             "handles the communication with Shotgun has " +
                             "been terminated.",
                    stack: undefined
                });
            }
        );
    };

    const _get_open_port = function(port_found_callback) {
        // Find an open port and send it to the supplied callback

        // TODO: allow specification of an explicit port to use for debugging
        //    perhaps something that is exposed during the build process?

        // https://nodejs.org/api/http.html#http_class_http_server
        const http = require('http');

        // keep track of how many times we've tried to find an open port
        var num_tries = 0;

        // the number of times to try to find an open port
        const max_tries = 25;

        // function to try a port. recurses until a port is found or the max
        // try limit is reached.
        const _try_port = function() {

            num_tries += 1;

            // double checking whether we need to continue here. this should
            // prevent this method from being called after a suitable port has
            // been identified.
            if (typeof self.communication_port !== "undefined") {
                // the port is defined. no need to continue
                return;
            }

            // check the current number of tries. if too many, emit a signal
            // indicating that a port could not be found
            if (num_tries > max_tries) {
                sg_manager.CRITICAL_ERROR.emit({
                    message: "Unable to set up the communication server that " +
                             "allows the shotgun integration to work. " +
                             "Specifically, there was a problem identifying " +
                             "a port to start up the server.",
                    stack: undefined
                });
                return;
            }

            // our method to find an open port seems a bit hacky, and not
            // entirely failsafe, but hopefully good enough. if you're reading
            // this and know a better way to get an open port, please make
            // changes.

            // the logic here is to create an http server, and provide 0 to
            // listen(). the OS will provide a random port number. it is *NOT*
            // guaranteed to be an open port, so we wait until the listening
            // event is fired before presuming it can be used. we close the
            // server before proceeding and there's no guarantee that some other
            // process won't start using it before our communication server is
            // started up.
            const server = http.createServer();

            // if we can listen to the port then we're using it and nobody else
            // is. close out and forward the port on for use by the
            // communication server
            server.on(
                "listening",
                function() {
                    // listening, so the port is available
                    self.communication_port = server.address().port;
                    server.close();
                }
            );

            // if we get an error, we presume that the port is already in use.
            server.on(
                "error",
                function(error) {
                    const port = server.address().port;
                    sg_logging.debug("Could not listen on port: " + port);
                    // will close after this event
                }
            );

            // when the server is closed, check to see if we got a port number.
            // if so, call the callback. if not, try again
            server.on(
                "close",
                function() {
                    if (typeof self.communication_port !== "undefined") {
                        // the port is defined. no need to continue
                        const port = self.communication_port;
                        sg_logging.debug("Found available port: " + port);
                        try {
                            port_found_callback(port);
                        } catch(error) {
                            sg_manager.CRITICAL_ERROR.emit({
                                message: "Unable to set up the communication " +
                                         "server that allows the shotgun " +
                                         "integration to work.",
                                stack: error.stack
                            });
                        }
                    } else {
                        // still no port. try again
                        _try_port();
                    }
                }
            );

            // now that we've setup the event callbacks, tell the server to
            // listen to a port assigned by the OS.
            server.listen(0);
        };

        // initiate the port finding
        _try_port();
    };

    const _on_server_port_found = function(port) {

        // TODO: docs. anything else? channels?
        sg_socket_io.SocketManager.start_socket_server(port, _cs_interface);

        // Register the socket manager for logging.
        sg_logging.rpc = sg_socket_io;

        // bootstrap the python process.
        _bootstrap_python(
            port
            // TODO: send a progress callback here
        );

        // TODO: python process should send context/state once bootstrapped
    };

    const _reload = function(event) {

        sg_logging.debug("Reloading the manager...");

        // shutdown the python process
        self.shutdown();

        // remember this extension id to reload it
        const extension_id = _cs_interface.getExtensionID();

        // close the extension
        self.on_unload();
        sg_logging.debug(" Closing the python extension.");
        _cs_interface.closeExtension();

        // request relaunch
        sg_logging.debug(" Relaunching the manager...");
        _cs_interface.requestOpenExtension(extension_id);
    };

    const _setup_event_listeners = function() {
        // setup listeners for any events that need to be processed by the
        // manager

        // ---- Events from the panel
        sg_panel.REQUEST_MANAGER_RELOAD.connect(_reload);

        // Handle python process disconnected
        sg_panel.REGISTERED_COMMAND_TRIGGERED.connect(
            // TODO: do the proper thing here...
            // TODO: post an event for the client to handle
            function(event) {
                sg_logging.debug("Registered Command Triggered: " + event.data)
                sg_socket_io.rpc_command(event.data)
            }
        );

    };
};

