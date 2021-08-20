import json

from .Node import (
    BaseNode,
    ChatPlatformNode,
    DelegatesNode,
    ListSelectionNode,
    PaymentNode,
    TextNode
)


class InputStatement:
    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.flag = kwargs.get("flag")
        self.input = kwargs.get("input")
        self.location = kwargs.get("location")
        self.text = kwargs.get("text")

    def __str__(self):
        if self.text:
            return self.text
        return super(InputStatement, self).__str__()

    def get_node(self):
        return BaseNode.deserialize(self.input)


class OutputStatement:
    """A statement represents a single spoken entity, sentence or phrase that someone can say."""

    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.confidence = kwargs.get("confidence")
        self.contents = []

    def __str__(self):
        for item in self.contents:
            if isinstance(item, ChatPlatformNode):
                return "Choose a platform"
            elif isinstance(item, DelegatesNode):
                return "Please select a delegate"
            elif isinstance(item, ListSelectionNode):
                return "Please select an option"
            elif isinstance(item, PaymentNode):
                return "Choose a payment"
            elif isinstance(item, TextNode):
                return item.data
        return super(OutputStatement, self).__str__()

    def append_node(self, node):
        self.contents.append(node)

    def append_text(self, text):
        self.contents.append(TextNode(text))

    def serialize(self):
        """Returns a dictionary representation of the statement."""
        data = {
            "confidence": self.confidence,
            "contents": self.contents,
            "user_id": self.user_id,
        }
        return data
