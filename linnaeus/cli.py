import base64
import click
import cv2
import json
import numpy as np
import os
from PIL import Image

from linnaeus.config import constants, silence

click_context = {
    'help_option_names': ['-h', '--help']
    }


def echo(ctx, msg, **kwargs):
    """
    Suppresses output if quiet option enabled.
    :param ctx: context
    :param msg: the message to display if quiet is not enabled
    :param kwargs: keyword args passed to click.echo()
    """
    quiet = ctx.obj.get('quiet', False)
    is_err = kwargs.get('err', False)
    if (not quiet) or is_err:
        click.echo(msg, **kwargs)


def confirm(ctx, msg, **kwargs):
    """
    Requests confirmation if quiet option is not enabled, otherwise auto-accepts and
    suppresses prompt.
    :param ctx: context
    :param msg: the message to display if quiet is not enabled
    :param kwargs: keyword args passed to click.echo()
    """
    if not ctx.obj.get('quiet', False):
        return click.confirm(msg, **kwargs)
    else:
        return True


def setup_path(ctx, path):
    """
    Aborts if the path already exists and should not be overwritten; otherwise creates
    necessary folders if not already present.
    :param ctx: context
    :param path: path to check/setup
    :return: None
    """
    if os.path.exists(path):
        confirm(ctx, f'{path} already exists. Overwrite?', abort=True)
    else:
        folders = os.path.sep.join(path.split(os.path.sep)[:-1])
        if folders != '':
            os.makedirs(folders, exist_ok=True)


def deserialise(ctx, path, factory, callback=None, saveas=None):
    """
    Attempts to deserialise the file at the given path. If it is not the correct type,
    runs a callback function if defined, and aborts if not.
    :param ctx: context
    :param path: the path to the file to try to deserialise
    :param factory: the MapFactory to use to deserialise (can just be MapFactory)
    :param callback: a function returning a Map
    :return: Map
    """
    from linnaeus import MapFactory
    try:
        read_map = factory.deserialise(MapFactory.load_text(path))
        return read_map
    except (json.JSONDecodeError, UnicodeDecodeError, IsADirectoryError):
        if callback is None:
            echo(ctx, f'Unable to deserialise {path}', err=True)
            raise click.Abort
        else:
            try:
                if saveas is None:
                    saveas = path + '.json'
                mp = callback(path)
                MapFactory.save_text(saveas, mp.serialise())
            except Exception as e:
                echo(ctx, f'Unable to create map from {path} ({e.__name__}).', err=True)
                raise click.Abort


@click.group(invoke_without_command=False, context_settings=click_context)
@click.option('--quiet', is_flag=True, default=False,
              help='Just output filenames - useful for scripting. WARNING: this will '
                   'auto-accept everything and set the log level to FATAL.')
@click.option('-d', '--delimiter', default='\n',
              help='Delimiter for piped input (defaults to newline).')
@click.pass_context
def cli(ctx, quiet, delimiter):
    """
    A command line interface for working with the linnaeus program.

    Run 'linnaeus <cmd> -h' for help with each subcommand.
    """
    ctx.obj = {
        'quiet': quiet
        }

    if quiet:
        silence()


@cli.command(short_help='Creates a reference map or component map.')
@click.argument('inputs', type=click.Path(exists=True), nargs=-1)
@click.option('-o', '--output', type=click.Path(),
              help='Map save path. Auto-generated if not supplied.')
