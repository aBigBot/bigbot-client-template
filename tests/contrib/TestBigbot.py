from core.models import TTSAudio
from contrib.Bigbot import BaseBinder
import main.Node as Node
from main.Statement import OutputStatement
import pytest


# ------------------------------------------------
# Setup
# ------------------------------------------------

class MockProcessor:

    def __init__(self):
        self.called = 0
        self.statement = None

    def post_message(self, statement, *args, **kwargs):
        self.called += 1
        self.statement = statement


@pytest.fixture
def init_binder(mocker):
    def generate_reference(*args, **kwargs):
        return 'fake-uuid'

    def get_full_url(*args, **kwargs):
        return 'fake-url'

    def init_mock(self, *args, **kwargs):
        self.processor = MockProcessor()

    mocker.patch('contrib.utils.get_full_url', new=get_full_url)
    mocker.patch.object(BaseBinder, '__init__', new=init_mock)
    mocker.patch.object(TTSAudio, 'generate_reference', new=generate_reference)
    tts_spy = mocker.spy(TTSAudio, 'generate_reference')

    binder = BaseBinder(None, None)

    return binder, tts_spy


# ------------------------------------------------
# Tests
# ------------------------------------------------

class TestBinderOnPostMessage:
    """Test output of Binder.on_post_message"""

    def test_1(self, init_binder):
        binder, _ = init_binder

        statement = OutputStatement(0)
        statement.append_text('test')

        binder.on_post_message(statement)
        new_statement = binder.processor.statement

        assert new_statement.text == 'test'
        assert new_statement.contents == [
            {
                'data': 'test',
                'node': 'big.bot.core.text',
            },
            {
                'data': 'fake-url',
                'node': 'big.bot.core.tts',
            },
        ]


class TestTTS:
    """Test TTS processing in BaseBinder.on_post_message"""

    def test_tts_processing_1(self, init_binder):
        """Statement has a text node so a tts node should be added automatically
        """
        binder, tts_spy = init_binder

        statement = OutputStatement(0)
        statement.append_text('test')

        binder.on_post_message(statement)
        contents = binder.processor.statement.contents

        assert contents == [
            {
                'data': 'test',
                'node': 'big.bot.core.text',
            },
            {
                'data': 'fake-url',
                'node': 'big.bot.core.tts',
            }
        ]
        assert binder.processor.called == 1
        tts_spy.assert_called_once()

    def test_tts_processing_2(self, init_binder):
        """Statement does not has a text node so it should not include a tts
        node
        """
        binder, _ = init_binder

        statement = OutputStatement(0)
        statement.append_node(Node.AudioNode('fake-audio'))
        statement.append_node(Node.ImageNode('fake-image'))

        binder.on_post_message(statement)
        contents = binder.processor.statement.contents

        has_tts = False
        for node in contents:
            if node['node'] == 'big.bot.core.tts':
                has_tts = True
                break

        assert has_tts == False
        assert contents == [
            {
                'data': 'fake-audio',
                'node': 'big.bot.core.audio',
                'meta': None,
            },
            {
                'data': 'fake-image',
                'node': 'big.bot.core.image',
                'meta': None,
            },
        ]
        assert binder.processor.called == 1

    def test_tts_processing_3(self, init_binder):
        """A tts node is added when a Statement has not contents, this is by
        design
        """
        binder, tts_spy = init_binder

        statement = OutputStatement(0)

        binder.on_post_message(statement)
        contents = binder.processor.statement.contents

        has_tts = False
        for node in contents:
            if node['node'] == 'big.bot.core.tts':
                has_tts = True
                break

        assert has_tts
        assert len(contents) == 1
        assert contents == [
            {
                'data': 'fake-url',
                'node': 'big.bot.core.tts',
            },
        ]
        assert binder.processor.called == 1
        tts_spy.assert_called_once()
