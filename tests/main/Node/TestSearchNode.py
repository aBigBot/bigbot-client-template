from main.Node import CancelNode, SearchNode
import pytest

# ------------------------------------------------
# Setup
# ------------------------------------------------

# ------------------------------------------------
# Tests
# ------------------------------------------------

def test_search_node_wrap_cancel():
    """Tests SearchNode.wrap_cancel"""
    node = SearchNode.wrap_cancel()
    assert node.serialize() == {
        'node': 'big.bot.core.search',
        'data': None,
        'meta': {
            'node': 'big.bot.core.cancel',
            'data': None,
            'meta': None,
        },
    }

    assert str(node) == 'Cancel'


def test_search_node_wrap_skip():
    """Tests SearchNode.wrap_skip"""
    node = SearchNode.wrap_skip()
    assert node.serialize() == {
        'node': 'big.bot.core.search',
        'data': None,
        'meta': {
            'node': 'big.bot.core.skip',
            'data': None,
            'meta': None,
        },
    }

    assert str(node) == 'Skip'


def test_search_node_wrap_text():
    """Tests SearchNode.wrap_text"""
    node = SearchNode.wrap_text('test', 'test')
    assert node.serialize() == {
        'node': 'big.bot.core.search',
        'data': 'test',
        'meta': {
            'node': 'big.bot.core.text',
            'data': 'test',
            'meta': None,
        },
    }

    assert str(node) == 'test'
