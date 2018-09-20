from . import _utils as utils

from .core import cli
from . import core, addtl, preprocessing, batch

if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])