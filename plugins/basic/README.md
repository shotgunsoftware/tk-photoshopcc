# Extension Development

This section is designed for developers and covers how to setup, build, and test
the Adobe CC extension.

The entire extension source lives here in the `tk-photoshopcc` engine in the
`extensions/basic` folder. This includes all of the pieces required by Adobe to
run as a CEP extension as well as the configuration and logic specific to
bootstrapping and running Shotgun Toolkit in a python process.

For more information about Adobe CEP extensions, here are some useful resources:

* [CEP Resources (Github)](https://github.com/Adobe-CEP/CEP-Resources)
* [David Berranca's Blog](http://www.davidebarranca.com/)
* [A Short Guide to HTML5 Extensions (Adobe)](http://www.adobe.com/devnet/creativesuite/articles/a-short-guide-to-HTML5-extensions.html)

## Setup

Before you can build and test the extension locally, you need to setup your
environment to test.

### PlayerDebugMode

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

### Development Repositories

If you're doing development on the `tk-photoshopcc` engine itself, or an app or
framework being loaded by the engine, you'll need to clone the config repo so
that you can make changes to it. The config used by the engine is the
[tk-config-pluginbasic](https://github.com/shotgunsoftware/tk-config-pluginbasic)
repo. Obviously, you'll also need to clone the repos for the bundle's you're
doing development on.

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

### Core Development and Testing

In order to bootstrap into a specific core, you'll need to alter the descriptor
in the extension's `config/core/core_api.yml` file. Simply change the descriptor
arguments in that file to point to a local clone of `tk-core` or to a specific
branch or tag in github.

## Building

In order to build the extension, you'll need to have a local copy of core that
has the `developer/build_plugin.py` script available (`v0.18.27` or later
preferably).

Building the extension requires running the `build_plugin.py` script from your
local core, supplying it with a source path (the path to the extension itself
in your development repo) and a destination path (the path where you want to
write the extension).

Here is an example of building the extension:

```shell
> cd ~/dev
> python tk-core/developer/build_plugin.py tk-photoshopcc/extensions/basic my_extension
```

The above command will write the built extension to the `~/dev/my_extension`
directory. In order for the extension to be picked up, it will need to live in
the CEP extensions directory:

```shell
# windows
> C:\Users\[user name]\AppData\Roaming\Adobe\CEP\extensions\

# osx
> ~/Library/Application Support/Adobe/CEP/extensions/
```

You can have the `build_plugin.py` script write directly to the extensions
directory, just be aware that the script will create a backup copy in the
same location if the destination folder already exists. Alternatively, you can
create a symlink in the extensions directory back to the build destination path
in your development area.

## Testing

Once you've followed the steps above, the extension should be available the
next time you startup Photoshop. If you do not see it, double check the steps
above.

The extension has a flyout menu with 2 options useful for testing and debugging:

* **Debug Console...** - Opens the default browser and displays
information about the extension and a clickable link to debug it.
* **Reload** - Reloads the extension, including restarting the
external python process.

As you make changes in your code, you will need to rebuild the extension using
the steps above. You can use the **Reload** menu item to reload the extension
after it has been rebuilt.

# Building the Plugin for Release

Coming soon...

## Clean up dev descriptors

# TODO:
* consider the case where you have the officially released extension installed
system wide, but you also want to do local development. Revisit once we've done
the initial release for beta testing.
* consider all the side effects of reloading the extension. does it actually
handle reconnecting properly. do we get a completely fresh environment?
