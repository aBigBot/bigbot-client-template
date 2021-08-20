import json
import threading

from silk.profiling.profiler import silk_profile

from core.models import DelegateSkill

from . import Log
from .Node import BaseNode, CancelNode, SearchNode, SkipNode
from .Statement import InputStatement


FLAG_CANCEL_SKILL = "FLAG_CANCEL_SKILL"
FLAG_DELEGATE_GROUP = "FLAG_DELEGATE_GROUP"
FLAG_HUMAN_DELEGATE = "FLAG_HUMAN_DELEGATE"
FLAG_SELECT_BOT_DELEGATE = "FLAG_SELECT_BOT_DELEGATE"
FLAG_SKILL_PROCESSOR = "FLAG_SKILL_PROCESSOR"
FLAG_STANDARD_INPUT = "FLAG_STANDARD_INPUT"
FLAG_START_SKILL = "FLAG_START_SKILL"


class FlagManager:
    def __init__(self):
        self.delegates = []
        self.groups = []
        self.package = ""

    def _get_delegates(self, binder, statement):
        self.package = binder.on_skill_intent(statement)

    def _get_package(self, binder, statement):
        self.delegates, self.groups = binder.process_utterance(statement)

    # @silk_profile(name="FlagManager.load")
    def load(self, binder, statement):
        bot = binder.get_bot()
        channel = binder.get_channel()
        node = statement.get_node()
        result = None
        state = binder.on_load_state()

        if channel.is_human_channel and not state.is_active():
            human_delegate = channel.human_delegate
            delegate, skill = binder.on_select_human_delegate_skill(human_delegate, statement)

            if statement.flag == FLAG_START_SKILL:
                if isinstance(statement.input, dict):
                    skill = statement.input.get_data()
                else:
                    skill = binder.on_get_skill(statement.input)
                result = (
                    InputStatement(statement.user_id, input=skill, text=statement.text),
                    FLAG_START_SKILL,
                )

            elif delegate and channel.bots_enabled:
                channel.bot_delegate_ids.add(delegate)
                binder.operator_id = delegate.user_id.id
                result = (
                    InputStatement(statement.user_id, input=skill.get_data(), text=statement.text),
                    FLAG_START_SKILL,
                )

            elif (
                not human_delegate.check_online_status()
                and human_delegate.offline_skill is not None
            ):
                skill = human_delegate.offline_skill
                bot_delegate = skill.bot_delegates.first()
                if bot_delegate:
                    channel.bot_delegate_ids.add(bot_delegate)
                    binder.operator_id = bot_delegate.id
                result = (
                    InputStatement(statement.user_id, input=skill.get_data(), text=statement.text),
                    FLAG_START_SKILL,
                )

            else:
                result = (statement, FLAG_STANDARD_INPUT)

        elif state.is_active():
            if statement.flag == FLAG_CANCEL_SKILL:
                result = (statement, FLAG_CANCEL_SKILL)
            elif binder.on_cancel_intent(statement):
                result = (statement, FLAG_CANCEL_SKILL)
            elif isinstance(node, SearchNode):
                child_node = node.get_node()
                if isinstance(child_node, CancelNode):
                    result = (statement, FLAG_CANCEL_SKILL)
                elif isinstance(node, SkipNode):
                    extra_stm = InputStatement(statement.user_id, text=statement.text)
                    result = (extra_stm, FLAG_SKILL_PROCESSOR)
                else:
                    extra_stm = InputStatement(
                        statement.user_id, input=node.data, text=statement.text
                    )
                    result = (extra_stm, FLAG_SKILL_PROCESSOR)
            else:
                result = (statement, FLAG_SKILL_PROCESSOR)

        if result is None:
            if statement.flag == FLAG_START_SKILL:
                package = statement.input
                if isinstance(package, DelegateSkill):
                    skill = package.get_data()
                else:
                    skill = binder.on_get_skill(package)
                    if skill:
                        skill = skill.get_data()

                if skill:
                    extra_stm = InputStatement(statement.user_id, input=skill, text=statement.text)

                    result = (extra_stm, FLAG_START_SKILL)
            else:
                package_thread = threading.Thread(
                    target=self._get_package, args=[binder, statement]
                )
                package_thread.start()

                delegates_thread = threading.Thread(
                    target=self._get_delegates, args=[binder, statement]
                )
                delegates_thread.start()

                package_thread.join()
                delegates_thread.join()

                if self.package and channel.bots_enabled:
                    skill = binder.on_get_skill(self.package)
                    if skill:
                        delegates = skill.bot_delegates.all()
                        if not delegates.filter(id=bot.id).exists() and delegates.count() > 0:
                            extra_stm = InputStatement(
                                statement.user_id,
                                input={"delegates": delegates, "skill": skill},
                            )
                            result = (extra_stm, FLAG_SELECT_BOT_DELEGATE)
                        else:
                            extra_stm = InputStatement(
                                statement.user_id, input=skill.get_data(), text=statement.text
                            )
                            result = (extra_stm, FLAG_START_SKILL)
                elif self.delegates or self.groups:
                    result = (
                        {
                            "delegate_groups": self.groups,
                            "human_delegates": self.delegates,
                            "statement": statement,
                        },
                        FLAG_HUMAN_DELEGATE,
                    )
                else:
                    result = (statement, FLAG_STANDARD_INPUT)

        if result is None:
            result = (statement, FLAG_STANDARD_INPUT)

        return result
