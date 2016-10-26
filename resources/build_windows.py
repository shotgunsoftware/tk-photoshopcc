

import os
import os.path
import shutil
import subprocess
import getpass

repo_root = r"d:\repositories\tk-adobecc\extensions"
extension_root = os.path.join(r"\\localhost\C\Users", getpass.getuser(), "AppData", "Roaming", "Adobe", "CEP", "extensions")

extensions = [
    "basic",
]

for extension in extensions:
    destination = os.path.join(extension_root, extension)
    # if os.path.exists(destination):
    #     print "Destination exists, deleting: {}".format(destination)
    #     shutil.rmtree(destination)

    print "Copying {0} to {1}...".format(extension, extension_root)
    # shutil.copytree(os.path.join(repo_root, extension), destination)
    subprocess.call(
        "robocopy {0} {1} /MIR /COPYALL".format(os.path.join(repo_root, extension), destination),
        shell=True,
    )
    