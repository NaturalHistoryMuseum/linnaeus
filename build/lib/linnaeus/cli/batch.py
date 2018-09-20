import itertools
import time

import click
import os
from watchdog.observers import Observer

from . import _decorators as decorators, _utils as utils, addtl, core, preprocessing


@core.cli.command(
    short_help='Runs a sequence of CLI functions to transform an input image into a '
               'composite with minimal user input.')
@decorators.inputfiles(nargs=-1)
@decorators.outputfile
@click.option('-c', '--components', type=click.Path(exists=True), required=True)
@click.option('--silhouette', is_flag=True, default=False)
@click.option('--prefix', type=click.Path(exists=True),
              help='The root directory of the components, either relative or absolute.')
@click.option('--combine-with', type=click.Path(exists=True),
              help='Add this input image on top of an existing map (preferably a '
                   'solution map for performance reasons, but reference maps will also '
                   'work).')
@click.option('--combine-gravity', type=click.STRING, default='C',
              help='Ignored if not combining; specifies the gravity for positioning '
                   'the input on top of the background.')
@click.option('--combine-offset', type=click.INT, nargs=2, default=(0, 0),
              help='Ignored if not combining; specifies the offset from the input\'s '
                   'calculated position on top of the background.')
@click.option('--greenscreen/--no-greenscreen', default=True,
              help='If true, will try to remove the background from the image before '
                   'mapping. (Does not actually have to be green.)')
@click.option('--cleanup/--no-cleanup', default=True,
              help='If true, will remove some intermediate files upon completion. '
                   'Leaves the completed solution map and the rendered image.')
@click.option('--watch', is_flag=True, default=False,
              help='Watch the folder(s) for new files.')
@click.pass_context
def go(ctx, inputs, output, components, silhouette, prefix, combine_with,
       combine_gravity, combine_offset, greenscreen, cleanup, watch):
    """
    Runs a sequence of CLI functions to transform an input image into a composite with
    minimal user input. Can also be used over a set of images (e.g. a folder),
    and can watch the folder for new files and process them as they become available.
    The sequence will be run separately for each input image. This method will make a
    lot of assumptions and have limited options. If you need more control, you will
    need to write your own script.
    """
    if not os.path.exists('.config'):
        make_config = click.confirm(
            'You don\'t have a .config file. Do you want to create one now?',
            default=True)
        if make_config:
            ctx.invoke(addtl.makeconfig)
        click.confirm('Continue with defaults?', abort=True)

    from linnaeus import MapFactory
    from linnaeus.config import TimeLogger, ProgressLogger
    utils.set_quiet(ctx, True)

    if len(inputs) == 0:
        click.echo('No input images specified.', err=True)
        raise click.Abort
    inputs = {'files' if k else 'folders': list(v) for k, v in
              itertools.groupby(sorted(inputs, key=lambda x: os.path.isfile(x)),
                                lambda x: os.path.isfile(x))}
    folder_files = [os.path.join(fol, f) for fol in inputs.get('folders', []) for f in
                    os.listdir(fol) if os.path.isfile(os.path.join(fol, f))]

    inputs['files'] = list(set(inputs.get('files', []) + folder_files))
    print(inputs)

    def _process(img):
        click.echo(f'Processing {img}')
        with TimeLogger(True) as t:
            cleaning_list = []
            if greenscreen:
                reoriented = ctx.invoke(preprocessing.orient, inputs=[img])
                grnscrn = ctx.invoke(preprocessing.removebg, inputs=[reoriented])
                cleaning_list += [reoriented, grnscrn]
                img = grnscrn

            subject_ref = ctx.invoke(core.makemap, inputs=[img])
            cleaning_list.append(subject_ref)
            subject_sol = ctx.invoke(core.solve, inputs=[subject_ref, components],
                                     silhouette=silhouette)

            if combine_with is not None:
                cleaning_list.append(subject_sol)
                combine_kwargs = {
                    'gravity': combine_gravity,
                    'offset': combine_offset
                    }
                if MapFactory.identify(MapFactory.load_text(
                        combine_with)) == MapFactory.reference().product_class:
                    combined_map = ctx.invoke(core.combine,
                                              inputs=[combine_with, subject_ref],
                                              **combine_kwargs)
                    cleaning_list.append(combined_map)
                    completed_sol = ctx.invoke(core.solve,
                                               inputs=[combined_map, components],
                                               silhouette=False)
                else:
                    completed_sol = ctx.invoke(core.combine,
                                               inputs=[combine_with, subject_sol],
                                               **combine_kwargs)
            else:
                completed_sol = subject_sol

            ctx.invoke(core.render, inputs=[completed_sol], prefix=prefix, output=output)
            if cleanup:
                for f in cleaning_list:
                    os.remove(f)

    file_list = inputs.get('files', [])
    for f in file_list:
        with ProgressLogger(len(file_list), len(file_list), use_click=True) as p:
            _process(f)
            p.next()

    if watch:
        handler = utils.FolderWatcher(_process)
        folder_observers = {f: Observer() for f in inputs.get('folders')}
        for f, observer in folder_observers.items():
            observer.schedule(handler, f, recursive=False)
            observer.start()
            click.echo(f'Watching {f}')
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            click.echo('Stopping...')
            for observer in folder_observers.values():
                observer.stop()
        for observer in folder_observers.values():
            observer.join()
