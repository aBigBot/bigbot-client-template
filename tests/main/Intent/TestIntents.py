import datetime
import pytest
import spacy

from core.models import User
from main.Binder import Registry
import main.Intent as intent
from main.Processor import SkillProcessor
from main.Statement import InputStatement


# --------------------------------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------------------------------


skill = {
    "package": "ai.bigbot.send-message",
    "name": "Send Message",
    "start": "8dvr",
    "blocks": [
        {
            "id": "8dvr",
            "parend_id": -1,
            "component": "main.Block.PromptText",
            "properties": [
                {
                    "name": "primary_text",
                    "value": "Please enter the email, the subject, and the body of the message",
                }
            ],
            "connections": [[1, "i1zt"]],
        },
        {
            "id": "i1zt",
            "parent_id": -1,
            "component": "main.Block.InputText",
            "properties": [
                {"name": "key", "value": "garbage"},
                {"name": "required", "value": False},
            ],
            "connections": [[1, "cze8"]],
        },
        {
            "id": "cze8",
            "parent_id": "i1zt",
            "component": "main.Block.InputEmail",
            "intent": "main.Intent.EmailIntent",
            "properties": [
                {"name": "key", "value": "email"},
                {"name": "prompt", "value": "Please enter the email to send the message to"},
                {"name": "required", "value": True},
            ],
            "connections": [[-1, "cze8"], [1, "tnfz"]],
        },
        {
            "id": "tnfz",
            "parent_id": "cze8",
            "component": "main.Block.InputText",
            "intent": "main.Intent.MultiLemmaIntent",
            "intent_properties": {"pattern": ["subject"]},
            "properties": [
                {"name": "key", "value": "subject"},
                {"name": "prompt", "value": "Please enter the subject of the message"},
                {"name": "required", "value": True},
            ],
            "connections": [[-1, "tnfz"], [1, "5ty6"]],
        },
        {
            "id": "5ty6",
            "parent_id": "tnfz",
            "component": "main.Block.InputText",
            "intent": "main.Intent.MultiLemmaIntent",
            "intent_properties": {"pattern": ["body"]},
            "properties": [
                {"name": "key", "value": "body"},
                {"name": "prompt", "value": "Please enter the body of the message"},
                {"name": "required", "value": True},
            ],
            "connections": [[-1, "5ty6"], [1, "opb7"]],
        },
        {
            "id": "opb7",
            "parent_id": "5ty6",
            "component": "main.Block.PromptText",
            "properties": [{"name": "primary_text", "value": ["Message sent to"]}],
            "connections": [[1, "3io0"]],
        },
        {
            "id": "3io0",
            "parent_id": "opb7",
            "component": "main.Block.PromptText",
            "properties": [{"name": "read", "value": "email"}],
            "connections": [[1, "fwju"]],
        },
        {
            "id": "fwju",
            "parent_id": "3io0",
            "component": "main.Block.PromptText",
            "properties": [{"name": "primary_text", "value": ["With subject"]}],
            "connections": [[1, "6v2h"]],
        },
        {
            "id": "6v2h",
            "parent_id": "3io0",
            "component": "main.Block.PromptText",
            "properties": [{"name": "read", "value": "subject"}],
            "connections": [[1, "t9bm"]],
        },
        {
            "id": "t9bm",
            "parent_id": "6v2h",
            "component": "main.Block.PromptText",
            "properties": [{"name": "primary_text", "value": ["And the message"]}],
            "connections": [[1, "73y2"]],
        },
        {
            "id": "73y2",
            "parent_id": "t9bm",
            "component": "main.Block.PromptText",
            "properties": [{"name": "read", "value": "body"}],
            "connections": [[1, "yyyx"]],
        },
        {
            "id": "yyyx",
            "parent_id": "73y2",
            "component": "main.Block.TerminalBlock",
            "properties": [],
            "connections": [],
        },
    ],
}


class MockState:
    def __init__(self):
        self.data = {}
        self.skill = skill

    def serialize(self):
        pass


class MockupBinder:
    def __init__(self):
        self.registry = Registry()
        self.state = MockState()

    def get_registry(self):
        return self.registry

    def on_context(self):
        pass

    def on_save_state(self, *args, **kwargs):
        pass


@pytest.fixture
def binder_setup():
    binder = MockupBinder()
    return {"binder": binder}


@pytest.fixture
def setup():
    nlp = intent.NLP.get_singleton()
    return {"nlp": nlp}


# --------------------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------------------


class TestAcceptIntent:
    def test(self, setup):
        nlp = setup["nlp"]
        accept_intent = intent.LemmaIntent(words=["accept ok", "yes"], __nlp__=nlp)

        doc = nlp("I accept")
        match = accept_intent.match(doc)
        assert match

        doc = nlp("Is ok")
        match = accept_intent.match(doc)
        assert match

        doc = nlp("Yes do it")
        match = accept_intent.match(doc)
        assert match


