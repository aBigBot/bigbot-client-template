import random

from chatterbot import ChatBot
from chatterbot.conversation import Statement as ChatterbotStatement
from mathparse import mathparse
import nltk
from silk.profiling.profiler import silk_profile

from bigbot.models import InputPattern, ResponsePhrase
from contrib.utils import FakeQuery
from core.models import BotDelegate, DelegateUtterance
from main import Log
from main.Component import ChatProvider
from main.Intent import NLP
from main.Node import BaseNode, ListSelectionNode
from main.Statement import OutputStatement
from main.Utterance import UtteranceDistance


class BigbotCorpus(ChatProvider):
    # @silk_profile(name="BigbotCorpus.can_process")
    def can_process(self, binder, statement, *args, **kwargs):
        return True

    # @silk_profile(name="BigbotCorpus.on_match_object")
    def on_match_object(self, binder, statement, *args, **kwargs):
        patterns = InputPattern.objects.all()
        if patterns:
            ud = UtteranceDistance(patterns.values_list("string", flat=True), statement.input)
            best_match = patterns[ud.index]
            Log.info("best_match", best_match)
            Log.info("best distance", ud.get_distance())
            # matched object
            return ud.get_distance(), best_match
        # No match
        return 0.0, None

    # @silk_profile(name="BigbotCorpus.process")
    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        phrases = match_object.response_ids.filter(delegate_id__isnull=False).filter(
            delegate_id__confidence__lte=threshold * 100
        )
        if phrases:
            responses_mapping = {}
            for phrase in phrases:
                delegate_id = str(phrase.delegate_id.id)
                if delegate_id not in responses_mapping:
                    responses_mapping[delegate_id] = []
                responses_mapping[delegate_id].append(phrase)
            for key, phrases in responses_mapping.items():
                phrase = random.choice(phrases)
                output = OutputStatement(phrase.delegate_id.user_id.id)
                raw_nodes = phrase.get_nodes()
                for item in raw_nodes:
                    node = BaseNode.deserialize(item)
                    if node:
                        output.append_node(node)
                binder.post_message(output)
        else:
            # move this logic to dedicated adapter
            channel = binder.get_channel()
            delegate = channel.bot_delegate_ids.filter(user_id=binder.operator_id).first()
            default_bot = BotDelegate.get_default_bot()
            if delegate is None:
                delegate = channel.bot_delegate_ids.first()
            fails = channel.increment_fail(delegate)
            if fails >= 3 and not channel.is_human_channel and delegate.id != default_bot.id:
                binder.on_send_fail_message(delegate)
            elif not channel.is_human_channel:
                output = OutputStatement(binder.operator_id)
                output.append_text(delegate.get_default_response())
                binder.post_message(output)


class BigbotUtterances(ChatProvider):
    """This ChatProvider checks if the user input is similar to an existing utterance"""

    def can_process(self, binder, statement, *args, **kwargs):
        if statement.text:
            return True
        return False

    def on_match_object(self, binder, statement, *args, **kwargs):
        nlp = NLP.get_singleton()

        bot = BotDelegate.objects.filter(user_id=binder.operator_id).first()
        if bot is None:
            return 0.0, None

        default_bot = BotDelegate.get_default_bot()
        if default_bot.id == bot.id:
            utterances = DelegateUtterance.objects.filter(intent_id__isnull=False)
        else:
            utterances = []
            skills = bot.skill_ids.all()
            for skill in skills:
                skill_utterances = skill.linked_utterances()
                for u in skill_utterances:
                    utterances.append(u)

        doc = nlp(statement.text)
        result = []

        for u in utterances:
            d = nlp(u.body)
            similarity = doc.similarity(d)
            if similarity * 100 >= bot.confidence:
                result.append((similarity, u))

        result.sort(key=lambda i: i[0], reverse=True)
        result = result[:5]

        Log.debug("BigbotUtterances", "result", result)

        if len(result) > 0:
            return result[0][0], result

        return 0.0, None

    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        from main.Processor import StartSkill
        from main.Statement import InputStatement

        bot = BotDelegate.objects.filter(user_id=binder.operator_id).first()
        default_bot = BotDelegate.get_default_bot()
        output = OutputStatement(binder.operator_id)

        output.append_text("Did you mean one of these:")
        data = [
            {
                "text": i[1].body,
                "value": i[1].body,
            }
            for i in match_object
        ]
        node = ListSelectionNode(data)
        output.append_node(node)

        binder.post_message(output)


class BigbotMathematical(ChatProvider):
    # @silk_profile(name="BigbotMathematical.can_process")
    def can_process(self, binder, statement, *args, **kwargs):
        return True

    # @silk_profile(name="BigbotMathematical.on_match_object")
    def on_match_object(self, binder, statement, *args, **kwargs):
        chatbot = ChatBot(
            "chatbot",
            read_only=True,
            logic_adapters=["chatterbot.logic.MathematicalEvaluation"],
            initialize=False,
        )
        try:
            output = chatbot.get_response(ChatterbotStatement(statement.input))
            return output.confidence, output.text
        except Exception as e:
            pass
        return 0.0, None

    # @silk_profile(name="BigbotMathematical.process")
    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        output = OutputStatement(binder.operator_id)
        output.append_text(match_object)
        binder.post_message(output)


class BigbotUnitConversion(ChatProvider):
    # @silk_profile(name="BigbotUnitConversion.can_process")
    def can_process(self, binder, statement, *args, **kwargs):
        return True

    # @silk_profile(name="BigbotUnitConversion.on_match_object")
    def on_match_object(self, binder, statement, *args, **kwargs):
        chatbot = ChatBot(
            "chatbot",
            read_only=True,
            logic_adapters=["chatterbot.logic.UnitConversion"],
            initialize=False,
        )
        try:
            output = chatbot.get_response(ChatterbotStatement(statement.input))
            return output.confidence, output.text
        except Exception as e:
            pass
        return 0, None

    # @silk_profile(name="BigbotUnitConversion.process")
    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        output = OutputStatement(binder.operator_id)
        output.append_text(match_object)
        binder.post_message(output)
