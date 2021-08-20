import json
from urllib.parse import urlparse, urlencode
import uuid

import chatterbot
from chatterbot import ChatBot, parsing
from chatterbot.comparisons import levenshtein_distance
from chatterbot.trainers import ListTrainer
from django.contrib.auth.models import Group
from django.template import Context, Template
from durations import Duration
import requests
from silk.profiling.profiler import silk_profile

from bigbot.models import InputPattern, ResponsePhrase
from contrib import mixin, utils
from contrib.application import Composer
from contrib.statement import Statement
from core.models import (
    AccessToken,
    ActiveChannel,
    BotDelegate,
    DelegateSkill,
    DelegateState,
    DelegateUtterance,
    HumanDelegate,
    HumanDelegateGroup,
    MailChannel,
    MailMessage,
    OauthAccess,
    Preference,
    ServiceProvider,
    User,
    UserProfile,
)
from main import Flag, Log
from main.Node import CancelNode, SearchNode, SkipNode, TextNode
from main.Statement import InputStatement
from main.Utterance import UtteranceDistance

from . import application
from .Bigbot import BaseBinder


DEFAULT_CANCEL_INTENTS = ["cancel"]
DEFAULT_CANCEL_MESSAGE = "Your request has been cancelled."
DEFAULT_HOST_KEY = "DEFAULT_HOST_KEY"
DEFAULT_HOST_VAL = "https://bigitsystems.com/bb/controller"


CTX_STANDARD_INPUT = 0
CTX_HUMAN_DELEGATE_SELECT = 1
CTX_BOT_DELEGATE_SELECT = 2
CTX_CANCEL_SKILL = 3
CTX_START_SKILL = 4
CTX_DELEGATE_GROUP_SELECT = 5


LOGICAL_ADAPTERS = [
    {
        "name": "Bigbot",
        "package": "bigbot.adapter.CorpusAdapter",
        "active": True,
    },
    {
        "name": "UnitConversion",
        "package": "chatterbot.logic.UnitConversion",
        "active": True,
    },
    {
        "name": "Mathematical",
        "package": "chatterbot.logic.MathematicalEvaluation",
        "active": True,
    },
    {
        "name": "BestMatch",
        "package": "chatterbot.logic.BestMatch",
        "active": True,
    },
    {
        "name": "TimeLogicAdapter",
        "package": "chatterbot.logic.TimeLogicAdapter",
        "active": False,
    },
]


class DelegateFinder:
    def __init__(self, user):
        self.user = user
        pass

    def apply_template(self, string):
        return string

    # @silk_profile(name="DelegateFinder.process")
    def process(self, value, match_skill=False):
        patterns = DelegateUtterance.objects.filter()

        # distance of each Utterance match close to input confidence
        if not match_skill:
            distance = []
            for pattern in patterns:
                first = chatterbot.conversation.Statement(pattern.body)
                second = chatterbot.conversation.Statement(value)
                distance.append(levenshtein_distance.compare(first, second))
            if not distance:
                return False
            best_match_index = distance.index(max(distance))
            matched_threshold = max(distance)
            intent_id = patterns[best_match_index].intent_id
            if not intent_id:
                return False
            top_match_skill = intent_id.skill_id
        else:
            matched_threshold = 1
            top_match_skill = match_skill

        available_delegates = BotDelegate.objects.filter(
            skill_ids__in=[top_match_skill],
            classification__in=(BotDelegate.DELEGATE_BOT, BotDelegate.BIGBOT),
        )
        possible_delegates = []
        for delegate in available_delegates:
            threshold = delegate.confidence / 100
            # confidence good enough for this delegate to match skill
            if matched_threshold >= threshold:
                possible_delegates.append(delegate)
        # Human delegate random if some other delegate match

        # if possible_delegates:
        #     humans = []
        #     for delegate in HumanDelegate.objects.exclude(user_id=self.user.id):
        #         # if delegate.user_id.groups.filter(name__in=['operator']):
        #         # TODO: Replace with keycloak user
        #         if delegate.user_id.groups.filter(name="operator"):
        #             humans.append(delegate)
        #     if humans:
        #         possible_delegates.extend(humans[:2])

        if possible_delegates:
            return [top_match_skill, possible_delegates]
        return False


