# -*- coding: utf-8 -*-
"""Command to detect the code of a calculation directory"""
import sys
from pathlib import Path

import click

from mushroom.detect import detect_codes


@click.command()
@click.argument("dirpaths", nargs=-1, type=click.Path(exists=True, file_okay=False))
@click.option("-q", "--quiet", is_flag=True,
              help="print only the short name of the most probable code")
def detect(dirpaths, quiet):
    """detect which code the calculation in a directory belongs to

    DIRPATHS defaults to the current directory. Exit with 1 if no code is
    detected in any directory.
    """
    if not dirpaths:
        dirpaths = (".",)
    found_any = False
    for dirpath in dirpaths:
        results = detect_codes(dirpath)
        found_any = found_any or bool(results)
        if quiet:
            if results:
                click.echo(results[0].code if len(dirpaths) == 1 else f"{dirpath}: {results[0].code}")
            continue
        click.echo(f"{click.format_filename(Path(dirpath).resolve())}:")
        if not results:
            click.echo("  no known calculation detected")
        for r in results:
            click.echo(f"  {r.code:8s} {r.name} (score {r.score})")
            for e in r.evidences:
                click.echo(f"           {e}")
    if not found_any:
        sys.exit(1)
