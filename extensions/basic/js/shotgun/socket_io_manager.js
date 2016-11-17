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
var sg_socket_io = sg_socket_io || {};

sg_socket_io.io = undefined;

sg_socket_io.emit = function(message_type, payload) {
    // Emits the provided payload stringified as JSON via the
    // currently open socket.io server.
    if ( sg_socket_io.io != undefined ) {
        sg_socket_io.io.emit(message_type, JSON.stringify(payload));
    }
};

sg_socket_io.rpc_log = function(level, message) {
    // Emits a "logging" message from the currently open socket.io
    // server. The log message string and level are combined into
    // a single payload object with "level" and "message" properties
    // that is JSON encoded before emission.
    var msg = {};
    msg.level = level;
    msg.message = message;
    sg_socket_io.emit("logging", msg);
};

sg_socket_io.rpc_command = function(uid) {
    // Emits a "command" message from the currently open socket.io
    // server. The given uid references an SGTK engine command by
    // the same id, which will be used to look up the appropriate
    // callback once the message is handled by a client.
    sg_socket_io.emit("command", uid);
};

sg_socket_io.SocketManager = new function() {
    var self = this;
    var io = undefined;

    var sanitize_path = function(file_path) {
        // Replaces Windows-style backslash paths with forward slashes.
        return file_path.replace(RegExp('\\\\', 'g'), '/');
    };

    var _eval_callback = function(next, result) {
        // The callback attached to each JSON-RPC call that's made.
        // TODO: Using false here as the first argument is saying
        // "no, there weren't any errors." We need to check the
        // result data structure here and make that determination
        // instead of always assuming success.
        next(false, result);
    };

    this.start_socket_server = function (port, csLib) {
        var path = require('path');
        var jrpc = require('jrpc');
        var io = require('socket.io').listen(port);
        sg_socket_io.io = io;

        sg_logging.info("Listening on port " + JSON.stringify(port));

        // Get the path to the extension.
        var ext_dir = csLib.getSystemPath(SystemPath.APPLICATION);
        var js_dir = path.join(ext_dir, "js", "shotgun");

        // Tell ExtendScript to load the rpc.jsx file that contains our
        // helper functions.
        var jsx_rpc_path = sanitize_path(path.join(js_dir, "ECMA", "rpc.jsx"));
        csLib.evalScript('$.evalFile("' + jsx_rpc_path + '")');

        sg_logging.info("Establishing jrpc interface.");

        function RPCInterface() {
            // The object that defines the JSON-RPC interface exposed
            // by the socket.io server. Each method on this object
            // becomes a callable method over the socket.io connection.

            this.get_global_scope = function(params, next) {
                // Maps the global scope of ExtendScript and returns a
                // list of wrapper objects as JSON data. Each wrapper
                // describes the object, its properties, and its methods.
                //
                // Args: N/A
                csLib.evalScript(
                    "map_global_scope()",
                    _eval_callback.bind(self, next)
                );
            };

            this.eval = function(params, next) {
                // Evalualtes an arbitrary string of Javascript in
                // ExtendScript and returns the resulting data.
                //
                // Args: [extendscript_command]
                csLib.evalScript(params[0], function(result) {
                    next(false, result);
                });
            };

            this.new = function(params, next) {
                // Instantiates an object for the given global-scope
                // class. The given class name must be available in the
                // global scope of ExtendScript at call time.
                //
                // Args: [class_name]
                var class_name = JSON.stringify(params.shift());
                var cmd = "rpc_new(" + class_name + ")";
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.get = function(params, next) {
                // Gets the value of the given property on the given object.
                //
                // Args: [object, property_name]
                var base = JSON.parse(params.shift());
                var property = params.shift();
                var args = [base.__uniqueid, JSON.stringify(property)].join();

                var cmd = "rpc_get(" + args + ")";
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.get_index = function(params, next) {
                // Gets the value for the given index number on the given
                // iterable object.
                //
                // Args: [object, index]
                var base = JSON.parse(params.shift());
                var index = JSON.stringify(params.shift());
                var args = [base.__uniqueid, index].join();

                var cmd = "rpc_get_index(" + args + ")";
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.set = function(params, next) {
                // Sets the value of the given property on the given object.
                //
                // Args: [object, property_name, value]
                var base = JSON.parse(params.shift());
                var property = params.shift();
                var value = params.shift();
                var args = [
                    base.__uniqueid,
                    JSON.stringify(property),
                    JSON.stringify(value)
                ].join();

                var cmd = "rpc_set(" + args + ")";
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.call = function(params, next) {
                // Calls the given method on the given object.
                //
                // Args: [method_wrapper, parent_uid, method_arg_1, method_arg_2, ...]
                var base = JSON.parse(params.shift());
                // The parent object of the method being called. Since we
                // need to know what the method is bound to in order to
                // actually call it (foo.bar(), with "foo" being the parent
                // object identified by its unique id, and "bar" being the
                // method itself being called.
                var parent_uid = params.shift();

                var args = [
                    base.__uniqueid,
                    JSON.stringify(params),
                    parent_uid
                ].join();

                if ( args.endsWith(",") ) {
                    args = args + "-1";
                }

                var cmd = "rpc_call(" + args + ")";
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

        };

        this.stop_socket_server = function() {
            sg_logging.debug("Shutting down socket server.")

            // TODO: properly shut down the socket server
        };

        sg_logging.info("Setting up connection handling...");

        // Define the root namespace interface. This will receive all
        // commands for interacting with ExtendScript.
        io.on("connection", function(socket) {
            sg_logging.info("Connection received!");

            var remote = new jrpc();
            remote.expose(new RPCInterface());

            socket.on("execute_command", function(message) {
                sg_logging.info(JSON.stringify(message));
                remote.receive(message);
            });

            socket.on("set_state", function(json_state) {
                // The client is setting the state.
                var state = JSON.parse(json_state);
                sg_logging.debug("Setting state from client: " +
                    state["context"]["display"]);

                // TODO: we're emitting a manager event. perhaps we should
                // have a set of events that come from socket.io? or perhaps
                // this should call a method on the manager (tried, but doesn't
                // seem to work!)? but this shouldn't really know about the
                // manager. anyway, this works, so revisit as time permits.
                sg_manager.UPDATE_STATE.emit(state);
            });

            remote.setTransmitter(function(message, next) {
                try {
                    io.emit("return", message);
                    return next(false);
                } catch (e) {
                    return next(true);
                }
            });
        });
    };
};
