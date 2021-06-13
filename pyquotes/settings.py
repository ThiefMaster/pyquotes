import os
import typing as t
from configparser import ConfigParser
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from warnings import warn


try:
    import toml
except ImportError:  # pragma: no cover
    toml = None


# exclude/skip lists from isort+flake8
DEFAULT_EXCLUDE = frozenset(
    {
        '__pycache__',
        '__pypackages__',
        '_build',
        '.bzr',
        '.direnv',
        '.eggs',
        '.git',
        '.hg',
        '.mypy_cache',
        '.nox',
        '.pants.d',
        '.pytest_cache',
        '.svn',
        '.tox',
        '.venv',
        '*.egg-info',
        '*.egg',
        'buck-out',
        'build',
        'CVS',
        'dist',
        'node_modules',
        'venv',
    }
)

MAX_CONFIG_SEARCH_DEPTH = 25
STOP_CONFIG_SEARCH_ON_DIRS = ('.git', '.hg')
CONFIG_FILE_SETTINGS = frozenset({'double_quotes', 'exclude', 'extend_exclude'})
CONFIG_SOURCES = ('.pyquotes.cfg', 'setup.cfg', 'pyproject.toml')
CONFIG_SECTIONS = {
    '.pyquotes.cfg': ('settings', 'pyquotes'),
    'pyproject.toml': ('tool.pyquotes',),
    'setup.cfg': ('pyquotes', 'tool:pyquotes'),
}

_STR_BOOLEAN_MAPPING = {
    'y': True,
    'yes': True,
    't': True,
    'on': True,
    '1': True,
    'true': True,
    'n': False,
    'no': False,
    'f': False,
    'off': False,
    '0': False,
    'false': False,
}


@dataclass(frozen=True)
class _Config:
    double_quotes: bool = False
    exclude: t.FrozenSet[str] = DEFAULT_EXCLUDE
    extend_exclude: t.FrozenSet[str] = frozenset()
    # CLI-only settings:
    quiet: bool = False
    verbose: bool = False
    diff: bool = False
    check_only: bool = False
    # runtime data:
    project_root: Path = None

    def __post_init__(self):
        object.__setattr__(self, 'exclude', frozenset(self.exclude))
        object.__setattr__(self, 'extend_exclude', frozenset(self.extend_exclude))
        if self.quiet and self.verbose:
            raise ValueError('quiet and verbose are mutually exclusive')


class Config(_Config):
    def __init__(self, cli_settings):
        self._excludes: t.Optional[t.FrozenSet[str]] = None
        project_root, config_settings = _find_config(Path(os.getcwd()))
        settings = {**config_settings, **cli_settings}
        super().__init__(**settings, project_root=project_root)

    @property
    def excludes(self) -> t.FrozenSet[str]:
        if self._excludes is not None:
            return self._excludes

        self._excludes = self.exclude | self.extend_exclude
        return self._excludes

    def is_path_excluded(self, path: Path):
        # based on matches_filename from flake8 (MIT-licensed)
        patterns = self.excludes
        if not patterns:
            return False
        basename = path.name
        if basename not in ('.', '..') and any(fnmatch(basename, p) for p in patterns):
            return True
        absolute_path = path.absolute()
        try:
            relative_path = absolute_path.relative_to(self.project_root)
        except ValueError:
            # no relative path matching outside the project root
            pass
        else:
            if any(fnmatch(relative_path, p) for p in patterns):
                return True
        return any(fnmatch(absolute_path, p) for p in patterns)


def _find_config(path: Path):
    # taken from isort (MIT-licensed)
    current_directory = path.absolute()
    tries = 0
    potential_root = None
    while current_directory and tries < MAX_CONFIG_SEARCH_DEPTH:
        for config_file_name in CONFIG_SOURCES:
            potential_config_file = current_directory / config_file_name
            if potential_config_file.is_file():
                try:
                    config_data = _get_config_data(
                        potential_config_file, CONFIG_SECTIONS[config_file_name]
                    )
                except Exception as exc:
                    warn(f'Could not load {potential_config_file}: {exc}')
                    config_data = {}
                else:
                    potential_root = current_directory
                    if config_data:
                        return current_directory, config_data

        for stop_dir in STOP_CONFIG_SEARCH_ON_DIRS:
            if (current_directory / stop_dir).is_dir():
                return current_directory, {}

        new_directory = current_directory.parent
        if new_directory == current_directory:
            break

        current_directory = new_directory
        tries += 1

    return (potential_root or path), {}


def _get_config_data(file_path: Path, sections):
    # taken from isort (MIT-licensed)
    settings = {}

    with file_path.open(encoding='utf-8') as config_file:
        if file_path.suffix == '.toml':
            if toml is None:
                raise RuntimeError(
                    'To parse toml files, you need to `pip install toml`'
                )
            config = toml.load(config_file)
            for section in sections:
                config_section = config
                for key in section.split('.'):
                    config_section = config_section.get(key, {})
                settings.update(config_section)
        else:
            config = ConfigParser(strict=False)
            config.read_file(config_file)
            for section in sections:
                if config.has_section(section):
                    settings.update(config.items(section))

    if not settings:
        return {}

    empty_config = _Config()
    valid_settings = {}
    for key, value in settings.items():
        orig_key = key
        key = key.replace('-', '_')
        if key not in CONFIG_FILE_SETTINGS:
            raise ValueError(f'unknown key: {orig_key}')
        existing_value_type = type(getattr(empty_config, key))
        if existing_value_type == frozenset:
            valid_settings[key] = frozenset(_as_list(value))
        elif existing_value_type == bool:
            # Only some configuration formats support native boolean values.
            if not isinstance(value, bool):
                value = _as_bool(value)
            valid_settings[key] = value
        else:  # pragma: no cover
            raise ValueError(f'unexpected type {existing_value_type} for key {key}')

    return valid_settings


def _as_list(value: str) -> t.List[str]:
    # taken from isort (MIT-licensed)
    if isinstance(value, list):
        return [item.strip() for item in value]
    return [
        item.strip() for item in value.replace('\n', ',').split(',') if item.strip()
    ]


def _as_bool(value: str) -> bool:
    # taken from isort (MIT-licensed)
    try:
        return _STR_BOOLEAN_MAPPING[value.lower()]
    except KeyError:  # pragma: no cover
        raise ValueError(f'invalid truth value {value}')
