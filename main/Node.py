import json

from django.utils.crypto import get_random_string
from jinja2 import Template


def all():
    data = [
        # Nodes that can be set by the user (?)
        AudioNode,
        BinaryNode,
        DateNode,
        DateTimeNode,
        DurationNode,
        IFrameNode,
        ImageNode,
        NotificationNode,
        OAuthNode,
        PaymentNode,
        PreviewNode,
        TextNode,
    ]
    for index, item in enumerate(data):
        data[index] = item(None, None).serialize()
    return data


class BaseNode:
    def __init__(self, node, data, meta):
        self.node = node
        self.data = data
        self.meta = meta
        pass

    def get_data(self):
        return self.data

    def get_meta(self):
        return self.meta

    def serialize(self):
        return {
            "node": self.node,
            "data": self.data,
            "meta": self.meta,
        }

    @staticmethod
    def deserialize(object):
        if isinstance(object, dict):
            if "node" in object and "data" in object:
                data = object.get("data")
                meta = object.get("meta")
                node = object.get("node")
                if node == "big.bot.core.audio":
                    return AudioNode(data, meta)
                if node == "big.bot.core.auth":
                    return AuthNode(data, meta)
                if node == "big.bot.core.binary":
                    return BinaryNode(data, meta)
                if node == "big.bot.core.cancel":
                    return CancelNode(data, meta)
                if node == "big.bot.core.carousel":
                    return CarouselNode(data, meta)
                if node == "big.bot.core.platform":
                    return ChatPlatformNode(data, meta)
                if node == "big.bot.core.delegates":
                    return DelegatesNode(data, meta)
                if node == "big.bot.core.iframe":
                    return IFrameNode(data, meta)
                if node == "big.bot.core.image":
                    return ImageNode(data, meta)
                if node == "big.bot.core.list":
                    return ListSelectionNode(data, meta)
                if node == "big.bot.core.notification":
                    return NotificationNode(data, meta)
                if node == "big.bot.core.oauth":
                    return OAuthNode(data, node)
                if node == "big.bot.core.payment":
                    return PaymentNode(data, meta)
                if node == "big.bot.core.picker.date":
                    return DateNode(data, meta)
                if node == "big.bot.core.picker.datetime":
                    return DateTimeNode(date, meta)
                if node == "big.bot.core.picker.duration":
                    return DurationNode(data, meta)
                if node == "big.bot.core.picker.file":
                    return InputFileNode(data, meta)
                if node == "big.bot.core.preview":
                    return PreviewNode(data, meta)
                if node == "big.bot.core.search":
                    return SearchNode(data, meta)
                if node == "big.bot.core.skip":
                    return SkipNode(data, meta)
                if node == "big.bot.core.text":
                    return TextNode(data, meta)


class AudioNode(BaseNode):
    def __init__(self, data, meta=None):
        super(AudioNode, self).__init__("big.bot.core.audio", data, meta)


class AuthNode(BaseNode):
    """This node is only used to send authentication credentials to the user. The node must have the
    following structure:

    {
        "node": "big.bot.core.auth",
        "data: {
            "access_token": "...",
            "token": "...",
            "uuid": "...",
        },
        "meta": None,
    }
    """

    def __init__(self, data, meta=None):
        import time

        data["created_at"] = time.time()
        super().__init__("big.bot.core.auth", data, meta)


class BinaryNode(BaseNode):
    def __init__(self, data, meta=None):
        super(BinaryNode, self).__init__("big.bot.core.binary", data, meta)


class CancelNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(CancelNode, self).__init__("big.bot.core.cancel", data, meta)

class CarouselNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(CarouselNode, self).__init__("big.bot.core.carousel", data, meta)

class ChatPlatformNode(BaseNode):
    def __init__(self, data, meta):
        super(ChatPlatformNode, self).__init__("big.bot.core.platform", data, meta)


class DateNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(DateNode, self).__init__("big.bot.core.picker.date", data, meta)


class DateTimeNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(DateTimeNode, self).__init__("big.bot.core.picker.datetime", data, meta)


class DelegatesNode(BaseNode):
    """Creates a delegates node, the node has the following structure:

    {
        "node": "big.bot.core.delegates",
        "data": [                                                   # List of delegates
            {
                "body": "Delegate Name",                            # Delegate's name
                "context": [2, 4],                                  # Delegate's contexts
                "image" "https://url.to.delegates.avatar.image",
                "values": [5, 27],                                  # Delegate's id and skill's id
            },
            ...
        ],
        "meta": None,
    }

    The context field can one of the following values:

    + [1] - Where 1 is CTX_HUMAN_DELEGATE_SELECT.
    + [2, 4] - Where 2 is CTX_BOT_DELEGATE_SELECT, and 4 is CTX_START_SKILL.

    There's to cases for the values field:

    + [5] - An array with a single integer in the case of HumanDelegates, the integer is the
      delegate's id.
    + [5, 27] - An array with two integers in the case of BotDelegates, the first integer is the
      delegate's id, the second integers is the skill's id.
    """

    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.delegates", data, meta)


class DurationNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(DurationNode, self).__init__("big.bot.core.picker.duration", data, meta)


class IFrameNode(BaseNode):
    def __init__(self, data, meta=None):
        super(IFrameNode, self).__init__("big.bot.core.iframe", data, meta)


class ImageNode(BaseNode):
    def __init__(self, data, meta=None):
        super(ImageNode, self).__init__("big.bot.core.image", data, meta)


class InputFileNode(BaseNode):
    """The node should have the following structure:

    {
        "node": "big.bot.core.picker.file",
        "data": None,
        "meta": {
            "accept": "image/*",
            "size": 1000000,
        },
    }

    Where:
        + accept: Accepted file extensions, can be any value accepted by the accept property of an
            HTML input tag.
        + size: Maximun size of the file in bytes.
    """

    def __init__(self, meta={}):
        super().__init__("big.bot.core.picker.file", None, meta)


class ListSelectionNode(BaseNode):
    """
    {
        "node": "big.bot.core.list",
        "data": [
            {
                "text": "Human Readable Value",
                "value": <custom_value>,
            }
        ],
        "meta": None,
    }
    """

    def __init__(self, data=[]):
        super().__init__("big.bot.core.list", data, None)

    def append_selection(self, item):
        self.data.append(item)


class LocalStorageNode(BaseNode):
    """Any data sent with this node will be stored in the browser's local storage, data is a
    dictionary with the elements to store.
    """

    def __init__(self, data={}):
        super().__init__("big.bot.core.storage", data, None)


class NotificationNode(BaseNode):
    def __init__(self, data, meta=None):
        super(NotificationNode, self).__init__("big.bot.core.notification", data, meta)


class OAuthNode(BaseNode):
    def __init__(self, data, meta=None):
        super(OAuthNode, self).__init__("big.bot.core.oauth", data, meta)


class PaymentNode(BaseNode):
    def __init__(self, data, meta=None):
        super(PaymentNode, self).__init__("big.bot.core.payment", data, meta)

    def sample(self):
        data = {
            "node": "big.bot.core.payment",
            "data": 549.99,
            "meta": {
                "charge_summary": "You have to pay",
                "currency_code": "USD",
                "currency_symbol": "$",
                "button_text": "Make Payment",
                "payment_services": [
                    {
                        "name": "Bank Card",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1",
                    },
                    {
                        "name": "Google Pay",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1",
                    },
                    {
                        "name": "Apple Pay",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1",
                    },
                ],
            },
        }


class PreviewNode(BaseNode):
    """Node to preview a URL. The node hass the following structure

    {
        "data": "<url>",
        "meta": {
            "summary": "URL's summary or descriptiom",
            "thumbnail": "URL's thumbnail",
            "title": "URL's title",
        },
    }
    """

    def __init__(self, data, meta={}):
        from contrib.utils import web_preview

        try:
            title, summary, thumbnail = web_preview(data)
        except:
            title, summary, thumbnail = "", "", ""

        if isinstance(meta, dict):
            meta = {
                "summary": meta.get("summary", summary),
                "thumbnail": meta.get("thumbnail", thumbnail),
                "title": meta.get("title", title),
            }
        else:
            meta = {"summary": summary, "thumbnail": thumbnail, "title": title}
        super().__init__("big.bot.core.preview", data, meta)


class PromiseNode(BaseNode):
    """
    {
        "id": "ahty",
        "type": "open",
    }
    """

    def __init__(self, data):
        super().__init__("big.bot.core.promise", data, None)

    @staticmethod
    def create():
        id_ = get_random_string(4, "abcdefghijklmnopqrstuvwxyz0123456789")
        open = PromiseNode({"id": id_, "type": "open"})
        close = open = PromiseNode({"id": id_, "type": "close"})
        return open, close


class SearchNode(BaseNode):
    def __init__(self, data, meta=None):
        super(SearchNode, self).__init__("big.bot.core.search", data, meta)

    def __str__(self):
        node = self.get_node()
        if isinstance(node, CancelNode):
            return "Cancel"
        elif isinstance(node, SkipNode):
            return "Skip"
        elif isinstance(node, TextNode):
            return node.data
        return super(SearchNode, self).__str__()

    @staticmethod
    def wrap_text(display_text, input):
        return SearchNode(input, TextNode(display_text).serialize())

    @staticmethod
    def wrap_cancel():
        return SearchNode(None, CancelNode().serialize())

    @staticmethod
    def wrap_skip():
        return SearchNode(None, SkipNode().serialize())

    def get_node(self):
        return BaseNode.deserialize(self.get_meta())


class SkipNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super(SkipNode, self).__init__("big.bot.core.skip", data, meta)


class TextNode(BaseNode):
    def __init__(self, data, meta=None):
        super(TextNode, self).__init__("big.bot.core.text", data, meta)


class TTSNode(BaseNode):
    def __init__(self, data, meta=None):
        super(TTSNode, self).__init__("big.bot.core.tts", data, meta)
