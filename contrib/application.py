# --------------------------------------------------------------------------------------------------
# WARNING: Some classes in this file are deprecated, look for the updated implmentations in the main
# app.
# --------------------------------------------------------------------------------------------------

import abc
import base64
import importlib.util
import json
import logging
import os
from urllib.parse import urlencode
import urllib.parse as urlparse

from django.contrib.auth import get_user_model
from django.template import Context, Template
from durations import Duration
from langdetect import detect
from requests_oauthlib import OAuth2Session

from contrib import utils
from core.models import AccessToken, AppData, ComponentUserResource, DelegateSkill
from mail.models import MailService
from main import Log


class AppSource:
    def __init__(self, name, location, *args, **kwargs):
        self.name = name
        self.location = location
        self.manifest = kwargs.get("manifest")
        self.init = kwargs.get("init")
        self.data = kwargs.get("data")

    def get_application(self):
        return load_instance(self.init).Application(self)

    def get_manifest(self):
        return json.loads(open(self.manifest, "r").read())

    def get_data(self):
        return json.loads(open(self.data, "r").read())


class BaseBuilderBlock:
    """WARNING: This class is deprecated. Look for the updated version in the module
    main.Block.BaseBlock
    """

    def __init__(self, source, descriptor):
        self.source = source
        self.component = self.__class__.__module__ + "." + self.__class__.__name__
        self.descriptor = descriptor

    def get_template(self):
        descriptor = self.descriptor.serialize()
        properties = self.load_template(DataLoader(self.source)).serialize()
        connections = self.load_connections()
        return {
            "component": self.component,
            "descriptor": descriptor,
            "template": properties,
            "connections": connections,
        }

    def get_connections(self, properties=[]):
        return self.load_connections(properties)

    @abc.abstractmethod
    def load_template(self, loader):
        pass

    @abc.abstractmethod
    def load_connections(self, properties=[]):
        # first on is key and second one is display
        return [[-1, ""]]


class BaseComponent:
    """WARNING: This class is deprecated. Look for the updated version in the module
    main.Component.BaseComponent
    """

    def get_preference(self, key):
        component_name = self.__class__.__module__ + "." + self.__class__.__name__
        return AppData.get_data(component_name, key)


class Composer:
    def __init__(self, *args, **kwargs):
        self.default_response = StatementGroup()
        self.logic_adapters = get_component(LogicAdapter)

    def process(self, statement, *args, **kwargs):
        selected_group, min_threshold = None, 0.0
        for adapter in self.logic_adapters:
            if adapter.can_process(statement):
                if adapter.threshold >= min_threshold:
                    statement_group = adapter.process(statement, *args, **kwargs)
                    if not statement_group.empty():
                        selected_group = statement_group
                if adapter.threshold >= 1.0:
                    break
        if selected_group:
            print("Composer: selected group from {}".format(selected_group.tag))
            return selected_group
        return self.default_response


class CoreServices:
    def __init__(self, parent_component):
        self.parent_component = parent_component
        pass

    def send_email(self, subject, email, content, *args, **kwargs):
        email_from = kwargs.get("email_from", "no-reply@abigbot.com")
        MailService.send(email_from, subject, [email], content)
        return True

    def get_oauth(self, user, component, scope=[]):
        provider = OAuthProvider.get(component, user, scope)
        if provider._authenticate():
            return provider
        return False

    def create_resource(self, user, model, resource, data):
        ComponentUserResource.objects.create(
            component=self.parent_component,
            user_id=user.id,
            model=model,
            resource=resource,
            data=json.dumps(data),
        )

    def read_resource(self, model, resource):
        record = ComponentUserResource.objects.get(
            component=self.parent_component, model=model, resource=resource
        )
        if record and record.data:
            return json.loads(record.data)

    def search_resource(self, user, model):
        if user:
            records = ComponentUserResource.objects.filter(
                component=self.parent_component,
                user_id=user.id,
                model=model,
            )
        else:
            records = ComponentUserResource.objects.filter(
                component=self.parent_component,
                model=model,
            )
        data = []
        for record in records:
            if record and record.data:
                data.append(json.loads(record.data))
        return data

    def get_user(self, uid):
        return get_user_model().objects.get(id=uid)

    def search_users(self, query, groups):
        result = get_user_model().objects.filter(
            groups__name__in=groups, first_name__icontains=query
        )
        data = []
        for item in result:
            data.append([item.id, str(item)])
        return data

    def send_notification(self, user, message):
        from core.models import MailChannel
        from core.models import BotDelegate

        channels = MailChannel.get_channels(user)
        default_bot = BotDelegate.get_default_bot()
        for channel in channels:
            for item in channel.bot_delegate_ids.all():
                if item.id == default_bot.id:
                    channel.post_message(default_bot.user_id, message)
                    return True


