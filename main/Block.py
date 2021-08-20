from abc import ABC, abstractmethod
import base64
import datetime
import json
import random
import re
import urllib.parse as url_parse

from chatterbot.parsing import datetime_parsing
from django.conf import settings
from durations import Duration
from jinja2 import Template

from . import Log, Utils
from .Node import (
    BinaryNode,
    ChatPlatformNode,
    DateNode,
    DateTimeNode,
    DurationNode,
    IFrameNode,
    ImageNode,
    InputFileNode,
    ListSelectionNode,
    OAuthNode,
    PaymentNode,
    PreviewNode,
    SearchNode,
)
from .Statement import OutputStatement
from core.models import AppData
from contrib.utils import levenshtein_distance


BLOCK_REJECT = -1
BLOCK_ACCEPT = 0
BLOCK_MOVE = 1
BLOCK_MOVE_X = 2
BLOCK_MOVE_Y = 3
BLOCK_MOVE_Z = 4


def get_block_by_id(binder, skill, block_id):
    for item in skill["blocks"]:
        if item["id"] == block_id:
            for block in binder.get_registry().blocks:
                if item["component"] == block.__module__ + "." + block.__name__:
                    connections = item.get("connections")
                    return block(binder.on_context(), item["id"], item["properties"], connections)
            raise Exception(f"Component not matched: '{item['component']}'")
    raise Exception(f"Block not matched: '{block_id}'")


def get_block_by_property(binder, skill, key_name, key_value):
    for item in skill["blocks"]:
        for block in binder.get_registry().blocks:
            if item["component"] == block.__module__ + "." + block.__name__:
                connections = item.get("connections")
                block_obj = block(binder.on_context(), item["id"], item["properties"], connections)
                value = block_obj.property_value(key_name)
                if key_value == value:
                    return block_obj
    raise Exception("block_id or key not matched: " + key_value)


class BlockResult:
    def __init__(self, block, code, connection):
        self.block = block
        self.code = code
        self.connection = connection

    # def is_rejected(self):
    #     return self.code == BLOCK_REJECT

    @staticmethod
    def status(block, code, connection):
        return BlockResult(block, code, connection)

    def post_skill(self):
        if isinstance(self.block, TerminalBlock):
            return self.block.post_skill()


class BaseBlock(ABC):
    def __init__(self, context, id, properties, connections):
        self.component = self.__class__.__module__ + "." + self.__class__.__name__
        self.context = context
        self.id = id
        self.properties = properties
        self.connections = connections
        self.template_properties = []
        self.load_template()
        # should call after load template
        self.on_init()

    def accept(self):
        return BlockResult.status(self, BLOCK_ACCEPT, self.find_connection(BLOCK_ACCEPT))

    def after_process(self, binder):
        state = binder.on_load_state()
        processed = state.data.get("__processed__", [])
        if self.id not in processed:
            processed.append(self.id)
        state.data["__processed__"] = processed
        binder.on_save_state(state.serialize())

    def append_template_properties(self, properties):
        self.template_properties.extend(properties)

    def before_process(self, binder, operator_id):
        """This method should be called before any standard input is processed. Override this method
        to process data before the block is processed, for example sending a choice list to the user
        or verifying the state of an OAuth token.

        Args:
            binder: Instance of main.Binder.Binder.
            operator_id (int): Bot's Id.

        Returns:
            BlockResult: This function can return an instance of BlockResult of None. When an
                instance is returned the current block will be skipped for the next block in the
                connection.
        """
        pass

    def set_property(self, property, value):
        item = {"name": property, "value": value}
        if item in self.properties:
            self.properties[self.properties.index(item)] = item
        else:
            self.properties.append(item)

    def get_connections(self, properties):
        return []

    def get_meta(self):
        return self.meta

    def find_connection(self, code):
        if self.connections:
            for item in self.connections:
                if item[0] == code:
                    return item[1]

    def load_template(self):
        """this method for defining block properties"""
        pass

    def move(self):
        return BlockResult.status(self, BLOCK_MOVE, self.find_connection(BLOCK_MOVE))

    def move_x(self):
        return BlockResult.status(self, BLOCK_MOVE_X, self.find_connection(BLOCK_MOVE_X))

    def move_y(self):
        return BlockResult.status(self, BLOCK_MOVE_Y, self.find_connection(BLOCK_MOVE_Y))

    def move_z(self):
        return BlockResult.status(self, BLOCK_MOVE_Z, self.find_connection(BLOCK_MOVE_Z))

    @abstractmethod
    def on_descriptor(self):
        pass

    def on_init(self):
        """use this method as constructor"""
        pass

    def on_search(self, binder, user_id, query, **kwargs):
        return [SearchNode.wrap_cancel()]

    def property_value(self, key, default=None):
        for item in self.properties:
            name = item["name"]
            value = item["value"]
            if name == key:
                return value
        return default

    def reject(self):
        connection = self.find_connection(BLOCK_REJECT)
        if connection.lower() == "reject":
            connection = self.id
        return BlockResult.status(self, BLOCK_REJECT, connection)

    def remove_template_properties(self, name):
        for item in self.template_properties:
            if item["name"] == name:
                self.template_properties.remove(item)

    def serialize(self):
        return {
            "component": self.component,
            "descriptor": self.on_descriptor(),
            "template": self.template_properties,
            "connections": self.get_connections(self.properties),
        }


