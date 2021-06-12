from pathlib import Path

import pytest

from pyquotes.transform import transform_source


TEST_DATA_SEP = '# --->'


def _get_data(datafile):
    data = (Path(__file__).parent / 'data' / datafile).read_text()
    orig, expected = data.split(TEST_DATA_SEP, 1)
    return orig.strip(), expected.strip()


@pytest.mark.parametrize(
    ('datafile', 'double_quotes'),
    (
        ('prefixes.py', False),
        ('docstrings.py', False),
        ('single_quotes.py', False),
        ('double_quotes.py', True),
    ),
)
def test_transforms(datafile, double_quotes):
    orig, expected = _get_data(datafile)
    assert transform_source(orig, double_quotes=double_quotes) == expected
