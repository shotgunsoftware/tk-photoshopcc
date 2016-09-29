

var make_persistent = function(persistent) {
    'use strict';

    var csLib = new CSInterface();

    if (persistent) {
        var event = new CSEvent("com.adobe.PhotoshopPersistent", "APPLICATION");
    } else {
        var event = new CSEvent("com.adobe.PhotoshopUnPersistent", "APPLICATION");
    }

    event.extensionId = csLib.getExtensionID();
    csLib.dispatchEvent(event);

};

var reload_extension = function() {
    "use strict";

    var csLib = new CSInterface();

    // remember the extension id to reload it
    var extension_id = csLib.getExtensionID();

    csLib.closeExtension();
    csLib.requestOpenExtension(extension_id);

};

var flyout_menu = function() {

	"use strict";
    var csLib = new CSInterface();

    // Ugly workaround to keep track of "checked" and "enabled" statuses
    var checkableMenuItem_isChecked = true;
    var targetMenuItem_isEnabled = true;

    // Flyout menu XML string.
    //   Debug Shotgun Extension...  > opens external debug console in browser
    var flyoutXML = "<Menu> \
          <MenuItem Id='sg_dev_debug_link_item' Label='Debug Shotgun Extension...' Enabled='true' Checked='false'/> \
          <MenuItem Id='sg_dev_reload_extension' Label='Reload Shotgun Extension' Enabled='true' Checked='false'/> \
        </Menu>";

    // Uses the XML string to build the menu
    csLib.setPanelFlyoutMenu(flyoutXML);

    // Flyout Menu Click Callback
    function flyoutMenuClickedHandler (event) {

        // the event's "data" attribute is an object, which contains "menuId" and "menuName"
        console.dir(event);
        switch (event.data.menuId) {
            case "sg_dev_debug_link_item":
                console.log("Opening debugger in default browser.");
                // the port should correspond to the port defined in .debug
                csLib.openURLInDefaultBrowser("http://localhost:45217");
                break;
            case "sg_dev_reload_extension":
                console.log("Reloading extension.");
                console.log("Debug console will need to be restarted.");
                // turn off persistence so we can reload, then turn it back on
                make_persistent(false);
                reload_extension();
                make_persistent(true);
                break;
            default:
                console.log(event.data.menuName + " clicked.");
        }
    }

    // Listen for the Flyout menu clicks
    csLib.addEventListener("com.adobe.csxs.events.flyoutMenuClicked", flyoutMenuClickedHandler);

};