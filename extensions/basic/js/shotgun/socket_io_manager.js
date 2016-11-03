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

sg_socket_io.SocketManager = new function() {
    var self = this;

    var sanitize_path = function(file_path) {
        // Replaces Windows-style backslash paths with forward slashes.
        return file_path.replace(RegExp('\\\\', 'g'), '/');
    };

    var _eval_callback = function(next, result) {
        next(false, result);
    };

    this.start_socket_server = function (port, csLib) {
        var path = require('path');
        var jrpc = require('jrpc');
        var io = require('socket.io').listen(port);

        sg_logging.info('Listening on port ' + JSON.stringify(port));

        // Get the path to the extension.
        var ext_dir = csLib.getSystemPath(SystemPath.APPLICATION);
        var js_dir = path.join(ext_dir, "js", "shotgun");

        // Tell ExtendScript to load the rpc.jsx file that contains our
        // helper functions.
        var jsx_rpc_path = sanitize_path(path.join(js_dir, 'ECMA', 'rpc.jsx'));
        csLib.evalScript('$.evalFile("' + jsx_rpc_path + '")');

        sg_logging.info('Establishing jrpc interface.');

        function RPCInterface() {
            // TODO: Logging will most likely go into its own namespace with
            // its own JSON-RPC interface. This is temporary as a result.
            this.log = function(params, next) {
                sg_logging.info(JSON.stringify(params));
                next(false, undefined);
            };

            this.get_global_scope = function(params, next) {
                csLib.evalScript(
                    'map_global_scope()',
                    _eval_callback.bind(self, next)
                );
            };

            this.eval = function(params, next) {
                csLib.evalScript(params[0], function(result) {
                    next(false, result);
                });
            };

            this.new = function(params, next) {
                var class_name = JSON.stringify(params.shift());
                var cmd = 'rpc_new(' + class_name + ')';
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.get = function(params, next) {
                var base = JSON.parse(params.shift());
                var property = params.shift();
                var args = [base.__uniqueid, JSON.stringify(property)].join();

                var cmd = 'rpc_get(' + args + ')';
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.get_index = function(params, next) {
                var base = JSON.parse(params.shift());
                var index = JSON.stringify(params.shift());
                var args = [base.__uniqueid, index].join();

                var cmd = 'rpc_get_index(' + args + ')';
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.set = function(params, next) {
                var base = JSON.parse(params.shift());
                var property = params.shift();
                var value = params.shift();
                var args = [
                    base.__uniqueid,
                    JSON.stringify(property),
                    JSON.stringify(value)
                ].join();

                var cmd = 'rpc_set(' + args + ')';
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };

            this.call = function(params, next) {
                var base = JSON.parse(params.shift());
                var parent_uid = params.shift();

                var args = [
                    base.__uniqueid,
                    JSON.stringify(params),
                    parent_uid
                ].join();

                if ( args.endsWith(',') ) {
                    args = args + "-1";
                }

                var cmd = 'rpc_call(' + args + ')';
                sg_logging.info(cmd);

                csLib.evalScript(
                    cmd,
                    _eval_callback.bind(self, next)
                );
            };
        };

        sg_logging.info('Setting up connection handling...');

        // Define the root namespace interface. This will receive all
        // commands for interacting with ExtendScript.
        io.on('connection', function(socket) {
            sg_logging.info('Connection received!');

            var remote = new jrpc();
            remote.expose(new RPCInterface());

            socket.on('execute_command', function(message) {
                sg_logging.info(JSON.stringify(message));
                remote.receive(message);
            });

            remote.setTransmitter(function(message, next) {
                try {
                    io.emit('return', message);
                    return next(false);
                } catch (e) {
                    return next(true);
                }
            });
        });
    };
};
