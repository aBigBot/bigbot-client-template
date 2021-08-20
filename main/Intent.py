from abc import ABC, abstractmethod
import inspect
import re
import sys
import typing

from chatterbot import parsing
import spacy
from spacy.language import Language
from spacy.matcher import DependencyMatcher, Matcher
from spacy.tokens import Token

from contrib import utils
from main import Log


@Language.component("quote_merger")
def quote_merger(doc):
    """This function merges multiple tokens enclosed between single or double quotes."""
    spans = []

    for match in re.finditer(r"\"(?:[^\"]|\.)*\"|'(?:[^']|\.)*'", doc.text):
        start, end = match.span()
        span = doc.char_span(start, end)
        if span is not None:
            spans.append(span)

    with doc.retokenize() as retokenizer:
        for span in spans:
            retokenizer.merge(span)
            for token in span:
                token._.is_quote = True

    return doc


class NLP:
    """Custom npl object"""

    _nlp = None

    @staticmethod
    def get_singleton():
        if NLP._nlp is None:
            nlp = spacy.load("en_core_web_md")
            nlp.add_pipe("quote_merger", first=True)
            Token.set_extension("is_quote", default=False)
            NLP._nlp = nlp
        return NLP._nlp


class IntentConfig:
    def serialize():
        return {
            "data": None,
            "description": "",
            "name": "",
        }


class Intent(ABC):
    """Looks for specifict tokens in a sting. This an abstract class and must be overried."""

    class Meta:
        """Use this class to set the intent's meta data.

        Attributes:
            config (list): Optional. A list of IntentConfig objects, if set the values set on the
                skill builder for this objects will be passed in the config parameter of __init__.
            description (str): A brief for the description.
            name (str): Opitonal. Human readable name.
        """

        pass

    def __call__(self, *args, **kwargs):
        return self.match(*args, **kwargs)

    @abstractmethod
    def match(self, processed_text, **kwargs):
        """Override this function to add custom matching

        Args:
            processed_text ():
            **kwargs: the values set for the config objects.

        Returns:
            any|None: The matched object or None if not match was found.
        """
        return None

    @classmethod
    def serialize(cls):
        meta = getattr(cls, "Meta", None)

        if meta is None:
            raise Exception("Meta is not set")

        result = {"component": cls.__module__ + "." + cls.__name__}

        config = getattr(meta, "config", None)
        if config:
            result["config"] = config

        description = getattr(meta, "description", None)
        if description:
            result["description"] = description
        else:
            result["description"] = cls.__name__

        name = getattr(meta, "name", None)
        if name:
            result["name"] = name
        else:
            result["name"] = cls.__name__

        type_ = getattr(meta, "type", None)
        if type_:
            result["type"] = type_

        return result


class LemmaIntent(Intent):
    class Meta:
        config = [
            {"name": "words", "type": "list", "description": "List of words to match"},
            {
                "name": "match",
                "type": "select",
                "default": "full",
                "attributes": {
                    "opiont": [
                        {"text": "Full Sentence", "value": "full"},
                        {"text": "After match", "value": "after"},
                        {"text": "Before match", "value": "before"},
                    ]
                },
            },
        ]
        description = "Matches one or more words using their lemma or 'base'."
        type = "str"

    def __init__(self, **config):
        words = config.get("words", [])
        nlp = config.get("__nlp__")

        self.on_match = config.get("match", "full")
        self.words = []

        for word in words:
            doc = nlp(word)
            for token in doc:
                if token.pos_ != "PUNCT":
                    self.words.append(token.lemma_)

    def match(self, doc):
        is_match, match, index = False, None, 0

        for sentence in doc.sents:
            for lemma in self.words:
                for i, token in enumerate(sentence):
                    if token.lemma_ == lemma:
                        index = i
                        is_match = True
                        match = sentence
                        break

        if match:
            if self.on_match == "after":
                match = match[index:].text
            if self.on_match == "before":
                match = match[: index - 1].text
            else:
                match = match.text

        return is_match, match


class DateIntent(Intent):
    class Meta:
        config = [{"name": "multiple", "type": "bool", "default": False}]
        description = "Extracts one or more dates from the input"
        type = "date"

    def __init__(self, **config):
        self.multiple = config.get("multiple", False)

    def match(self, doc):
        matches = parsing.datetime_parsing(doc.text)

        if len(matches) > 0:
            if self.multiple:
                return [m[1].strftime("%Y-%m-%d") for m in matches]
            return matches[0][1].strftime("%Y-%m-%d")


class DateTimeIntent(Intent):
    class Meta:
        config = [{"name": "multiple", "type": "bool", "default": False}]
        description = "Extracts one or more dates from the input"
        type = "datetime"

    def __init__(self, **config):
        self.multiple = config.get("multiple", False)

    def match(self, doc):
        matches = parsing.datetime_parsing(doc.text)

        if len(matches) > 0:
            if self.multiple:
                return [m[1].strftime("%Y-%m-%dT%T") for m in matches]
            return matches[0][1].strftime("%Y-%m-%dT%T")


class DependencyIntent(Intent):
    class Meta:
        config = [{"name": "patterns", "type": "code"}]
        description = "This is a complex intent, a sentence relation to extract any useful data"
        type = "str"

    def __init__(self, **config):
        self.patterns = config.get("patterns", [])

    def match(self, doc):
        matcher = DependencyMatcher("MATCHER", self.pattern)
        matches = matcher(doc)