# ----------------------------------------------------------------------
# Input Blocks
# ----------------------------------------------------------------------


class InputBlock(BaseBlock):
    def before_process(self, binder, operator_id):
        prompt = self.property_value("prompt")
        if prompt:
            output = OutputStatement(operator_id)
            output.append_text(prompt)
            binder.post_message(output)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]

    def load(self, binder):
        """this method return value from state"""
        state = binder.on_load_state()
        key = self.property_value("key")
        return state.data.get(key)

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Key",
                    "name": "key",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
                {
                    "text": "Prompt",
                    "name": "prompt",
                    "format": "string",
                    "input_type": "textarea",
                    "required": False,
                    "auto": True,
                    "description": "Display text before processing block",
                    "value": None,
                },
                {
                    "text": "Required",
                    "name": "required",
                    "format": "boolean",
                    "input_type": "checkbox",
                    "required": True,
                    "description": "If set to false this property become optional.",
                    "value": False,
                },
            ]
        )

    @abstractmethod
    def on_process(self, binder, user_id, statement):
        return self.reject()

    def on_search(self, binder, user_id, query, **kwargs):
        required = self.property_value("required")
        if required is not None and not required:
            resources = super(InputBlock, self).on_search(binder, user_id, query, **kwargs)
            resources.extend([SearchNode.wrap_skip()])
            return resources
        return super(InputBlock, self).on_search(binder, user_id, query, **kwargs)

    def process(self, binder, user_id, statement):
        """by pass input validation while skip node given"""
        required = self.property_value("required")
        if not required and statement.input is None:
            self.save(binder, None)
            return self.move()
        return self.on_process(binder, user_id, statement)

    def save(self, binder, value):
        """Stores value in the skill state. The key used to store the value must be declared in the
        block properties:

        {
            ...
            "properties": [
                ...,
                {
                    "name": key",
                    "value": "my_key"
                }
            ]
        }
        """
        state = binder.on_load_state()
        key = self.property_value("key")
        state.data[key] = value
        binder.on_save_state(state.serialize())


class DecisionBlock(InputBlock):
    def after_process(self, binder):
        pass

    def before_process(self, binder, operator_id):
        super().before_process(binder, operator_id)
        connections = self.property_value("connections")
        node = ListSelectionNode(connections)
        output = OutputStatement(operator_id)
        output.append_node(node)
        binder.post_message(output)

    def get_connections(self, *args, **kwargs):
        return [[BLOCK_REJECT, "Reject"]]

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Prompt",
                    "name": "prompt",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "auto": True,
                    "description": "Display text before processing block",
                    "value": None,
                },
                {
                    "text": "Connections",
                    "name": "connections",
                    "format": "connections",
                    "input_type": "connections",
                    "required": True,
                    "unique": False,
                    "auto": True,
                    "decription": "Maps a list of options to blocks",
                    "value": [],
                },
            ]
        )

    def on_descriptor(self):
        return {
            "name": "Decission Block",
            "summary": "Decission tree block",
            "category": "input",
        }

    def on_process(self, binder, operator_id, statement):
        connections = self.property_value("connections")

        for connection in connections:
            if statement.input == connection["value"]:
                return BlockResult(self, BLOCK_MOVE, connection["value"])

            if levenshtein_distance(connection["text"], statement.text) > 0.9:
                return BlockResult(self, BLOCK_MOVE, connection["value"])

        return self.reject()

    def on_search(self, binder, user_id, query, **kwargs):
        connections = self.property_value("connections")
        result = super().on_search(binder, user_id, query, **kwargs)

        for connection in connections:
            if query.lower() in connection["text"].lower():
                result.append(SearchNode.wrap_text(connection["text"], connection["value"]))

        return result

    def property_value(self, key):
        if key == "required":
            return True
        return super().property_value(key)


