import click
import json
import os
from PIL import Image

from linnaeus import Builder, MapFactory, SolveError
from linnaeus.config import constants
from linnaeus.models import ReferenceMap

click_context = {
    'help_option_names': ['-h', '--help']
    }


def setup_path(path):
    """
    Aborts if the path already exists and should not be overwritten; otherwise creates
    necessary folders if not already present.
    :param path: path to check/setup
    :return: None
    """
    if os.path.exists(path):
        click.confirm(f'{path} already exists. Overwrite?', abort=True)
    else:
        folders = os.path.sep.join(path.split(os.path.sep)[:-1])
        if folders != '':
            os.makedirs(folders, exist_ok=True)


def deserialise(path, factory, callback=None, saveas=None):
    """
    Attempts to deserialise the file at the given path. If it is not the correct type,
    runs a callback function if defined, and aborts if not.
    :param path: the path to the file to try to deserialise
    :param factory: the MapFactory to use to deserialise (can just be MapFactory)
    :param callback: a function returning a Map
    :return: Map
    """
    try:
        read_map = factory.deserialise(MapFactory.load_text(path))
        return read_map
    except (json.JSONDecodeError, UnicodeDecodeError, IsADirectoryError):
        if callback is None:
            click.echo(f'Unable to deserialise {path}', err=True)
            raise click.Abort
        else:
            try:
                if saveas is None:
                    saveas = path + '.json'
                mp = callback(path)
                MapFactory.save_text(saveas, mp.serialise())
            except Exception as e:
                click.echo(f'Unable to create map from {path} ({e.__name__}).', err=True)
                raise click.Abort


@click.group(invoke_without_command=False, context_settings=click_context)
def cli():
    """
    A command line interface for working with the linnaeus program.

    Run 'linnaeus <cmd> -h' for help with each subcommand.
    """
    pass


@cli.command(short_help='Creates a reference map or component map.')
@click.argument('inputs', type=click.Path(exists=True), nargs=-1)
@click.option('-o', '--output', type=click.Path(),
              help='Map save path. Auto-generated if not supplied.')
def makemap(inputs, output):
    """
    Creates a reference map or component map.

    If a single input file path is given, a reference map will be made. If a directory
    path and/or multiple file paths are given, a component map will be made.
    """
    iden = os.path.splitext(inputs[0].split(os.path.sep)[-1])[0]

    if len(inputs) > 1 or os.path.isdir(inputs[0]):
        output = output or MapFactory.component().defaultpath(iden)
        setup_path(output)

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
                click.echo(f'Ignoring {i}')
        component_map = MapFactory.component().from_local(**kwargs)
        MapFactory.save_text(output, component_map.serialise())
    elif os.path.isfile(inputs[0]):
        inputs = inputs[0]
        try:
            Image.open(inputs)
        except OSError:
            click.echo(f'Unable to open {inputs}.', err=True)
            raise click.Abort
        output = output or MapFactory.reference().defaultpath(iden)
        setup_path(output)
        reference_map = MapFactory.reference().from_image_local(inputs)
        MapFactory.save_text(output, reference_map.serialise())
    else:
        click.echo('Cannot identify target type.', err=True)
        raise click.Abort
    click.echo(f'Saved map to {output}!')


@cli.command(short_help='Displays some details about a serialised map file.')
@click.argument('path', type=click.Path(exists=True))
def readmap(path):
    """
    Displays some details about the given serialised map file. Can also act as a sort
    of validator for serialised map files in that if it can load them, they're valid.
    """
    read_map = deserialise(path, MapFactory)
    click.echo(click.style(path, bold=True))
    click.echo(f'{type(read_map).__name__} with {len(read_map)} items')
    if isinstance(read_map, ReferenceMap):
        w, h = read_map.bounds
        click.echo(f'{w} "pixels" wide, {h} "pixels" tall')
    click.echo('An example record:')
    click.echo(read_map.records[0])


@cli.command(short_help='Attempts to solve the given reference and component set.')
@click.argument('ref', type=click.Path(exists=True))
@click.argument('comps', type=click.Path(exists=True), nargs=-1)
@click.option('-o', '--output', type=click.Path(),
              help='Solution map output path. Auto-generated if not given.')
@click.option('-t', '--tolerance', default=-1,
              help='Use masking to ignore components that are unlikely to match - this '
                   'is much faster but more likely to fail. Lower tolerance = more '
                   'components removed.')
def solve(ref, comps, output, tolerance):
    """
    Attempts to create a solution map for the given reference and component set.

    The reference and components can be given as paths to serialised maps or as a path
    to
    an image file (for the reference) and one or more paths to image files and/or
    directories (for the component map), similar to the makemap command.
    """
    iden = os.path.splitext(ref.split(os.path.sep)[-1])[0]
    output = output or MapFactory.solution().defaultpath(iden)
    setup_path(output)

    # load and/or make maps
    ref_map = deserialise(ref, MapFactory.reference(),
                          MapFactory.reference().from_image_local, saveas=MapFactory.reference().defaultpath(iden))

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
            click.echo(f'Ignoring {i}')
    saveas = MapFactory.component().defaultpath(comps[0].split(os.path.sep)[-1])
    if len(comps) > 1:
        comp_map = MapFactory.component().from_local(**kwargs)
        MapFactory.save_text(saveas, comp_map.serialise())
    else:
        comps = comps[0]
        comp_map = deserialise(comps, MapFactory.component(),
                               lambda x: MapFactory.component().from_local(**kwargs),
                               saveas=saveas)

    solved = False
    tol = float(tolerance)
    use_mask = True
    attempts = 0
    while not solved and attempts < 5:
        attempts += 1
        try:
            solution_map = Builder.solve(ref_map, comp_map,
                                         mask_tolerance=tol, use_mask=use_mask)
            MapFactory.save_text(output, solution_map.serialise())
            solved = True
        except SolveError as e:
            click.echo(e, err=True)
            if not use_mask or attempts >= 5:
                click.echo('Nothing more to be done. Aborting.')
                raise click.Abort
            elif use_mask and tol < -0.5 and click.confirm(
                    f'Increase tolerance to {tol/2}?', default=True):
                tol /= 2
            else:
                click.confirm('Disable mask?', abort=True, default=True)
                use_mask = False


@cli.command(short_help='Generate an image from a solution map.')
@click.argument('solution', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(),
              help='Built image output path. Auto-generated if not given.')
@click.option('--adjust/--no-adjust', default=True,
              help='Whether or not to adjust the colour of the components to better '
                   'match the reference.')
@click.option('--prefix', type=click.Path(exists=True),
              help='The root directory of the components, either relative or absolute.')
def render(solution, output, adjust, prefix):
    """
    Generates a jpg image from the given solution map.

    Component maps use relative paths, not absolute, so if the component map was
    generated in a different directory the relative paths will no longer be valid. If
    this is the case, use the '--prefix' flag to specify the location of the components.
    """
    output = output or os.path.splitext(solution)[0] + '.jpg'
    setup_path(output)
    solution_map = deserialise(solution, MapFactory.solution())
    canvas = Builder.fill(solution_map, adjust=adjust, prefix=prefix)
    canvas.save(output)


@cli.command(short_help='Generate a .config file.')
def makeconfig():
    constants.dump('.config')
