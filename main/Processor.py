import json
import time

from silk.profiling.profiler import silk_profile

from main import Block, Log
from main.Intent import NLP
from main.Node import DelegatesNode
from main.Statement import OutputStatement, InputStatement


class BaseProcessor:
    def __init__(self):
        pass

    def on_process(self, binder, input):
        pass

    def get_context(self):
        return {"user": {"first_name": "Jonathan"}}


class CancelSkill(BaseProcessor):
    # @silk_profile(name="CancelSkill.on_process")
    def on_process(self, binder, input):
        state = binder.on_load_state()
        state.skill = None
        state.block_id = None
        state.data = {}
        state.extra = {}
        binder.on_save_state(state.serialize())

        output = OutputStatement(binder.on_load_state().operator_id)
        output.append_text("Your request has been cancelled.")
        binder.post_message(output)


class SkillProcessor(BaseProcessor):
    # @silk_profile(name="SkillProcessor.on_process")
    def on_process(self, binder, input, is_start=False):
        state = binder.on_load_state()
        block = Block.get_block_by_id(binder, state.skill, state.block_id)
        post_skill = None
        post_skill_action = 0
        post_skill_data = state.data
        result = None

        while True:
            if not result:
                processed = state.data.get("__processed__", [])
                if isinstance(block, Block.InputBlock):
                    processed = self.process_intents(binder, state, input)

                    if block.id in processed:
                        result = block.move()
                        state.block_id = result.connection
                        block = Block.get_block_by_id(binder, state.skill, result.connection)
                        if isinstance(block, Block.InputBlock) and not block.id in processed:
                            binder.on_save_state(state.serialize())
                            block.before_process(binder, state.operator_id)
                            break
                        result = None
                        continue

                    result = block.process(binder, state.operator_id, input)
                else:
                    result = block.process(binder, state.operator_id)

                if result.code != -1:
                    block.after_process(binder)

            if result.connection is None:
                state = binder.on_load_state()
                post_skill_action = result.block.property_value("action")
                post_skill_data = state.data
                post_skill_package = result.post_skill()
                post_skill_template = result.block.property_value("template", "")
                post_skill = binder.on_get_skill(post_skill_package)
                if post_skill:
                    post_skill = post_skill.get_data()
                state.skill = None
                state.block_id = None
                state.data = {}
                state.extra = {}
                binder.on_save_state(state.serialize())
                break

            else:
                state = binder.on_load_state()
                state.block_id = result.connection
                binder.on_save_state(state.serialize())
                block = Block.get_block_by_id(binder, state.skill, result.connection)
                if block.id not in processed:
                    result = block.before_process(binder, state.operator_id)
                    if isinstance(block, Block.InputBlock) and not result:
                        break
                else:
                    result = None

        if post_skill_action == 1:
            # start new chain skill
            post_skill_input = InputStatement(binder.on_load_state().user_id)
            post_skill_input.input = post_skill
            StartSkill().on_process(binder, post_skill_input)
        elif post_skill_action == 2:
            binder.on_hand_over_user(post_skill_package, post_skill_data, post_skill_template)
        elif post_skill_action == 3:
            binder.on_hand_over_group(post_skill_package, post_skill_data, post_skill_template)

    # @silk_profile(name="SkillProcessor.process_intents")
    def process_intents(self, binder, state, statement):
        """ """
        import importlib

        processed = state.data.get("__processed__", [])
        input = statement.text

        if not input:
            return processed, statement

        nlp = NLP.get_singleton()
        doc = nlp(input)

        for block_data in state.skill["blocks"]:
            block = Block.get_block_by_id(binder, state.skill, block_data["id"])
            if (
                block.id in processed
                or isinstance(block, Block.DecisionBlock)
                or not isinstance(block, Block.InputBlock)
            ):
                continue

            intent_component = block_data.get("intent")
            intent_kwargs = block_data.get("intent_properties", {})
            if intent_component is None:
                continue

            dot = intent_component.rfind(".")
            if dot == -1:
                Log.error("process_intents", "Indalid component", intent_component)
                processed.append(block.id)
                continue

            module = intent_component[:dot]
            component = intent_component[dot + 1 :]

            module = importlib.import_module(module)
            component = getattr(module, component)

            intent = component(__nlp__=nlp, **intent_kwargs)
            match = intent(doc)

            key = block.property_value("key")

            if match and key:
                processed.append(block.id)
                state.data[key] = match

        state.data["__processed__"] = processed
        binder.on_save_state(state.serialize())

        return processed


class SelectDelegate(BaseProcessor):
    def on_process(self, binder, input):
        delegates = input.input["delegates"]
        skill = input.input["skill"]

        node = DelegatesNode(
            [
                {
                    "body": d.name,
                    "contexts": [2, 4],
                    "image": d.user_id.get_avatar_url(),
                    "values": [d.id, skill.id],
                }
                for d in delegates
            ]
        )
        output = OutputStatement(binder.on_load_state().operator_id)
        output.append_node(node)
        binder.post_message(output)


class StandardInput(BaseProcessor):
    # @silk_profile(name="StandardInput.on_process")
    def on_process(self, binder, input):
        output = OutputStatement(binder.on_load_state().operator_id)
        final_output = binder.on_standard_input(input, output)
        if final_output:
            binder.post_message(final_output)


class StartSkill(BaseProcessor):
    # @silk_profile(name="StartSkill.on_process")
    def on_process(self, binder, input):
        skill = input.input

        state = binder.on_load_state()
        state.skill = skill
        state.block_id = skill["start"]
        binder.on_save_state(state.serialize())

        SkillProcessor().on_process(binder, input, True)