class InputDate(InputBlock):
    def before_process(self, binder, operator_id):
        output = OutputStatement(operator_id)
        output.append_node(DateNode())
        binder.post_message(output)

    def on_descriptor(self):
        return {"name": "Date Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                result = datetime_parsing(statement.input)
                match, date, pos = result[0]
                self.save(binder, f"{date.strftime('%Y-%m-%dT%T')}.{int(date.microsecond/1000)}Z")
                return self.move()
            except Exception as e:
                output = OutputStatement(user_id)
                output.append_text("Sorry, I did not understand you")
                binder.post_message(output)


class InputDateTime(InputBlock):
    def before_process(self, binder, operator_id):
        output = OutputStatement(operator_id)
        output.append_node(DateTimeNode())
        binder.post_message(output)

    def on_descriptor(self):
        return {
            "name": "Date time Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                result = datetime_parsing(statement.input)
                match, date, pos = result[0]
                self.save(binder, f"{date.strftime('%Y-%m-%dT%T')}.{int(date.microsecond/1000)}Z")
                return self.move()
            except Exception as e:
                output = OutputStatement(user_id)
                output.append_text("Sorry, I did not understand you")
                binder.post_message(output)


class InputDuration(InputBlock):
    def before_process(self, binder, operator_id):
        output = OutputStatement(operator_id)
        output.append_node(DurationNode())
        binder.post_message(output)

    def on_descriptor(self):
        return {
            "name": "Duration Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                dur = Duration(statement.text.lower())
                if dur.to_seconds():
                    value = [int(dur.to_hours()), int(dur.to_minutes() % 60)]
                    self.save(binder, value)
                    return self.move()
            except Exception as e:
                Log.error("InputDuration.on_process", e)
        return super(InputDuration, self).on_process(binder, user_id, statement)


class InputEmail(InputBlock):
    def on_descriptor(self):
        return {"name": "Email Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            regex = "[a-z0-9]+[._]?[a-z0-9]+[@]\w+[.]\w{2,3}"
            match = re.search(regex, statement.input.lower())
            if match:
                self.save(binder, match.string[match.start() : match.end()])
                return self.move()
        return super(InputEmail, self).on_process(binder, user_id, statement)


class InputFile(InputBlock):
    """Sends an InputFileNode to the user, the user must return (or statement.input )a JSON object
    with the following structure:

    {
        "file": "file contents...",
        "file_name": "file_name.txt",
        "file_size": 156244,
    }

    Where:
        + file: File contents encoded as a base64 string:
            "data:<mime_type>;base64,<base64 string ...>"
        + file_name: File name.
        + file_size: Size of the file in bytes.
    """

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "File type",
                    "name": "accept",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "Valid file extensions",
                    "value": "",
                },
                {
                    "text": "Size",
                    "name": "size",
                    "format": "integer",
                    "input_type": "number",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "Maximum file size in bytes",
                    "value": 1000000,
                },
            ]
        )

    def before_process(self, binder, operator_id):
        accept = self.property_value("accept")
        size = self.property_value("size")
        output = OutputStatement(operator_id)
        output.append_node(InputFileNode({"accept": accept, "size": size}))
        binder.post_message(output)

    def on_descriptor(self):
        return {"name": "File Input", "summary": "Shows a file input field", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                file = statement.input["file"]
                file_name = statement.input["file_name"]
                file_size = statement.input["file_size"]
                max_size = int(self.property_value("size")) or 1000000
            except Exception as e:
                Log.error("InputFile.on_process", e)
                return self.reject()

            if max_size < file_size:
                output = OutputStatement(user_id)
                output.append_text(f"File should be smaller than {max_size} bytes")
                binder.post_message(output)
                return self.reject()

            base64_re = re.compile(r"^data:(?P<mimetype>[^;]+);base64,(?P<data>.+)$")
            match = base64_re.match(file)
            if match:
                self.save(binder, statement.input)
                return self.move()
        return self.reject()


class InputLoop(InputBlock):
    def before_process(self, binder, user_id):
        output = OutputStatement(user_id)
        loop_question = self.property_value("loop_question")
        if loop_question:
            output.append_text(text=loop_question)
        else:
            output.append_text(text="Do you want to add another?")
        binder.post_message(output)

    def on_descriptor(self):
        return {"name": "Loop Input", "summary": "Loop the blocks", "category": "input"}

    def load_template(self):
        super(InputLoop, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Loop question",
                    "name": "loop_question",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "Prompt text for loop",
                    "value": None,
                },
                {
                    "text": "Accept text",
                    "name": "accept_text",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "Text for accepting to start the loop",
                    "value": "Do you want to enter again?",
                },
                {
                    "text": "Skip text",
                    "name": "skip_text",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "Text for skipping the loop",
                    "value": "Skip",
                },
            ]
        )

    def on_process(self, binder, user_id, statement):
        state = binder.on_load_state()
        blocks = state.skill["blocks"]
        real_user_id = binder.on_load_state().user_id
        state_data = state.data
        key = self.property_value("key")

        if isinstance(statement, str):
            # TODO: compare the statement with yes or no and return the value
            item = statement
        else:
            item = statement.input
            # if loop data exists
            if state_data.get(key):
                data = {}
                data["loop_data"] = state_data[key]["loop_data"]
                data["loop_count"] = state_data[key]["loop_count"] + 1
                loop_data_keys = self._get_keys_from_blocks(binder, state.skill, blocks)
                for k in state_data.keys():
                    if k in loop_data_keys:
                        data["loop_data"][k].append(state_data[k])
                self.save(binder, data)
            # for first time loop
            else:
                data = {}
                data["loop_count"] = 1
                data["loop_data"] = {}
                loop_data_keys = self._get_keys_from_blocks(binder, state.skill, blocks)
                for k, v in state_data.items():
                    if k in loop_data_keys:
                        data["loop_data"][k] = [v]
                self.save(binder, data)
            # starts the loop
            if item == BLOCK_ACCEPT:
                return BlockResult.status(self, BLOCK_ACCEPT, self.find_connection(BLOCK_ACCEPT))
            # skips the loop
            else:
                return self.move()
        return super().on_process(binder, user_id, statement)

    def _get_keys_from_blocks(self, binder, skill, blocks):
        start_block_id = [
            start_block for state, start_block in self.connections if state == BLOCK_ACCEPT
        ][0]
        end_block_id = self.id
        temp_block = get_block_by_id(binder, skill, start_block_id)

        loop_keys = []
        while temp_block.id != end_block_id:
            for block_property in temp_block.properties:
                if block_property["name"] == "key":
                    loop_keys.append(block_property["value"])
            next_block_id = [
                next_block for state, next_block in temp_block.connections if state == BLOCK_MOVE
            ][0]
            temp_block = get_block_by_id(binder, skill, next_block_id)
        return loop_keys

    def on_search(self, binder, user_id, query, **kwargs):
        accept_text = self.property_value("accept_text")
        skip_text = self.property_value("skip_text")
        selections = [SearchNode.wrap_text(skip_text, 1), SearchNode.wrap_text(accept_text, 0)]
        suggestions = super(InputLoop, self).on_search(binder, user_id, query, **kwargs)
        selections.extend(suggestions)
        return selections