class SkillFinder:
    def __init__(self, user):
        pass

    # @silk_profile(name="SkillFinder.process")
    def process(self, delegate, value):
        patterns = DelegateUtterance.objects.filter()
        distance = []
        for pattern in patterns:
            first = chatterbot.conversation.Statement(pattern.body)
            second = chatterbot.conversation.Statement(value)
            distance.append(levenshtein_distance.compare(first, second))
        if not distance:
            return False
        best_match_index = distance.index(max(distance))
        matched_threshold = max(distance)
        intent_id = patterns[best_match_index].intent_id
        if not intent_id:
            return False
        top_match_skill = intent_id.skill_id
        if delegate.skill_ids.filter(id=top_match_skill.id):
            threshold = delegate.confidence / 100
            if matched_threshold >= threshold:
                return top_match_skill
        return False


class SkillProcessor:
    def __init__(self, user, delegate, state):
        self.debug = True
        self.user = user
        self.active_state = state
        self.delegate = delegate
        self.host = state.skill_id.provider.controller

    def execute_skill(self, skill, values, input_array, response_array, result_extra):
        result_extra = json.loads(result_extra) if result_extra else {}
        data = self.format_values(input_array, values)
        package = skill.package
        component = skill.component
        user = self.user
        input = values

        provider = application.get_skill_provider(component)
        result = provider.on_execute(package, user, data, input=input, result_extra=result_extra)
        text = ""
        for node in response_array:
            if node["node"] == "big.bot.core.text":
                text = provider.build_text(
                    package, user, node["content"], result, input=input, result_extra=result_extra
                )
            output = provider.build_result(
                package, user, node, result, input=input, result_extra=result_extra
            )
            if output:
                node["data"] = output
        return Statement(text=text, contents=response_array, uid=self.getUID()), result

    def get_ongoing_state(self):
        # this returns skill state object if any
        return self.active_state

    # @silk_profile(name="SkillProcessor.get_output")
    def get_output(self):
        integration = self.integration_handler()
        if integration:
            return integration

        state = self.get_ongoing_state()
        cursor = state.cursor
        input_array = state.skill_id.get_input_data()

        # process in sequence
        if len(input_array) > cursor:
            # output
            object = input_array[cursor]
            # extra logic for domain filter
            self.format_domain(object, state.get_data())

            statement = Statement(text=self.apply_template(object["string"]), uid=self.getUID())
            nodes = {
                "date": "big.bot.core.picker.date",
                "datetime": "big.bot.core.picker.datetime",
                "duration": "big.bot.core.picker.duration",
            }
            if object["type"] in nodes:
                statement.contents.append({"node": nodes[object["type"]], "data": False})
            return statement
            pass
        else:
            # final result
            data = state.get_data()
            response_array = state.skill_id.get_response_data()

            try:
                c_id = self.active_state.channel_id
                result, res = self.execute_skill(
                    state.skill_id, data, input_array, response_array, self.active_state.result
                )
                self.active_state.delete()

                if state.skill_id.next_skill:
                    sender_user = User.objects.filter(id=result.uid).first()
                    c_id.post_message(sender_user, result.text, data=result.serialize())
                    next_skill = DelegateSkill.objects.filter(
                        package=state.skill_id.next_skill
                    ).first()
                    new_active_state = DelegateState.set_skill(next_skill, c_id)
                    new_active_state.data = json.dumps(data)
                    new_active_state.result = json.dumps(res)
                    new_active_state.save()
                    new_sp = SkillProcessor(self.user, self.delegate, new_active_state)
                    stmt = new_sp.start()
                    return stmt

                return result
            except Exception as e:
                utils.log_exception(e)
                return Statement(text=self.delegate.get_default_response(), uid=self.getUID())
        pass

    def getOAuthToken(self):
        token = OauthAccess.objects.filter(
            user_id=self.user.id, provider=self.active_state.skill_id.provider.code
        ).first()
        if token:
            return token.access_token
        return False

    def getUID(self):
        return self.delegate.user_id.id

    def find_suggestion(self, query):
        suggestions = []
        # TODO: Update the next line or deprecate
        if self.user.in_group("cross", "public"):
            state = self.get_ongoing_state()
            if state:
                suggestions.append(
                    {"contexts": [CTX_CANCEL_SKILL], "body": "Cancel", "values": ["cancel"]}
                )
                cursor = state.cursor
                input_array = state.skill_id.get_input_data()
                if len(input_array) > cursor:
                    # output
                    cursor_item = input_array[cursor]
                    if not cursor_item["required"]:
                        suggestions.append(
                            {"contexts": [CTX_STANDARD_INPUT], "body": "Skip", "values": [False]}
                        )
                    if cursor_item["type"] in ["many2one", "searchable"]:
                        self.format_domain(cursor_item, state.get_data())
                        user = self.user
                        component = state.skill_id.component
                        package = state.skill_id.package
                        provider = application.get_skill_provider(component)
                        for item in provider.on_search(
                            package, user, cursor_item, query, data=state.get_data()
                        ):
                            suggestions.append(
                                {
                                    "contexts": [CTX_STANDARD_INPUT],
                                    "body": item["text"],
                                    "values": [item["value"]],
                                }
                            )
                    elif cursor_item["type"] == "selection":
                        for item in (
                            [i for i in cursor_item["selections"] if query in i[0]]
                            if query
                            else cursor_item["selections"]
                        ):
                            suggestions.append(
                                {
                                    "contexts": [CTX_STANDARD_INPUT],
                                    "body": item[1],
                                    "values": [item[0]],
                                }
                            )
        return suggestions

    def format_domain(self, object, data_collection):
        if "domain" in object:
            for cond in object["domain"]:
                if isinstance(cond[2], str) and cond[2] in data_collection:
                    cond[2] = data_collection[cond[2]]
                else:
                    pass

    def format_values(self, input_array, values):
        for input_object in input_array:
            if input_object["field"] in values:
                if values[input_object["field"]]:
                    if input_object["type"] == "duration":
                        values[input_object["field"]] = float(
                            str(values[input_object["field"]][0])
                            + "."
                            + str(int(values[input_object["field"]][1] * 100 / 60))
                        )
        return values

    # @silk_profile(name="SkillProcessor.integration_handler")
    def integration_handler(self):
        component = self.active_state.skill_id.component
        package = self.active_state.skill_id.package
        user = self.user

        if not component:
            if self.debug:
                msg = "No component has been set for {}.".format(package)
                return Statement(text=msg, uid=self.getUID(), contents=[])
            else:
                msg = "Service is unavailable."
                return Statement(text=msg, uid=self.getUID(), contents=[])

        skill_provider = application.get_skill_provider(component)
        provider = self.active_state.skill_id.provider
        if not skill_provider:
            if self.debug:
                msg = "{} not found in registry, please register first".format(component)
                return Statement(text=msg, uid=self.getUID(), contents=[])
            else:
                msg = "Service is unavailable."
                return Statement(text=msg, uid=self.getUID(), contents=[])

        for item in skill_provider.auth_providers(package, user, data=self.active_state.get_data()):
            oauth = item._authenticate()
            if not oauth:
                auth_url = item._get_authorization_url()
                contents = [
                    {
                        "node": "big.bot.core.oauth",
                        "data": auth_url,
                        "icon": provider.get_icon(),
                        "title": provider.name,
                        "description": provider.description,
                    },
                ]
                stmt = Statement(
                    text="You need to authorize your account to process this request.",
                    uid=self.getUID(),
                    contents=contents,
                )
                return stmt
        return False

    # this will tell how much we should jump from inputs in case attr invisible used
    def jump_counter(self, cursor, data, input_array, broke, counter=1):
        if (
            not broke
            and input_array[cursor]["type"] == "searchable"
            and "multi" in input_array[cursor]
        ):
            if "attrs" in input_array[cursor]:
                attr = input_array[cursor]["attrs"]
                if "invisible" in attr:
                    invisible = attr["invisible"]
                    should_skip_0 = True
                    for item in invisible:
                        if item[1] == "=":
                            if data[item[0]] != item[2]:
                                should_skip_0 = False
                                break
                        elif item[1] == "!=":
                            if data[item[0]] == item[2]:
                                should_skip_0 = False
                                break
                    if not should_skip_0:
                        return 0

        if len(input_array) > cursor + 1:
            next_cursor = cursor + 1
            next = input_array[next_cursor]
            print("===========current=========", next)
            if "attrs" in next:
                attr = next["attrs"]
                if "invisible" in attr:
                    invisible = attr["invisible"]
                    print("===========invisible=========", invisible)
                    should_skip = True
                    for item in invisible:
                        if item[1] == "=":
                            if data[item[0]] != item[2]:
                                should_skip = False
                                break
                        elif item[1] == "!=":
                            if data[item[0]] == item[2]:
                                should_skip = False
                                break
                    if should_skip:
                        counter += 1
                        cursor += 1
                        return self.jump_counter(cursor, data, input_array, broke, counter)
        return counter

    # this return true if input excepted in respect to current input_object
    def parse_inputs(self, input, body, input_object):
        if (
            "required" in input_object
            and not input_object["required"]
            and isinstance(input, bool)
            and not input
        ):
            return False

        if input_object["type"] in ["text", "string"]:
            if isinstance(input, str):
                return input
        elif input_object["type"] == "integer":
            if isinstance(input, int):
                return input
        elif input_object["type"] == "float":
            if isinstance(input, float):
                return input
        elif input_object["type"] == "selection":
            if isinstance(input, str):
                for selection in input_object["selections"]:
                    if selection[0] == input:
                        return selection[0]
            # fuzzy
            for selection in input_object["selections"]:
                if selection[1].lower() == body.lower():
                    return selection[0]
        elif input_object["type"] == "date":
            if isinstance(input, str) and utils.is_date(input):
                return input
            # fuzzy
            p_val = parsing.datetime_parsing(body)
            if p_val:
                try:
                    return p_val[0][1].strftime("%Y-%m-%d")
                except:
                    pass
        elif input_object["type"] == "datetime":
            if isinstance(input, str) and utils.is_datetime(input):
                return input
            # fuzzy
            p_val = parsing.datetime_parsing(body)
            if p_val:
                try:
                    return p_val[0][1].strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        elif input_object["type"] == "duration":
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
        elif input_object["type"] in ["many2one", "searchable"]:
            return input
            if isinstance(input, int) and input >= 0:
                return input
            # fuzzy
            object = {
                "token": self.getOAuthToken(),
                "method": "name_search",
                "query": body,
                "model": input_object["model"],
                "domain": [],
            }
            if "domain" in input_object:
                object["domain"] = input_object["domain"]
            response = requests.post(url=self.host, data={"data": json.dumps(object)})
            if response:
                result = response.json()["result"]
                if result and len(result) == 1:
                    return result[0]["id"]
        return None

    def process(self, value, body):
        # this process skill workflow further
        self.put_input(value, body)
        output = self.get_output()
        return output

    def put_input(self, input, body):
        integration = self.integration_handler()
        if integration:
            return integration
        # input must be appropriate void()
        state = self.get_ongoing_state()
        cursor = state.cursor
        data = state.get_data()
        input_array = state.skill_id.get_input_data()

        component = state.skill_id.component
        package = state.skill_id.package
        provider = application.get_skill_provider(component)
        user = self.user

        if len(input_array) > cursor:
            input_object = input_array[cursor]
            # p_val = self.parse_inputs(input, body, input_object)
            p_val = provider.parse_input(package, user, input_object, input, body, data=data)
            if p_val is not None:
                # save/increase cursor if valid
                multi = True if "multi" in input_object else False
                broke = (
                    True
                    if isinstance(input, str) and input.startswith("\\(") and input.endswith(")")
                    else False
                )
                if not broke:
                    state.put_data(input_object["field"], p_val, multi)
                if cursor < len(input_array):
                    state.cursor = cursor + self.jump_counter(
                        cursor, state.get_data(), input_array, broke
                    )
                state.save()
        pass

    # @silk_profile(name="SkillProcessor.start")
    def start(self):
        # should return statement
        output = self.get_output()
        return output


