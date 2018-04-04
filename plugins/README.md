# Extension Development

This section is designed for developers and covers how to setup, build, and test
the Shotgun Photoshop CC extension.

For more information about Adobe CEP extensions, here are some useful resources:

* [CEP Resources (Github)](https://github.com/Adobe-CEP/CEP-Resources)
* [David Berranca's Blog](http://www.davidebarranca.com/)
* [A Short Guide to HTML5 Extensions (Adobe)](http://www.adobe.com/devnet/creativesuite/articles/a-short-guide-to-HTML5-extensions.html)

## Building & Testing

Building the extension requires a little bit of setup. The following sections
cover the prerequisites and various scenarios for building and testing the
extension.

### OS-specific CEP extensions install directories:

All Adobe extensions live in a single directory. The directory is specific to
the current OS. Here are the directories for Windows and OS X. It is important
to be able to access these directories in order to monitor and manually clean up
extensions during development should something go awry.

```shell
# Windows
> C:\Users\[user name]\AppData\Roaming\Adobe\CEP\extensions\

# OS X
> ~/Library/Application Support/Adobe/CEP/extensions/
```

### Build Script

Because the SG-Adobe integration is built via the **Toolkit as a Plugin** framework,
you'll need to rebuild the SG plugin into an Adobe extension as you make changes
to the code.

In order to build the extension, you'll need to run the included
`developer/build_extension.py` script. This is a wrapper around the
`build_plugin.py` from core (`v0.18.27` or later).

Building the extension requires running the `build_extension.py` script with a
local copy of tk-core, supplying it with options about where and how to build
the output extension.

The arguments for the build script look like this:

```bash
> ./build_extension.py --help
usage: build_extension.py [-h] --core /path/to/tk-core --plugin_name name
                          --extension_name name
                          [--sign /path/to/ZXPSignCmd /path/to/certificate password]
                          [--bundle_cache]
                          [--version v#.#.#]
                          [--output_dir /path/to/output/extension]

Build and package an Adobe extension for the engine. This includes
signing the extension with the supplied certificate. The extension will be
built in the engine repo unless an output directory is specified.

optional arguments:
  -h, --help            show this help message and exit
  --core /path/to/tk-core, -c /path/to/tk-core
                        The path to tk-core to use when building the toolkit
                        plugin.
  --plugin_name name, -p name
                        The name of the engine plugin to build. Ex: 'basic'.
  --extension_name name, -e name
                        The name of the output extension. Ex:
                        'com.sg.basic.ps'
  --sign /path/to/ZXPSignCmd /path/to/certificate password, -s /path/to/ZXPSignCmd /path/to/certificate password
                        If supplied, sign the build extension. Requires 3
                        arguments: the path to the 'ZXPSignCmd', the
                        certificate and the password.Note, the ZXPSignCmd can
                        be downloaded here:
                        https://github.com/Adobe-CEP/CEP-Resources/tree/master/ZXPSignCMD/4.0.7
  --bundle_cache, -b    If supplied, include the 'bundle_cache' directory in
                        the build plugin. If not, it is removed after the
                        build.
  --version v#.#.#, -v v#.#.#
                        The version to attached to the built plugin. If not
                        specified, the version will be set to 'dev' and will
                        override any version of the extension at
                        launch/install time. The current version can be found
                        in the .version file that lives next to the existing
                        .zxp file.
  --output_dir /path/to/output/extension, -o /path/to/output/extension
                        If supplied, output the built extension here. If not
                        supplied, the extension will be built in the engine
                        directory at the top level.
```

There are quite a few options for the script. The sections below will outline
how to use the build script for different testing scenarios.

### PlayerDebugMode

If you plan to do local development and testing with an unsigned/uncertified
extensions, you will need to set some OS-specific preferences:

As per the Adobe docs:

> Applications will normally not load an extension unless it is
> cryptographically signed. However, during development we want to be able to
> quickly test an extension without having to sign it. To turn on debug mode:
>
> * On Mac, open the file `~/Library/Preferences/com.adobe.CSXS.7.plist` and add a
> row with key `PlayerDebugMode`, of type `String`, and value `1`.
> * On Windows, open the registry key `HKEY_CURRENT_USER/Software/Adobe/CSXS.7`
> and add a key named `PlayerDebugMode`, of type `String`, and value `1`
>
> You should only need to do this once.

If on Mac 10.9 and higher

>Staring with Mac 10.9, Apple introduced a caching mechanism for plist files.
>Your modifications to plist files does not take effect until the cache gets updated
>(on a periodic basis, you cannot know exactly when the update will happen). To make sure
>your modifications take effect, there are two methods.
>
>* Kill cfprefsd process, e.g. `killall cfprefsd`. It will restart automatically. Then the update takes effect.
>* Restart your Mac, or log out the current user and re-log in.

### Local testing without signing

It is possible to build and test the extension without bundling it into a `.zxp`
file (what Adobe wants for its Add-ons site). This scenario will simply run the
underlying SG plugin build into a directory of your choosing.

To test with this setup, set an environment variable:
`SHOTGUN_ADOBE_DISABLE_AUTO_INSTALL`. In the classic toolkit startup (web,
Desktop, tk-shell) this will prevent the `.zxp` packaged with the engine from
being installed automatically.

Now you can build the extension directly to the CEP extensions directory. Here's
an example of the command run from the top level of the engine repo:

```
python developer/build_extension.py -c ../tk-core -p basic -e com.sg.basic.ps -o "/Users/josh/Library/Application Support/Adobe/CEP/extensions/"
```

Argument breakdown:

* `-c /path/to/core`: The local path to the `tk-core` to use for building the plugin
* `-p plugin_name': The engine plugin to build. Plugins found in the engine's `plugins` directory.
* `-e extension_name`: The output name of the adobe extension to build. This should match the
`ExtensionBundleId` found in the extensions manifest (`CSXS/manifest.xml`).
* `-o output_dir`: The output directory to write the built extension. Here we're
writing directly to the installed CEP extensions directory.

Repeat this command as you make changes to the plugin code to update the installed
extension. NOTE: Older versions of the core `build_plugin.py` script will leave a
backup directory in the CEP extensions directory, next to the build. You will likely
want to make sure these are cleaned up after each build to avoid confusion and prevent
issues inside the Adobe product.

### `Adobe Docs`

* [ZXPSignCmd](https://github.com/Adobe-CEP/CEP-Resources/tree/master/ZXPSignCMD/4.0.7)
* [Packaging and Signing Extensions](http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/creativesuite/pdfs/SigningTechNote_CC.pdf)

### Local testing with signing

You can also build a signed extension that mimics the final build. This workflow
involves building a `.zxp` file that can be auto-installed and updated as you
launch toolkit (via web, Desktop, or tk-shell).

First, make sure you do **NOT** have the `SHOTGUN_ADOBE_DISABLE_AUTO_INSTALL`
set in your environment. We will build the `.zxp` and allow the auto install to
run. This env variable prevents that.

Next, clean out any previous direct builds (see previous section) from the CEP
install directory. The first toolkit startup will install the `.zxp` automatically.

Finally, download the `ZXPSignCmd` tool to sign the built extension. You can find
it [here](https://github.com/Adobe-CEP/CEP-Resources/tree/master/ZXPSignCMD/4.0.7)

Now you can build the `.zxp` file with the extension build script. Here's an
example command run from the top level of the engine repo:

```
python developer/build_extension.py -c ../tk-core -p basic -e com.sg.basic.ps -s ../ZXPSignCmd ~/Documents/certs/my_certificate.p12 my_cert_password
```

The first few arguments are identical to the previous example. The additional
arguments are:

* `-s ../ZXPSignCmd`: The path to the `ZXPSignCmd` tool that you previously
downloaded
* `~/Documents/certs/my_certificate.p12`: The second argument to the `-s` (sign)
option is the path to certificate to use to sign the extension.
* `my_cert_password`: The third argument to the `-s` option is the password for
the certificate.

Since the `-o` (output directory) option was not supplied, the `.zxp` file will
be build and overwrite the `.zxp` file in the engine. The built extension file
will look like this:

```
com.sg.basic.ps.version
com.sg.basic.ps.zxp
```

Notice the `.version` file. This file is used by the toolkit startup logic to
know when to auto install the extension. When the `-v` (version) flag is not
specified, this file will contain the string `dev` which tells the engine
startup code to always install/update this extension. This makes the developer
round trip from extension build to engine startup straight forward. A copy of
this `.version` file is also included in the `.zxp` bundle so that when it is
unpacked within the CEP extensions directory, it can be easily compared against
what is in the engine for the non `dev` case.

If you're worried about overwriting the `.zxp` file bundled with the engine,
remember you can always use `git checkout` to discard your changes.

### Building for Release

Building for release is almost identical to the previous example with the
exception of specifying an actual version. To do that, you simple add an additional
argument to the build command:

```
python developer/build_extension.py -c ../tk-core -p basic -e com.sg.basic.ps -s ../ZXPSignCmd ~/Documents/certs/my_certificate.p12 my_cert_password -v v0.0.1
```

The results of the command will look like this:

```
com.sg.basic.ps.version
com.sg.basic.ps.zxp
```

Unlike the previous section, the `.version` file will now include the string
`v0.0.1`. As bug fixes and features are added to the extension, and it is rebuilt
with higher version numbers, the engine startup code will use this file to
compare and determine if the user's installed version requires an update.

#### Signature verification:

Once the `.zxp` bundle is created, you can verify the signature using the same
`ZXPSignCmd` supplied to the build script. Here's the usage:

```
> ZXPSignCmd -verify com.sg.basic.ps.zxp -certInfo
```

The output of the command will show the basic information about the certificate.
Most importantly, it should show `OS Trusted: true`, `Revoked: false`, a valid
timestamp within the valid certificate's signing range.

Note, the command may take a couple of minutes to run. For more information, see
this [document from adobe](http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/creativesuite/pdfs/SigningTechNote_CC.pdf).

#### Important Developer Note:

Once the extension is signed and installed, **any** modifications to the files
in that directory will cause Adobe's signature verification to fail. It is
important to understand this while developing. Because the `basic` plugin
includes python code we have manually disabled the creation of `.pyc` files
during boostrap for this reason.


### Testing

The `basic` plugin/extension has a flyout menu with options useful for testing
and debugging.

* **Chrome Console...** - Requires Chrome as the default browser. Opens a Chrome
console connected to the Adobe extensions.
* **Reload Shotgun Extension** - Reloads the extension, including restarting the
external python process.

To enable these, set the environment variable `TK_DEBUG`.

### Configuration repo

If you're doing development on the `tk-photoshop` engine and launching it
via the Adobe CC launcher (Toolkit as a plugin), you'll need to clone the config
repo so that you can change it to point to your development repo(s). The config
used by the engine is the [tk-config-basic](https://github.com/shotgunsoftware/tk-config-basic)
repo. Obviously, you'll also need to clone the repos for the bundle's you're
doing development on as well.

The base configuration is defined in the extension's `info.yml`. You will need
to change the descriptor arguments to point to your development repository. Here
is an example:

```yaml
base_configuration:
  #type: app_store
  #name: tk-config-pluginbasic

  type: dev
  path: /path/to/my/dev/config/repo
```

Once you're pointing to your configuration development repo, you can change the
bundle descriptors in the configuration's environment files to point to the
development repos for the bundles you're working on.


