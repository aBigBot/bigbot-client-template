import base64
from datetime import datetime
import hashlib
import importlib
import importlib.util
import io
import json
import math
import mimetypes
import os
import random
import re
import shutil
import sys
import time
from urllib.parse import urlparse
import uuid
import zipfile

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import Now
from django.http import HttpResponse, JsonResponse
from django.utils.translation import ugettext_lazy as _
from django_middleware_global_request.middleware import get_request
from silk.profiling.profiler import silk_profile

from contrib import mixin, permissions, utils
from contrib.exceptions import JsonRPCException
from contrib.keycloak import KeycloakController, KeycloakUser
from contrib.statement import Statement
from main import Log

from . import exceptions


# --------------------------------------------------------------------------------------------------
# Cusmtom Fields
# --------------------------------------------------------------------------------------------------


class KeycloakUUID(models.UUIDField):
    """Custom UUID field that fetches data from Keycloak"""

    description = "Custom UUID field that fetches data from Keycloak"

    def db_type(self, connection):
        data = self.db_type_parameters(connection)
        try:
            return connection.data_types["UUIDField"] % data
        except:
            return None

    def get_internal_type(self):
        return "KeycloakUUID"

    @staticmethod
    def serialize_object(id):
        if type(id) == str:
            id = uuid.UUID(id)
        user = KeycloakController.get_user(id, False)
        return user.serialize("__all__")


# --------------------------------------------------------------------------------------------------
# User Model
# --------------------------------------------------------------------------------------------------


class User(AbstractUser):
    avatar = models.OneToOneField(
        "core.Attachment", on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    is_human = models.BooleanField(default=True)
    keycloak_user = KeycloakUUID(default=None, blank=True, null=True)

    def _setup_avatar(self):
        if self.is_human:
            avatar_file = open(settings.BASE_DIR + "/static/images/default_user.png", "rb")
        else:
            avatar_file = open(settings.BASE_DIR + "/static/images/default_bot.png", "rb")
        self.avatar = Attachment.put_attachment("user", self.id, "avatar", avatar_file)
        self.save()

    def get_avatar_base64(self):
        if self.avatar is None:
            self._setup_avatar()
        return self.avatar.to_base64()

    def get_avatar_url(self):
        if self.avatar is None:
            self._setup_avatar()
        return self.avatar.get_url()

    def update_avatar_base64(self, base64_string):
        data, mimetype = utils.parse_base64(base64_string)

        if self.avatar is None:
            self.avatar = Attachment.put_base64("user", self.id, "avatar", "avatar", base64_string)
        else:
            self.avatar.update_base64(base64_string)

        self.save()

    def update_keycloak_user(self, keycloak_user):
        self.email = keycloak_user.email
        self.first_name = keycloak_user.firstName
        self.keycloak_user = keycloak_user.id
        self.last_name = keycloak_user.lastName
        self.save()

    @staticmethod
    def get_keycloak_user(keycloak_user):
        if type(keycloak_user) == str:
            keycloak_user = KeycloakController.get_user(keycloak_user)
        user = User.objects.filter(keycloak_user=keycloak_user.id).first()
        if user:
            return user
        return User.objects.create(
            email=keycloak_user.email,
            first_name=keycloak_user.firstName,
            keycloak_user=keycloak_user.id,
            last_name=keycloak_user.lastName,
            username=str(uuid.uuid4()),
        )


# --------------------------------------------------------------------------------------------------
# Credentials Models
# --------------------------------------------------------------------------------------------------


class AccessToken(mixin.Model, models.Model):
    """This model creates credentials for a chat user. The user is most of the time an anonymous
    user.
    """

    access_token = models.CharField(max_length=254, unique=True)
    access_uuid = models.CharField(max_length=254, unique=True, null=True)
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="access_token")

    class Meta:
        unique_together = ["access_token", "access_uuid"]

    def __str__(self):
        return self.user_id.username

    def _get_user(self):
        try:
            return (
                User.objocts.select_related(
                    "active_channel", "archived_channels", "avatar", "human_delegate"
                )
                .prefetch_related("bot_delegates", "human_delegate__mail_channels")
                .get(id=self.user_id.id)
            )
        except Exception as e:
            Log.error("AccessToken._get_user", e)
            return False

    @staticmethod
    def authenticate(uuid, token, keycloak_user=None):
        if keycloak_user:
            user = User.objects.filter(keycloak_user=keycloak_user.id).first()
            record = None
            if user:
                record = (
                    AccessToken.objects.filter(user_id=user)
                    .select_related("user_id__human_delegate")
                    .prefetch_related("user_id__archived_channels")
                    .first()
                )
                if not record:
                    record = AccessToken.create_token(user)
            if record:
                return user

        if uuid and token:
            record = (
                AccessToken.objects.filter(access_uuid=uuid, access_token=token)
                .select_related("user_id__human_delegate")
                .prefetch_related("user_id__archived_channels")
                .first()
            )
            if record:
                return record.user_id

        return False

    @staticmethod
    def create_token(user):
        return AccessToken.objects.create(user_id=user)

    @staticmethod
    def find(uuid, token):
        if uuid and token:
            return AccessToken.objects.filter(access_uuid=uuid, access_token=token).first()
        return False

    @staticmethod
    def find_from_uuid(uuid):
        if uuid:
            record = AccessToken.objects.filter(access_uuid=uuid).first()
            if record:
                return record.user_id
        return False

    @staticmethod
    # @silk_profile(name="AccessToken.get_or_create_keycloak_user")
    def get_or_create_keycloak_user(keycloak_user, token, uuid):
        """Checks if keycloak_user is linked to any specific credentials, if not assigns the
        crentials to the user.

        Args:
            keycloak_user: An instance of contrib.keycloak.KeycloakUser
            token (uuid)
            uuid (uuid)

        Returns:
            An instance of AccessToken
        """
        user = (
            User.objects.filter(keycloak_user=keycloak_user.id)
            .select_related("access_token")
            .first()
        )
        access_token = getattr(user, "access_token", None)
        if access_token:
            return access_token
        access_token = AccessToken.objects.get(access_token=token, access_uuid=uuid)
        access_token.user_id.update_keycloak_user(keycloak_user)
        return access_token

    def save(self, *args, **kwargs):
        if not self.pk:
            self.access_uuid = str(uuid.uuid4())
            self.access_token = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def serialize(self):
        return {"uuid": self.access_uuid, "token": self.access_token}


class ApiKeys(mixin.Model, models.Model):
    """This model creates a set of credentials to be used by an external client. The credentials
    will give access to the REST API to the client.
    """

    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    api_key = models.CharField(max_length=254, unique=True)
    api_secret = models.CharField(max_length=254, unique=True)

    def __str__(self):
        return self.user_id.username

    def save(self, *args, **kwargs):
        if not self.pk:
            self.api_key = str(uuid.uuid4())
            self.api_secret = str(uuid.uuid4())
        super(ApiKeys, self).save(*args, **kwargs)

    @staticmethod
    def get_key(user):
        object = ApiKeys.objects.filter(user_id=user.id).first()
        if not object:
            object = ApiKeys.objects.create(user_id=user)
        return object

    @staticmethod
    def get_keys(request, user):
        object = ApiKeys.objects.filter(user_id=user.id).first()
        if not object:
            object = ApiKeys.objects.create(user_id=user)
        return object

    @staticmethod
    def find_api_keys(uuid, token, revoke=False):
        user = AccessToken.authenticate(uuid, token)
        if not user:
            user = ApiKeys.authenticate(uuid, token)
        if user:
            if revoke:
                for item in ApiKeys.objects.filter(user_id=user.id):
                    item.delete()
            object = ApiKeys.objects.filter(user_id=user.id).first()
            if not object:
                object = ApiKeys.objects.create(user_id=user)
            data = {
                "api_key": object.api_key,
                "api_secret": object.api_secret,
            }
            return data
        return False

    @staticmethod
    def authenticate(api_key, api_secret):
        if api_key and api_secret:
            object = ApiKeys.objects.filter(api_key=api_key, api_secret=api_secret).first()
            if object:
                return object.user_id
        return False


# --------------------------------------------------------------------------------------------------
# Application Models
# --------------------------------------------------------------------------------------------------


