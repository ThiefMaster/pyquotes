import parso
from parso.python.tree import DocstringMixin, PythonLeaf
from parso.tree import BaseNode

from pyquotes.quotes import normalize_string_prefix, normalize_string_quotes


class _CombinedFString(PythonLeaf):
    __slots__ = ()
    type = 'combined_fstring'


def _replace_fstring(node):
    # parso separates string and python parts of fstrings which is probably a
    # good idea in most cases, but it makes quote normalization much harder, so
    # we convert it back to a single string containing the full f-string
    prefix = node.children[0].prefix
    value = node.get_code(include_prefix=False)
    return _CombinedFString(value, node.start_pos, prefix)


def _iter_strings(tree):
    # note: this function mutates the tree while iterating it as it
    # needs to replace f-string nodes
    seen_string_nodes = set()

    def scan(parent):
        if isinstance(parent, DocstringMixin):
            doc_node = parent.get_doc_node()
            if doc_node is not None and doc_node not in seen_string_nodes:
                seen_string_nodes.add(doc_node)
                yield True, doc_node

        for i, node in enumerate(parent.children):
            if node.type == 'string' and node not in seen_string_nodes:
                seen_string_nodes.add(node)
                yield False, node
            elif node.type == 'fstring':
                parent.children[i] = node = _replace_fstring(node)
                yield False, node
            elif isinstance(node, BaseNode):
                yield from scan(node)

    return scan(tree)


def transform_source(source: str, double_quotes: bool = False) -> str:
    tree = parso.parse(source)
    for is_doc, leaf in _iter_strings(tree):
        normalize_string_prefix(leaf)
        normalize_string_quotes(leaf, is_doc, double_quotes=double_quotes)
    return tree.get_code()
