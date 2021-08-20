from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import models
from django_middleware_global_request.middleware import get_request

from main import Log


RESTRICT_SUPER_USER = False


def check_permissions(user, permissions, access_type):
    if user is None:
        raise PermissionDenied("Insuficient permissions")

    user_permissions = set()
    attr = getattr(permissions, "all", [])
    if isinstance(attr, list):
        for group in attr:
            user_permissions.add(group)
    if isinstance(attr, str):
        user_permissions.add(attr)

    attr = getattr(permissions, access_type, [])
    if isinstance(attr, list):
        for group in attr:
            user_permissions.add(group)
    if isinstance(attr, str):
        user_permissions.add(attr)

    return user.in_group(*user_permissions)


def env(object, option="name_to_model"):
    named_instance = models_list()
    # name_to_model | class_to_model | name_to_class
    if option == "class_to_model":
        for key, val in named_instance.items():
            if str(val) == str(object):
                return named_instance[key]()
        return False
    if option == "name_to_class":
        return named_instance[object]
    return named_instance[object]()


def models_list():
    from bigbot.models import InputPattern, ResponsePhrase
    from contrib.keycloak import KeycloakUser
    from core.models import (
        ApiKeys,
        AppData,
        BotDelegate,
        DelegateIntent,
        DelegateSkill,
        DelegateUtterance,
        Integration,
        HumanDelegate,
        HumanDelegateGroup,
        LocationPattern,
        Preference,
        ServiceProvider,
        TTSAudio,
    )

    return {
        "app.data": AppData,
        "api.keys": ApiKeys,
        "bot.delegate": BotDelegate,
        "delegate": BotDelegate,
        "delegate.delegate": BotDelegate,
        "delegate.intent": DelegateIntent,
        "delegate.skill": DelegateSkill,
        "delegate.utterance": DelegateUtterance,
        "integration": Integration,
        "input.pattern": InputPattern,
        "keycloak.user": KeycloakUser,
        "location.pattern": LocationPattern,
        "preference": Preference,
        "res.users": HumanDelegate,
        "response.phrase": ResponsePhrase,
        "service.provider": ServiceProvider,
        "tts.audio": TTSAudio,
        "user.group": HumanDelegateGroup,
    }


def request():
    from django_middleware_global_request.middleware import get_request

    return get_request()


class Access:
    CREATE = "create"
    READ = "read"
    UNLINK = "unlink"
    WRITE = "write"


class AccessRights:
    def __init__(self):
        self.group_access_rights = {}
        self.user_rights = False

    # Todo [Read,Create,Write,Unlink] : [1,1,1,1]
    def add_group_rights(self, group_name, read, create, write, unlink):
        self.group_access_rights[group_name] = [read, create, write, unlink]

    def has_group_rights(self, group_name, access_type):
        if group_name in self.group_access_rights:
            if access_type == Access.READ:
                return self.group_access_rights[group_name][0] == 1
            elif access_type == Access.CREATE:
                return self.group_access_rights[group_name][1] == 1
            elif access_type == Access.WRITE:
                return self.group_access_rights[group_name][2] == 1
            elif access_type == Access.UNLINK:
                return self.group_access_rights[group_name][3] == 1
        return False

    # Todo only PrimaryField/IntegerField/Many2One/Many2Many
    def add_user_rights(self, reference_field, read, write, unlink):
        self.user_rights = [reference_field, [read, write, unlink]]

    # Todo only PrimaryField/IntegerField/Many2One/Many2Many allowed $user_id must be non zero int
    def has_user_rights(self, object, user_id, access_type):
        if not self.user_rights:
            return True
        if access_type == Access.READ:
            if self.user_rights[1][0] != 1:
                return False
        elif access_type == Access.WRITE:
            if self.user_rights[1][1] != 1:
                return False
        elif access_type == Access.UNLINK:
            if self.user_rights[1][2] != 1:
                return False

        if hasattr(object, self.user_rights[0]):
            field_object = object._meta.get_field(self.user_rights[0])
            field_type = field_object.get_internal_type()
            field_value = field_object.value_from_object(object)
            if field_type == "AutoField":
                return field_value == user_id
            elif field_type == "IntegerField":
                return field_value == user_id
            elif field_type == "ForeignKey":
                return field_value == user_id
            elif field_type == "OneToOneField":
                return field_value == user_id
            elif field_type == "ManyToManyField":
                for single_object in field_value:
                    if single_object.id == user_id:
                        return True

        return False


