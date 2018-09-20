import click
import json
import os
from watchdog import events

from linnaeus.config import silence


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


def final(ctx, output, save_callback=None):
    """
    The final command - makes sure the output path exists, saves it, displays &
    returns the file path.
    :param ctx: context
    :param output: the output file path
    :param save_callback: a function taking the output file path as an argument to
                          save the command's product to that file
    :return: the output file path
    """
    if save_callback is not None:
        setup_path(ctx, output)
        save_callback(output)
    click.echo(output)
    return output


def set_quiet(ctx, quiet):
    """
    Turn off logging.
    :param ctx: context
    :param quiet: if True, turn logging off; if False, don't
    """
    ctx.obj = {
        'quiet': quiet
        }

    if quiet:
        silence()


def new_filename(input_filename, new_folder=None, suffix=None, new_ext=None):
    """
    Manipulate the input's filename by changing the immediate parent folder and/or
    adding a suffix and/or changing the extension.
    :param input_filename: the path to derive the new path from
    :param new_folder: the immediate parent folder to change to, e.g. /home/x/file.txt
                       to /home/y/file.txt
    :param suffix: add a suffix to the file name, e.g. file.txt to file_processed.txt
    :param new_ext: change the file's extension, e.g. file.txt to file.json
    :return: the new file path
    """
    *folders, filename = os.path.split(input_filename)
    filename, ext = os.path.splitext(filename)
    if new_folder is not None:
        folders[-1] = new_folder
    if suffix is not None:
        filename += f'_{suffix}'
    if new_ext is not None:
        ext = new_ext
    return os.path.join(*folders, os.path.extsep.join([filename, ext]))


class FolderWatcher(events.FileSystemEventHandler):
    """
    Monitors for file creation events and executes a callback taking the path as the
    only parameter.
    """

    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if event.is_directory:
            return
        else:
            self.callback(event.src_path)