class EmailIntent(Intent):
    class Meta:
        config = [{"name": "multiple", "type": "bool", "default": False}]
        description = "Extracts one or more emails from the input"
        type = "email"

    def __init__(self, **config):
        self.multiple = config.get("multiple", False)

    def match(self, doc):
        email_regex = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+", re.I)
        matches = email_regex.findall(doc.text)

        if len(matches) > 0:
            if self.multiple:
                return matches
            else:
                return matches[0]


class FuzzyMatchItent(Intent):
    class Meta:
        config = [
            {"name": "words", "type": "list"},
            {
                "name": "threshold",
                "type": "float",
                "default": 0.8,
                "attributes": {"min": 0, "max": 1, "step": 0.01},
            },
            {
                "name": "match",
                "type": "select",
                "default": "full",
                "attributes": {
                    "options": [
                        {"text": "Full Sentence", "value": "full"},
                        {"text": "After match", "value": "after"},
                        {"text": "Before match", "value": "before"},
                    ]
                },
            },
        ]
        description = "Matches one or more words using fuzzy matching"
        type = "str"

    def __init__(self, **config):
        self.method = config.get("match", "full")
        self.threshold = config.get("threshold", 1)
        self.words = config.get("words", [])

    def match(self, doc):
        sentences = list(filter(lambda x: len(x) > 0, re.split(",\s?", doc.text)))

        best_match = None
        best_ratio = 0
        idx = -1

        for index, sentence in enumerate(sentences):
            tmp_match = None
            tmp_ratio = 0

            for word in self.words:
                ratio, string = utils.fuzzy_search(word, sentence)
                if ratio > tmp_ratio:
                    tmp_match = string
                    tmp_ratio = ratio

            if tmp_ratio >= self.threshold and tmp_ratio > best_ratio:
                idx = index
                index = sentence.lower().index(tmp_match)
                best_ratio = tmp_ratio
                if self.method == "after":
                    best_match = sentence[index + len(tmp_match) :]
                elif self.method == "before":
                    best_match = sentence[:index]
                else:
                    best_match = sentence

        if best_match:
            sentences.pop(idx)
            return best_match


class MultiLemmaIntent(Intent):
    class Meta:
        config = [{"name": "pattern", "type": "code"}]
        description = "Match a sequential sets of lemmas"
        type = "str"

    def __init__(self, **config):
        nlp = config["__nlp__"]
        pattern = config.get("pattern", [])
        new_pattern = []

        added = False
        for index, item in enumerate(pattern):
            if added:
                new_pattern.append({"OP": "*"})
            added = False

            if type(item) == list:
                new_pattern.append({"LEMMA": {"IN": item}})
                added = True
            elif type(item) == str:
                new_pattern.append({"LEMMA": item})
                added = True

        self.matcher = Matcher(nlp.vocab)
        self.matcher.add("MultiLemma", [new_pattern])

    def match(self, doc):
        matches = self.matcher(doc)
        longest = (0, 0)
        for _, start, end in matches:
            if longest[1] - longest[0] < end - start:
                longest = (start, end)

        quotes = []
        for token in doc:
            if token._.is_quote:
                quotes.append(token)

        best, best_token = 999999, None
        for token in quotes:
            if abs(token.i - longest[0]) < best:
                best = abs(token.i - longest[0])
                best_token = token
            if abs(token.i - longest[1]) < best:
                best = abs(token.i - longest[1])
                best_token = token

        if best_token:
            return best_token.text[1:-1]

        return doc[longest[1] :].text


class MoneyIntent(Intent):
    class Meta:
        description = "Extracts a money quantity from the input"

    def match(self, doc):
        is_match = False
        for ent in doc.ents_:
            if ent.label_ == "MONEY":
                is_match = True
                break
        return is_match


class NumberIntent(Intent):
    class Meta:
        config = [{"name": "multiple", "type": "bool", "default": False}]
        description = "Extracts one or more quantities from the input"
        type = "number"

    def __init__(self, **config):
        self.multiple = config.get("multiple", False)

    def match(self, doc):
        matches = []

        for ent in doc.ents:
            if ent.label_ == "CARDINAL":
                matches.append(ent)

        print(matches)

        if len(matches) > 0:
            if self.multiple:
                return [self.parse_entity(i) for i in matches]
            return self.parse_entity(matches[0])

    @staticmethod
    def parse_entity(ent):
        value = None

        try:
            value = float(ent.text)
            if value and value.is_integer():
                value = int(value)
        except:
            try:
                value = utils.text2int(ent.text)
            except:
                pass

        return value


class PhoneIntent(Intent):
    class Meta:
        description = "Extracts one ore more phone numbers from the input"


class TimeIntent(Intent):
    class Meta:
        config = [{"name": "multiple", "type": "bool", "default": False}]
        description = "Extracts one or more times from the input"
        type = "time"

    def __init__(self, **config):
        self.multiple = config.get("multiple", False)

    def match(self, doc):
        matches = parsing.datetime_parsing(doc.text)

        if len(matches) > 0:
            if self.multiple:
                return [m[1].strftime("T%T") for m in matches]
            return matches[0][1].strftime("T%T")


# classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
all = [
    DateIntent,
    DateTimeIntent,
    EmailIntent,
    MultiLemmaIntent,
    NumberIntent,
    TimeIntent,
]