class BotProcessor:
    def __init__(self, user):
        self.chatbot_name = "bigbot"
        self.user = user
        self.channel = ActiveChannel.get_channel(user)
        self.message_ids = []
        # self.is_authenticated = user.groups.filter(name = 'cross').exists()
        self.is_authenticated = True

    # @silk_profile(name="BotProcessor.attempt_cancellation")
    def attempt_cancellation(self, delegate, active_state, value):
        cancel_intents = Preference.get_value("KEY_CANCEL_INTENT", DEFAULT_CANCEL_INTENTS)
        if value in cancel_intents:
            active_state.delete()
            stmt = Statement(text="Your query has been cancelled.", uid=delegate.user_id.id)
            self.post_message(stmt)
            return True
        return False

    # @silk_profile(name="BotProcessor.delegate_suggestions")
    def delegate_suggestions(self, bot_delegate, skill, delegates):
        str_delegate = "Please select an available delegate to assist with this."
        delegate_content = []
        request = mixin.request()
        for delegate in delegates:
            p_user = delegate.user_id
            if isinstance(delegate, HumanDelegate):
                context = [CTX_HUMAN_DELEGATE_SELECT]
                value = [delegate.id]
            else:
                context = [CTX_BOT_DELEGATE_SELECT, CTX_START_SKILL]
                value = [delegate.id, skill.id]
            image = delegate.user_id.get_avatar_url()
            delegate_content.append(
                {"body": str(delegate), "contexts": context, "values": value, "image": image}
            )
        contents = [{"node": "big.bot.core.delegates", "data": delegate_content}]
        stm = Statement(text=str_delegate, uid=bot_delegate.user_id.id, contents=contents)
        self.post_message(stm)

    def find_suggestions(self, query):
        suggestions = []
        bot_delegate = self.channel.bot_delegate_ids.first()
        if bot_delegate:
            binder = BaseBinder(self, bot_delegate.user_id.id)

            # Get suggestions from skill
            if binder.on_load_state().is_active():
                items = binder.search_query(query)
                for item in items:
                    body = str(item)
                    value = item.serialize()
                    suggestions.append(
                        {"contexts": [CTX_STANDARD_INPUT], "body": body, "values": [value]}
                    )
            # Get suggestions from bot
            else:
                # Get suggestions from default bot
                if bot_delegate.id == BotDelegate.get_default_bot().id:
                    skill_ids = []

                    if query:
                        utterances = DelegateUtterance.objects.filter(
                            body__icontains=query, intent_id__isnull=False
                        ).order_by("-body")[:5]
                    else:
                        utterances = DelegateUtterance.objects.filter(intent_id__isnull=False)[:5]

                    for utterance in utterances:
                        intent = utterance.intent_id
                        skill = intent.skill_id
                        if skill.id not in skill_ids:
                            if BotDelegate.objects.filter(skill_ids__in=[skill.id]):
                                skill_ids.append(skill.id)
                                suggestions.append(
                                    {
                                        "contexts": [CTX_START_SKILL],
                                        "body": intent.skill_id.name,
                                        "values": [skill.id],
                                    }
                                )

                    for delegate in HumanDelegate.objects.filter(utterances__isnull=False):
                        for utterance in delegate.utterances.filter(body__icontains=query):
                            suggestions.append(
                                {
                                    "body": utterance.body,
                                    "contexts": [CTX_HUMAN_DELEGATE_SELECT],
                                    "values": [delegate.id, utterance.body],
                                }
                            )

                    for group in HumanDelegateGroup.objects.filter(utterances__isnull=False):
                        for utterance in group.utterances.filter(body__icontains=query):
                            suggestions.append(
                                {
                                    "body": utterance.body,
                                    "contexts": [CTX_DELEGATE_GROUP_SELECT],
                                    "values": [group.id, utterance.body],
                                }
                            )
                # Get suggestions from a non default bot
                else:
                    if query:
                        utterances = DelegateUtterance.objects.filter(
                            body__icontains=query, intent_id__isnull=False
                        ).order_by("-body")
                    else:
                        utterances = DelegateUtterance.objects.filter(intent_id__isnull=False)
                    skill_ids = []
                    for utterance in utterances:
                        intent = utterance.intent_id
                        skill = intent.skill_id
                        if BotDelegate.objects.filter(id=bot_delegate.id, skill_ids__in=[skill.id]):
                            if skill.id not in skill_ids:
                                skill_ids.append(skill.id)
                                suggestions.append(
                                    {
                                        "contexts": [CTX_START_SKILL],
                                        "body": intent.skill_id.name,
                                        "values": [skill.id],
                                    }
                                )

        suggestions.sort(key=lambda i: i["body"].lower())
        return suggestions

    # New Method
    def get_bot_delegate(self):
        channel = ActiveChannel.get_channel(self.user)
        return channel.bot_delegate_ids.first()

    # New Method
    def match_package(self, statement):
        delegate = self.get_bot_delegate()
        if not delegate:
            return
        confidence = delegate.confidence

        # DelegateUtterance
        utterances = DelegateUtterance.objects.filter(intent_id__isnull=False)
        if not utterances:
            return
        ud = UtteranceDistance(utterances.values_list("body", flat=True), statement.input)
        if ud.get_confidence() >= confidence:
            skill = utterances[ud.index].intent_id.skill_id
            return skill.package

    # @silk_profile(name="BotProcessor.post_message")
    def post_message(self, statement):
        if statement:
            sender_user = User.objects.filter(id=statement.uid).first()
            item = self.channel.post_message(
                sender_user, statement.text, data=statement.serialize()
            )
            self.message_ids.append(item)
            return item
        return False

    # @silk_profile(name="BotProcessor.process")
    def process(self, message):
        Log.info("BotProcessor.process", message)
        incoming_message = self.channel.post_message(self.user, message.body)
        for index in range(len(message.contexts)):
            context = message.contexts[index]
            value = message.values[index]

            bot_delegate = self.channel.bot_delegate_ids.first()
            if bot_delegate and bot_delegate.id != BotDelegate.get_default_bot().id:
                binder = BaseBinder(self, bot_delegate.user_id.id)
                if context == CTX_STANDARD_INPUT:
                    binder.select_processor(
                        InputStatement(
                            self.user.id,
                            flag=Flag.FLAG_STANDARD_INPUT,
                            input=value,
                            location=message.location,
                            text=message.body,
                        )
                    )
                    continue
                elif context == CTX_START_SKILL:
                    package = DelegateSkill.objects.filter(id=value).first().package
                    binder.select_processor(
                        InputStatement(
                            self.user.id,
                            flag=Flag.FLAG_START_SKILL,
                            input=package,
                            location=message.location,
                            text=message.body,
                        )
                    )
                    continue
                elif context == CTX_CANCEL_SKILL:
                    binder.select_processor(
                        InputStatement(
                            self.user.id,
                            flag=Flag.FLAG_CANCEL_SKILL,
                            input=value,
                            location=message.location,
                            text=message.body,
                        )
                    )
                    continue

            if context == CTX_STANDARD_INPUT:
                self.process_standard_input(message.body, value, location=message.location)
            elif context == CTX_START_SKILL:
                self.process_start_skill(message.body, value, location=message.location)
            elif context == CTX_BOT_DELEGATE_SELECT:
                self.process_bot_delegate_select(message.body, value)
            elif context == CTX_HUMAN_DELEGATE_SELECT:
                self.process_human_delegate_select(message.body, message.values)
            elif context == CTX_DELEGATE_GROUP_SELECT:
                self.process_delegate_group_select(message.body, message.values)
            elif context == CTX_CANCEL_SKILL:
                self.process_cancel_skill(message.body, value)

    # @silk_profile(name="BotProcessor.process_bot_delegate_select")
    def process_bot_delegate_select(self, body, value):
        if not self.is_authenticated:
            return

        bot_delegate = BotDelegate.objects.filter(id=value).first()
        channel = MailChannel.ensure_bot_delegate_channel(self.user, bot_delegate)
        ActiveChannel.set_channel(self.user, channel)
        self.channel = channel

    # @silk_profile(name="BotProcessor.process_cancel_skill")
    def process_cancel_skill(self, body, value):
        if not self.is_authenticated:
            return
        bot_delegate = self.channel.bot_delegate_ids.first()
        if bot_delegate:
            active_state = DelegateState.get_state(self.channel)
            if active_state:
                active_state.delete()
                stm = Statement(text=DEFAULT_CANCEL_MESSAGE, uid=bot_delegate.user_id.id)
                self.post_message(stm)

    # @silk_profile(name="BotProcessor.process_from_adapters")
    def process_from_adapters(self, value):
        active_delegate = self.channel.bot_delegate_ids.filter().first()
        default_delegate = BotDelegate.get_default_bot()
        composer = Composer()
        composer.default_response.add(
            Statement(default_delegate.get_default_response(), default_delegate.user_id.id)
        )
        response = composer.process(Statement(value, self.user.id), delegate=active_delegate)
        for statement in response.all():
            self.post_message(statement)

        # active_bot = self.channel.bot_delegate_ids.filter().first()
        # negative_result = False
        # for channel in MailChannel.get_channels(self.user):
        #     bot = channel.bot_delegate_ids.filter().first()
        #     if bot:
        #         result = self.process_from_bot(channel, bot, value)
        #         if result:
        #             negative_result = True
        # if not negative_result:
        #     statement = Statement(active_bot.default_response, active_bot.user_id.id)
        #     self.post_message(statement)

    def process_from_bot(self, channel, bot_delegate, value):
        logic_adapters = []
        bigbot_delegate = BotDelegate.get_default_bot()

        for ADAPTER in Preference.get_value("LOGICAL_ADAPTERS", LOGICAL_ADAPTERS):
            if ADAPTER["active"]:
                if bot_delegate.id == bigbot_delegate.id:
                    logic_adapters.append(
                        {"import_path": ADAPTER["package"], "delegate": bot_delegate}
                    )
                elif ADAPTER["package"] == "bigbot.adapter.CorpusAdapter":
                    logic_adapters.append(
                        {"import_path": ADAPTER["package"], "delegate": bot_delegate}
                    )

        threshold = bot_delegate.confidence / 100
        default_response = bot_delegate.get_default_response()

        chatbot = ChatBot(
            self.chatbot_name,
            read_only=True,
            logic_adapters=logic_adapters,
        )
        chatbot_statement = chatterbot.conversation.Statement(text=value)

        try:
            output = chatbot.get_response(chatbot_statement)
        except:
            return False

        if output.confidence >= threshold:
            statement = Statement(
                output.text, bot_delegate.user_id.id, confidence=output.confidence
            )
            self.post_message(statement)
            return True
        else:
            if bot_delegate.classification == BotDelegate.BIGBOT:
                delegate_finder = DelegateFinder(self.user)
                delegates_and_skill = delegate_finder.process(value)
                if delegates_and_skill:
                    self.delegate_suggestions(
                        bot_delegate, delegates_and_skill[0], delegates_and_skill[1]
                    )
                    return True
            pass
        return False

    # @silk_profile(name="BotProcessor.process_delegate_group_select")
    def process_delegate_group_select(self, body, values):
        group_id, message = values
        group = HumanDelegateGroup.objects.get(id=group_id)
        delegates = group.human_delegates.all()
        user_delegate = HumanDelegate.objects.filter(user_id=self.user).first()
        if delegates.count() > 0 and user_delegate:
            channel = MailChannel.objects.filter(human_delegate_ids__in=[user_delegate.id])
            for delegate in delegates:
                channel = channel.filter(human_delegate_ids__in=[delegate.id])
            channel = channel.first()

            if channel is None:
                channel = MailChannel.ensure_human_delegate_channel(self.user, delegates.first())
                for delegate in delegates[1:]:
                    channel.human_delegate_ids.add(delegate)
                default_bot = BotDelegate.get_default_bot()
                channel.bot_delegate_ids.add(default_bot)

            ActiveChannel.set_channel(self.user, channel)
            self.channel = channel
            self.channel.post_message(self.user, message)

    # @silk_profile(name="BotProcessor.process_human_delegate_select")
    def process_human_delegate_select(self, body, values):
        if not self.is_authenticated:
            return
        delegate_id, message = values
        human_delegate = HumanDelegate.objects.filter(id=delegate_id).first()
        channel = MailChannel.ensure_human_delegate_channel(self.user, human_delegate)
        ActiveChannel.set_channel(self.user, channel)
        self.channel = channel
        self.channel.post_message(self.user, message)

    # @silk_profile(name="process_skill")
    def process_skill(self, delegate, active_state, value, body):
        sp = SkillProcessor(self.user, delegate, active_state)
        stmt = sp.process(value, body)
        self.post_message(stmt)

    # @silk_profile(name="BotProcessor.process_standard_input")
    def process_standard_input(self, body, value, **kwargs):
        if not self.is_authenticated:
            self.process_from_adapters(value)
        default_bot = BotDelegate.get_default_bot()
        bot_delegate = self.channel.bot_delegate_ids.first()

        if self.channel.is_human_channel:
            # Humans
            binder = BaseBinder(self, default_bot.user_id.id)
            binder.select_processor(
                InputStatement(
                    self.user.id,
                    flag=Flag.FLAG_STANDARD_INPUT,
                    input=value,
                    location=kwargs.get("location"),
                    text=body,
                )
            )
            return

        if default_bot.id == bot_delegate.id:
            delegate_finder = DelegateFinder(self.user)
            delegates_and_skill = delegate_finder.process(value)
            if delegates_and_skill:
                self.delegate_suggestions(
                    bot_delegate, delegates_and_skill[0], delegates_and_skill[1]
                )
            else:
                binder = BaseBinder(self, bot_delegate.user_id.id)
                binder.select_processor(
                    InputStatement(
                        self.user.id,
                        flag=Flag.FLAG_STANDARD_INPUT,
                        input=value,
                        location=kwargs.get("location"),
                        text=body,
                    )
                )
                # self.process_from_adapters(value)
        else:
            active_state = DelegateState.get_state(self.channel)
            if active_state:
                if not self.attempt_cancellation(bot_delegate, active_state, value):
                    self.process_skill(bot_delegate, active_state, value, body)
            else:
                skill_finder = SkillFinder(self.user)
                skill = skill_finder.process(bot_delegate, value)
                if skill:
                    self.start_skill(bot_delegate, skill)
                else:
                    self.process_from_adapters(value)

    # @silk_profile(name="BotProcessor.process_start_skill")
    def process_start_skill(self, body, value, **kwargs):
        if not self.is_authenticated:
            return

        delegate_skill = DelegateSkill.objects.filter(id=value).first()

        if self.channel.is_human_channel:
            bot_delegate = BotDelegate.objects.filter(skill_ids__in=[value]).first()
            if bot_delegate:
                binder = BaseBinder(self, bot_delegate.user_id.id)
                binder.select_processor(
                    InputStatement(
                        self.user.id,
                        flag=Flag.FLAG_START_SKILL,
                        input=delegate_skill,
                        location=kwargs.get("location"),
                        text=body,
                    )
                )
                return

        bot_delegate = self.channel.bot_delegate_ids.first()
        default_bot = BotDelegate.get_default_bot()
        if bot_delegate.id == default_bot.id:
            delegate_finder = DelegateFinder(self.user)
            delegates_and_skill = delegate_finder.process(value, delegate_skill)
            if delegates_and_skill:
                self.delegate_suggestions(
                    bot_delegate, delegates_and_skill[0], delegates_and_skill[1]
                )
            else:
                # no possible unless wrong un associate suggestion clicked
                pass
        else:
            # This code is probaly no longer used
            active_state = DelegateState.set_skill(delegate_skill, self.channel)
            sp = SkillProcessor(self.user, bot_delegate, active_state)
            stmt = sp.start()
            self.post_message(stmt)

    def revoke_skill(self, delegate, active_state):
        sp = SkillProcessor(self.user, delegate, active_state)
        stmt = sp.start()
        self.post_message(stmt)

    def start_skill(self, delegate, skill):
        active_state = DelegateState.set_skill(skill, self.channel)
        sp = SkillProcessor(self.user, delegate, active_state)
        stmt = sp.start()
        self.post_message(stmt)
