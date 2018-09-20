import click


def outputfile(fn):
    return click.option('-o', '--output', type=click.Path(),
                        help='Map save path. Auto-generated if not supplied.')(fn)


def inputfiles(nargs=1):
    def _dec(fn):
        return click.argument('inputs', type=click.Path(exists=True), nargs=nargs)(fn)

    return _dec
