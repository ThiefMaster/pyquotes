import difflib
import pathlib
import shutil
import sys
import typing as t
from datetime import datetime

import click

import pyquotes
from pyquotes.settings import Config
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
    '--check-only',
    '--check',
    '-c',
    is_flag=True,
    help='Only check files without updating them.',
)
@click.option(
    '--exclude',
    multiple=True,
    metavar='PATTERN',
    help='''
    Exclude files/directories matching this pattern. Can be used multiple times.
    Replaces the built-in excludes. Does not apply to explicitly-specified files.
    ''',
)
@click.option(
    '--extend-exclude',
    '-X',
    multiple=True,
    metavar='PATTERN',
    help='''
    Exclude files/directories matching this pattern. Can be used multiple times.
    Extends the built-in excludes. Does not apply to explicitly-specified files.
    ''',
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
def main(files: t.List[pathlib.Path], **cli_settings):
    """
    A tool that ensures consistent string quotes in your Python code.

    When passing a directory, all *.py files inside will be processed recursively.

    If any files needed changes, it exits with a non-zero status code.
    """
    # discard all missing values to get the dataclass defaults
    cli_settings = {k: v for k, v in cli_settings.items() if v}
    try:
        config = Config(cli_settings)
    except ValueError as exc:
        raise click.BadArgumentUsage(str(exc))
    has_changes = False
    files = [pathlib.Path(f) for f in files]  # `path_type` in click 7 is useless
    for file in _expand_dirs(files, config):
        try:
            changed = _process_file(file, config=config)
        except Exception:
            click.echo(f'Error while processing {file}', err=True)
            raise
        if changed:
            has_changes = True
    sys.exit(1 if has_changes else 0)


def _expand_dirs(
    files: t.Iterable[pathlib.Path], config: Config, check_ext: bool = False
) -> t.Iterable[pathlib.Path]:
    for file in files:
        if config.is_path_excluded(file):
            if config.verbose:
                click.echo(f'{file} is excluded', err=True)
        elif file.is_file():
            if not check_ext or file.suffix == '.py':
                yield file
        elif file.is_dir():
            yield from _expand_dirs(file.iterdir(), config, check_ext=True)


def _process_file(file: pathlib.Path, config: Config):
    old_code = file.read_text()
    new_code = transform_source(old_code, double_quotes=config.double_quotes)
    if old_code == new_code:
        if config.verbose:
            click.echo(f'{file} is up to date', err=True)
        return False

    if config.diff:
        diff_lines = difflib.unified_diff(
            old_code.splitlines(),
            new_code.splitlines(),
            f'{file}:before',
            f'{file}:after',
            _getmtime(file),
            _getmtime(None),
            lineterm='',
        )
        click.echo('\n'.join(diff_lines))
        return True

    if config.check_only:
        if not config.quiet:
            click.echo(f'{file} needs changes', err=True)
        return True

    _atomic_overwrite(file, new_code)
    if not config.quiet:
        click.echo(f'Updated {file}', err=True)
    return True


def _atomic_overwrite(file: pathlib.Path, content: str):
    tmp_file = file.with_suffix(f'{file.suffix}.pyquoted')
    tmp_file.touch()
    shutil.copymode(file, tmp_file)
    tmp_file.write_text(content)
    tmp_file.replace(file)


def _getmtime(path: t.Optional[pathlib.Path]) -> str:  # pragma: no cover
    if path is None:
        return datetime.now().isoformat()
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
