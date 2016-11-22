
import os.path
import sys

python_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "python",
    ),
)

print ""
print "Prepending to sys.path: %s" % python_path
sys.path = [python_path] + sys.path

