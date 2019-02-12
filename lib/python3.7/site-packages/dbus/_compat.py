# Python 2 / Python 3 compatibility helpers.

import sys

is_py3 = (sys.version_info.major == 3)
is_py2 = not is_py3