@click.pass_context
def makemap(ctx, inputs, output):
    """
    Creates a reference map or component map.

    If a single input file path is given, a reference map will be made. If a directory
    path and/or multiple file paths are given, a component map will be made.
    """
    from linnaeus import MapFactory

    iden = os.path.splitext(inputs[0].split(os.path.sep)[-1])[0]

    if len(inputs) > 1 or os.path.isdir(inputs[0]):
        output = output or MapFactory.component().defaultpath(iden)
        setup_path(ctx, output)

        kwargs = {
            'folders': [],
            'files': []
            }
        for i in inputs:
            if os.path.isfile(i):
                kwargs['files'].append(i)
            elif os.path.isdir(i):
                kwargs['folders'].append(i)
            else:
                echo(ctx, f'Ignoring {i}')
        component_map = MapFactory.component().from_local(**kwargs)
        MapFactory.save_text(output, component_map.serialise())
    elif os.path.isfile(inputs[0]):
        inputs = inputs[0]
        try:
            Image.open(inputs)
        except OSError:
            echo(ctx, f'Unable to open {inputs}.', err=True)
            raise click.Abort
        output = output or MapFactory.reference().defaultpath(iden)
        setup_path(ctx, output)
        reference_map = MapFactory.reference().from_image_local(inputs)
        MapFactory.save_text(output, reference_map.serialise())
    else:
        echo(ctx, 'Cannot identify target type.', err=True)
        raise click.Abort
    click.echo(output)


@cli.command(short_help='Displays some details about a serialised map file.')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def readmap(ctx, path):
    """
    Displays some details about the given serialised map file. Can also act as a sort
    of validator for serialised map files in that if it can load them, they're valid.
    """
    from linnaeus import MapFactory
    from linnaeus.models import ReferenceMap
    read_map = deserialise(ctx, path, MapFactory)
    echo(ctx, click.style(path, bold=True))
    echo(ctx, f'{type(read_map).__name__} with {len(read_map)} items')
    if isinstance(read_map, ReferenceMap):
        w, h = read_map.bounds
        echo(ctx, f'{w} "pixels" wide, {h} "pixels" tall')
    echo(ctx, 'An example record:')
    echo(ctx, read_map.records[0])


@cli.command(short_help='Attempts to solve the given reference and component set.')
@click.argument('ref', type=click.Path(exists=True))
@click.argument('comps', type=click.Path(exists=True), nargs=-1)
@click.option('-o', '--output', type=click.Path(),
              help='Solution map output path. Auto-generated if not given.')
@click.option('-t', '--tolerance', default=-1,
              help='Use masking to ignore components that are unlikely to match - this '
                   'is much faster but more likely to fail. Lower tolerance = more '
                   'components removed.')
@click.option('--silhouette', is_flag=True, help='Create a silhouette image, i.e. not '
                                                 'matched on colour. Only really works '
                                                 'with references with transparency.')
@click.pass_context
def solve(ctx, ref, comps, output, tolerance, silhouette):
    """
    Attempts to create a solution map for the given reference and component set.

    The reference and components can be given as paths to serialised maps or as a path
    to
    an image file (for the reference) and one or more paths to image files and/or
    directories (for the component map), similar to the makemap command.
    """
    from linnaeus import Builder, MapFactory, SolveError
    iden = os.path.splitext(ref.split(os.path.sep)[-1])[0].split('_')[0]
    output = output or MapFactory.solution().defaultpath(iden)
    setup_path(ctx, output)

    # load and/or make maps
    ref_map = deserialise(ctx, ref, MapFactory.reference(),
                          MapFactory.reference().from_image_local,
                          saveas=MapFactory.reference().defaultpath(iden))

    kwargs = {
        'folders': [],
        'files': []
        }
    for i in comps:
        if os.path.isfile(i):
            kwargs['files'].append(i)
        elif os.path.isdir(i):
            kwargs['folders'].append(i)
        else:
            echo(ctx, f'Ignoring {i}')
    saveas = MapFactory.component().defaultpath(comps[0].split(os.path.sep)[-1])
    if len(comps) > 1:
        comp_map = MapFactory.component().from_local(**kwargs)
        MapFactory.save_text(saveas, comp_map.serialise())
    else:
        comps = comps[0]
        comp_map = deserialise(ctx, comps, MapFactory.component(),
                               lambda x: MapFactory.component().from_local(**kwargs),
                               saveas=saveas)

    solution_map = None
    if silhouette:
        try:
            solution_map = Builder.silhouette(ref_map, comp_map)
        except SolveError as e:
            echo(ctx, f'Something went wrong: {e}', err=True)
            raise click.Abort
    else:
        tol = float(tolerance)
        use_mask = True
        attempts = 0
        while solution_map is None and attempts < 5:
            attempts += 1
            try:
                solution_map = Builder.solve(ref_map, comp_map,
                                             mask_tolerance=tol, use_mask=use_mask)
                break
            except SolveError as e:
                echo(ctx, e, err=True)
                if not use_mask or attempts >= 5:
                    echo(ctx, 'Nothing more to be done. Aborting.', err=True)
                    raise click.Abort
                elif use_mask and tol < -0.5 and confirm(ctx,
                                                         f'Increase tolerance to '
                                                         f'{tol/2}?',
                                                         default=True):
                    tol /= 2
                else:
                    confirm(ctx, 'Disable mask?', abort=True, default=True)
                    use_mask = False

    if solution_map is not None:
        MapFactory.save_text(output, solution_map.serialise())
        click.echo(output)


