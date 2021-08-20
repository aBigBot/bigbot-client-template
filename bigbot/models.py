import json
import random
import string

from django.db import models
from django.db.models import Max
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from contrib import mixin, permissions
from contrib.utils import get_full_url
from core.models import Attachment, BotDelegate, User
from main import Log


class ResponsePhrase(mixin.Model, models.Model):
    class Permissions:
        all = permissions.USER

    attachment = models.ForeignKey(
        Attachment,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    hash = models.CharField(
        default=None,
        max_length=32,
        blank=True,
        null=True,
    )
    string = models.TextField()
    delegate_id = models.ForeignKey(BotDelegate, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(default="big.bot.core.text", max_length=128)

    def __str__(self):
        return self.string

    def get_nodes(self):
        node = {"data": self.string, "meta": None, "node": self.type}

        if self.type not in ["big.bot.core.iframe", "big.bot.core.preview", "big.bot.core.text"]:
            node["data"] = get_full_url(reverse("response_media", args=[self.id]))

        return [node]

    def save(self, *args, **kwargs):
        import hashlib

        if self.hash is None:
            if self.attachment is not None:
                self.hash = self.attachment.checksum
            else:
                self.hash = hashlib.md5(self.string.encode()).hexdigest()
        super().save(*args, **kwargs)

    def serialize(self, *args, **kwargs):
        data = {"delegate_id": self.delegate_id.id, "responseText": self.string, "type": self.type}
        if self.attachment is not None:
            data["file"] = self.attachment.to_base64()
            data["fileName"] = self.attachment.name
        return data

    @staticmethod
    def get_singleton(data):
        import hashlib

        object = None
        try:
            data = json.loads(data)
        except:
            pass

        if type(data) == str:
            hash_ = hashlib.md5(data.encode()).hexdigest()
            object = ResponsePhrase.objects.filter(string=data).first()
            if not object:
                object = ResponsePhrase.objects.filter(hash=hash_).first()
            if not object:
                object = ResponsePhrase.objects.create(hash=hash_, string=data)
        else:
            file = data.get("file")
            filename = data.get("fileName")
            kwargs = {"string": data["responseText"], "type": data["responseType"]["value"]}

            if kwargs["type"] in [
                "big.bot.core.iframe",
                "big.bot.core.preview",
                "big.bot.core.text",
            ]:
                kwargs["hash"] = hashlib.md5(kwargs["string"].encode()).hexdigest()
            else:
                kwargs["hash"] = hashlib.md5(file.encode()).hexdigest()

            object = ResponsePhrase.objects.filter(hash=kwargs["hash"]).first()
            if object is None:
                object = ResponsePhrase.objects.create(**kwargs)

            if file is not None:
                object.attachment = Attachment.put_base64(
                    "response.phrase",
                    object.id,
                    "attachment",
                    filename,
                    file,
                )

        return object


class InputPattern(mixin.Model, models.Model):
    class Permissions:
        all = permissions.USER

    LANGUAGE_POLICY_INDEPENDENT = 0
    LANGUAGE_POLICY_LNG_BOUND = 1

    CHOICES_LANGUAGE_POLICY = (
        (LANGUAGE_POLICY_INDEPENDENT, _("Language Independent")),
        (LANGUAGE_POLICY_LNG_BOUND, _("Bounded within language")),
    )

    string = models.TextField()
    # remove it
    delegate_id = models.ForeignKey(BotDelegate, on_delete=models.CASCADE, null=True, blank=True)
    response_ids = models.ManyToManyField(ResponsePhrase)
    lang_policy = models.IntegerField(
        choices=CHOICES_LANGUAGE_POLICY, null=True, default=LANGUAGE_POLICY_INDEPENDENT
    )

    def __str__(self):
        return self.string

    def save(self, *args, **kwargs):
        if InputPattern.objects.filter(string=self.string).first() and not self.pk:
            return
        super(InputPattern, self).save(*args, **kwargs)

    @staticmethod
    def get_singleton(string):
        object = InputPattern.objects.filter(string=string).first()
        if not object:
            object = InputPattern.objects.create(string=string)
        return object

    @staticmethod
    def post_values(string, responses, id=None):
        rec = InputPattern.objects.get(id=id) if id else InputPattern.get_singleton(string)
        rec.response_ids.clear()
        for response in responses:
            phrase = ResponsePhrase.get_singleton(response)
            phrase.delegate_id = BotDelegate.objects.get(id=response["delegate_id"])
            phrase.save()
            rec.delegate_id = BotDelegate.objects.get(id=response["delegate_id"])
            rec.response_ids.add(phrase)
        rec.save()

    @staticmethod
    def post_list_values(data_list):
        from chatterbot import ChatBot
        from chatterbot.trainers import ListTrainer

        chatbot = ChatBot(
            "",
            read_only=True,
        )
        trainer = ListTrainer(chatbot)
        trainer.train(data_list)
        pass

    @staticmethod
    def delete_list_values():
        from chatterbot import ChatBot
        from chatterbot.trainers import ListTrainer

        chatbot = ChatBot(
            "",
            read_only=True,
        )
        chatbot.storage.drop()
        pass