class InputNumber(InputBlock):
    def on_descriptor(self):
        return {"name": "Number Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            if isinstance(statement.input, int) or isinstance(statement.input, float):
                self.save(binder, statement.input)
                return self.move()
        return super(InputNumber, self).on_process(binder, user_id, statement)


class InputOAuth(InputBlock):
    def before_process(self, binder, operator_id):
        user_id = binder.on_load_state().user_id
        oauth = self.oauth(binder, user_id)

        if oauth:
            return self.move()

        component_name = self.property_value("component")
        component = binder.get_registry().get_component(binder, component_name)
        authorization_url = component.get_authorization_url(binder, user_id)
        output = OutputStatement(operator_id)
        output.append_text("Please authenticate your account")
        output.append_node(OAuthNode(authorization_url, component._meta))
        binder.post_message(output)

    def oauth(self, binder, user_id):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        return component_object.authenticate(binder, user_id)

    def on_descriptor(self):
        return {"name": "OAuth Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, operator_id, input):
        authorization_response = input.input
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        on_redirect = component_object.on_redirect(binder, authorization_response)
        if on_redirect:
            return self.move()
        return self.reject()

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "search",
                    "search_filter": "OAuthProvider",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                }
            ]
        )

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Accept"], [BLOCK_REJECT, "Reject"]]


class InputPayment(InputBlock):
    def before_process(self, binder, operator_id):
        real_user_id = binder.on_load_state().user_id
        amount = self.property_value("amount")
        currency_code = "USD"
        meta = {
            "charge_summary": "You have to pay",
            "currency_code": currency_code,
            "currency_symbol": "$",
            "button_text": "Pay " + str(amount) + " " + currency_code,
            "payment_services": [],
        }
        objects = binder.get_registry().payment_providers(binder)
        for component_object in objects:
            payment_url = component_object.get_payment_url(
                binder, real_user_id, amount, currency_code
            )
            payment_method = component_object.get_meta()
            # need improvement for including such meta
            if "name" not in payment_method:
                payment_method["name"] = "None"
            elif "icon" not in payment_method:
                payment_method["icon"] = "https://commons.wikimedia.org/wiki/File:PayPal.svg"
            payment_method["payment_url"] = payment_url
            meta["payment_services"].append(payment_method)
        payment_node = PaymentNode(amount, meta)
        output = OutputStatement(operator_id)
        output.append_node(payment_node)
        binder.post_message(output)

    def on_init(self):
        super(InputPayment, self).on_init()
        self.remove_template_properties("required")

    def on_descriptor(self):
        return {"name": "Payment Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, input):
        try:
            authorization_response = input.input
            params = Utils.parse_params(authorization_response)
            component_name = params["component"]
            component_object = binder.get_registry().get_component(binder, component_name)
            on_redirect = component_object.on_redirect(binder, authorization_response)
            if on_redirect:
                return self.move()
        except:
            pass
        return self.reject()

    def load_template(self):
        pass

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]


