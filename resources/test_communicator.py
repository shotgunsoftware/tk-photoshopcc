
import pprint
import sys

sys.path.append("/Users/jeff/Documents/repositories/tk-framework-adobe/extensions/http_server/python")
sys.path.append("d:/repositories/tk-adobecc/python")

from adobecc import Communicator

adobe = Communicator()

# Get the active document.
# ad = adobe.app.activeDocument

# Show the File->Open dialog.
# adobe.app.openDialog()

# Pop up a message/alert dialog.
# adobe.alert("WOOT")

# Set the ruler units to percentage intervals. Can also use adobe.Units.PIXELS to
# show pixel intervals.
# adobe.app.preferences.rulerUnits = adobe.Units.PERCENT

# Open a file.
# f = adobe.File("c:/wtf.jpg")
# adobe.app.load(f)

# Export a file for the web.
# adobe.app.activeDocument.exportDocument(
#     adobe.File("c:/WTFEXPORT.jpg"),
#     adobe.ExportType.SAVEFORWEB,
#     adobe.rpc_new("ExportOptionsSaveForWeb"),
# )


# Export a file for the web for each layer of the active document.
doc = adobe.app.activeDocument
layers = doc.artLayers
layers = [layers[i] for i in xrange(layers.length)]
original_visibility = [layer.visible for layer in layers]

save_for_web = adobe.ExportType.SAVEFORWEB
export_options = adobe.ExportOptionsSaveForWeb()

for layer in layers:
    layer.visible = False

for layer in layers:
    layer.visible = True
    out_file = adobe.File("c:/YES.%s.jpg" % str(layer.name))
    doc.exportDocument(
        out_file,
        save_for_web,
        export_options,
    )
    layer.visible = False

for (i, layer) in enumerate(layers):
    layer.visible = original_visibility[i]

