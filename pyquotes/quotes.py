# Most code in this file is taken from or heavily based on the quote
# normalization logic of black (https://github.com/psf/black) which
# is also under the MIT license.

import re


STRING_PREFIX_CHARS = 'furbFURB'
D3 = '"""'
S3 = "'''"


def _sub_twice(regex, replacement, original):
    return regex.sub(replacement, regex.sub(replacement, original))


def normalize_string_prefix(leaf):
    match = re.match(r'^([' + STRING_PREFIX_CHARS + r']*)(.*)$', leaf.value, re.DOTALL)
    assert match is not None, f'failed to match string {leaf.value!r}'
    orig_prefix = match.group(1)
    # XXX: r isn't casefolded on purpose - https://github.com/psf/black/issues/1244
    new_prefix = (
        orig_prefix.replace('F', 'f')
        .replace('B', 'b')
        .replace('U', 'u')
        .replace('u', '')
    )
    leaf.value = f'{new_prefix}{match.group(2)}'


def normalize_string_quotes(leaf, is_doc, double_quotes=False):
    value = leaf.value.lstrip(STRING_PREFIX_CHARS)

    # docstring handling taken from axblack
    # see https://github.com/axiros/axblack/issues/6
    if double_quotes and value[:3] in (D3, S3):
        if value[:3] == D3:
            return
        orig_quote = S3
        new_quote = D3
    elif value[:3] == D3:
        if is_doc:
            return
        orig_quote = D3
        new_quote = S3
    elif value[:3] == S3:
        if not is_doc:
            return
        orig_quote = S3
        new_quote = D3
    elif value[0] == '"':
        orig_quote = '"'
        new_quote = "'"
    else:
        orig_quote = "'"
        new_quote = '"'

    first_quote_pos = leaf.value.find(orig_quote)
    assert first_quote_pos != -1

    prefix = leaf.value[:first_quote_pos]
    unescaped_new_quote = re.compile(rf'(([^\\]|^)(\\\\)*){new_quote}')
    escaped_new_quote = re.compile(rf'([^\\]|^)\\((?:\\\\)*){new_quote}')
    escaped_orig_quote = re.compile(rf'([^\\]|^)\\((?:\\\\)*){orig_quote}')
    body = leaf.value[(first_quote_pos + len(orig_quote)) : -len(orig_quote)]

    if 'r' in prefix.casefold():
        if unescaped_new_quote.search(body):
            # There's at least one unescaped new_quote in this raw string
            # so converting is impossible
            return

        # Do not introduce or remove backslashes in raw strings
        new_body = body
    else:
        # remove unnecessary escapes
        new_body = _sub_twice(escaped_new_quote, rf'\1\2{new_quote}', body)
        if body != new_body:
            # Consider the string without unnecessary escapes as the original
            body = new_body
            leaf.value = f'{prefix}{orig_quote}{body}{orig_quote}'
        new_body = _sub_twice(escaped_orig_quote, rf'\1\2{orig_quote}', new_body)
        new_body = _sub_twice(unescaped_new_quote, rf'\1\\{new_quote}', new_body)

    if 'f' in prefix.casefold():
        matches = re.findall(
            r'''
            (?:[^{]|^)\{  # start of the string or a non-{ followed by a single {
                ([^{].*?)  # contents of the brackets except if begins with {{
            \}(?:[^}]|$)  # A } followed by end of the string or a non-}
            ''',
            new_body,
            re.VERBOSE,
        )
        for m in matches:
            if '\\' in str(m):
                # Do not introduce backslashes in interpolated expressions
                return

    # edge cases
    if new_quote == D3 and new_body[-1:] == '"':
        new_body = new_body[:-1] + '\\"'
    elif new_quote == S3 and new_body[-1:] == "'":
        new_body = new_body[:-1] + "\\'"

    orig_escape_count = body.count('\\')
    new_escape_count = new_body.count('\\')
    if new_escape_count > orig_escape_count:
        return  # Do not introduce more escaping

    string_quote_style = '"' if double_quotes else "'"
    if new_escape_count == orig_escape_count and orig_quote == string_quote_style:
        return

    leaf.value = f'{prefix}{new_quote}{new_body}{new_quote}'