class InputSearchable(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Searchable Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        real_user_id = binder.on_load_state().user_id

        if isinstance(statement, str):
            query = statement
            item = component_object.on_query_search(
                binder, real_user_id, package, self, query, skill=state.skill
            )
            if item:
                valid = component_object.on_verify_input(
                    binder, real_user_id, package, self, item, skill=state.skill
                )
                if valid:
                    self.save(binder, item)
                    return self.move()
        else:
            item = statement.input
            if item:
                valid = component_object.on_verify_input(
                    binder, real_user_id, package, self, item, skill=state.skill
                )
                if valid:
                    self.save(binder, item)
                    return self.move()

        return super().on_process(binder, user_id, statement)

    def load_template(self):
        super(InputSearchable, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "search",
                    "search_filter": "SkillProvider",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
                {
                    "text": "Model",
                    "name": "model",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
            ]
        )

    def on_search(self, binder, user_id, query, **kwargs):
        real_user_id = binder.on_load_state().user_id
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]
        result = component_object.on_search(
            binder, real_user_id, package, self, query, skill=state.skill
        )
        resources = super(InputSearchable, self).on_search(binder, user_id, query, **kwargs)
        resources.extend(result)
        return resources


class InputSelection(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Selection Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            if self._in_selection(statement):
                value = statement.input
                self.save(binder, value)
                return self.move()
            fuzzy_item = self._fuzzy_item(statement)
            if fuzzy_item:
                value = fuzzy_item
                self.save(binder, value)
                return self.move()
        return super(InputSelection, self).on_process(binder, user_id, statement)

    def load_template(self):
        super(InputSelection, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Selections",
                    "name": "selections",
                    "format": "json",
                    "input_type": "textarea",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": [["draft", "Draft"]],
                }
            ]
        )

    # def get_connections(self, properties):
    #     connections = super(InputBlock, self).get_connections(properties)
    #     for idx, val in enumerate(self.property_value('selections')):
    #         pass
    #     return connections

    def _in_selection(self, statement):
        for item in self.property_value("selections"):
            if item[0] == statement.input:
                return True
        return False

    def _fuzzy_item(self, statement):
        for item in self.property_value("selections"):
            if item[1].lower() == statement.input.lower():
                return item[0]
        return None

    def on_search(self, binder, user_id, query, **kwargs):
        result = []
        for index, item in enumerate(self.property_value("selections")):
            txt, val = item[1], item[0]
            if query.lower() in txt.lower():
                result.append(SearchNode.wrap_text(txt, val))
        resources = super(InputSelection, self).on_search(binder, user_id, query, **kwargs)
        resources.extend(result)
        return resources


class InputSkill(InputBlock):
    """ """

    def before_process(self, binder, operator_id):
        component_name = self.property_value("component")
        component = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        component_object.before_process(
            binder, operator_id, package, state.data, properties=self.properties, skill=state.skill
        )

    def on_descriptor(self):
        return {"name": "Skill Input", "summary": "Passes user input to skill", "category": "input"}

    def on_process(self, binder, user_id, statement):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        result = component_object.on_execute(
            binder,
            user_id,
            package,
            state.data,
            statement,
            properties=self.properties,
            skill=state.skill,
        )
        if result:
            self.context["result"] = result
            self.context["input"] = state.data
            nodes = self.property_value("nodes")
            if nodes:
                output = OutputStatement(user_id)
                for item in nodes:
                    if item["node"] == "big.bot.core.iframe":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_node(IFrameNode(html))
                        binder.post_message(output)
                    elif item["node"] == "big.bot.core.text":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_text(html)
                        binder.post_message(output)
            return self.move()
        return super().on_process(binder, user_id, statement)

    def on_search(self, binder, user_id, query):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        try:
            result = component_object.on_search(
                binder,
                user_id,
                package,
                state.data,
                query,
                properties=self.properties,
                skill=state.skill,
            )
        except Exception as e:
            Log.error("InputSkill.on_search", e)
            result = [SearchNode.wrap_cancel()]

        return result

    def load_template(self):
        super(InputSkill, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Output Nodes",
                    "name": "nodes",
                    "format": "json",
                    "input_type": "nodes",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": [],
                }
            ]
        )


