import os
import sys

from setuptools.config import StaticModule


sys.path.insert(0, os.getcwd())
version = StaticModule('pyquotes').__version__
tag_version = sys.argv[1]

if tag_version != version:
    print(
        f'::error::Tag version {tag_version} does not match package version {version}'
    )
    sys.exit(1)