@cli.command(short_help='Generate an image from a solution map.')
@click.argument('solution', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(),
              help='Built image output path. Auto-generated if not given.')
@click.option('--adjust/--no-adjust', default=True,
              help='Whether or not to adjust the colour of the components to better '
                   'match the reference.')
@click.option('--prefix', type=click.Path(exists=True),
              help='The root directory of the components, either relative or absolute.')
@click.pass_context
def render(ctx, solution, output, adjust, prefix):
    """
    Generates a jpg image from the given solution map.

    Component maps use relative paths, not absolute, so if the component map was
    generated in a different directory the relative paths will no longer be valid. If
    this is the case, use the '--prefix' flag to specify the location of the components.
    """
    from linnaeus import Builder, MapFactory
    if output is None:
        *solution_folders, solution_name = os.path.split(solution)
        solution_folders[-1] = 'outputs'
        solution_name = os.path.splitext(solution_name)[0] + '.png'
        output = os.path.join(*solution_folders, solution_name)
    setup_path(ctx, output)
    solution_map = deserialise(ctx, solution, MapFactory.solution())
    canvas = Builder.fill(solution_map, adjust=adjust, prefix=prefix)
    canvas.save(output)
    click.echo(output)


@cli.command(short_help='Generate a .config file.')
@click.pass_context
def makeconfig(ctx):
    constants.dump('.config')


@cli.command(short_help='Combine maps.')
@click.argument('inputs', type=click.Path(exists=True), nargs=2)
@click.option('-o', '--output', type=click.Path(),
              help='Built image output path. Auto-generated if not given.')
@click.option('--gravity', default='C',
              help='(Solution/Reference maps only): C(enter), N(orth), S(outh), '
                   'E(ast), or W(est). Can also combine NSEW (e.g. NE for top right '
                   'corner).')
@click.option('--offset', nargs=2,
              help='(Solution/Reference maps only): Manually define x, y offset for '
                   'new map. Overrides --gravity.')
@click.option('--overlay/--no-overlay', default=True,
              help='(Solution/Reference maps only): if True, the new map is added on '
                   'top of the base map. If False, it is added next to the base map.')
@click.option('--prefix', default='.',
              help='(Component maps only): the root path for images in the base map. '
                   'The images in the new map should be reachable from the same root '
                   'path OR should be in a subdirectory of this path.')
@click.pass_context
def combine(ctx, inputs, output, **kwargs):
    from linnaeus import MapFactory

    basemap = deserialise(ctx, inputs[0], MapFactory)
    newmap = deserialise(ctx, inputs[1], MapFactory)

    if isinstance(basemap, MapFactory.component().product_class):
        kwargs = {
            'prefix': kwargs.get('prefix', '.')
            }
    else:
        if 'offset' in kwargs and len(kwargs['offset']) == 2:
            kwargs['gravity'] = kwargs['offset']
        del kwargs['offset']
        del kwargs['prefix']

    combined_map = MapFactory.combine(basemap, newmap, **kwargs)
    if output is None:
        filename = inputs[0].split(os.path.sep)[-1]
        filename = 'combined_' + filename
        output = os.path.join('maps', filename)
    setup_path(ctx, output)
    MapFactory.save_text(output, combined_map.serialise())
    click.echo(output)