class TestDateIntent:
    def test(self, setup):
        nlp = setup["nlp"]
        date_intent = intent.DateIntent()

        doc = nlp("Sent it on May 3")
        match = date_intent(doc)

        assert match == "2021-05-03"


class TestDateTimeIntent:
    def test(self, setup):
        nlp = setup["nlp"]
        date_intent = intent.DateTimeIntent()

        doc = nlp("Sent it on May 3 at 3 pm")
        match = date_intent(doc)

        assert match == "2021-05-03T15:00:00"


class TestEmailIntent:
    def test_extract_one(self, setup):
        nlp = setup["nlp"]
        doc = nlp("sent a message to hello@example.com")
        email_intent = intent.EmailIntent()

        match = email_intent.match(doc)

        assert match == "hello@example.com"

    def test_extract_multiple(self, setup):
        nlp = setup["nlp"]
        doc = nlp("sent a message to hello@example.com, hello@gmail.com, and hello@hotmail.com")
        email_intent = intent.EmailIntent(multiple=True)

        match = email_intent.match(doc)

        assert match == ["hello@example.com", "hello@gmail.com", "hello@hotmail.com"]


class TestLemmaIntent:
    def test_simple(self, setup):
        nlp = setup["nlp"]
        lemma_intent = intent.LemmaIntent(words=["sing"], __nlp__=nlp)

        doc = nlp("I sing every morning.")
        match = lemma_intent.match(doc)
        assert match

        doc = nlp("I sang in the morning.")
        match = lemma_intent.match(doc)
        assert match

        doc = nlp("I had sung in the morning.")
        match = lemma_intent.match(doc)
        assert match

    def test_complex(self, setup):
        nlp = setup["nlp"]
        lemma_intent = intent.LemmaIntent(words=["accept ok", "yes"], __nlp__=nlp)

        doc = nlp("I accept")
        match = lemma_intent.match(doc)
        assert match

        doc = nlp("Is ok")
        match = lemma_intent.match(doc)
        assert match

        doc = nlp("Yes do it")
        match = lemma_intent.match(doc)
        assert match


class TestMultiLemmaIntent:
    def test_1(self, setup):
        nlp = setup["nlp"]
        ml_intent = intent.MultiLemmaIntent(pattern=["new", "post"], __nlp__=nlp)

        doc = nlp("Create a new post called 'Hello World!'")
        match = ml_intent(doc)

        assert match == "Hello World!"

    def test_2(self, setup):
        nlp = setup["nlp"]
        ml_intent = intent.MultiLemmaIntent(pattern=[["delete", "remove"], "post"], __nlp__=nlp)

        doc = nlp("Remove the post called 'Hello World!'")
        match = ml_intent(doc)

        assert match == "Hello World!"


class TestNumberIntent:
    def test_big_number_word(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent(multiple=True)

        doc = nlp(
            "I want to buy two hundred and twenty four apples and three thousand and fifty one oranges"
        )
        match = number_intent(doc)

        assert match == [224, 3051]

    def test_big_multiple_number_word(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent()

        doc = nlp("I want to buy two hundred and twenty four apples")
        match = number_intent(doc)

        assert match == 224

    def test_float(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent()

        doc = nlp("I want to buy 2.1 apples")
        match = number_intent(doc)

        assert match == 2.1

    def test_multiple_simple(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent(multiple=True)

        doc = nlp("I want to buy 2 apples and 3 oranges")
        match = number_intent(doc)

        assert match == [2, 3]

    def test_simple(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent()

        doc = nlp("I want to buy 2 apples")
        match = number_intent(doc)

        assert match == 2

    def test_simple_word(self, setup):
        nlp = setup["nlp"]
        number_intent = intent.NumberIntent()

        doc = nlp("I want to buy two apples")
        match = number_intent(doc)

        assert match == 2


class TestTimeIntent:
    def test_1(self, setup):
        nlp = setup["nlp"]
        time_intent = intent.TimeIntent()

        doc = nlp("Sent it at 3 pm")
        match = time_intent(doc)

        assert match == "T15:00:00"


class TestMultipleIntents:
    def test(self):
        binder = MockupBinder()
        input_ = "Sent a message to hello@example.com with the subject 'Hello' and the body 'How have you been?'"

        processor = SkillProcessor()
        statement = InputStatement(None, input=input_, text=input_)

        processed = processor.process_intents(binder, binder.state, statement)

        data = binder.state.data

        assert data["body"] == "How have you been?"
        assert data["email"] == "hello@example.com"
        assert data["subject"] == "Hello"
