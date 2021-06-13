import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

import pyquotes
from pyquotes.cli import main
from pyquotes.transform import transform_source


@pytest.fixture(autouse=True)
def cli_runner():
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem() as path:
        path = Path(path)
        shutil.copytree(
            Path(__file__).parent / 'data/cli', path / 'code', symlinks=True
        )
        yield runner


def _assert_unchanged(name):
    __tracebackhide__ = True
    orig = Path(__file__).parent / 'data/cli' / name
    assert (Path('code') / name).read_text() == orig.read_text()


def _assert_changed(name):
    __tracebackhide__ = True
    orig = Path(__file__).parent / 'data/cli' / name
    assert (Path('code') / name).read_text() == transform_source(orig.read_text())


def test_version(cli_runner):
    result = cli_runner.invoke(main, ['--version'], prog_name='pyquotes')
    assert result.exit_code == 0
    assert result.output.strip() == f'pyquotes, version {pyquotes.__version__}'


def test_quiet_verbose_invalid(cli_runner):
    result = cli_runner.invoke(
        main, ['--quiet', '--verbose', 'code'], prog_name='pyquotes'
    )
    assert result.exit_code != 0
    assert 'Error: quiet and verbose are mutually exclusive' in result.stderr


def test_check_only_verbose(cli_runner):
    result = cli_runner.invoke(
        main, ['--check-only', '--verbose', 'code'], prog_name='pyquotes'
    )
    _assert_unchanged('a.py')
    _assert_unchanged('nested/b.py')
    _assert_unchanged('nested/weird.py')
    assert result.exit_code == 1
    assert sorted(result.stderr.strip().splitlines()) == [
        'code/a.py is up to date',
        'code/build is excluded',
        'code/nested/b.py needs changes',
        'code/nested/weird.py needs changes',
    ]
    assert not result.output


def test_check_only_quiet(cli_runner):
    result = cli_runner.invoke(
        main, ['--check-only', '--quiet', 'code'], prog_name='pyquotes'
    )
    _assert_unchanged('a.py')
    _assert_unchanged('nested/b.py')
    assert result.exit_code == 1
    assert result.stderr == ''
    assert not result.output


def test_check_only(cli_runner):
    result = cli_runner.invoke(
        main, ['--check-only', '-X', 'weird.py', 'code'], prog_name='pyquotes'
    )
    _assert_unchanged('a.py')
    _assert_unchanged('nested/b.py')
    assert result.exit_code == 1
    assert result.stderr.strip() == 'code/nested/b.py needs changes'
    assert not result.output


def test_check_only_uptodate(cli_runner):
    result = cli_runner.invoke(
        main, ['--check-only', 'code/a.py'], prog_name='pyquotes'
    )
    _assert_unchanged('a.py')
    assert result.exit_code == 0
    assert result.stderr == ''
    assert not result.output


def test_diff(cli_runner, monkeypatch):
    monkeypatch.setattr('pyquotes.cli._getmtime', lambda x: '<time is meaningless>')
    result = cli_runner.invoke(
        main, ['--diff', '-X', 'weird.py', 'code'], prog_name='pyquotes'
    )
    _assert_unchanged('a.py')
    _assert_unchanged('nested/b.py')
    assert result.exit_code == 1
    assert result.stderr == ''
    assert result.output.strip().splitlines() == [
        '--- code/nested/b.py:before\t<time is meaningless>',
        '+++ code/nested/b.py:after\t<time is meaningless>',
        '@@ -1 +1 @@',
        '-hello = "world"',
        "+hello = 'world'",
    ]


def test_update(cli_runner):
    result = cli_runner.invoke(main, ['code'], prog_name='pyquotes')
    _assert_unchanged('a.py')
    _assert_changed('nested/b.py')
    _assert_changed('nested/weird.py')
    assert result.exit_code == 1
    assert sorted(result.stderr.strip().splitlines()) == [
        'Updated code/nested/b.py',
        'Updated code/nested/weird.py',
    ]
    assert result.output == ''


def test_update_file(cli_runner):
    result = cli_runner.invoke(main, ['code/build/nope.py'], prog_name='pyquotes')
    _assert_changed('build/nope.py')
    assert result.exit_code == 1
    assert result.stderr.strip() == 'Updated code/build/nope.py'
    assert result.output == ''


def test_update_quiet(cli_runner):
    result = cli_runner.invoke(main, ['--quiet', 'code'], prog_name='pyquotes')
    _assert_unchanged('a.py')
    _assert_changed('nested/b.py')
    assert result.exit_code == 1
    assert result.stderr == ''
    assert result.output == ''


def test_error(cli_runner, monkeypatch):
    def _fail(*a, **kw):
        raise Exception('kaboom')

    monkeypatch.setattr('pyquotes.cli.transform_source', _fail)
    result = cli_runner.invoke(main, ['code/a.py'], prog_name='pyquotes')
    assert result.exit_code != 0
    assert result.stderr.strip() == 'Error while processing code/a.py'
    assert result.output == ''


def test_excludes(cli_runner):
    result = cli_runner.invoke(
        main,
        ['--check-only', '--verbose', '--exclude', 'weird.py', 'code'],
        prog_name='pyquotes',
    )
    assert result.exit_code == 1
    assert sorted(result.stderr.strip().splitlines()) == [
        'code/a.py is up to date',
        'code/build/nope.py needs changes',
        'code/nested/b.py needs changes',
        'code/nested/weird.py is excluded',
    ]
    assert not result.output


def test_extend_excludes(cli_runner):
    result = cli_runner.invoke(
        main,
        ['--check-only', '--verbose', '--extend-exclude', 'weird.py', 'code'],
        prog_name='pyquotes',
    )
    assert result.exit_code == 1
    assert sorted(result.stderr.strip().splitlines()) == [
        'code/a.py is up to date',
        'code/build is excluded',
        'code/nested/b.py needs changes',
        'code/nested/weird.py is excluded',
    ]
    assert not result.output
