import json


class Message:
    """
    A statement represents a single spoken entity, sentence or
    phrase that someone can say.
    """

    __slots__ = (
        "body",
        "contexts",
        "location",
        "values",
    )

    def __init__(self, **kwargs):
        self.body = kwargs.get("body")
        self.contexts = kwargs.get("contexts")
        self.location = kwargs.get("location")
        self.values = kwargs.get("values")

    def __str__(self):
        return str(self.serialize())

    def serialize(self):
        result = {}
        for key in dir(self):
            if "__" in key:
                continue
            attr = getattr(self, key)
            if type(attr) not in [bool, dict, float, int, list, str]:
                continue
            result[key] = getattr(self, key)
        return result
