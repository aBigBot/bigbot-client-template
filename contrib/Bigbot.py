import abc
import importlib.util
import json
import os

from django.conf import settings
from jinja2 import Template
from silk.profiling.profiler import silk_profile
import textdistance

from contrib.utils import FakeQuery
from core.models import (
    ActiveChannel,
    BotDelegate,
    ConfigModel,
    DelegateSkill,
    DelegateUtterance,
    HumanDelegate,
    HumanDelegateGroup,
    Integration,
    MailChannel,
    OAuthTokenModel,
    Preference,
    SkillModel,
    StateModel,
    TTSAudio,
    User,
)
from main import Log
from main.Binder import Binder, Registry
from main.Component import ChatProvider, OAuthProvider, SkillProvider
from main.Config import AppConfig
from main.Node import DelegatesNode, ImageNode, OAuthNode, PaymentNode, TextNode
from main.State import ChannelState
from main.Statement import OutputStatement
from main.Utterance import UtteranceDistance


def get_apps_sources():
    cwd = os.path.abspath(os.getcwd())

    allowed_apps = ["bigbot"]
    for enabled_app in Integration.objects.filter(enabled=True):
        if enabled_app.label not in allowed_apps:
            allowed_apps.append(enabled_app.label)

    apps = []
    for app in allowed_apps:
        app_dir = os.path.join(cwd, "apps", app)
        if os.path.isdir(app_dir):
            manifest = os.path.join(app_dir, "manifest.json")
            init = os.path.join(app_dir, "init.py")
            if os.path.exists(manifest) and os.path.exists(init):
                apps.append(
                    AppSource(
                        app,
                        app_dir,
                        manifest=manifest,
                        init=init,
                    )
                )

    return apps


def get_components():
    all = []
    for source in get_apps_sources():
        try:
            app = source.get_application()
        except Exception as e:
            Log.error("get_components", e)
            app = None
        if isinstance(app, AppConfig):
            for item in app.components:
                all.append(item)
    return all


