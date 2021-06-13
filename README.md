# pyquotes ![Tests](https://github.com/ThiefMaster/pyquotes/actions/workflows/tests.yml/badge.svg)

Single quotes are superior. And if you disagree, there's an option for this as well.

In any case, quotes should be consistent throughout the codebase, and not rely on tools like black
that reformat everything. Of course using those tools is perfectly fine if you want this behavior,
but sometimes you *just* want to avoid discussing the quote style during PR reviews).

## Usage

```
$ pyquotes --help
Usage: pyquotes [OPTIONS] FILES...

  A tool that ensures consistent string quotes in your Python code.

  When passing a directory, all *.py files inside will be processed
  recursively.

  If any files needed changes, it exits with a non-zero status code.

Options:
  -V, --version                 Show the version and exit.
  -h, --help                    Show this message and exit.
  -D, --double-quotes           Prefer double quotes.
  -q, --quiet                   Do not output which files have been
                                reformatted.

  -v, --verbose                 Be more verbose and show all files being
                                processed.

  -d, --diff                    Only show diffs without updating files.
  -c, --check-only, --check     Only check files without updating them.
  --exclude PATTERN             Exclude files/directories matching this
                                pattern. Can be used multiple times. Replaces
                                the built-in excludes. Does not apply to
                                explicitly-specified files.

  -X, --extend-exclude PATTERN  Exclude files/directories matching this
                                pattern. Can be used multiple times. Extends
                                the built-in excludes. Does not apply to
                                explicitly-specified files.
```

Use `--diff` or `--check-only` if you want to run this script in CI (usually using
flake8-quotes as explained below is the better choice though).

## Configuration

`exclude`, `extend-exclude` and `double-quotes` can be configured via the following
files (looked up in this order, the first one containing settings is used):

- `.pyquotes.cfg` - ConfigParser format, `settings` or `pyquotes` section
- `setup.cfg` - ConfigParser format, `pyquotes` or `tool:pyquotes` section
- `pyproject.toml` - TOML format, `tool.pyquotes` section

Parsing `pyproject.toml` requires `toml` to be installed; a warning is emitted
if the file exists and no config is found elsewhere and `toml` is missing.

Note that `exclude` should not be used in most cases; unless you really need to
whitelist something that's excluded by default.

### setup.cfg

```ini
[pyquotes]
double-quotes = false
extend-exclude =
    htmlcov
    .vscode
```

The same format can be used in `.pyquotes.cfg` as well.

### pyproject.toml

```toml
[tool.pyquotes]
double-quotes = false
extend-exclude = ['htmlcov', '.vscode']
```

## flake8

If you use flake8, you may want to install [flake8-quotes](https://pypi.org/project/flake8-quotes/)
to also get warnings if the code currently has incorrect quotes. You can use the following options
if you want single quotes:

```ini
[flake8]
inline-quotes = single
multiline-quotes = single
docstring-quotes = double
avoid-escape = true
```

Note that flake8-quotes is completely independent from this tool, so inconsistencies are possible.
Please open an issue if you discover any such cases.
