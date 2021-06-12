import difflib
import pathlib
import shutil
import sys
import typing as t
from datetime import datetime

import click

import pyquotes
from pyquotes.transform import transform_source


@click.command()
@click.version_option(pyquotes.__version__, '--version', '-V')
@click.help_option('--help', '-h')
@click.option('--double-quotes', '-D', is_flag=True, help='Prefer double quotes.')
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    help='Do not output which files have been reformatted.',
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Be more verbose and show all files being processed.',
)
@click.option(
    '--diff', '-d', is_flag=True, help='Only show diffs without updating files.'
)
@click.option(
    '--check-only', '-c', is_flag=True, help='Only check files without updating them.'
)
@click.argument(
    'files',
    nargs=-1,
    required=True,
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
)
def main(
    files: t.List[pathlib.Path],
    quiet=False,
    verbose=False,
    diff=False,
    check_only=False,
    double_quotes=False,
):
    """
    A tool that ensures consistent string quotes in your Python code.

    When passing a directory, all *.py files inside will be processed recursively.

    If any files needed changes, it exits with a non-zero status code.
    """
    if quiet and verbose:
        raise click.BadOptionUsage('verbose', 'Cannot mix verbose and quiet')
    has_changes = False
    files = [pathlib.Path(f) for f in files]  # `path_type` in click 7 is useless
    for file in _expand_dirs(files):
        try:
            changed = _process_file(
                file,
                quiet=quiet,
                verbose=verbose,
                diff=diff,
                check_only=check_only,
                double_quotes=double_quotes,
            )
        except Exception:
            click.echo(f'Error while processing {file}')
            raise
        if changed:
            has_changes = True
    sys.exit(1 if has_changes else 0)


def _expand_dirs(
    files: t.Iterable[pathlib.Path], check_ext: bool = False
) -> t.Iterable[pathlib.Path]:
    for file in files:
        if file.is_file():
            if not check_ext or file.suffix == '.py':
                yield file
        elif file.is_dir():
            yield from _expand_dirs(file.iterdir(), check_ext=True)


def _process_file(
    file: pathlib.Path,
    *,
    quiet: bool,
    verbose: bool,
    diff: bool,
    check_only: bool,
    double_quotes: bool,
):
    absfile = file.absolute()
    old_code = file.read_text()
    new_code = transform_source(old_code, double_quotes=double_quotes)
    if old_code == new_code:
        if verbose:
            click.echo(f'{file} is up to date', err=True)
        return False

    if diff:
        diff_lines = difflib.unified_diff(
            old_code.splitlines(),
            new_code.splitlines(),
            f'{absfile}:before',
            f'{absfile}:after',
            _getmtime(file),
            datetime.now().isoformat(),
            lineterm='',
        )
        click.echo('\n'.join(diff_lines))
        return True

    if check_only:
        if not quiet:
            click.echo(f'{file} needs changes', err=True)
        return True

    _atomic_overwrite(file, new_code)
    if not quiet:
        click.echo(f'Updated {file}', err=True)
    return True


def _atomic_overwrite(file: pathlib.Path, content: str):
    tmp_file = file.with_suffix(f'{file.suffix}.pyquoted')
    tmp_file.touch()
    shutil.copymode(file, tmp_file)
    tmp_file.write_text(content)
    tmp_file.replace(file)


def _getmtime(path: pathlib.Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