class InputText(InputBlock):
    def on_descriptor(self):
        return {"name": "Text Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            self.save(binder, statement.input)
            return self.move()
        return super(InputText, self).on_process(binder, user_id, statement)


# ----------------------------------------------------------------------
# Interpreter Blocks
# ----------------------------------------------------------------------


class InterpreterBlock(BaseBlock):
    def __init__(self, context, id, properties, connections):
        super(InterpreterBlock, self).__init__(context, id, properties, connections)
        self.context = context
        self.id = id
        self.properties = properties
        self.connections = connections

    @abstractmethod
    def on_process(self, binder, user_id):
        return self.move_x()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Accept"], [BLOCK_MOVE_X, "Reject"]]

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                }
            ]
        )


class DataExchange(InterpreterBlock):
    def on_descriptor(self):
        return {
            "category": "exchange",
            "name": "Data Exchange",
            "summary": "Calls a data exchange component",
        }

    def on_process(self, binder, operator_id):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_data_exchange(binder, component_name)
        state = binder.on_load_state()
        data = state.data
        package = state.skill["package"]

        input = self.property_value("input")
        if input:
            tmp = {}
            for from_, to in input:
                tmp[to] = data.get(from_)
            input = tmp
        else:
            input = {}

        result = component_object(binder, operator_id, package, data, **input)

        output = self.property_value("output")
        if output and result:
            for from_, to in output:
                data[to] = result.get(from_)
        elif result:
            for key in result:
                data[key] = result[key]

        state.data = data
        binder.on_save_state(state.serialize())

        return self.move()

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Input Data",
                    "name": "input",
                    "format": "json",
                    "input_type": "nodes",
                    "required": False,
                    "description": "Input data for the exchange function",
                    "value": [],
                },
                {
                    "text": "Output Data",
                    "name": "output",
                    "format": "json",
                    "input_type": "nodes",
                    "required": False,
                    "description": "Input data for the exchange function",
                    "value": [],
                },
            ]
        )


class InterpreterSkill(InterpreterBlock):
    def on_descriptor(self):
        return {
            "name": "Skill Interpreter",
            "summary": "This block runs logic.",
            "category": "interpreter",
        }

    def on_process(self, binder, user_id):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        result = component_object.on_execute(
            binder, user_id, package, state.data, properties=self.properties, skill=state.skill
        )
        if result:
            self.context["result"] = result
            self.context["input"] = state.data
            # self.save(binder, result)
            nodes = self.property_value("nodes")
            if nodes:
                output = OutputStatement(user_id)
                for item in nodes:
                    if item["node"] == "big.bot.core.text":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_text(html)
                        binder.post_message(output)
                    elif item["node"] == "big.bot.core.iframe":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_node(IFrameNode(html))
                        binder.post_message(output)
                    pass
            return self.move()
        return super().on_process(binder, user_id)

    def load_template(self):
        super(InterpreterSkill, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Output Nodes",
                    "name": "nodes",
                    "format": "json",
                    "input_type": "nodes",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": [],
                }
            ]
        )


# ----------------------------------------------------------------------
# Prompt Blocks
# ----------------------------------------------------------------------


class PromptBlock(BaseBlock):
    @abstractmethod
    def on_process(self, binder, user_id):
        return self.move()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"]]


class PromptBinary(PromptBlock):
    def before_process(self, binder, operator_id):
        property = "binary"
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Binary", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        binary = self.property_value("binary")
        output = OutputStatement(user_id)
        output.append_node(BinaryNode(binary))
        binder.post_message(output)
        return super(PromptBinary, self).on_process(binder, user_id)

    def load_template(self):
        super(PromptBinary, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Binary",
                    "name": "binary",
                    "format": "binary",
                    "input_type": "file",
                    "file_limit": 50000,
                    "mime_types": ["*/*"],
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
                {
                    "auto": False,
                    "description": "If set, reads the property from the data instead",
                    "format": "string",
                    "input_type": "text",
                    "name": "read",
                    "required": False,
                    "text": "Read",
                    "unique": True,
                    "value": None,
                },
            ]
        )