class DataLoader:
    def __init__(self, source):
        self.source = source
        self.data = None
        self.type = None

    def from_file(self, reference):
        file_location = "{}/{}".format(self.source.location, reference)
        self.data = open(file_location, "r").read()
        return self

    def serialize(self):
        from xmljson import badgerfish as bf
        from xmljson import parker, Parker
        from xml.etree.ElementTree import fromstring
        from json import dumps

        data_dict = bf.data(fromstring(self.data))
        if "properties" in data_dict and "attr" in data_dict["properties"]:
            txt = dumps(bf.data(fromstring(self.data))["properties"]["attr"])
            txt = txt.replace("@", "")
            return json.loads(txt)

        return []


class Descriptor:
    """WARNING: This class is deprecated"""

    def __init__(self, name, *args, **kwargs):
        self.name = name

    def serialize(self):
        return self.__dict__


class LogicAdapter(BaseComponent):
    def __init__(self, descriptor, *args, **kwargs):
        self.threshold = 0.0
        self.descriptor = descriptor
        self._statement_group = StatementGroup(
            tag=self.__class__.__module__ + "." + self.__class__.__name__
        )

    def can_process(self, statement, *args, **kwargs):
        pass

    def process(self, statement, *args, **kwargs):
        return self._statement_group

    def set_threshold(self, threshold):
        self.threshold = threshold

    def add_response(self, statement):
        self._statement_group.add(statement)

    def compare(
        self,
        primary,
        secondary,
    ):
        from chatterbot.comparisons import levenshtein_distance
        from chatterbot.conversation import Statement as ChatterbotStatement

        return levenshtein_distance.compare(
            ChatterbotStatement(primary), ChatterbotStatement(secondary)
        )

    def language(self, text):
        return detect(text)


