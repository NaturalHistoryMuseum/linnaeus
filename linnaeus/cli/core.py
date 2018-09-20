import click
import os
from PIL import Image

from . import _decorators as decorators, _utils as utils

click_context = {
    'help_option_names': ['-h', '--help']
    }


@click.group(invoke_without_command=False, context_settings=click_context)
@click.option('--quiet', is_flag=True, default=False,
              help='Just output filenames - useful for scripting. WARNING: this will '
                   'auto-accept everything and set the log level to FATAL.')
@click.pass_context
def cli(ctx, quiet):
    """
    A command line interface for working with the linnaeus program.

    Run 'linnaeus <cmd> -h' for help with each subcommand.
    """
    utils.set_quiet(ctx, quiet)


@cli.command(short_help='Creates a reference map or component map.')
@decorators.inputfiles(nargs=-1)
@decorators.outputfile
@click.option('--resize/--no-resize', default=True,
              help='Whether or not to resize the image. Unless the image is TINY or '
                   'you really want to preserve every single pixel, leave this alone. '
                   'Only for reference maps.')
@click.pass_context
def makemap(ctx, inputs, output, resize):
    """
    Creates a reference map or component map.

    If a single input file path is given, a reference map will be made. If a directory
    path and/or multiple file paths are given, a component map will be made.
    """
    from linnaeus import MapFactory

    iden = os.path.splitext(inputs[0].split(os.path.sep)[-1])[0]

    if len(inputs) > 1 or os.path.isdir(inputs[0]):
        output = output or MapFactory.component().defaultpath(iden)
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
                utils.echo(ctx, f'Ignoring {i}')
        component_map = MapFactory.component().from_local(**kwargs)
        return utils.final(ctx, output,
                           lambda x: MapFactory.save_text(x, component_map.serialise()))
    elif os.path.isfile(inputs[0]):
        inputs = inputs[0]
        try:
            Image.open(inputs)
        except OSError:
            utils.echo(ctx, f'Unable to open {inputs}.', err=True)
            raise click.Abort
        output = output or MapFactory.reference().defaultpath(iden)
        reference_map = MapFactory.reference().from_image_local(inputs, resize)
        return utils.final(ctx, output,
                           lambda x: MapFactory.save_text(x, reference_map.serialise()))
    else:
        utils.echo(ctx, 'Cannot identify target type.', err=True)
        raise click.Abort


@cli.command(short_help='Attempts to solve the given reference and component set.')
@decorators.inputfiles(nargs=-1)
@decorators.outputfile
@click.option('-t', '--tolerance', default=-1,
              help='Use masking to ignore components that are unlikely to match - this '
                   'is much faster but more likely to fail. Lower tolerance = more '
                   'components removed.')
@click.option('--silhouette', is_flag=True, help='Create a silhouette image, i.e. not '
                                                 'matched on colour. Only really works '
                                                 'with references with transparency.')
@click.pass_context
def solve(ctx, inputs, output, tolerance, silhouette):
    """
    Attempts to create a solution map for the given reference and component set.

    The reference and components can be given as paths to serialised maps or as a path
    to
    an image file (for the reference) and one or more paths to image files and/or
    directories (for the component map), similar to the makemap command.
    """
    from linnaeus import Builder, MapFactory, SolveError
    ref, *comps = inputs

    iden = os.path.splitext(ref.split(os.path.sep)[-1])[0].split('_')[0]
    output = output or MapFactory.solution().defaultpath(iden)

    # load and/or make maps
    ref_map = utils.deserialise(ctx, ref, MapFactory.reference(),
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
            utils.echo(ctx, f'Ignoring {i}')
    saveas = MapFactory.component().defaultpath(comps[0].split(os.path.sep)[-1])
    if len(comps) > 1:
        comp_map = MapFactory.component().from_local(**kwargs)
        MapFactory.save_text(saveas, comp_map.serialise())
    else:
        comps = comps[0]
        comp_map = utils.deserialise(ctx, comps, MapFactory.component(),
                                     lambda x: MapFactory.component().from_local(
                                         **kwargs),
                                     saveas=saveas)

    solution_map = None
    if silhouette:
        try:
            solution_map = Builder.silhouette(ref_map, comp_map)
        except SolveError as e:
            utils.echo(ctx, f'Something went wrong: {e}', err=True)
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
                utils.echo(ctx, e, err=True)
                if not use_mask or attempts >= 5:
                    utils.echo(ctx, 'Nothing more to be done. Aborting.', err=True)
                    raise click.Abort
                elif use_mask and tol < -0.5 and utils.confirm(ctx,
                                                               f'Increase tolerance to '
                                                               f'{tol/2}?',
                                                               default=True):
                    tol /= 2
                else:
                    utils.confirm(ctx, 'Disable mask?', abort=True, default=True)
                    use_mask = False

    if solution_map is not None:
        return utils.final(ctx, output,
                           lambda x: MapFactory.save_text(x, solution_map.serialise()))


@cli.command(short_help='Generate an image from a solution map.')
@decorators.inputfiles()
@decorators.outputfile
@click.option('--adjust/--no-adjust', default=True,
              help='Whether or not to adjust the colour of the components to better '
                   'match the reference.')
@click.option('--prefix', type=click.Path(exists=True),
              help='The root directory of the components, either relative or absolute.')
@click.pass_context
def render(ctx, inputs, output, adjust, prefix):
    """
    Generates a jpg image from the given solution map.

    Component maps use relative paths, not absolute, so if the component map was
    generated in a different directory the relative paths will no longer be valid. If
    this is the case, use the '--prefix' flag to specify the location of the components.
    """
    from linnaeus import Builder, MapFactory
    solution = inputs[0]
    output = output or utils.new_filename(solution, new_folder='outputs', new_ext='png')
    solution_map = utils.deserialise(ctx, solution, MapFactory.solution())
    canvas = Builder.fill(solution_map, adjust=adjust, prefix=prefix)
    return utils.final(ctx, output, lambda x: canvas.save(x))


@cli.command(short_help='Combine maps.')
@decorators.inputfiles(nargs=2)
@decorators.outputfile
@click.option('--gravity', default='C',
              help='(Solution/Reference maps only): C(enter), N(orth), S(outh), '
                   'E(ast), or W(est). Can also combine NSEW (e.g. NE for top right '
                   'corner).')
@click.option('--position', nargs=2,
              help='(Solution/Reference maps only): Manually define x, y position for '
                   'new map. Cannot use with --gravity.')
@click.option('--offset', nargs=2, default=(0, 0),
              help='(Solution/Reference maps only): An x, y offset from the position ('
                   'whether specified manually via --position or calculated with '
                   '--gravity).')
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

    basemap = utils.deserialise(ctx, inputs[0], MapFactory)
    newmap = utils.deserialise(ctx, inputs[1], MapFactory)

    if isinstance(basemap, MapFactory.component().product_class):
        kwargs = {
            'prefix': kwargs.get('prefix', '.')
            }
    else:
        if 'position' not in kwargs or len(kwargs['position']) != 2:
            kwargs['position'] = kwargs['gravity']
        del kwargs['gravity']
        del kwargs['prefix']

    combined_map = MapFactory.combine(basemap, newmap, **kwargs)
    output = output or utils.new_filename(inputs[0], new_folder='maps',
                                          suffix='combined')
    return utils.final(ctx, output,
                       lambda x: MapFactory.save_text(x, combined_map.serialise()))
