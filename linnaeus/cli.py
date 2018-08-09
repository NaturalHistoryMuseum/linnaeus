import click
import os
from PIL import Image

from linnaeus import MapFactory
from linnaeus.config import constants
from linnaeus.models import ReferenceMap, ComponentMap

pathsep = '/' if os.getcwd().startswith('/') else '\\'


@click.group(invoke_without_command=False)
def cli():
    pass


@cli.command()
@click.argument('target')
@click.option('-o', '--output')
def makemap(target, output):
    if not os.path.exists(target):
        click.echo(f'Cannot find {target}', err=True)
        return
    if os.path.isdir(target):
        target_type = 'comp'
    elif os.path.isfile(target):
        try:
            Image.open(target)
            target_type = 'ref'
        except:
            click.echo(f'Unable to open {target}.', err=True)
            return
    else:
        click.echo('Cannot identify target type.')
    target_iden = [x for x in target.split(pathsep)[-1].split('.') if x != ''][0]
    output = output or (os.path.join('maps',
                                     f'{target_iden}_ref_{constants.max_ref_size}.json'
                                     )
                        if target_type == 'ref' else
                        os.path.join('maps',
                                     f'{target_iden}_'
                                     f'{constants.dominant_colour_method}.json'))
    if os.path.exists(output):
        click.confirm(f'{output} already exists. Overwrite?', abort=True)
    os.makedirs(pathsep.join(output.split(pathsep)[:-1]), exist_ok=True)
    if target_type == 'ref':
        # make a new reference map
        reference_map = MapFactory.reference().from_image_local(target)
        # and save it
        MapFactory.save_text(output, reference_map.serialise())
    else:
        # make a new component map
        component_map = MapFactory.component().from_local(folders=[target])
        # and save it
        MapFactory.save_text(output, component_map.serialise())
    click.echo(f'Saved map to {output}!')


@cli.command()
@click.argument('target')
def readmap(target):
    if not os.path.exists(target):
        click.echo(f'Cannot find {target}', err=True)
    read_map = MapFactory.deserialise(MapFactory.load_text(target))
    click.echo(click.style(target, bold=True))
    click.echo(f'{type(read_map).__name__} with {len(read_map)} items')
    if isinstance(read_map, ReferenceMap):
        w, h = read_map.bounds
        click.echo(f'{w} "pixels" wide, {h} "pixels" tall')
    click.echo('An example record:')
    click.echo(read_map.records[0])