class OAuthProvider:
    def __init__(self):
        self.component = self.__class__.__module__ + "." + self.__class__.__name__

    def _init(self, user, scope, required):
        self.user = user
        self.scope = scope
        self.required = required

        if not self.get_settings():
            raise Exception("settings is undefined for component: " + self.component)

    def get_settings(self):
        return AppData.get_data(self.component, self._key_oauth_settings())

    def oauth(self):
        saved_token = self._get_token()
        return self.build_oauth(saved_token)

    @abc.abstractmethod
    def authorization_url(self, scope, redirect_uri, settings):
        # authorization_url, state = self.oauth.authorization_url('https://accounts.google.com/o/oauth2/auth',
        #                                                         access_type="offline", prompt="select_account")
        # return authorization_url
        pass

    def _authenticate(self):
        settings = self.get_settings()
        # saved token
        auth_token = self._get_token()

        if auth_token:
            # check if expired
            expired = self.is_expired(auth_token, settings)
            if expired:
                # refresh if expired
                auth_token = self.refresh_token(auth_token, settings)
                if auth_token:
                    self._save_token(auth_token)
            # create OAuth2Session using latest token
            oauth = OAuth2Session(token=auth_token)
            # make sure it is valid against latest scope
            authorized = self.is_scope_authorized(oauth, self.scope)
            if authorized:
                # return un expired authorized scope token
                return oauth
        return False

    @abc.abstractmethod
    def is_expired(self, token, settings):
        pass

    @abc.abstractmethod
    def refresh_token(self, token, settings):
        pass

    @abc.abstractmethod
    def is_scope_authorized(self, oauth, scope):
        # req = oauth.get('https://www.googleapis.com/oauth2/v1/tokeninfo')
        # if req.status_code == 200:
        #     return True
        # return False
        pass

    @abc.abstractmethod
    def fetch_token(self, scope, redirect_uri, settings, authorization_response, *args, **kwargs):
        # return self.oauth.fetch_token('https://accounts.google.com/o/oauth2/token',
        #                               authorization_response=authorization_response,
        #                               client_secret=self.client_secret)
        pass

    @abc.abstractmethod
    def build_oauth(self, token):
        return False

    def _save_token(self, token):
        AppData.put_data(self.component, OAuthProvider._key_oauth_token(self.user.id), token)
        pass

    def _get_token(self):
        return AppData.get_data(self.component, OAuthProvider._key_oauth_token(self.user.id))

    def _key_oauth_settings(self):
        return "oauth_settings"

    @staticmethod
    def _key_oauth_token(uid):
        return "uid_" + str(uid) + "_oauth_token"

    @staticmethod
    def clear_token(component, uid):
        AppData.remove_data(component, OAuthProvider._key_oauth_token(uid))

    @staticmethod
    def get(component, user, scope, required=True):
        provider = get_oauth_provider(component)
        provider._init(user, scope, required)
        return provider

    def _get_redirect_uri(self):
        return "http://dev.abigbot.com/oauth/provider"
        # return 'http://localhost/outlook/callback'
        # return 'http://localhost/oauth/provider'
        # return 'https://demo.abigbot.com/oauth/provider'
        # return 'http://localhost:3001/callback'
        # return 'https://console.bigitsystems.com/oauth/provider'

    @staticmethod
    def _dump_token(authorization_response, request):
        parsed = urlparse.urlparse(authorization_response)
        state_encoded = urlparse.parse_qs(parsed.query)["state"][0]
        state_str = base64.b64decode(state_encoded).decode()
        state = json.loads(state_str)
        user = AccessToken.authenticate(state["access_uuid"], state["access_token"])
        provider = OAuthProvider.get(state["component"], user, state["scope"])
        settings = AppData.get_data(provider.component, provider._key_oauth_settings())
        token = provider.fetch_token(
            state["scope"],
            provider._get_redirect_uri(),
            settings,
            authorization_response,
            request=request,
        )
        provider._save_token(token)
        return provider

    @staticmethod
    def _dump_token_post(authorization_response, request):
        state_encoded = authorization_response["state"]
        state_str = base64.b64decode(state_encoded).decode()
        state = json.loads(state_str)
        user = AccessToken.authenticate(state["access_uuid"], state["access_token"])
        provider = OAuthProvider.get(state["component"], user, state["scope"])
        settings = AppData.get_data(provider.component, provider._key_oauth_settings())
        token = provider.fetch_token(
            state["scope"],
            provider._get_redirect_uri(),
            settings,
            authorization_response,
            request=request,
        )
        provider._save_token(token)
        return provider

    def _get_encoded_state(self):
        token = AccessToken.create_token(self.user)
        state = {
            "access_uuid": token.access_uuid,
            "access_token": token.access_token,
            "component": self.component,
            "scope": self.scope,
        }
        state_str = json.dumps(state)
        state = base64.b64encode(bytes(state_str, "utf-8")).decode()
        return state

    def _get_authorization_url(self):
        settings = AppData.get_data(self.component, self._key_oauth_settings())
        auth_url = self.authorization_url(self.scope, self._get_redirect_uri(), settings)
        state = self._get_encoded_state()
        auth_url = self._build_url(auth_url, {"state": state})
        return auth_url

    def _build_url(self, url, params):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)
        return urlparse.urlunparse(url_parts)