@cli.command(short_help='Create a reference map of text.')
@click.argument('text', type=click.STRING)
@click.argument('font', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(),
              help='Built image output path. Auto-generated if not given.')
@click.option('-c', '--colour', type=click.INT, nargs=4, default=(0, 0, 0, 255),
              help='RGBA colour for the text. Defaults to solid black.')
@click.option('-s', '--size', type=click.INT, default=20,
              help='Font size in px. Defaults to 20.')
@click.pass_context
def textmap(ctx, text, font, output, colour, size):
    from linnaeus import MapFactory

    iden = os.path.splitext(os.path.split(font)[-1])[0] + f'_{size}px'
    output = output or f'maps/{iden}.json'
    setup_path(ctx, output)

    reference_map = MapFactory.reference().from_text(text, font, size, colour)
    MapFactory.save_text(output, reference_map.serialise())
    click.echo(output)


@cli.command(short_help='Create a reference map of a QR code.')
@click.argument('data', type=click.STRING)
@click.option('-o', '--output', type=click.Path(),
              help='Built image output path. Auto-generated if not given.')
@click.option('-c', '--colour', type=click.INT, nargs=4, default=(0, 0, 0, 255),
              help='RGBA colour for the data blocks. Defaults to solid black.')
@click.option('-s', '--size', type=click.INT, default=20,
              help='Block size in px. Defaults to 20.')
@click.pass_context
def qr(ctx, data, output, colour, size):
    from linnaeus import MapFactory

    output = output or f'maps/qr_{base64.b64encode(data)}_{size}.json'
    setup_path(ctx, output)

    reference_map = MapFactory.reference().from_qr_data(data, colour, size)
    MapFactory.save_text(output, reference_map.serialise())
    click.echo(output)


@cli.group()
@click.pass_context
def prepro(ctx):
    pass


@prepro.command(short_help='Remove the background from a reference image.')
@click.argument('image', type=click.Path(exists=True))
@click.option('-c', '--colour', nargs=3, type=click.INT,
              help='Use this colour (RGB) as the background to remove. Auto-calculated '
                   'from the image edges (or corners using the --corners flag) if not '
                   'given.')
@click.option('-b', '--background', type=click.Path(exists=True),
              help='Use this image as the background to remove. Takes priority over '
                   '--colour. If neither is given the colour is auto-calculated.')
@click.option('-o', '--output', type=click.Path(),
              help='Processed image output path. Auto-generated if not given.')
@click.option('--corners', is_flag=True, default=False,
              help='Use corner pixels instead of edges to determine the dominant '
                   'colour.')
@click.option('--fill-edges/--no-fill-edges', default=True,
              help='Try to fix/smooth edges of the subject that are in contact with '
                   'the edges of the image.')
@click.option('--holes/--no-holes', default=True,
              help='Remove areas matching the background colour from within the main '
                   'subject shape.')
@click.option('-e', '--erode', type=click.INT, default=2,
              help='Erodes the mask before applying to remove colour edges and other '
                   'artefacts.')
@click.pass_context
def removebg(ctx, image, colour, background, output, corners, fill_edges, holes, erode):
    """
    Remove the background from an image (i.e. an image to be used as a reference) and
    save it. Intended for use on images with a clearly defined subject against a plain
    background.
    """
    from linnaeus.preprocessing import BackgroundRemover, colourspace
    img = np.array(Image.open(image))
    if background is not None:
        bg = BackgroundRemover(img, bg_image=np.array(Image.open(background)))
    elif len(colour) == 3:
        hsv_colour = colourspace(colour, cv2.COLOR_RGB2HSV_FULL)[0, 0]
        bg = BackgroundRemover(img,
                               colour=hsv_colour)
    elif corners:
        bg = BackgroundRemover.from_corners(img)
    else:
        bg = BackgroundRemover.from_edges(img)
    masked_img = Image.fromarray(
        bg.apply(bg.create_mask(fill_edges, holes, erosion=erode)))
    output = output or os.path.splitext(image)[0] + '_bg.png'
    masked_img.save(output)
    click.echo(output)


if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])