class Model:
    class Permissions:
        """Sets the permissions for the class, the permissions are set by assigning a role or list
        of roles to the operation, the operations are: create, read, unlink, write, and all which
        includes all the operations. The roles are: __manager__, __operator__, and __superuser__.
        Where the permission hierarchy goes: __operator__ < __manager__ < __superuser__.

        Example:
            class Permissions:
                all = ["__manager__", "__superuser__"]    # Full permissions
                read = "__operator__"                     # Only has read permissions
        """

        pass

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self._object = self._model_object()
        self._permissions = self.Permissions
        try:
            self._user = get_request().keycloak_user
        except:
            self._user = None

    def _get_field_value(self, name):
        if hasattr(self, name):
            field_object = self._meta.get_field(name)
            field_type = field_object.get_internal_type()
            field_value = field_object.value_from_object(self)
            if field_type in [
                "CharField",
                "AutoField",
                "TextField",
                "EmailField",
                "BooleanField",
                "IntegerField",
            ]:
                return field_value
            elif field_type in ["UUIDField"]:
                return str(field_value)
            elif field_type in ["KeycloakUUID"]:
                try:
                    return field_object.serialize_object(field_value)
                except:
                    return None
            elif field_type in ["ForeignKey", "OneToOneField"]:
                if field_value:
                    single_value = getattr(self, name)
                    return [single_value.id, str(single_value)]
            elif field_type in ["ManyToManyField"]:
                ids = []
                for single_value in field_value:
                    ids.append(single_value.id)
                return ids
        return False

    def _load_filter(self, filter):
        conditions = {}
        for con in filter:
            if con[0] not in conditions:
                conditions[con[0]] = con[1]
        return conditions

    def _model_object(self):
        app_label = self._meta.app_label
        model_name = self.__class__.__name__
        object = apps.get_model(app_label=app_label, model_name=model_name)
        return object.objects

    def check_permissions(self, access_type):
        return check_permissions(self._user, self._permissions, access_type)

    def create(self, values):
        if not self.check_permissions(Access.CREATE):
            return False
        pre_vals = {}
        for key, val in values.items():
            if hasattr(self, key):
                field_object = self._meta.get_field(key)
                field_type = field_object.get_internal_type()
                if field_type in [
                    "CharField",
                    "TextField",
                    "EmailField",
                    "BooleanField",
                    "IntegerField",
                ]:
                    pre_vals[key] = val
                elif field_type in ["ForeignKey", "OneToOneField"]:
                    rel_object = env(
                        field_object.related_model, option="class_to_model"
                    )._model_object()
                    rel = rel_object.get(id=val)
                    pre_vals[key] = rel

        record = self._object.create(**pre_vals)

        for key, val in values.items():
            if hasattr(self, key):
                field_object = self._meta.get_field(key)
                field_type = field_object.get_internal_type()
                if field_type in ["ManyToManyField"]:
                    rel_object = env(
                        field_object.related_model, option="class_to_model"
                    )._model_object()
                    for rel in rel_object.filter(id__in=val):
                        getattr(record, key).add(rel)

        return record

    def get(self):
        self.check_permissions(Access.READ)
        return self

    def get_fields_value(self, fields):
        return self.serialize(fields)

    def name_filter(self, query):
        if query:
            return [[["name__contains", query]], 5, ["name", "desc"]]
        else:
            return [[], 5, ["name", "desc"]]

    def name_search(self, query):
        results = []
        sort = self.name_filter(query)[2]
        limit = self.name_filter(query)[1]
        filter = self.name_filter(query)[0]
        sort = "-" + sort[0] if not sort[1].lower() == "asc" else sort[0]
        records = self._object.filter(**self._load_filter(filter)).order_by(sort)[:limit]
        for object in records:
            if object.check_permissions(Access.READ):
                results.append([object.id, str(object)])
        return results

    def read(self, id):
        if not self.check_permissions(Access.READ):
            return False
        object = self._object.filter(id=id).first()
        return object

    def search(self, filter=[], limit=0, offset=0, sort=["id", "desc"], raise_exception=False):
        sort = "-" + sort[0] if not sort[1].lower() == "asc" else sort[0]
        records = self._object.filter(**self._load_filter(filter)).order_by(sort)
        records = records[offset:] if limit == 0 else records[offset : offset + limit]
        result = []
        for record in records:
            if record.check_permissions(Access.READ):
                result.append(record)
        return result

    def search_count(self, filter=[]):
        return len(self.search(filter))

    def serialize(self, fields=[]):
        if "id" not in fields:
            fields.insert(0, "id")
        values = {}
        for name in fields:
            values[name] = self._get_field_value(name)
        return values

    def unlink(self):
        if not self.check_permissions(Access.UNLINK):
            return False
        self.delete()
        return True

    def write(self, values):
        if not self.check_permissions(Access.WRITE):
            return False
        for key, val in values.items():
            if hasattr(self, key):
                field_object = self._meta.get_field(key)
                field_type = field_object.get_internal_type()
                if field_type in [
                    "CharField",
                    "TextField",
                    "EmailField",
                    "BooleanField",
                    "IntegerField",
                ]:
                    setattr(self, key, val)
                elif field_type in ["ForeignKey", "OneToOneField"]:
                    rel_object = env(
                        field_object.related_model, option="class_to_model"
                    )._model_object()
                    rel = rel_object.get(id=val)
                    setattr(self, key, rel)
                elif field_type in ["ManyToManyField"]:
                    getattr(self, key).clear()
                    rel_object = env(
                        field_object.related_model, option="class_to_model"
                    )._model_object()
                    for rel in rel_object.filter(id__in=val):
                        getattr(self, key).add(rel)
        self.save()
        return True