class SkillProvider:
    """WARNING: This class is deprecated. Look for the new implementation in the module
    main.Component
    """

    def __init__(self, descriptor):
        self.component = self.__class__.__module__ + "." + self.__class__.__name__
        self.descriptor = descriptor
        self.services = CoreServices(self.component)

    def auth_providers(self, package, user, *args, **kwargs):
        return []

    def on_start(self, package, user, bundle, *args, **kwargs):
        pass

    def get_provider(self, component, package, user):
        for item in self.auth_providers(package, user):
            if item.component == component:
                return item

    def create_search_item(self, text, value, *args, **kwargs):
        item = {
            "text": text,
            "value": value,
        }
        return item

    def on_execute(self, package, user, data, *args, **kwargs):
        return {}

    def build_text(self, package, user, content, result, *args, **kwargs):
        input = kwargs.get("input")
        t = Template(content)
        c = Context({"user": user, "result": result, "input": input})
        output = t.render(c)
        return output

    def build_result(self, package, user, node, result, *args, **kwargs):
        input = kwargs.get("input")
        if node["node"] == "big.bot.core.text":
            t = Template(node["content"])
            c = Context({"user": user, "result": result, "input": input})
            output = t.render(c)
            return output
        elif node["node"] == "big.bot.core.iframe":
            t = Template(node["content"])
            c = Context({"user": user, "result": result, "input": input})
            output = t.render(c)
            return output

    def on_search(self, package, user, node, query, *args, **kwargs):
        return []

    def parse_input(self, package, user, node, input, body, *args, **kwargs):
        if "required" in node and not node["required"] and isinstance(input, bool) and not input:
            return False
        if node["type"] in ["text", "string"]:
            if isinstance(input, str):
                return input
        elif node["type"] == "integer":
            if isinstance(input, int):
                return input
        elif node["type"] == "float":
            if isinstance(input, float):
                return input
        elif node["type"] == "date":
            if isinstance(input, str) and utils.is_date(input):
                return input
            # fuzzy
            from chatterbot import parsing

            p_val = parsing.datetime_parsing(body)
            if p_val:
                try:
                    return p_val[0][1].strftime("%Y-%m-%d")
                except:
                    pass
        elif node["type"] == "datetime":
            if isinstance(input, str) and utils.is_datetime(input):
                return input
            # fuzzy
            from chatterbot import parsing

            p_val = parsing.datetime_parsing(body)
            if p_val:
                try:
                    return p_val[0][1].strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        elif node["type"] == "duration":
            if (
                isinstance(input, list)
                and len(input) == 2
                and isinstance(input[0], int)
                and isinstance(input[1], int)
                and input[0] >= 0
                and input[1] >= 0
            ):
                return input
            try:
                dur = Duration(body)
                if dur.to_seconds():
                    return [int(dur.to_hours()), int(dur.to_minutes() % 60)]
            except:
                pass
        elif node["type"] == "selection":
            if isinstance(input, str):
                for selection in node["selections"]:
                    if selection[0] == input:
                        return selection[0]
            # fuzzy
            for selection in node["selections"]:
                if selection[1].lower() == body.lower():
                    return selection[0]
        elif node["type"] in ["many2one", "searchable"]:
            match_input = self.match_input(package, user, node, input, body, *args, **kwargs)
            return match_input

        return None

    def match_input(self, package, user, node, input, body, *args, **kwargs):
        return input

    def on_event(self, event, *args, **kwargs):
        return None

    def should_accept_input(self, package, user, node, input, *args, **kwargs):
        return True


class StatementGroup:
    def __init__(self, *args, **kwargs):
        self.tag = kwargs.get("tag")
        self._statements = []

    def add(self, statement):
        self._statements.append(statement)

    def all(self):
        return self._statements

    def empty(self):
        if self._statements:
            return False
        return True


def get_apps_sources():
    cwd = os.path.abspath(os.getcwd())
    directory = "apps"
    path = os.path.join(cwd, directory)
    apps = []
    for file in os.listdir(path):
        if not file.startswith("."):
            app_dir = os.path.join(cwd, directory, file)
            if os.path.isdir(app_dir):
                manifest = os.path.join(cwd, directory, file, "manifest.json")
                init = os.path.join(cwd, directory, file, "init.py")
                data = os.path.join(cwd, directory, file, "data.json")
                location = os.path.join(cwd, directory, file)
                if os.path.exists(manifest) and os.path.exists(init) and os.path.exists(data):
                    apps.append(AppSource(file, location, manifest=manifest, init=init, data=data))
    return apps


def get_component(instance_class, component=None):
    if component:
        for source in get_apps_sources():
            app = source.get_application()
            for item in app.components:
                if isinstance(item, instance_class):
                    if item.component == component:
                        return item
    else:
        all = []
        for source in get_apps_sources():
            app = source.get_application()
            for item in app.components:
                if isinstance(item, instance_class):
                    all.append(item)
        return all


def get_oauth_provider(module):
    for item in get_apps_sources():
        app = item.get_application()
        for component in app.components:
            if isinstance(component, OAuthProvider):
                if component.component == module:
                    return component


def get_skill_provider(module):
    for item in get_apps_sources():
        app = item.get_application()
        for component in app.components:
            if isinstance(component, SkillProvider):
                if component.component == module:
                    return component


def import_app_data(app_name):
    for item in get_apps_sources():
        if item.name == app_name:
            data = item.get_data()
            for item_data in data:
                DelegateSkill.post_values(
                    item_data["name"],
                    item_data["package"],
                    json.dumps(item_data["input_arch"]),
                    json.dumps(item_data["response_arch"]),
                )
                record = DelegateSkill.objects.filter(package=item_data["package"]).first()
                record.component = item_data["component"]
                record.save()


def load_instance(location):
    spec = importlib.util.spec_from_file_location("module.init", location)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


# saw = get_apps_sources()[0]
# app = saw.get_application()
# com = app.components[0]
# print(com.descriptor.package)
# print('Bigbot application driver loaded....')