class PromptChatPlatform(PromptBlock):
    def before_process(self, binder, operator_id):
        pass
        # property = "telegram_bot_username"
        # data = binder.on_load_state().data
        # read_property = self.property_value("read")
        # if read_property and property:
        #     value = data.get(read_property)
        #     self.set_property(property, value)

    def on_descriptor(self):
        return {
            "name": "Chat Platforms",
            "summary": "No description available",
            "category": "prompt",
        }

    def on_process(self, binder, user_id):
        # load value from template for further integrations
        real_user_id = binder.on_load_state().user_id
        # base64 encode user id as payload
        # need a better value than user id for payload because user can fake the id
        payload = json.dumps({"user": real_user_id}, separators=(",", ":"))
        b64_bytes = base64.b64encode(payload.encode("utf-8"))
        payload = b64_bytes.decode("utf-8")

        bot_username = AppData.get_data("com.big.bot.telegram", "BOT_USERNAME")
        whatsapp_business_phone = AppData.get_data(
            "com.big.bot.whatsapp", "WA_BUSINESS_PHONE_NUMBER"
        )
        data = {}
        data["platforms"] = []
        meta = {"header": "Available Platforms", "button_text": "Chat now"}
        if bot_username:
            icon = open(settings.BASE_DIR + "/static/images/telegram.png", "rb")
            icon_bytes = base64.b64encode(icon.read())
            icon.close()
            data["platforms"].append(
                {
                    "name": "Telegram",
                    "icon": "data:image/png;base64," + icon_bytes.decode("utf-8"),
                    "url": "https://t.me/" + bot_username + "?start=" + payload,
                }
            )

        if whatsapp_business_phone:
            icon = open(settings.BASE_DIR + "/static/images/whatsapp.png", "rb")
            icon_bytes = base64.b64encode(icon.read())
            icon.close()
            payload_text = "[{}] Let's continue our chat.".format(payload)
            payload_text = url_parse.quote(payload_text)
            data["platforms"].append(
                {
                    "name": "WhatsApp",
                    "icon": "data:image/png;base64," + icon_bytes.decode("utf-8"),
                    "url": "https://wa.me/" + whatsapp_business_phone + "?text=" + payload_text,
                }
            )

        if len(data["platforms"]) > 0:
            chat_platform = ChatPlatformNode(data, meta)
            output = OutputStatement(user_id)
            output.append_node(chat_platform)
            binder.post_message(output)
        return super(PromptChatPlatform, self).on_process(binder, user_id)

    def load_template(self):
        super(PromptChatPlatform, self).load_template()
        # self.append_template_properties(
        #     [
        #         {
        #             "text": "Telegram Bot Username",
        #             "name": "telegram_bot_username",
        #             "format": "string",
        #             "input_type": "text",
        #             "required": True,
        #             "description": "<Description of property.>",
        #             "value": "",
        #         },
        #     ]
        # )


class PromptDate(PromptBlock):
    def before_process(self, binder, operator_id):
        property = ""
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Date", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DateNode(None))
        binder.post_message(output)
        return super(PromptDate, self).on_process(binder, user_id)

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Date",
                    "name": "date",
                    "format": "time",
                    "input_type": "date",
                    "unique": False,
                    "auto": False,
                    "description": "Date",
                }
            ]
        )


class PromptDateTime(PromptBlock):
    def before_process(self, binder, operator_id):
        property = ""
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Date Time", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DateTimeNode(None))
        binder.post_message(output)
        return super(PromptDateTime, self).on_process(binder, user_id)


class PromptDuration(PromptBlock):
    def before_process(self, binder, operator_id):
        property = ""
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Date Time", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DurationNode(None))
        binder.post_message(output)
        return super(PromptDuration, self).on_process(binder, user_id)


class PromptImage(PromptBlock):
    def before_process(self, binder, operator_id):
        property = "image"
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Image", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        image = self.property_value("image")
        output = OutputStatement(user_id)
        output.append_node(ImageNode(image))
        binder.post_message(output)
        return super(PromptImage, self).on_process(binder, user_id)

    def load_template(self):
        super(PromptImage, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Image",
                    "name": "image",
                    "format": "binary",
                    "input_type": "file",
                    "file_limit": 50000,
                    "mime_types": ["image/jpeg", "image/png", "image/gif"],
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
                {
                    "auto": False,
                    "description": "If set, reads the property from the data instead",
                    "format": "string",
                    "input_type": "text",
                    "name": "read",
                    "required": False,
                    "text": "Read",
                    "unique": True,
                    "value": None,
                },
            ]
        )


class PromptPreview(PromptBlock):
    def before_process(self, binder, operator_id):
        property = "url"
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"category": "prompt", "name": "Preview", "summary": "Previews a URL"}

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "test": "URL",
                    "name": "url",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "",
                    "value": "https://example.com",
                },
                {
                    "auto": False,
                    "description": "If set, reads the property from the data instead",
                    "format": "string",
                    "input_type": "text",
                    "name": "read",
                    "required": False,
                    "text": "Read",
                    "unique": True,
                    "value": None,
                },
            ]
        )

    def on_process(self, binder, user_id):
        url = self.property_value("url")
        output = OutputStatement(user_id)
        output.append_node(PreviewNode(url))
        binder.post_message(output)
        return super().on_process(binder, user_id)