class Attachment(mixin.Model, models.Model):

    name = models.CharField(max_length=254)
    size = models.FloatField(null=False)
    file_uuid = models.CharField(max_length=254, null=False)
    mime_type = models.CharField(max_length=64, null=False)
    checksum = models.CharField(max_length=128, null=False)
    ref_field = models.CharField(max_length=128, null=True)
    res_id = models.IntegerField(null=False)
    model = models.CharField(max_length=32, null=False)
    data = models.BinaryField(null=True)

    def __str__(self):
        return self.name

    def update_base64(self, base64_string):
        data, mimetype = utils.parse_base64(base64_string)
        data = base64.b64decode(data.encode())
        self.checksum = hashlib.md5(data).hexdigest()
        self.data = data
        self.mime_type = mimetype
        self.size = sys.getsizeof(data)
        self.save()

    @staticmethod
    def add_message_file(message_id, file):
        message = MailMessage.objects.filter(message_id=message_id).first()
        if message:
            model = "mail.message"
            name = file.name
            res_id = message.id
            size = len(file)
            mime_type = mimetypes.guess_type(file.name)[0]
            data = file.read()
            checksum = hashlib.md5(data).hexdigest()
            record = Attachment.objects.create(
                name=name,
                model=model,
                res_id=res_id,
                size=size,
                checksum=checksum,
                mime_type=mime_type,
                data=data,
            )
        return

    @staticmethod
    def get_attachment(model, res_id, ref_field):
        record = Attachment.objects.filter(res_id=res_id, model=model, ref_field=ref_field).first()
        if record:
            request = mixin.request()
            return (
                settings.HTTP_PROTOCOL
                + "://"
                + request.META["HTTP_HOST"]
                + "/consumer/file?checksum="
                + record.checksum
                + "&file_uuid="
                + record.file_uuid
            )
        return False

    @staticmethod
    def get_message_attachments(message):
        if message:
            return Attachment.objects.filter(res_id=message.id, model="mail.message")
        return []

    @staticmethod
    def get_message_file(checksum, file_uuid):
        record = Attachment.objects.filter(
            checksum=checksum,
            file_uuid=file_uuid,
        ).first()
        if record:
            return HttpResponse(record.data, content_type=record.mime_type)
        return HttpResponse(status=500)

    def get_url(self):
        return (
            settings.HTTP_PROTOCOL
            + "://"
            + settings.SERVER_HOST
            + "/consumer/file?checksum="
            + self.checksum
            + "&file_uuid="
            + self.file_uuid
        )

    @staticmethod
    def put_attachment(model, res_id, ref_field, file):
        name = file.name
        data = file.read()
        size = sys.getsizeof(data)
        checksum = hashlib.md5(data).hexdigest()
        mime_type = mimetypes.guess_type(file.name)[0]
        record = Attachment.objects.filter(res_id=res_id, model=model, ref_field=ref_field).first()
        if not record:
            record = Attachment.objects.create(
                name=name,
                model=model,
                res_id=res_id,
                size=size,
                checksum=checksum,
                mime_type=mime_type,
                data=data,
                ref_field=ref_field,
            )
        else:
            record.name = name
            record.size = size
            record.checksum = checksum
            record.data = data
            record.mime_type = mime_type
            record.save()
        return record

    @staticmethod
    def put_base64(model, res_id, ref_field, filename, base64_string):
        """Creates an attachment from a base64 string"""
        base64_regex = re.compile(r"^data:(?P<mimetype>[^;]+);base64,(?P<data>.+)$")
        match = base64_regex.match(base64_string)

        if match is None:
            raise Exception("Invalid base64 string")

        data = base64.b64decode(match.group("data").encode())
        mime_type = match.group("mimetype")
        checksum = hashlib.md5(data).hexdigest()
        size = sys.getsizeof(data)

        try:
            record = Attachment.objects.filter(
                model=model,
                ref_field=ref_field,
                res_id=res_id,
            ).first()
            if checksum != record.checksum:
                record.checksum = checksum
                record.data = data
                record.name = filename
                record.mime_type = mime_type
                record.size = size
                record.save()
        except:
            record = Attachment.objects.create(
                checksum=checksum,
                data=data,
                mime_type=mime_type,
                model=model,
                name=filename,
                ref_field=ref_field,
                res_id=res_id,
                size=size,
            )

        return record

    def save(self, *args, **kwargs):
        if not self.pk:
            self.file_uuid = str(uuid.uuid4())
        super(Attachment, self).save(*args, **kwargs)

    def to_base64(self):
        """Encodes the data as base64"""
        import base64

        if self.data is None:
            raise Exception("Attachment contains no data")
        b64 = base64.encodebytes(self.data)
        b64 = "data:{};base64,{}".format(self.mime_type, b64.decode())
        b64 = b64.replace("\n", "")
        return b64


