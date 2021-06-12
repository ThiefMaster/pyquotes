# pyquotes

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
  -V, --version        Show the version and exit.
  -h, --help           Show this message and exit.
  -D, --double-quotes  Prefer double quotes.
  -q, --quiet          Do not output which files have been reformatted.
  -v, --verbose        Be more verbose and show all files being processed.
  -d, --diff           Only show diffs without updating files.
  -c, --check-only     Only check files without updating them.
```

Use `--diff` or `--check-only` if you want to run this script in CI (usually using
flake8-quotes as explained below is the better choice though).

## Flake8

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
