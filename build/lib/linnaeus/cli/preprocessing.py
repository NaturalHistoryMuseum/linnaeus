import click
import cv2
import numpy as np
from PIL import Image

from . import _decorators as decorators, _utils as utils
from .core import cli


@cli.group(invoke_without_command=False)
@click.pass_context
def preprocess(ctx):
    pass


@preprocess.command(short_help='Reorient an image based on EXIF data.')
@decorators.inputfiles()
@decorators.outputfile
@click.pass_context
def orient(ctx, inputs, output):
    from linnaeus.preprocessing import exif
    img = exif.apply_orientation(Image.open(inputs[0]))
    output = output or utils.new_filename(inputs[0], new_folder='preprocess',
                                          suffix='orient', new_ext='png')
    return utils.final(ctx, output, lambda x: img.save(x))


@preprocess.command(short_help='Remove the background from a reference image.')
@decorators.inputfiles()
@decorators.outputfile
@click.option('-c', '--colour', nargs=3, type=click.INT,
              help='Use this colour (RGB) as the background to remove. Auto-calculated '
                   'from the image edges (or corners using the --corners flag) if not '
                   'given.')
@click.option('--bg', type=click.Path(exists=True),
              help='Use this image as the background to remove. Takes priority over '
                   '--colour. If neither is given the colour is auto-calculated.')
@click.option('--corners', is_flag=True, default=False,
              help='Use corner pixels instead of edges to determine the dominant '
                   'colour.')
@click.option('--fill-edges/--no-fill-edges', default=True,
              help='Try to fix/smooth edges of the subject that are in contact with '
                   'the edges of the image.')
@click.option('--holes/--no-holes', default=True,
              help='Remove areas matching the background colour from within the main '
                   'subject shape.')
@click.option('--erode', type=click.INT, default=2,
              help='Erodes the mask before applying to remove colour edges and other '
                   'artefacts.')
@click.option('--sobel', is_flag=True, default=False,
              help='Use a Sobel filter to help detect the edges.')
@click.pass_context
def removebg(ctx, inputs, output, colour, bg, corners, fill_edges, holes, erode,
             sobel):
    """
    Remove the background from an image (i.e. an image to be used as a reference) and
    save it. Intended for use on images with a clearly defined subject against a plain
    background.
    """
    from linnaeus.preprocessing import BackgroundRemover, colourspace
    img = np.array(Image.open(inputs[0]))
    if bg is not None:
        bg_rem = BackgroundRemover(img, bg_image=np.array(Image.open(bg)))
    elif len(colour) == 3:
        hsv_colour = colourspace(colour, cv2.COLOR_RGB2HSV_FULL)[0, 0]
        bg_rem = BackgroundRemover(img,
                                   colour=hsv_colour)
    elif corners:
        bg_rem = BackgroundRemover.from_corners(img)
    else:
        bg_rem = BackgroundRemover.from_edges(img)
    masked_img = Image.fromarray(
        bg_rem.apply(
            bg_rem.create_mask(fill_edges, holes, erosion=erode, use_sobel=sobel)))
    output = output or utils.new_filename(inputs[0], new_folder='preprocess',
                                          suffix='bg', new_ext='png')
    return utils.final(ctx, output, lambda x: masked_img.save(x))
