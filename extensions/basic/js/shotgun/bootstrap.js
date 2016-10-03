// Copyright (c) 2016 Shotgun Software Inc.
//
// CONFIDENTIAL AND PROPRIETARY
//
// This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
// Source Code License included in this distribution package. See LICENSE.
// By accessing, using, copying or modifying this work you indicate your
// agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
// not expressly granted therein are reserved by Shotgun Software Inc.

// figure out the python folder
// put together python bootstrap command
// get the path to the extension

// namespace
var sg_bootstrap = sg_bootstrap || {};

sg_bootstrap.bootstrap = function(ext_dir) {
    // Bootstrap the toolkit python process.
    //
    // Returns a `child_process.ChildProcess` object for the running
    // python process with a bootstrapped toolkit core.

    const child_process = require("child_process");
    const path = require('path');

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

    console.log("Bootstrapping: " + plugin_bootstrap_py);

    // launch a separate process to bootstrap python with toolkit running...
    // > cd $ext_dir
    // > python /path/to/ext/bootstrap.py
    console.log("Spawning child process... ");
    try {
        var python_process = child_process.spawn(
            // TODO: default to Desktop python if found?
            // TODO: fall back to system python
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
        console.log("Child process spawned! PID: " + python_process.pid)
    }
    catch (err) {
        console.log("Child process failed to spawn:  " + err)
    }

    return python_process;
};

