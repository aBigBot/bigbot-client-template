from main.Node import (
    AudioNode,
    BaseNode,
    BinaryNode,
    CancelNode,
    IFrameNode,
    ImageNode,
    NotificationNode,
    SearchNode,
    SkipNode,
    TextNode,
)
import pytest

# ------------------------------------------------
# Setup
# ------------------------------------------------

# ------------------------------------------------
# Tests
# ------------------------------------------------

class TestBaseNodeDeserialize:
    """Tests BaseNode.deserialize"""

    def test_no_object(self):
        node = BaseNode.deserialize(None)
        assert node is None

    def test_no_data(self):
        node = BaseNode.deserialize({'node': 'big.bot.core.invalid'})
        assert node is None

    def test_invalid_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.invalid',
            'data': 'test',
        })
        assert node is None

    def test_audio_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.audio',
            'data': 'test',
        })
        assert isinstance(node, AudioNode)

    def test_binary_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.binary',
            'data': 'test',
        })
        assert isinstance(node, BinaryNode)

    def test_cancel_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.cancel',
            'data': 'test',
        })
        assert isinstance(node, CancelNode)

    def test_iframe_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.iframe',
            'data': 'test',
        })
        assert isinstance(node, IFrameNode)

    def test_image_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.image',
            'data': 'test',
        })
        assert isinstance(node, ImageNode)

    def test_notification_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.notification',
            'data': 'test',
        })
        assert isinstance(node, NotificationNode)

    def test_cancel_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.search',
            'data': 'test',
        })
        assert isinstance(node, SearchNode)

    def test_skip_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.skip',
            'data': 'test',
        })
        assert isinstance(node, SkipNode)

    def test_text_node(self):
        node = BaseNode.deserialize({
            'node': 'big.bot.core.text',
            'data': 'test',
        })
        assert isinstance(node, TextNode)