def load_instance(location):
    spec = importlib.util.spec_from_file_location("module.init", location)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class BaseBinder(Binder):
    def __init__(self, processor, operator_id):
        self.processor = processor
        self.channel_id = processor.channel.id
        self.user_id = processor.user.id
        self.operator_id = operator_id
        super(BaseBinder, self).__init__(
            self.local_registry(),
            OAUTH_REDIRECT_URL=settings.OAUTH_REDIRECT_URL,
            PAYMENT_REDIRECT_URL=settings.PAYMENT_REDIRECT_URL,
            HTML_RENDER_URL=settings.HTML_RENDER_URL,
        )

    def get_bot(self):
        return self.processor.get_bot_delegate()

    def get_channel(self):
        return self.processor.channel

    # add all component within local registry
    def local_registry(self):
        allowed_installed_only = True
        installed_source = ["bigbot"]
        enabled_integrations = Integration.objects.filter(enabled=True)

        for integration in enabled_integrations:
            if integration.label not in enabled_integrations:
                installed_source.append(integration.label)

        registry = Registry()
        if not allowed_installed_only:
            for source in get_apps_sources():
                try:
                    app = source.get_application()
                except Exception as e:
                    Log.error("BaseBinder.local_registry", e)
                    app = None
                if app:
                    for component in app.components:
                        registry.register(component)
                    for de in app.data_exchange:
                        registry.register_data_exchange(de)
        else:
            for source in get_apps_sources():
                if source.name in installed_source:
                    try:
                        app = source.get_application()
                    except Exception as e:
                        Log.error("BaseBinder.local_registry", e)
                        app = None
                    if app:
                        for component in app.components:
                            registry.register(component)
                        for de in app.data_exchange:
                            registry.register_data_exchange(de)
        return registry

    # @silk_profile(name="BaseBinder.on_cancel_intent")
    def on_cancel_intent(self, statement):
        utterances = Preference.get_value("KEY_CANCEL_INTENT", ["cancel"])
        if isinstance(statement.input, str) and statement.input.lower().strip() in utterances:
            return True
        return False

    def on_context(self):
        return self.on_load_state().data

    def on_get_component_config(self, component_name):
        model_object = ConfigModel.objects.filter(component_name=component_name).first()
        if model_object:
            return model_object.get_data()
        return None

    def on_get_data_exchange(self, component):
        registry = self.local_registry()
        result = []
        return registry

    # this method should return json skill via package
    # @silk_profile(name="BaseBinder.on_get_skill")
    def on_get_skill(self, package):
        model_object = DelegateSkill.objects.filter(package=package).first()
        if model_object:
            return model_object
        return None

    def on_hand_over_group(self, group_id, data, template_str):
        from django.db.models import Count

        group = HumanDelegateGroup.objects.get(id=group_id)
        delegates = group.human_delegates.all()
        user_delegate = HumanDelegate.objects.filter(user_id=self.processor.user).first()
        if delegates.count() > 0 and user_delegate:
            delegate_ids = delegates.values_list("id", flat=True)
            channel = (
                MailChannel.objects.annotate(humans=Count("human_delegate_ids"))
                .filter(humans=delegates.count() + 1, human_delegate_ids__in=delegate_ids)
                .filter(human_delegate_ids__in=[user_delegate.id])
                .first()
            )

            if channel is None:
                channel = MailChannel.ensure_human_delegate_channel(
                    user_delegate.user_id, delegates.first()
                )
                for delegate in delegates[1:]:
                    channel.human_delegate_ids.add(delegate)
                default_bot = BotDelegate.get_default_bot()

            ActiveChannel.set_channel(self.user_id, channel)

            if template_str:
                template = Template(template_str)
                message = template.render(data)
                channel.post_message(self.processor.user, message)

    def on_hand_over_user(self, user_id, data, template_str):
        user = User.objects.filter(keycloak_user=user_id).first()

        if user is None:
            raise Exception("User does not exist")

        human_delegate = HumanDelegate.find(user)
        channel = MailChannel.ensure_human_delegate_channel(self.processor.user, human_delegate)
        ActiveChannel.set_channel(self.user_id, channel)

        if template_str:
            template = Template(template_str)
            message = template.render(data)
            channel.post_message(self.processor.user, message)

    def on_human_delegate(self, statement, delegate_groups, human_delegates):
        user = User.objects.get(id=statement.user_id)
        if user is None:
            raise Exception("Sender does not exist")

        if human_delegates.count() == 1 and delegate_groups.count() == 0:
            channel = MailChannel.ensure_human_delegate_channel(user, human_delegates.first())
            channel.post_message(user, statement.text)
        elif delegate_groups.count() == 1 and human_delegates.count() == 0:
            delegates = delegate_groups.first().human_delegates.all()
            if delegates.count() > 0:
                channel = MailChannel.ensure_human_delegate_channel(user, delegates.first())
                for delegate in delegates[1:]:
                    channel.human_delegate_ids.add(delegate)
                channel.post_message(user, statement.text)
        else:
            delegates = []
            for delegate in human_delegates:
                delegates.append(
                    {
                        "body": delegate.name,
                        "contexts": [1],
                        "image": delegate.image,
                        "values": [delegate.id, statement.text],
                    }
                )
            for group in delegate_groups:
                delegates.append(
                    {
                        "body": group.name,
                        "contexts": [5],
                        "image": group.get_image(),
                        "values": [group.id, statement.text],
                    }
                )
            node = DelegatesNode(delegates)
            output = OutputStatement(self.operator_id, text="Please select a delegate")
            output.append_node(node)
            self.post_message(output)

    def on_load_oauth_token(self, component_name, user_id):
        no_scope = "none"
        model_object = OAuthTokenModel.objects.filter(
            component_name=component_name, user_id=user_id, scope=no_scope
        ).first()
        if model_object:
            return model_object.get_data()
        return None

    def on_load_state(self):
        state_json = {
            "block_id": None,
            "channel_id": self.channel_id,
            "data": {},
            "extra": {},
            "operator_id": self.operator_id,
            "skill": None,
            "user_id": self.user_id,
        }
        model_object = StateModel.objects.filter(reference_id=self.channel_id).first()
        if model_object and model_object.data:
            state_json = json.loads(model_object.data)
            state_json["channel_id"] = self.channel_id
            state_json["operator_id"] = self.operator_id
            state_json["user_id"] = self.user_id
        return ChannelState.deserialize(state_json)

    def on_post_message(self, statement):
        from contrib.statement import Statement as OldStatement

        Log.message("Message", str(statement))
        contents = []
        text = str(statement)

        for item in statement.contents:
            if isinstance(item, OAuthNode):
                text = item.meta["description"]
                contents.append(
                    {
                        "node": item.node,
                        "data": item.data,
                        "icon": item.meta["icon"],
                        "title": item.meta["title"],
                        "description": item.meta["description"],
                    }
                )
            elif isinstance(item, TextNode):
                contents.append(
                    {
                        "node": item.node,
                        "data": item.data,
                    }
                )
            else:
                contents.append(
                    {
                        "node": item.node,
                        "data": item.data,
                        "meta": item.meta,
                    }
                )

        old_statement = OldStatement(text, statement.user_id, contents=contents)
        self.processor.post_message(old_statement)

    # should render searchable
    def on_render_searchable(self, items):
        pass

    def on_save_oauth_token(self, component_name, user_id, token):
        no_scope = "none"
        model_object = OAuthTokenModel.objects.filter(
            component_name=component_name, user_id=user_id, scope=no_scope
        ).first()
        if not model_object:
            model_object = OAuthTokenModel.objects.create(
                component_name=component_name, user_id=user_id, scope=no_scope
            )
        model_object.data = json.dumps(token)
        model_object.save()
        pass

    # must return super
    def on_save_state(self, state_serialized):
        model_object = StateModel.objects.filter(reference_id=self.channel_id).first()
        if not model_object:
            model_object = StateModel.objects.create(reference_id=self.channel_id)
        model_object.data = json.dumps(state_serialized, indent=4)
        model_object.save()

    # @silk_profile(name="BaseBinder.on_select_human_delegate")
    def on_select_human_delegate(self, statement):
        delegates = []
        best_distance = 0.5
        best_match = None
        utterances = DelegateUtterance.objects.filter(human_delegates__isnull=False)

        for utterance in utterances:
            match = textdistance.levenshtein.normalized_similarity(
                utterance.body.lower(), statement.text.lower()
            )
            if match > best_distance:
                best_distance = match
                best_match = utterance

        if best_match:
            return best_match.human_delegates.all()
        return None

    # @silk_profile(name="BaseBinder.on_select_human_delegate_skill")
    def on_select_human_delegate_skill(self, human_delegate, statement):
        user = human_delegate.user_id
        if not user:
            return None, None

        delegates = BotDelegate.objects.filter(owner=user)
        skills = set()
        for delegate in delegates:
            for skill in delegate.skill_ids.all():
                skills.add(skill)

        utterances = set()
        for skill in skills:
            for intent in skill.intents.all():
                for utterance in intent.utterances.all():
                    utterances.add(utterance)

        best_distance = 0.5
        best_match = None
        for utterance in utterances:
            match = textdistance.levenshtein.normalized_similarity(
                utterance.body.lower(), statement.text.lower()
            )
            if match > best_distance:
                best_distance = match
                best_match = utterance

        if best_match:
            skill = best_match.intent_id.skill_id
            return delegates.filter(skill_ids__in=[skill.id]).first(), skill
        return None, None

    # @silk_profile(name="BaseBinder.on_send_fail_message")
    def on_send_fail_message(self, bot_delegate):
        channel = self.get_channel()
        channel.reset_fails()
        human_delegate = bot_delegate.get_owner_delegate()
        user = human_delegate.user_id
        text = "Hey I'm {} {}, seems {} couldn't help you this time, what can I do for you?".format(
            user.first_name, user.last_name, bot_delegate.name
        )
        new_channel = MailChannel.ensure_human_delegate_channel(self.processor.user, human_delegate)
        ActiveChannel.set_channel(self.user_id, new_channel)
        new_channel.post_message(human_delegate.user_id, text)

    # this method should return package if intent matched
    def on_skill_intent(self, statement):
        package = self.processor.match_package(statement)
        return package

    # @silk_profile(name="BaseBinder.on_standard_input")
    def on_standard_input(self, input, output):
        match_object, best_provider, confidence = None, None, 0.0
        for item in get_components():
            if not issubclass(item, ChatProvider):
                continue
            component_name = item.__class__.__module__ + "." + item.__class__.__name__
            config = self.on_get_component_config(component_name)
            chat_provider = item(config)
            if chat_provider.can_process(self, input):
                chat_object = chat_provider.on_match_object(self, input)
                if chat_object[0] > confidence:
                    confidence = chat_object[0]
                    match_object = chat_object[1]
                    best_provider = chat_provider

        if best_provider and confidence > 0:
            best_provider.process(self, input, confidence, match_object)
        else:
            channel = self.get_channel()
            delegate = BotDelegate.objects.filter(user_id=self.operator_id).first()
            default_bot = BotDelegate.get_default_bot()
            fails = channel.increment_fail(delegate)
            if fails >= 3 and not channel.is_human_channel and delegate.id != default_bot.id:
                self.on_send_fail_message(delegate)
            elif not channel.is_human_channel:
                output = OutputStatement(self.operator_id)
                output.append_text(delegate.get_default_response())
                self.post_message(output)

    def process_utterance(self, statement):
        best_distance = 0.5
        best_match = None

        for utterance in DelegateUtterance.objects.all():
            match = textdistance.levenshtein.normalized_similarity(
                utterance.body.lower(), statement.text.lower()
            )
            if match > best_distance:
                best_distance = match
                best_match = utterance

        if best_match:
            delegates = best_match.human_delegates.all()
            groups = best_match.delegate_groups.all()
            return delegates, groups

        return None, None


class AppSource:
    def __init__(self, name, location, *args, **kwargs):
        self.name = name
        self.location = location
        self.manifest = kwargs.get("manifest")
        self.init = kwargs.get("init")

    def get_application(self):
        return load_instance(self.init).Application(self)

    def get_manifest(self):
        return json.loads(open(self.manifest, "r").read())
