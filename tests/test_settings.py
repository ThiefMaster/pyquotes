from pathlib import Path
import textwrap

import pytest

from pyquotes.settings import DEFAULT_EXCLUDE, Config, _find_config


@pytest.mark.parametrize(
    ('excludes', 'path', 'expected'),
    (
        (frozenset(), '.venv', False),
        (frozenset({'.*'}), '.venv', True),
        (frozenset({'build'}), 'some/build', True),
        (frozenset({'build'}), 'build', True),
        (frozenset({'/foo/bar'}), '/foo/bar/test', False),
        (frozenset({'/foo/bar/*'}), '/foo/bar/test', True),
        (frozenset({'foo/bar'}), '/test/foo/bar', True),
    ),
)
def test_is_path_excluded(excludes, path, expected, monkeypatch):
    monkeypatch.setattr('pyquotes.settings._find_config', lambda p: ('/test', {}))
    cfg = Config({'exclude': frozenset(excludes)})
    assert cfg.is_path_excluded(Path(path)) == expected


def test_merge_excludes(monkeypatch):
    monkeypatch.setattr('pyquotes.settings._find_config', lambda p: ('/test', {}))
    cfg = Config({'extend_exclude': ('foo',)})
    assert cfg.excludes == DEFAULT_EXCLUDE | {'foo'}


def _make_config(section, as_toml=False):
    if as_toml:
        return (
            textwrap.dedent(
                f'''
                [{section}]
                double-quotes = true
                exclude = ['foo', 'bar']
                extend_exclude = ['test', 'moo']
                '''
            ).strip()
            + '\n'
        )
    else:
        return (
            textwrap.dedent(
                f'''
                [{section}]
                double-quotes = true
                exclude = foo, bar
                extend_exclude =
                    test
                    moo
                '''
            ).strip()
            + '\n'
        )


@pytest.mark.parametrize(
    ('name', 'section'),
    (
        ('.pyquotes.cfg', 'settings'),
        ('.pyquotes.cfg', 'pyquotes'),
        ('setup.cfg', 'pyquotes'),
        ('setup.cfg', 'tool:pyquotes'),
        ('pyproject.toml', 'tool.pyquotes'),
    ),
)
@pytest.mark.parametrize('use_subdir', (False, True))
def test_find_config(monkeypatch, tmpdir, name, section, use_subdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 1 + use_subdir)
    tmpdir = Path(tmpdir)
    (tmpdir / name).write_text(_make_config(section, name.endswith('.toml')))
    startdir = tmpdir
    if use_subdir:
        subdir = tmpdir / 'sub'
        subdir.mkdir()
        startdir = subdir
    assert _find_config(startdir) == (
        tmpdir,
        {
            'double_quotes': True,
            'exclude': {'foo', 'bar'},
            'extend_exclude': {'test', 'moo'},
        },
    )


@pytest.mark.parametrize('name', ('.pyquotes.cfg', 'setup.cfg', 'pyproject.toml'))
@pytest.mark.parametrize('use_subdir', (False, True))
def test_find_config_empty(monkeypatch, tmpdir, name, use_subdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 1 + use_subdir)
    tmpdir = Path(tmpdir)
    (tmpdir / name).touch()
    startdir = tmpdir
    if use_subdir:
        subdir = tmpdir / 'sub'
        subdir.mkdir()
        startdir = subdir
    assert _find_config(startdir) == (tmpdir, {})


def test_find_config_toodeep(monkeypatch, tmpdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 2)
    tmpdir = Path(tmpdir)
    (tmpdir / '.pyquotes.cfg').write_text(_make_config('pyquotes'))
    subdir = tmpdir / 'sub' / 'dir'
    subdir.mkdir(parents=True)
    assert _find_config(subdir) == (
        subdir,
        {},
    )


def test_find_config_stopdir(monkeypatch, tmpdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 3)
    tmpdir = Path(tmpdir)
    (tmpdir / '.pyquotes.cfg').write_text(_make_config('pyquotes'))
    subdir = tmpdir / 'sub' / 'dir'
    subdir.mkdir(parents=True)
    rootdir = tmpdir / 'sub' / '.git'
    rootdir.mkdir()
    assert _find_config(subdir) == (
        rootdir.parent,
        {},
    )


def test_find_config_invalid_key(monkeypatch, tmpdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 1)
    tmpdir = Path(tmpdir)
    (tmpdir / '.pyquotes.cfg').write_text('[pyquotes]\nfoo = bar')
    with pytest.warns(
        UserWarning, match=r'Could not load .*/\.pyquotes\.cfg: unknown key: foo'
    ):
        assert _find_config(tmpdir) == (tmpdir, {})


def test_find_config_no_toml(monkeypatch, tmpdir):
    monkeypatch.setattr('pyquotes.settings.MAX_CONFIG_SEARCH_DEPTH', 1)
    monkeypatch.setattr('pyquotes.settings.toml', None)
    tmpdir = Path(tmpdir)
    (tmpdir / 'pyproject.toml').write_text('[tool.pyquotes]\nfoo = bar')
    with pytest.warns(
        UserWarning,
        match=r'Could not load .*/pyproject\.toml: To parse toml files, you need to `pip install toml`',
    ):
        assert _find_config(tmpdir) == (tmpdir, {})