class DelegateSkill(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    name = models.CharField(max_length=64)
    package = models.CharField(max_length=64)
    active = models.BooleanField(default=True)
    data = models.TextField(default="{}")

    def __str__(self):
        return self.name

    def get_data(self):
        if self.data:
            result = json.loads(self.data)
            result["id"] = self.id
            return result
        return None

    def linked_utterances(self):
        """Returns a list of the utterances linked to the skill"""
        result = set()
        intents = self.intents.all()
        for intent in intents:
            utterances = intent.utterances.all()
            for u in utterances:
                result.add(u)
        return list(result)

    @staticmethod
    def post_values(name: str, package: str, data: dict, id_=None):
        """Creates or updates a new DelegateSkill

        Args:
            name (str): Skill's name.
            package (str): Skill's package.
            data (dict): Skill's definition.
            id_ [int, None]: Updates skill when value is not None.
        """
        data["name"] = name
        data["package"] = package
        if id_:
            record = DelegateSkill.objects.get(id=id_)
            record.data = json.dumps(data)
            record.name = name
            record.package = package
            record.save()
        else:
            DelegateSkill.objects.create(data=json.dumps(data), name=name, package=package)
        return True

    def save(self, *args, **kwargs):
        json_str = json.loads(self.data)
        self.name = json_str["name"]
        self.package = json_str["package"]
        super(DelegateSkill, self).save(*args, **kwargs)


class Lang(mixin.Model, models.Model):

    name = models.CharField(max_length=32)
    iso_code = models.CharField(max_length=3)

    def __str__(self):
        return self.name


class LocationPattern(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    class Types(models.TextChoices):
        BOT = "BOT", _("Bot Delegate")
        GROUP = "GROUP", _("Group")
        HUMAN = "HUMAN", _("Human Delegate")

    pattern = models.CharField(max_length=200)
    resource_id = models.IntegerField()
    type = models.CharField(max_length=5, choices=Types.choices, default=Types.BOT)

    def __str__(self):
        return self.pattern

    @staticmethod
    def match_location(location):
        location = urlparse(location).path
        exact_location = LocationPattern.objects.filter(pattern=location).first()
        if exact_location:
            return exact_location
        regex_patterns = LocationPattern.objects.filter(pattern__contains="*")
        for regex_pattern in regex_patterns:
            if re.match(regex_pattern.pattern.replace("*", ".*"), location):
                return regex_pattern

    def get_resource(self):
        if self.type == "BOT":
            return BotDelegate.objects.get(id=self.resource_id)
        elif self.type == "HUMAN":
            return HumanDelegate.objects.get(id=self.resource_id)
        elif self.type == "GROUP":
            return HumanDelegateGroup.objects.get(id=self.resource_id)

    @staticmethod
    def post_values(id=None, pattern="", resource_id=0, type="BOT"):
        if id:
            record = LocationPattern.objects.get(id=id)
            record.pattern = pattern
            record.resource_id = resource_id
            record.type = type
            record.save()
        else:
            record = LocationPattern.objects.create(
                pattern=pattern, resource_id=resource_id, type=type
            )
        return True


class BotDelegate(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    BIGBOT = 0
    DELEGATE_BOT = 1
    SUPPORT_BOT = 2

    CLASS_CHOICES = (
        (BIGBOT, _("Bigbot")),
        (DELEGATE_BOT, _("Delegate")),
        (SUPPORT_BOT, _("Support")),
    )

    avatar = models.ForeignKey(
        Attachment, default=None, on_delete=models.SET_NULL, blank=True, null=True
    )
    classification = models.IntegerField(choices=CLASS_CHOICES, null=False, default=BIGBOT)
    confidence = models.IntegerField(default=60)
    default_response = models.TextField(default="['Sorry I did not understand that.']")
    # default_skill = models.OneToOneField(
    #     "core.DelegateSkill", on_delete=models.SET_NULL, default=None, blank=True, null=True
    # )
    groups = models.TextField(default="[]")
    language = models.ForeignKey(Lang, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(default="BotDelegate", max_length=20, blank=True, null=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_bots",
        default=None,
        blank=True,
        null=True,
    )
    skill_ids = models.ManyToManyField(DelegateSkill, related_name="bot_delegates", blank=True)
    user_id = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="bot_delegates"
    )

    def __str__(self):
        return self.name

    def check_permissions(self, access_type):
        has_permissions = super().check_permissions(access_type)
        bot_groups = json.loads(self.groups)
        return has_permissions or self._user.in_group(*bot_groups)

    @staticmethod
    # @silk_profile(name="BotDelegate.get_default_bot")
    def get_default_bot():
        record = BotDelegate.objects.filter(classification=BotDelegate.BIGBOT).first()
        if not record:
            user, created = User.objects.get_or_create(username="Bigbot")
            if created:
                user.groups.add(Group.objects.get(name="bot"))
                user.is_human = False
                user.save()
            record = BotDelegate.objects.create(classification=BotDelegate.BIGBOT, user_id=user)
        return record

    def get_default_response(self):
        try:
            responses = json.loads(self.default_response)
            return random.choice(responses)
        except:
            return self.default_response

    # @silk_profile(name="BotDelegate.get_owner_delegate")
    def get_owner_delegate(self):
        return getattr(self.owner, "human_delegate", None)

    @staticmethod
    def get_support_bot():
        record = BotDelegate.objects.filter(classification=BotDelegate.SUPPORT_BOT).first()
        if not record:
            user = User.objects.create(
                username="Support",
            )
            user.groups.add(Group.objects.get(name="bot"))
            user.is_human = False
            user.save()
            record = BotDelegate.objects.create(
                classification=BotDelegate.SUPPORT_BOT, user_id=user
            )
        return record

    @staticmethod
    def get_users(query=None):
        data = []
        if query is None:
            users = User.objects.filter(groups__name="bot")
        else:
            users = User.objects.filter(groups__name="bot", username__icontains=query).order_by(
                "-username"
            )
        for item in users:
            data.append({"id": item.id, "name": str(item)})
        return data

    def name_filter(self, query):
        if query:
            return [[["user__first_name__contains", query]], 5, ["id", "desc"]]
        else:
            return [[], 5, ["id", "desc"]]

    @staticmethod
    def post_values(
        owner, name, base64avatar, confidence, default_response, skill_ids, groups=[], id=None
    ):
        if type(default_response) != str:
            default_response = json.dumps(default_response, separators=(",", ":"))

        owner = User.get_keycloak_user(owner)

        if id:
            rec = BotDelegate.objects.get(id=id)
            rec.confidence = confidence
            rec.default_response = default_response
            rec.name = name
            rec.owner = owner
        else:
            rec = BotDelegate.objects.create(
                classification=BotDelegate.DELEGATE_BOT,
                confidence=confidence,
                default_response=default_response,
                name=name,
                owner=owner,
            )

        if rec.user_id is None:
            user = User.objects.create(username=uuid.uuid4())
            user.is_human = False
            user.update_avatar_base64(base64avatar)
            rec.user_id = user
        else:
            rec.user_id.is_human = False
            rec.user_id.update_avatar_base64(base64avatar)

        rec.skill_ids.clear()
        skills = DelegateSkill.objects.filter(id__in=skill_ids)
        rec.skill_ids.add(*skills)

        rec.groups = json.dumps(groups)
        rec.save()

    def serialize(self, fields=[]):
        result = super().serialize(fields)
        if "avatar" in result:
            result["avatar"] = self.user_id.get_avatar_base64()
        if "default_response" in result:
            try:
                result["default_response"] = json.loads(result["default_response"])
            except:
                pass
        if "groups" in result:
            result["groups"] = json.loads(result["groups"])
        if "owner" in result:
            if self.owner:
                result["owner"] = {
                    "id": utils.normalize_uuid(self.owner.keycloak_user),
                    "email": self.owner.email,
                    "firstName": self.owner.first_name,
                    "lastName": self.owner.last_name,
                    "username": self.owner.email,
                }
            else:
                result["owner"] = None
        return result


class HumanDelegate(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    BASE = 0
    OPERATOR = 1

    CLASS_CHOICES = (
        (BASE, _("Base")),
        (OPERATOR, _("Operator")),
    )

    classification = models.IntegerField(choices=CLASS_CHOICES, null=False, default=BASE)
    data = models.TextField(default="{}")
    offline_skill = models.ForeignKey(
        DelegateSkill, on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="human_delegate")
    utterances = models.ManyToManyField("core.DelegateUtterance", related_name="human_delegates")

    def __str__(self):
        if self.user_id.first_name:
            return f"{self.user_id.first_name} {self.user_id.last_name}"
        return self.user_id.username

    @property
    def name(self):
        return f"{self.user_id.first_name} {self.user_id.last_name}"

    @staticmethod
    # @silk_profile(name="HumanDelegate.add_user_client")
    def add_user_client(user, client_uuid):
        """This method registers the last time a chat client was used by the user"""
        delegate = user.human_delegate
        if user:
            data = json.loads(delegate.data)
            data[client_uuid] = time.time() + 5 * 60
            delegate.data = json.dumps(data, separators=(",", ":"))
            delegate.save()

    def check_online_status(self):
        """Checks if an user is online, a user is considered to be online if thye have interacted
        with the server in the last 5 minutes.
        """
        is_online = False
        try:
            data = json.loads(self.data)
            keys_to_remove = []
            for client in data:
                if data[client] < time.time():
                    keys_to_remove.append(client)
                else:
                    is_online = True
            for key in keys_to_remove:
                del data[key]
            self.data = json.dumps(data, separators=(",", ":"))
            self.save()
        except Exception as e:
            Log.error("HumanDelegate.check_online_status", e)
        return is_online

    @staticmethod
    # @silk_profile(name="HumanDelegate.get_by_keycloak_user")
    def get_by_keycloak_user(uuid):
        user = User.objects.filter(keycloak_user=uuid).select_related("human_delegate").first()
        human_delegate = getattr(user, "human_delegate", None)
        if human_delegate:
            return human_delegate
        human_delegate = HumanDelegate.objects.create(classification=1, user_id=user)
        return human_delegate

    def name_filter(self, query):
        if query:
            return [[["user__first_name__contains", query]], 5, ["id", "desc"]]
        else:
            return [[], 5, ["id", "desc"]]

    @staticmethod
    # @silk_profile(name="HumanDelegate.find")
    def find(user_id):
        record = (
            HumanDelegate.objects.filter(user_id=user_id.id)
            .prefetch_related("user_id__archived_channels")
            .first()
        )
        if not record:
            record = HumanDelegate.objects.create(user_id=user_id)
        return record

    @staticmethod
    def remove_user_client(user, client_uuid):
        delegate = HumanDelegate.objects.filter(user_id=user).first()
        if user:
            data = json.loads(delegate.data)
            if client_uuid in data:
                del data[client_uuid]
            delegate.data = json.dumps(data, separators=(",", ":"))
            delegate.save()


class HumanDelegateGroup(mixin.Model, models.Model):
    class Permissions:
        all = permissions.SUPERUSER

    human_delegates = models.ManyToManyField(HumanDelegate, related_name="delegate_groups")
    icon = models.OneToOneField(
        Attachment, on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    name = models.CharField(max_length=50)
    utterances = models.ManyToManyField("core.DelegateUtterance", related_name="delegate_groups")

    def get_image(self):
        return Attachment.get_attachment("user.group", self.id, "icon")

    @staticmethod
    def post_values(**values):
        delegates = values.get("delegates", [])
        icon = values.get("icon", False)
        id = values.get("id")
        name = values.get("name", "")
        utterances = values.get("utterances", [])

        if id:
            record = HumanDelegateGroup.objects.get(id=id)
        else:
            record = HumanDelegateGroup.objects.create(name=name)
        record.name = name

        if icon:
            attachment = Attachment.put_base64("user.group", record.id, "icon", "icon", icon)
            record.icon = attachment

        record.save()

        record.human_delegates.clear()
        for delegate in delegates:
            user = User.get_keycloak_user(delegate)
            human_delegate = getattr(user, "human_delegate", None)
            if human_delegate is None:
                human_delegate = HumanDelegate.objects.create(user_id=user)
            record.human_delegates.add(human_delegate)

        record.utterances.clear()
        for utterance in utterances:
            u = DelegateUtterance.get_record(utterance)
            record.utterances.add(u)

        return True

    def serialize(self, *args, **kwargs):
        result = super().serialize(*args, **kwargs)

        if "human_delegates" in result:
            result["human_delegates"] = []
            for delegate in self.human_delegates.all():
                result["human_delegates"].append(delegate.user_id.keycloak_user)

        if "icon" in result:
            attachment = Attachment.objects.filter(
                model="user.group", ref_field="icon", res_id=self.id
            ).first()
            if attachment:
                result["icon"] = attachment.to_base64()
            else:
                result["icon"] = None

        if "utterances" in result:
            result["utterances"] = [u.body for u in self.utterances.all()]

        return result


class UserProfile(models.Model):
    """This model has some basic profile information for users and bots.

    WARNING: This model is most likely going to be removed in the future as more functionality is
    moved to Keycloak.
    """

    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="user_profile",
    )
    image = models.ImageField()

    def __str__(self):
        return str(self.user_id)

    def save(self, *args, **kwargs):
        image = self.image
        self.image = None
        super(UserProfile, self).save(*args, **kwargs)
        if image:
            Attachment.put_attachment("user.profile", self.id, "image", image)

    @staticmethod
    def get_avatar_uri(user_id):
        if not user_id:
            return None
        record = UserProfile.objects.filter(user_id=user_id.id).first()
        if not record:
            record = UserProfile.objects.create(user_id=user_id)

        attachment = Attachment.get_attachment("user.profile", record.id, "image")
        if attachment:
            return attachment

        if user_id.groups.filter(name="bot"):
            file_obj = open(settings.BASE_DIR + "/static/images/default_bot.png", "rb")
        else:
            file_obj = open(settings.BASE_DIR + "/static/images/default_user.png", "rb")
        attachment = Attachment.put_attachment("user.profile", record.id, "image", file_obj)
        return attachment.get_url()

    @staticmethod
    def get_avatar_base64(user_id):
        record = UserProfile.objects.filter(user_id=user_id.id).first()
        if not record:
            record = UserProfile.objects.create(user_id=user_id)
            if user_id.groups.filter(name="bot"):
                file_obj = open(settings.BASE_DIR + "/static/images/default_bot.png", "rb")
            else:
                file_obj = open(settings.BASE_DIR + "/static/images/default_user.png", "rb")
            Attachment.put_attachment("user.profile", record.id, "image", file_obj)

        attachment = Attachment.objects.filter(
            model="user.profile", res_id=record.id, ref_field="image"
        ).first()
        return attachment.to_base64()

    @staticmethod
    def save_base64_avatar(user, avatar):
        record = UserProfile.objects.filter(user_id=user.id).first()
        if not record:
            record = UserProfile.objects.create(user_id=user)
        Attachment.put_base64("user.profile", record.id, "image", "avatar", avatar)


class MailChannel(mixin.Model, models.Model):

    bot_delegate_ids = models.ManyToManyField(BotDelegate, related_name="mail_channels")
    bots_enabled = models.BooleanField(default=True)
    channel_uuid = models.CharField(max_length=255, unique=True)
    data = models.TextField(default="{}")
    human_delegate_ids = models.ManyToManyField(HumanDelegate, related_name="mail_channels")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    is_human_channel = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        strings = []
        for item in self.bot_delegate_ids.all():
            strings.append(str(item))
        for item in self.human_delegate_ids.all():
            strings.append(str(item))
        return ", ".join(strings)

    @property
    def human_delegate(self):
        return HumanDelegate.objects.filter(user_id=self.owner).first()

    @staticmethod
    def create_welcome_messages(channel, bot_delegate):
        contents = [
            {
                "node": "big.bot.core.image",
                "data": "https://bigbot-static-public.s3-ap-southeast-1.amazonaws.com/GIFs/hello_06.gif",
            }
        ]
        messages = [
            Statement(text="Hello!", uid=bot_delegate.user_id.id, contents=contents),
            Statement(text="How may I help you?", uid=bot_delegate.user_id.id),
        ]
        for statement in messages:
            channel.post_message(bot_delegate.user_id, statement.text, data=statement.serialize())

    def display_name(self):
        return "Undefined"

    @staticmethod
    # @silk_profile(name="ensure_bot_delegaet_channel")
    def ensure_bot_delegate_channel(user_id, bot_delegate):
        self_human_delegate = user_id.human_delegate
        MailChannel.ensure_default(self_human_delegate)
        channel = (
            MailChannel.objects.annotate(
                bots=Count("bot_delegate_ids"), humans=Count("human_delegate_ids")
            )
            .filter(
                bots=1,
                humans=1,
                bot_delegate_ids__in=[bot_delegate.id],
                human_delegate_ids__in=[self_human_delegate.id],
            )
            .first()
        )
        if not channel:
            channel = MailChannel.objects.create()
            channel.human_delegate_ids.add(self_human_delegate)
            channel.bot_delegate_ids.add(bot_delegate)
            channel.owner = bot_delegate.user_id
            channel.save()
        return channel

    @staticmethod
    # @silk_profile(name="ensure_default")
    def ensure_default(human_delegate):
        default_bot = BotDelegate.get_default_bot()
        channel = (
            MailChannel.objects.annotate(
                bots=Count("bot_delegate_ids"), humans=Count("human_delegate_ids")
            )
            .filter(
                bots=1,
                humans=1,
                bot_delegate_ids__in=[default_bot.id],
                human_delegate_ids__in=[human_delegate.id],
            )
            .prefetch_related("bot_delegate_ids", "human_delegate_ids", "mail_messages")
            .first()
        )

        if not channel:
            channel = MailChannel.objects.create()
            channel.human_delegate_ids.add(human_delegate)
            channel.bot_delegate_ids.add(default_bot)
            channel.save()
        else:
            archived_channel = human_delegate.user_id.archived_channels.filter(
                channel=channel
            ).first()
            if archived_channel:
                archived_channel.delete()

        has_messages = channel.mail_messages.exists()
        if not has_messages:
            MailChannel.create_welcome_messages(channel, default_bot)

        return channel

    @staticmethod
    # @silk_profile(name="ensure_human_delegate_channel")
    def ensure_human_delegate_channel(user_id, human_delegate):
        # support_bot = BotDelegate.get_support_bot()
        self_human_delegate = user_id.human_delegate
        MailChannel.ensure_default(self_human_delegate)
        MailChannel.ensure_default(human_delegate)
        channel = MailChannel.objects.annotate(humans=Count("human_delegate_ids")).filter(
            humans=2, human_delegate_ids__in=[self_human_delegate.id]
        )
        channel = channel.filter(human_delegate_ids__in=[human_delegate.id]).first()
        if not channel:
            bot_delegate = BotDelegate.get_default_bot()
            channel = MailChannel.objects.create()
            channel.human_delegate_ids.add(human_delegate)
            channel.human_delegate_ids.add(self_human_delegate)
            channel.bot_delegate_ids.add(bot_delegate)
            channel.owner = human_delegate.user_id
            channel.bots_enabled = False
            channel.is_human_channel = True
            channel.save()
        return channel

    @staticmethod
    def find_channel(user_id, channel_uuid):
        human_delegate = user_id.human_delegate
        return MailChannel.objects.filter(
            channel_uuid=channel_uuid,
            human_delegate_ids__in=[human_delegate.id],
        ).first()

    @staticmethod
    def get_channels(user_id):
        human_delegate = user_id.human_delegate
        MailChannel.ensure_default(human_delegate)
        archived_channels = user_id.archived_channels.all().values_list("channel", flat=True)
        channels = (
            human_delegate.mail_channels.exclude(id__in=archived_channels)
            .order_by("-updated_at")
            .prefetch_related("bot_delegate_ids", "human_delegate_ids")
        )
        return channels

    def get_messages(self):
        return MailMessage.objects.filter(channel_id=self.id).order_by("-id")

    def increment_fail(self, bot_delegate):
        key = str(bot_delegate.id)
        data = json.loads(self.data)
        if not key in data:
            data[key] = 1
        else:
            data[key] += 1
        self.data = json.dumps(data, separators=(",", ":"))
        self.save()
        return data[key]

    # @silk_profile(name="MailChannel.post_message")
    def post_message(self, sender, body, message_id=False, data={}):
        from main.apps import MainAppConfig

        for delegate in self.human_delegate_ids.all():
            if delegate.user_id == sender:
                continue
            try:
                platforms = ProfileLink.objects.filter(user_id=delegate.user_id)
                for platform in platforms:
                    try:
                        for component, bot in MainAppConfig.chat_bots:
                            if platform.platform == component:
                                bot.on_message(platform, body)
                    except Exception as e:
                        Log.error("on_message", e)
            except Exception as e:
                Log.error("MailChannel.post_message", e)

        message = MailMessage.objects.create(
            body=body,
            channel_id=self,
            data=data,
            message_id=message_id,
            sender=sender,
        )
        self.updated_at = Now()
        self.save()
        return message

    def reset_fails(self, *args, **kwargs):
        self.data = "{}"
        self.save()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.channel_uuid = str(uuid.uuid4())
        super(MailChannel, self).save(*args, **kwargs)

    # @silk_profile(name="MailChannel.serialize")
    def serialize(self, user):
        image = None
        if self.human_delegate_ids.count() == 1:
            try:
                bot_delegate = self.bot_delegate_ids.first()
                image = bot_delegate.user_id.get_avatar_url()
            except Exception as e:
                Log.error("MailChannel.serialize", e)
        else:
            for human_delegate in self.human_delegate_ids.all():
                if not user == human_delegate.user_id:
                    image = human_delegate.user_id.get_avatar_url()
                    break

        data = {
            "id": self.id,
            "bots_enabled": self.bots_enabled,
            "channel_uuid": self.channel_uuid,
            "image": image,
            "name": str(self),
        }
        return data


class ActiveChannel(mixin.Model, models.Model):

    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="active_channel")
    channel_id = models.ForeignKey(
        MailChannel, on_delete=models.CASCADE, related_name="active_channels"
    )

    def __str__(self):
        return str(self.user_id) + ": " + str(self.channel_id)

    @staticmethod
    def get_channel(user_id):
        record = (
            ActiveChannel.objects.filter(user_id=user_id.id)
            .prefetch_related(
                "channel_id__bot_delegate_ids",
                "channel_id__human_delegate_ids",
                "channel_id__mail_messages",
            )
            .first()
        )
        if record:
            return record.channel_id
        human_delegate = user_id.human_delegate
        channel = MailChannel.ensure_default(human_delegate)
        return channel

    @staticmethod
    # @silk_profile(name="ActiveChannel.set_channel")
    def set_channel(user_id, channel_id):
        record = ActiveChannel.objects.filter(user_id=user_id).first()
        if not record:
            ActiveChannel.objects.create(user_id=user_id, channel_id=channel_id)
        else:
            record.channel_id = channel_id
            record.save()


class ArchivedChannel(models.Model):
    channel = models.ForeignKey(MailChannel, on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="archived_channels", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["channel", "user"]


class AppData(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    component = models.CharField(max_length=128)
    description = models.CharField(default="", max_length=128)
    data = models.TextField()
    key = models.CharField(max_length=128)
    type = models.CharField(default="str", max_length=5)

    def __repr__(self):
        return f"<AppData ({self.component}:{self.key}): {self.data} ({self.type})>"

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def _str2val(value, type):
        if type == "bool" and value == "False":
            return False
        if type == "bool" and value == "True":
            return True
        if type == "dict":
            return json.loads(value)
        if type == "float":
            return float(value)
        if type == "int":
            return int(value)
        if type == "list":
            return json.loads(value)
        return value

    @staticmethod
    def _val2str(value, type_):
        if type_ == "bool":
            if isinstance(value, bool):
                value = str(value)
            else:
                value = "False"
        elif type_ == "dict":
            if isinstance(value, dict):
                value = json.dumps(value)
            else:
                value = "{}"
        elif type_ == "float":
            if isinstance(value, (float, int)):
                value = str(value)
            else:
                value = "0.0"
        elif type_ == "int":
            if isinstance(value, (float, int)):
                value = str(value)
            else:
                value = "0"
        elif type_ == "list":
            if isinstance(value, list):
                value = json.dumps(value)
            else:
                value = "[]"
        else:
            value = str(value)
            type_ = "str"
        return value, type_

    @staticmethod
    def get_data(component, key):
        """Returns the parsed data of

        Args:
            component (str): Component's identifier
            key (str): Data key

        Returns:
            Parsed data or None if data does not exist.
        """
        record = AppData.objects.filter(component=component, key=key).first()
        if record:
            return AppData._str2val(record.data, record.type)
        return None

    @staticmethod
    def get_components():
        """Returns a dictionary of dictionaries where:

        {
            "my.component": {
                "key_1": {
                    "id": 1,                             # Record's id
                    "data": "value",
                    "description": "Key description",
                    "type": "str",
                },
                "key_2": {
                    ...
                },
            },
            "other.component": {
                ...
            },
            ...
        }
        """
        result = {}
        records = AppData.objects.all()
        for record in records:
            print(record)
            if record.component not in result:
                result[record.component] = {}
            result[record.component][record.key] = {
                "id": record.id,
                "data": AppData._str2val(record.data, record.type),
                "description": record.description,
                "type": record.type,
            }
        return result

    @staticmethod
    def post_values(**records):
        """Updates multiple AppData records.

        Args:
            records (dict): A dictionary with the same structure of the dictionary returned by
                AppData.get_components
        """
        for component in records:
            for key in records[component]:
                record = AppData.objects.filter(
                    id=records[component][key]["id"],
                    component=component,
                    key=key,
                ).first()
                if record is None:
                    raise Exception("Record <AppData: {}:{}> does not exist").format(component, key)
                record.data = records[component][key]["data"]
                record.save()
        return True

    @staticmethod
    def put_data(component, key, data=None, type_=str, description=""):
        """Creates a new record in the database.

        Args:
            component (str): Component's string identifier
            key (str): Data key
            data: Data value, stored as a string, must be an instance of type. If the record was
                previously created the value must be an instance of the original type.
            type_: Type of the data. Value is only used when the record is created. The value is used
                to parse the data in the methods AppData.get_data and AppData.put_data. It can be
                one of the following built-in types: bool, dict, float, int, list, or str. Any non
                valid type will be treated as a str. Defaults to str.
            description (str): Key's description.
        """
        types_repr = {
            bool: "bool",
            dict: "dict",
            float: "float",
            int: "int",
            list: "list",
            str: "str",
        }

        record = AppData.objects.filter(component=component, key=key).first()
        if record is None:
            record = AppData.objects.create(component=component, key=key)
            if type_ in types_repr:
                type_ = types_repr[type_]
            else:
                try:
                    type_ = type.lower()
                except:
                    type_ = "str"
        else:
            data = record.data
            description = record.description
            type_ = record.type

        record.data, record.type = AppData._val2str(data, type_)
        record.description = description
        record.save()

    @staticmethod
    def remove_data(component, key):
        """Removes a record from the database.

        Args:
            component (str): Component's string identifier
            key (str): Data key

        Returns:
            True: If record was removed.
            False: If record does not exist.
        """
        obj = AppData.objects.filter(component=component, key=key).first()
        if obj:
            obj.delete()
            return True
        return False

    def save(self, *args, **kwargs):
        self.type = self.type.lower()
        super().save(*args, **kwargs)


class ComponentUserResource(mixin.Model, models.Model):

    component = models.CharField(max_length=128)
    user_id = models.IntegerField()
    model = models.CharField(max_length=64)
    resource = models.CharField(max_length=64, null=True)
    data = models.TextField()

    def __str__(self):
        return self.model


class DelegateIntent(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    name = models.CharField(max_length=64)
    skill_id = models.ForeignKey(
        DelegateSkill, on_delete=models.CASCADE, null=False, related_name="intents"
    )

    def __repr__(self):
        name = self.id
        if self.name:
            name = self.name
        return f"<DelegateIntent: {name}>"

    def __str__(self):
        return self.__repr__()

    def serialize(self, *args, **kwargs):
        utterances = DelegateUtterance.objects.filter(intent_id=self)
        return {
            "id": self.id,
            "name": self.name,
            "skill_id": [
                self.skill_id.id,
                self.skill_id.name,
            ],
            "utterance_ids": [
                {
                    "id": utterance.id,
                    "body": utterance.body,
                }
                for utterance in utterances
            ],
        }

    @staticmethod
    def post_values(name, skill_id, utterance_ids, id):
        skill = DelegateSkill.objects.get(id=skill_id)
        if id:
            record = DelegateIntent.objects.get(id=id)
            record.name = name
            record.skill_id = skill
            record.save()
        else:
            record = DelegateIntent.objects.create(name=name, skill_id=skill)
        utterances = DelegateUtterance.objects.filter(intent_id=record)
        for utterance in utterances:
            utterance.intent_id = None
            utterance.save()
        for item in utterance_ids:
            utterance = DelegateUtterance.objects.get(id=item)
            utterance.intent_id = record
            utterance.save()


class DelegateState(mixin.Model, models.Model):

    skill_id = models.ForeignKey(
        DelegateSkill, on_delete=models.CASCADE, null=False, related_name="delegate_states"
    )
    channel_id = models.ForeignKey(
        MailChannel, on_delete=models.CASCADE, related_name="delegate_states"
    )
    cursor = models.IntegerField(default=0)
    data = models.TextField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.skill_id.name

    @staticmethod
    # @silk_profile(name="DelegateState.get_state")
    def get_state(channel_id):
        record = DelegateState.objects.filter(channel_id=channel_id.id).first()
        if record:
            return record
        return False

    @staticmethod
    # @silk_profile(name="Delegate.set_skill")
    def set_skill(skill_id, channel_id):
        record = DelegateState.objects.filter(channel_id=channel_id.id).first()
        if not record:
            record = DelegateState.objects.create(skill_id=skill_id, channel_id=channel_id)
        else:
            record.skill_id = skill_id
            record.cursor = 0
            record.data = {}
            record.save()
        return record

    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return {}

    def put_data(self, name, object, multi=False):
        data = self.get_data()
        if multi:
            if name not in data:
                data[name] = []
            data[name].append(object)
        else:
            data[name] = object
        self.data = json.dumps(data)


class DelegateUtterance(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    body = models.CharField(max_length=255)
    intent_id = models.ForeignKey(
        DelegateIntent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utterances",
    )

    def __repr__(self):
        return self.body

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def get_record(body):
        record = DelegateUtterance.objects.filter(body=body.strip().lower()).first()
        if not record:
            record = DelegateUtterance.objects.create(body=body.strip().lower())
        return record

    def name_filter(self, query):
        if query:
            return [[["body__contains", query]], 5, ["body", "desc"]]
        else:
            return [[], 5, ["body", "desc"]]

    def serialize(self, *args, **kwargs):
        result = super().serialize(*args, **kwargs)

        if self.intent_id:
            if self.intent_id.skill_id:
                result["linked_skill"] = [self.intent_id.skill_id.id, self.intent_id.skill_id.name]
            else:
                result["linked_skill"] = None
        else:
            result["linked_skill"] = None

        return result


class Integration(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    data = models.TextField()
    enabled = models.BooleanField(default=True)
    label = models.CharField(max_length=50)

    def __repr__(self):
        return f"<Integration: {self.label}>"

    def __str__(self):
        return self.__repr__()

    def _get_module(self):
        try:
            module_path = os.path.join(settings.BASE_DIR, "apps", self.label, "init.py")
            spec = importlib.util.spec_from_file_location("module.init", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            app = module.Application(None)
        except Exception as e:
            Log.error("Integration.get_module", e)
            app = None
        return app

    @staticmethod
    def install(zip_file, files, manifest):
        """Creates or updates an existing integration"""
        apps_path = os.path.join(settings.BASE_DIR, "apps")
        label = files[0].replace("/", "").lower()
        integration = Integration.objects.filter(label=label).first()

        if integration is None:
            integration = Integration.objects.create(data=json.dumps(manifest), label=label)
        elif integration.name != manifest["name"]:
            raise Exception("Integration will override a different integration")
        else:
            integration.data = json.dumps(manifest)
            integration.save()

        if not os.path.isdir(apps_path):
            os.mkdir(apps_path)

        for file_ in files:
            zip_file.extract(file_, apps_path)

        app = integration._get_module()
        if app:
            app.registry()

    @property
    def name(self):
        data = json.loads(self.data)
        return data["name"]

    @staticmethod
    def post_values(enabled, id):
        """Activates or desactivates an integration"""
        try:
            integration = Integration.objects.get(id=id)
            integration.enabled = enabled
            integration.save()
        except Exception as e:
            Log.error("Integration.post_values", e)
            raise JsonRPCException("Integration does not exist")
        return True

    def serialize(self, *args, **kwargs):
        result = super().serialize(*args, **kwargs)
        if "data" in result:
            result["data"] = json.loads(result["data"])
        return result

    @staticmethod
    def submit(b64_integration):
        try:
            data, _ = utils.parse_base64(b64_integration)
            byte_data = base64.decodebytes(data.encode())
            io_object = io.BytesIO(byte_data)
            zip_file = zipfile.ZipFile(io_object)
        except Exception as e:
            Log.error("Integration.submit", e)
            raise Exception("Invalid zip file")

        valid, data = Integration.validate(zip_file)

        if not valid:
            raise JsonRPCException("Invalid integration", data=data["errors"])

        try:
            Integration.install(zip_file, data["files"], data["manifest"])
        except Exception as e:
            raise JsonRPCException(str(e))

        return True

    @staticmethod
    def uninstall(id):
        """Removes an integration"""
        integration = Integration.objects.get(id=id)

        app = integration._get_module()
        if app:
            app.remove_variables()

        integration_path = os.path.join(settings.BASE_DIR, "apps", integration.label)
        shutil.rmtree(integration_path)

        integration.delete()
        return True

    @staticmethod
    def validate(zip_file):
        """Verifies if zip_file is a valid integration.

        Args:
            zip_file: An instance of zipfile.ZipFile.

        Returns:
            tuple[bool, dict]: The first item in the tuple is True if the integration is valid. The
                second item is a dict with three fields:
                + errors: A  dict with multiple errors if the integrations is not valid.
                + files: List of valid files.
                + manifest: Contents of manifest.json.
        """

        file_fiters = [re.compile("^.*__pycache__.*$")]
        required_files = [
            ("components.py", re.compile(r"^[^/]*/component.py$")),
            ("init.py", re.compile(r"^[^/]*/init.py$")),
            ("manifest.json", re.compile(r"^[^/]*/manifest.json$")),
        ]
        rootdir_re = re.compile(r"^[^/]+/$")

        integration_files = zip_file.infolist()
        result = {"errors": {}, "files": [], "manifest": {}}
        valid = True

        directories = 0
        for info in integration_files:
            if info.is_dir() and rootdir_re.match(info.filename):
                directories += 1
        if directories == 0:
            utils.append_error(
                result["errors"], "File must contain a root directory", key="structure"
            )
            valid = False
        elif directories > 1:
            utils.append_error(
                result["errors"], "File can only contain a root directory", key="structure"
            )
            valid = False

        for required_file, regex in required_files:
            filename = ""
            match = None

            for info in integration_files:
                filename = info.filename
                match = regex.match(filename)
                if match:
                    break

            if not match:
                utils.append_error(
                    result["errors"],
                    "File must be included in the root directory",
                    key=required_file,
                )
                valid = False
            elif required_file == "manifest.json":
                with zip_file.open(filename) as manifest:
                    try:
                        result["manifest"] = json.load(manifest)
                        manifest_errors = Integration.validate_manifest(result["manifest"])
                        if len(manifest_errors) > 0:
                            utils.append_error(
                                result["errors"],
                                *manifest_errors,
                                key=required_file,
                            )
                            valid = False
                    except Exception as e:
                        utils.append_error(
                            result["errors"],
                            str(e),
                            key=required_file,
                        )
                        valid = False

        for info in integration_files:
            filter_ = False

            for file_filter in file_fiters:
                match = file_filter.match(info.filename)
                if match:
                    filter_ = True
                    break

            if not filter_:
                result["files"].append(info.filename)

        return valid, result

    @staticmethod
    def validate_manifest(manifest):
        """Validates an integration manifest.

        Args:
            manifest (dict): Manifest data.

        Returns:
            list: List of errors. Empty if valid.
        """
        errors = []

        if "author" not in manifest:
            errors.append("Field 'author' is required.")
        if "name" not in manifest:
            errors.append("Field 'name' is required.")
        if "summary" not in manifest:
            errors.append("Field 'summary' is required.")
        if "version" not in manifest:
            errors.append("Field 'version' is required.")
        if "website" not in manifest:
            errors.append("Field 'website' is required.")

        return errors


class MailMessage(mixin.Model, models.Model):

    TYPE_COMMENT = "comment"
    TYPE_NOTIFICATION = "notification"

    body = models.TextField(null=True)
    channel_id = models.ForeignKey(
        MailChannel,
        related_name="mail_messages",
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
    )
    data = models.TextField(null=True)
    date = models.DateTimeField(auto_now_add=False, auto_now=True)
    message_id = models.CharField(max_length=255, unique=True)
    message_type = models.CharField(max_length=255, default=TYPE_COMMENT)
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="send_messages"
    )
    user_ids = models.ManyToManyField(User, related_name="mail_messages")

    def __str__(self):
        return self.body

    def save(self, *args, **kwargs):
        if not self.pk:
            self.date = datetime.now()
            if not self.message_id:
                self.message_id = str(uuid.uuid4())
            if self.data:
                self.data = json.dumps(self.data)
        super(MailMessage, self).save(*args, **kwargs)

    # @silk_profile(name="MailMessage.serialize")
    def serialize(self, user):
        data = {
            "id": self.id,
            "attachments": [],
            "avatar": self.sender.get_avatar_url(),
            "body": self.body,
            "channel_id": self.channel_id.id,
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S"),
            "is_human": self.sender.is_human,
            "outgoing": True if user.id == self.sender.id else False,
            "message_id": self.message_id,
            "sender": [self.sender.id, str(self.sender)],
        }

        # TODO: This code needs to be optimized
        # for attachment in Attachment.get_message_attachments(self):
        #     data["attachments"].append(
        #         {
        #             "name": attachment.name,
        #             "url": attachment.get_url(),
        #             "mime_type": attachment.mime_type,
        #             "type": attachment.name.split(".")[1],
        #         }
        #     )

        self.put_statement(data)
        return data

    def put_statement(self, data):
        if self.data:
            try:
                data["statement"] = json.loads(self.data)
                if "text" not in data["statement"]:
                    data["statement"]["text"] = self.body
                return
            except:
                pass
        data["statement"] = {"text": self.body}


class OauthAccess(mixin.Model, models.Model):

    ODOO = "odoo"
    GOOGLE = "google"

    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth")
    provider = models.CharField(max_length=255)
    access_token = models.CharField(max_length=254)
    refresh_token = models.CharField(max_length=254, null=True)
    expires_in = models.IntegerField(default=0)
    updated = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.user_id.username + ", " + self.provider

    @staticmethod
    def add_oauth(user_id, provider, access_token, refresh_token, expires_in):
        record = OauthAccess.objects.filter(user_id=user_id, provider=provider).first()
        if not record:
            OauthAccess.objects.create(
                user_id=user_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )
        else:
            record.access_token = access_token
            record.refresh_token = refresh_token
            record.expires_in = expires_in
            record.save()

        return

    @staticmethod
    def get_oauth(user_id, provider):
        return OauthAccess.objects.filter(user_id=user_id.id, provider=provider).first()


class Preference(mixin.Model, models.Model):
    class Permissions:
        all = permissions.ADMIN

    TYPE_INT = 1
    TYPE_STR = 2
    TYPE_BOOL = 3
    TYPE_FLOAT = 4
    TYPE_OBJECT = 5

    DATA_TYPE = (
        (TYPE_INT, _("Integer")),
        (TYPE_STR, _("String")),
        (TYPE_BOOL, _("Boolean")),
        (TYPE_FLOAT, _("Float")),
        (TYPE_OBJECT, _("Object")),
    )

    key = models.CharField(max_length=254)
    value = models.TextField()
    type = models.IntegerField(choices=DATA_TYPE)

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        if not self.pk:
            pass
        super(Preference, self).save(*args, **kwargs)

    @staticmethod
    def put_value(key, value):
        if value:
            db_pref = Preference.objects.filter(key=key).first()
            if isinstance(value, int):
                if not db_pref:
                    Preference.objects.create(type=Preference.TYPE_INT, key=key, value=str(value))
                else:
                    db_pref.value = str(value)
                    db_pref.save()
            elif isinstance(value, float):
                if not db_pref:
                    Preference.objects.create(type=Preference.TYPE_FLOAT, key=key, value=str(value))
                else:
                    db_pref.value = str(value)
                    db_pref.save()
            elif isinstance(value, str):
                if not db_pref:
                    Preference.objects.create(type=Preference.TYPE_STR, key=key, value=str(value))
                else:
                    db_pref.value = str(value)
                    db_pref.save()
            elif isinstance(value, bool):
                if not db_pref:
                    Preference.objects.create(type=Preference.TYPE_BOOL, key=key, value=str(value))
                else:
                    db_pref.value = str(value)
                    db_pref.save()
            elif isinstance(value, dict) or isinstance(value, list):
                if not db_pref:
                    Preference.objects.create(
                        type=Preference.TYPE_OBJECT, key=key, value=json.dumps(value)
                    )
                else:
                    db_pref.value = json.dumps(value)
                    db_pref.save()
        pass

    @staticmethod
    def get_value(key, default=False):
        obj = Preference.objects.filter(key=key).first()
        if obj and obj.value:
            if obj.type == Preference.TYPE_INT:
                return int(obj.value)
            elif obj.type == Preference.TYPE_FLOAT:
                return float(obj.value)
            elif obj.type == Preference.TYPE_STR:
                return str(obj.value)
            elif obj.type == Preference.TYPE_BOOL:
                return bool(obj.value)
            elif obj.type == Preference.TYPE_OBJECT:
                return json.loads(obj.value)

        return default

    @staticmethod
    def remove_value(key):
        obj = Preference.objects.filter(key=key).first()
        if obj:
            obj.delete()

    @staticmethod
    def post_bundle_values(**values):
        from contrib.processor import LOGICAL_ADAPTERS

        for item in values["adapters"]:
            for info in LOGICAL_ADAPTERS:
                if info["package"] == item["package"]:
                    item["name"] = info["name"]
        Preference.put_value("LOGICAL_ADAPTERS", values["adapters"])
        Preference.put_value("KEY_PRIMARY_COLOR", values["themeColor"])
        Preference.put_value("KEY_CANCEL_INTENT", values["skill_cancel_hidden"])
        Preference.put_value("AUDIO_PROVIDER", values["vueradio"])
        Preference.put_value("KEY_AWS_ACCESS_ID", values["aws_access_id"])
        Preference.put_value("KEY_AWS_SECRET_KEY", values["aws_secret_key"])
        Preference.put_value("GOOGLE_TTS_CRED", values["google_tts_cred"])
        Preference.put_value("GLOBAL_COMP_FUNCTION", values["comp_funct"])
        Preference.put_value("SENDGRID_APIKEY", values["sendgrid_apikey"])

    @staticmethod
    def get_bundle_values(uuid, token):
        from contrib.processor import LOGICAL_ADAPTERS

        apikeys = ApiKeys.find_api_keys(uuid, token)
        if not apikeys:
            apikeys = {}
        data = {
            "adapters": Preference.get_value("LOGICAL_ADAPTERS", LOGICAL_ADAPTERS),
            "themeColor": Preference.get_value("KEY_PRIMARY_COLOR", "#3BB9FF"),
            "skill_cancel_hidden": Preference.get_value("KEY_CANCEL_INTENT", ["cancel"]),
            "vueradio": Preference.get_value("AUDIO_PROVIDER", "google"),
            "comp_funct": Preference.get_value(
                "GLOBAL_COMP_FUNCTION", "chatterbot.comparisons.LevenshteinDistance"
            ),
            "aws_access_id": Preference.get_value("KEY_AWS_ACCESS_ID", ""),
            "aws_secret_key": Preference.get_value("KEY_AWS_SECRET_KEY", ""),
            "google_tts_cred": Preference.get_value("GOOGLE_TTS_CRED", ""),
            "sendgrid_apikey": Preference.get_value("SENDGRID_APIKEY", ""),
            "api_key": apikeys.get("api_key"),
            "api_secret": apikeys.get("api_secret"),
        }
        return data


class ServiceProvider(mixin.Model, models.Model):

    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=64)
    code = models.CharField(max_length=64)
    icon = models.ImageField()
    host = models.CharField(max_length=255, null=True, default="localhost")
    oauth = models.TextField()
    validation_endpoint = models.URLField(max_length=255, null=True, default="/oauth2/tokeninfo")
    data_endpoint = models.URLField(max_length=255, null=True, default="/data/controller")
    controller = models.URLField(max_length=255, null=True)

    def __str__(self):
        return self.name

    @staticmethod
    def get_redirect_uri():
        request = mixin.request()
        return settings.HTTP_PROTOCOL + "://" + request.META["HTTP_HOST"] + "/oauth/provider"

    def save(self, *args, **kwargs):
        icon = self.icon
        self.icon = None
        super(ServiceProvider, self).save(*args, **kwargs)
        if icon:
            Attachment.put_attachment("service.provider", self.id, "icon", icon)

    def get_icon(self):
        return Attachment.get_attachment("service.provider", self.id, "icon")

    @staticmethod
    def get_by_code(code):
        record = ServiceProvider.objects.filter(code=code).first()
        if record:
            return record
        return False

    @staticmethod
    def get_by_host(host):
        record = ServiceProvider.objects.filter(host=host).first()
        if record:
            return record
        return False


class TTSAudio(mixin.Model, models.Model):

    AMAZON_POLLY = 0
    GOOGLE_TTS = 1

    SERVICE_CHOICES = (
        (AMAZON_POLLY, "Amazon Polly"),
        (GOOGLE_TTS, "Google TTS"),
    )

    AUDIO_FORMAT_MP3 = "audio/mpeg"
    AUDIO_FORMAT_OGG_VORGIS = "audio/ogg"

    AUDIO_FORMAT_CHOICES = ((AUDIO_FORMAT_MP3, "MP3"), (AUDIO_FORMAT_OGG_VORGIS, "Vorgis OGG"))

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    body = models.TextField()
    data = models.BinaryField(default=None, blank=True, null=True)
    hash = models.CharField(
        default=None,
        max_length=32,
        blank=True,
        null=True,
        unique=True,
    )
    lang = models.CharField(max_length=20, default="en-US")
    mimetype = models.CharField(
        max_length=127,
        default=AUDIO_FORMAT_MP3,
        choices=AUDIO_FORMAT_CHOICES,
    )
    service = models.IntegerField(
        choices=SERVICE_CHOICES,
        default=AMAZON_POLLY,
    )

    def save(self, *args, **kwargs):
        self.body = self.clean_text(self.body)
        if self.hash is None or self.hash == "":
            self.hash = TTSAudio.hash_string(self.body)
        super().save(*args, **kwargs)

    @staticmethod
    def clean_text(body):
        import re

        """Strips, removes punctuation, and returns a lowercased version of body
        """
        f = filter(lambda c: c.isalnum() or c.isspace(), body.strip().lower())
        res = "".join(f)
        res = re.sub(r"\s\s+", " ", res)
        res = re.sub(r"\t", " ", res)
        res = re.sub(r"\n", " ", res)
        return res

    @staticmethod
    def base64(uuid, *args, **kwargs):
        """Get the audio data as a base64 string"""
        data, mimetype = TTSAudio.generate_data(uuid, *args, **kwargs)
        b64 = base64.encodebytes(data)
        return "data:{};base64,{}".format(mimetype, b64.decode())

    @staticmethod
    def generate_base64(body):
        """
        Returns base64 encoded data of body, creates record if it doesn't exist.
        """
        uuid = TTSAudio.generate_reference(body)
        return TTSAudio.base64(uuid)

    @staticmethod
    def generate_data(uuid, service=AMAZON_POLLY, **kwargs):
        """Returns the records data, creates it if it doesn't exist using
        service.

        Check the vendors documentation for a full list of the supported
        languages and voices:

        Amazon Polly:
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/polly.html?highlight=synthesize_speech#Polly.Client.synthesize_speech
        Google TTS:
            https://cloud.google.com/text-to-speech/docs/voices

        Args:
            uuid (str): Record's UUID
            service (int): id of the audio service: 0 for Amazon Polly; 1 for
                Google TTS.
            format (str): format of the audio data, can be 'mp3' or
                'ogg_vorbis'. Default: 'mp3'
            lang (str): Default: 'en-US'
            voice (str): VoiceId. Default: 'Joanna' (Amazon Polly); 'FEMALE'
                (Google TTS).

        Returns:
            A tuple of two items. The first item is the audio data, and
            the second item is the audio's mime-type.

        Throws:
            django.core.exception.ObjectDoesNotExist: if uuid doesn't belong to
                any existing record.
            django.core.exception.ValidationError: if uuid is not valid.
            TTSException: If the data couldn't be generated.
        """
        record = TTSAudio.objects.get(uuid=uuid)

        if record.data is None:
            data = None

            text_data = TTSAudio.clean_text(record.body)
            if service == TTSAudio.AMAZON_POLLY:
                data = TTSAudio.tts_polly(text_data, **kwargs)
            if service == TTSAudio.GOOGLE_TTS:
                data = TTSAudio.tts_google(text_data, **kwargs)

            record.data = data
            record.lang = kwargs.get("lang", record.lang)
            record.mimetype = TTSAudio.get_full_mimetype(format)
            record.service = service
            record.save()

        return record.data, record.mimetype

    @staticmethod
    def generate_authenticated_url(body):
        ref_uuid = TTSAudio.generate_reference(body)
        return (
            settings.HTTP_PROTOCOL
            + "://"
            + get_request().META["HTTP_HOST"]
            + "/media/audio?uuid="
            + str(ref_uuid)
        )

    @staticmethod
    def generate_reference(body, generate_data=False):
        """
        Returns UUID of record with body, creates record if it doesn't exist.

        Args:
            body (str): String that will be used the TTS audio
            generate_data (bool): If True the audio data will be generated in
                another thread.

        Returns:
            The new record UUID

        Raises:
            Exception is body is longer than 500 characters.
        """
        from .exceptions import TTSException

        cleaned = TTSAudio.clean_text(body)
        hashed = TTSAudio.hash_string(cleaned)

        if len(cleaned) > 500:
            raise TTSException("Body must have at most 500 characters")

        try:
            record = TTSAudio.objects.get(hash=hashed)
        except TTSAudio.DoesNotExist:
            print("-" * 20, "TTSAudio DoesNotExist", "-" * 20)
            record = None
        except Exception as e:
            print("-" * 20, "TTSAudio Exception", "-" * 20)
            print(e)
            record = None
        if record is None:
            record = TTSAudio.objects.create(body=cleaned, hash=hashed)
        if generate_data:
            import threading

            thread = threading.Thread(
                target=TTSAudio.generate_data,
                args=[record.uuid],
            )
            thread.start()
        return record.uuid

    @staticmethod
    def get_full_mimetype(format):
        if format == "ogg_vorbis":
            return TTSAudio.AUDIO_FORMAT_OGG_VORGIS
        return TTSAudio.AUDIO_FORMAT_MP3

    @staticmethod
    def hash_string(string):
        """Generates an unique hash for string"""
        from hashlib import md5

        return md5(string.encode()).hexdigest()

    @staticmethod
    def post_values(string):
        """Alternative name for TTSAudio.generate_reference"""
        return TTSAudio.generate_reference(string)

    @staticmethod
    def tts_google(
        text_data,
        *,
        format="mp3",
        lang="en-US",
        voice="FEMALE",
    ):
        """Generates TTS audio using Google TTS services"""
        # TODO: This method hasn't been tested
        from google.cloud import texttospeech

        format = "OGG_OPUS" if format == "ogg_vorbis" else "MP3"

        client = texttospeech.TextToSpeechClient()

        input_text = texttospeech.SynthesisInput(text=text_data)

        return client.synthesize_speech(
            request={
                "input": input_text,
                "voice": {
                    "languageCode": lang,
                    "ssmlGender": voice,
                },
                "audio_config": {"audioEncoding": format},
            }
        )

    @staticmethod
    def tts_polly(
        text_data,
        *,
        engine="neural",
        format="mp3",
        lang="en-GB",
        voice="Emma",
    ):
        """Generates TTS Audio using Amazon Polly services"""
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
        from contextlib import closing
        from django.conf import settings

        initialized = False
        try:
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SECRET_KEY,
                region_name=settings.AWS_REGION,
            )
            initialized = True
        except AttributeError as e:
            print("{1} {0} {1}".format(e, "=" * 5))
            print("===== Using configuration in '.aws/credentials' =====")
            initialized = False

        if not initialized:
            session = boto3.Session()

        try:
            polly = session.client("polly")
        except Exception as e:
            print("===== Unable to read '.aws/credentials' =====")
            raise e

        stream = None

        try:
            response = polly.synthesize_speech(
                Text=text_data,
                LanguageCode=lang,
                OutputFormat=format,
                VoiceId=voice,
                Engine=engine,
            )
        except (BotoCoreError, ClientError) as error:
            Log.error("Amazon Polly error", error)

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as sb:
                stream = sb.read()

        else:
            raise exceptions.TTSException(
                "Amazon Polly request didn't include any AudioStream data"
            )

        return stream


class UserOTP(mixin.Model, models.Model):

    MAX_ATTEMPT = 3

    otp = models.CharField(max_length=32)
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="otps")
    attempt = models.IntegerField(default=MAX_ATTEMPT)

    def __str__(self):
        return str(self.user_id) + " [" + self.otp + "]"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.otp = UserOTP.generateOTP()
        super(UserOTP, self).save(*args, **kwargs)

    @staticmethod
    def authenticate(email, otp):
        record = UserOTP.objects.filter(user_id__email=email).first()
        if record:
            if record.otp == otp:
                user = User.objects.get(id=record.user_id.id)
                record.delete()
                return user
            if record.attempt == 0:
                record.delete()
                return False
            record.attempt = record.attempt - 1
            record.save()
        return False

    @staticmethod
    def get_otp(user):
        record = UserOTP.objects.filter(user_id=user.id).first()
        if not record:
            record = UserOTP.objects.create(user_id=user)
        else:
            record.otp = UserOTP.generateOTP()
            record.attempt = UserOTP.MAX_ATTEMPT
            record.save()
            pass
        return record

    @staticmethod
    def generateOTP():
        digits = "0123456789"
        OTP = ""
        for i in range(6):
            OTP += digits[math.floor(random.random() * 10)]
        return OTP


# modular models start from here

# this model stores json state
class StateModel(models.Model):
    # typically channel_id
    reference_id = models.IntegerField()
    data = models.TextField(null=True)

    def __str__(self):
        if self.data:
            state = json.loads(self.data)
            if state["skill"]:
                return "State.... " + state["skill"]["name"]
        return "State.... None"

    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return None


# this models stores json skill
class SkillModel(models.Model):
    # global unique id
    name = models.CharField(max_length=64, blank=True)
    package = models.CharField(max_length=64, blank=True)
    data = models.TextField(null=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        json_str = json.loads(self.data)
        self.name = json_str["name"]
        self.package = json_str["package"]
        super(SkillModel, self).save(*args, **kwargs)

    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return None


# save component config
class ConfigModel(models.Model):
    # typically channel_id
    component_name = models.CharField(max_length=64)
    data = models.TextField(null=False)

    def __str__(self):
        return self.component_name

    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return None


# save oauth token
class OAuthTokenModel(models.Model):
    # typically channel_id
    component_name = models.CharField(max_length=64)
    user_id = models.IntegerField()
    scope = models.TextField()
    data = models.TextField()

    def __str__(self):
        return self.component_name

    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return None


# modular models ends here

# profile link for BigBot user profile and third party chat platforms
class ProfileLink(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile_link")
    platform = models.CharField(max_length=64)
    platform_user_id = models.CharField(max_length=64)

    def __str__(self):
        return self.platform
