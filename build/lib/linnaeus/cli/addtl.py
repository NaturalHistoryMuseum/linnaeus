import base64
import click
import os

from linnaeus.config import constants
from . import _decorators as decorators, _utils as utils
from .core import cli


@cli.command(short_help='Displays some details about a serialised map file.')
@decorators.inputfiles()
@click.pass_context
def readmap(ctx, inputs):
    """
    Displays some details about the given serialised map file. Can also act as a sort
    of validator for serialised map files in that if it can load them, they're valid.
    """
    from linnaeus import MapFactory
    from linnaeus.models import ReferenceMap
    read_map = utils.deserialise(ctx, inputs[0], MapFactory)
    utils.echo(ctx, click.style(inputs[0], bold=True))
    utils.echo(ctx, f'{type(read_map).__name__} with {len(read_map)} items')
    if isinstance(read_map, ReferenceMap):
        w, h = read_map.bounds
        utils.echo(ctx, f'{w} "pixels" wide, {h} "pixels" tall')
        utils.echo(ctx, 'An example record:')
        utils.echo(ctx, read_map.records[0])


@cli.command(short_help='Generate a .config file.')
@click.pass_context
def makeconfig(ctx):
    constants.dump('.config')


@cli.command(short_help='Create a reference map of text.')
@click.argument('text', type=click.STRING, nargs=-1)
@click.option('-f', '--font', type=click.Path(exists=True))
@decorators.outputfile
@click.option('-c', '--colour', type=click.INT, nargs=4, default=(0, 0, 0, 255),
              help='RGBA colour for the text. Defaults to solid black.')
@click.option('-s', '--size', type=click.INT, default=20,
              help='Font size in px. Defaults to 20.')
@click.pass_context
def textmap(ctx, text, font, output, colour, size):
    from linnaeus import MapFactory

    text = '\n'.join(text)
    iden = os.path.splitext(os.path.split(font)[-1])[
               0] + f'-{base64.b64encode(text.encode()).decode()}_{size}px'
    output = output or f'maps/{iden}.json'

    reference_map = MapFactory.reference().from_text(text, font, size, colour)

    return utils.final(ctx, output,
                       lambda x: MapFactory.save_text(x, reference_map.serialise()))


@cli.command(short_help='Create a reference map of a QR code.')
@click.argument('data', type=click.STRING, nargs=-1)
@decorators.outputfile
@click.option('-c', '--colour', type=click.INT, nargs=4, default=(0, 0, 0, 255),
              help='RGBA colour for the data blocks. Defaults to solid black.')
@click.option('-s', '--size', type=click.INT, default=1,
              help='Block size in px. Defaults to 1.')
@click.pass_context
def qr(ctx, data, output, colour, size):
    from linnaeus import MapFactory

    data = ''.join(data)
    output = output or f'maps/qr-{base64.b64encode(data.encode()).decode()}_{size}.json'
    utils.setup_path(ctx, output)

    reference_map = MapFactory.reference().from_qr_data(data, colour, size)

    return utils.final(ctx, output,
                       lambda x: MapFactory.save_text(x, reference_map.serialise()))
