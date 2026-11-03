"""Command-line calculation summaries and convergence plots."""
import glob
import json
from pathlib import Path
import click
from mushroom.cli._utils import MultiValueCommand, multi_option
from mushroom.cli.band import _engine, _output, _axes, _finish


@click.command(cls=MultiValueCommand)
@click.argument('directories', nargs=-1)
@click.option('--pat')
@click.option('--code')
@multi_option('--param')
@click.option('--sort', 'sort_field')
@click.option('--fields')
@click.option('--delta', type=click.Choice(['energy']))
@click.option('--csv', 'csvpath')
@click.option('--json', 'jsonpath')
@multi_option('--plot')
@_engine
@_output
def collect(directories, pat, code, param, sort_field, fields, delta, csvpath, jsonpath, plot, engine, output):
    """Summarize calculations in DIRECTORIES, optionally matching --pat."""
    from mushroom.collect import collect as gather, format_table, write_csv, plot_convergence
    paths = list(directories) or glob.glob(pat or '*/')
    dirs = []
    for path in paths:
        if Path(path).is_dir():
            dirs.append(path)
        else:
            click.echo('Skipping non-directory: ' + path, err=True)
    params = {}
    for item in param:
        if '=' not in item:
            raise click.UsageError('--param requires NAME=REGEX')
        name, pattern = item.split('=', 1)
        params[name] = pattern
    rows = gather(dirs, code=code, params=params)
    if sort_field:
        rows.sort(key=lambda r: (r.get(sort_field) is None, r.get(sort_field)))
    fields = fields.split(',') if fields else None
    click.echo('\n'.join(format_table(rows, fields=fields, delta=delta)))
    if csvpath:
        write_csv(rows, csvpath, fields)
    if jsonpath:
        Path(jsonpath).write_text(json.dumps(rows, indent=2) + '\n')
    if plot:
        pairs = [value.split(':') for value in plot]
        if any(len(pair) != 2 for pair in pairs):
            raise click.UsageError('--plot requires X:Y')
        fig, axes = _axes(engine, len(pairs))
        plot_convergence([axes] if len(pairs) == 1 else axes, rows, pairs)
        _finish(fig, engine, output, 'collect')