class PromptText(PromptBlock):
    def before_process(self, binder, operator_id):
        property = "primary_text"
        data = binder.on_load_state().data
        read_property = self.property_value("read")
        if read_property and property:
            value = data.get(read_property)
            self.set_property(property, value)

    def on_descriptor(self):
        return {"name": "Text", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_text(self._get_display_text())
        binder.post_message(output)
        return super(PromptText, self).on_process(binder, user_id)

    def load_template(self):
        super(PromptText, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Text Primary",
                    "name": "primary_text",
                    "format": "array",
                    "input_type": "textarea",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": [],
                },
                {
                    "auto": False,
                    "description": "If set, reads the property from the data instead",
                    "format": "string",
                    "input_type": "text",
                    "name": "read",
                    "required": False,
                    "text": "Read",
                    "unique": True,
                    "value": None,
                },
            ]
        )

    def _get_display_text(self):
        value = self.property_value("primary_text")
        if type(value) == str:
            pattern = value
        else:
            pattern = random.choice(value)
        template = Template(pattern)
        html = template.render(self.context)
        return html


# ----------------------------------------------------------------------
# Terminal Blocks
# ----------------------------------------------------------------------


class TerminalBlock(BaseBlock):
    def on_descriptor(self):
        return {
            "name": "Terminate",
            "summary": "This block terminate the workflow.",
            "category": "default",
        }

    def process(self, binder, user_id):
        return self.move()

    def get_connections(self, properties):
        return []

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Post Action",
                    "name": "action",
                    "format": "enum",
                    "input_type": "select",
                    "required": True,
                    "description": "<Description of property.>",
                    "enum": [
                        {"name": "Do Nothing", "value": 0},
                        {"name": "Start Skill", "value": 1},
                        {"name": "Hand over user", "value": 2},
                        {"name": "Hand over group", "value": 3},
                    ],
                    "value": 0,
                },
                {
                    "text": "Post Skill",
                    "name": "post_skill",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "description": "<Description of property.>",
                    "value": None,
                },
                {
                    "text": "Template",
                    "name": "template",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "description": "Template used when handing over a skill",
                    "value": "",
                },
            ]
        )

    def post_skill(self):
        return self.property_value("post_skill")


# ----------------------------------------------------------------------
# Special Blocks
# ----------------------------------------------------------------------


class GotoBlock(BaseBlock):
    def get_connections(self):
        return []

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Block ID",
                    "name": "block",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "Block ID",
                    "value": None,
                }
            ]
        )

    def on_descriptor(self):
        return {
            "name": "GOTO Block",
            "summary": "Navigates to a specific block.",
            "category": "other",
        }

    def on_process(self, binder, user_id, statement):
        block = self.property_value("block")
        return BlockResult(self, BLOCK_MOVE, block)


class TimeoutBlock(InputBlock):
    def before_process(self, binder, operator_id):
        import threading

        key = f"__running_{self.id}__"
        state = binder.on_load_state()
        running = state.data.get(key)

        if running is None:
            state.data[key] = True
            binder.on_save_state(state.serialize())
            thread = threading.Thread(target=self.timeout, args=[binder])
            thread.start()

    def get_connections(self):
        return [[BLOCK_MOVE, "Next"], [BLOCK_MOVE_X, "ON_TIMEOUT"]]

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Delay time",
                    "name": "delay",
                    "format": "float",
                    "input_type": "number",
                    "required": True,
                    "description": "Delay time",
                    "value": 5.0,
                },
                {
                    "text": "Skip if input",
                    "name": "skip",
                    "format": "enum",
                    "input_type": "select",
                    "required": False,
                    "description": "Skip execution if user received a response from a delegate",
                    "enum": [
                        {"name": "Do not skip", "value": 0},
                        {"name": "Skip if any input", "value": 1},
                        {"name": "Skip if delegate input", "value": 2},
                    ],
                    "value": 0,
                },
                {
                    "text": "Block ID",
                    "name": "block",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "description": "Jump to this block if skip is set",
                    "value": None,
                },
            ]
        )

    def on_descriptor(self):
        return {
            "name": "Timeout Block",
            "summary": "Delays the new block",
            "category": "other",
        }

    def on_process(self, binder, user_id, statement):
        return BlockResult(self, BLOCK_REJECT, self.id)

    def timeout(self, binder):
        from main.Processor import SkillProcessor
        from main.Statement import InputStatement

        delay = self.property_value("delay")
        skip = self.property_value("skip")

        time.sleep(delay)

        block_id = None
        for connection in self.connections:
            if connection[0] == BLOCK_MOVE:
                block_id = connection[1]
                break

        state = binder.on_load_state()
        state.block_id = block_id
        binder.on_save_state(state.serialize())
        statement = InputStatement(binder.user_id, input=state.skill)

        processor = SkillProcessor()
        processor.on_process(binder, statement)
