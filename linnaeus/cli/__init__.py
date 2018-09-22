from linnaeus.cli import _utils as utils

from linnaeus.cli.core import cli
from linnaeus.cli import core, addtl, preprocessing, batch

if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])