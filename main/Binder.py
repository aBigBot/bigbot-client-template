import abc
from abc import ABC, abstractmethod
import json
import base64
from deprecated import deprecated
import urllib.parse as urlparse

from silk.profiling.profiler import silk_profile

from contrib.exceptions import JsonRPCException

from . import Flag, Log
from .Block import (
    get_block_by_id,
    DataExchange as DataExchangeBlock,
    DecisionBlock,
    GotoBlock,
    InputDate,
    InputDateTime,
    InputDuration,
    InputEmail,
    InputFile,
    InputLoop,
    InputNumber,
    InputOAuth,
    InputPayment,
    InputSearchable,
    InputSelection,
    InputSkill,
    InputText,
    InterpreterSkill,
    PromptBinary,
    PromptChatPlatform,
    PromptDate,
    PromptDateTime,
    PromptDuration,
    PromptPreview,
    PromptImage,
    PromptText,
    TerminalBlock,
    TimeoutBlock,
)
from .Component import (
    ChatPlatform,
    ChatProvider,
    DataExchange,
    PaymentProvider,
    state_from_response,
    user_id_from_state,
)
from .Flag import FlagManager
from .Node import PromiseNode
from .Processor import CancelSkill, SelectDelegate, SkillProcessor, StandardInput, StartSkill
from .Statement import InputStatement, OutputStatement


INPUT_BLOCKS = [
    DecisionBlock,
    InputDate,
    InputDateTime,
    InputDuration,
    InputEmail,
    InputFile,
    InputLoop,
    InputNumber,
    InputOAuth,
    InputPayment,
    InputSearchable,
    InputSelection,
    InputSkill,
    InputText,
    TimeoutBlock,
]
INTERPRETER_BLOCKS = [DataExchangeBlock, InterpreterSkill]
OTHER_BLOCKS = [GotoBlock, TerminalBlock]
PROMPT_BLOCKS = [
    PromptBinary,
    PromptChatPlatform,
    PromptDate,
    PromptDateTime,
    PromptDuration,
    PromptImage,
    PromptPreview,
    PromptText,
]


def _get_block_names(block_classes):
    data = []
    for item in block_classes:
        data.append(item.__module__ + "." + item.__name__)
    return data


def get_component(query, filter):
    data = []
    reg = Registry()
    for item in reg.components:
        data.append([item.get_name(), item.__name__])
    return data


def get_connections(component_name, properties):
    reg = Registry()
    for block in reg.blocks:
        if block.__module__ + "." + block.__name__ == component_name:
            block_object = block(None, None, None, None)
            return block_object.get_connections(properties)
    return None


class Registry:
    """A Registry instance keeps a record of all available blocks and components

    Attributes:
        blocks: Available blocks.
        components: Available components.
    """

    def __init__(self):
        self.blocks = []
        self.chat_platforms = []
        self.chat_providers = []
        self.components = []
        self.data_exchange = []

        self.blocks.extend(INPUT_BLOCKS)
        self.blocks.extend(INTERPRETER_BLOCKS)
        self.blocks.extend(PROMPT_BLOCKS)
        self.blocks.extend(OTHER_BLOCKS)

    def get_component(self, binder, component_name):
        """Returns a registered component if it exists.

        Args:
            binder: An instance of main.Binder.Binder
            component: The full name of the component, must include the component's package and
                module e.g. "apps.wordpress.WordpressComponent"

        Returns:
             The registered component if it exists, None otherwise.
        """
        for item in self.components:
            item_name = item.__module__ + "." + item.__name__
            if item_name == component_name:
                config = binder.on_get_component_config(item_name)
                return item(config)

    def get_data_exchange(self, binder, component_name):
        for de in self.data_exchange:
            if de[1] == component_name:
                return de[0](None)

    def payment_providers(self, binder):
        """Returns of all PaymentProviders available for binder

        Args:
            binder: An instance of main.Binder.Binder
        """
        array_list = []
        for item in self.components:
            item_name = item.__module__ + "." + item.__name__
            config = binder.on_get_component_config(item_name)
            object = item(config)
            if isinstance(object, PaymentProvider):
                array_list.append(object)
        return array_list

    def register(self, object):
        """Register a new component

        Args:
            object: An instance of main.Component.BaseComponent
        """
        if isinstance(object, ChatPlatform):
            self.chat_platforms.append(object)
        elif isinstance(object, DataExchange):
            self.data_exchange.append(component)
        else:
            self.components.append(object)

    def register_data_exchange(self, data_exchange):
        self.data_exchange.append(data_exchange)


class Binder(ABC):
    """A binder instance. This is an abstract class and should be extended.

    Attributes:
        html_render_url: Full URL to view used to render HTML templates generated by the skills.
        oauth_redirect_url: Full URL to view used to process OAuth requests.
        payment_redirect_url: Full URL to view used to process payment requests.
        registry: Registry instance.
    """

    def __init__(self, registry, **kwargs):
        self.html_render_url = kwargs.get("HTML_RENDER_URL")
        self.oauth_redirect_url = kwargs.get("OAUTH_REDIRECT_URL")
        self.payment_redirect_url = kwargs.get("PAYMENT_REDIRECT_URL")
        self.registry = registry

    def create_promise(self, user_id, operator_id):
        open_promise_node, close_promise_node = PromiseNode.create()

        create_promise = OutputStatement(operator_id)
        create_promise.append_node(open_promise_node)
        self.on_post_message(create_promise)

        close_promise = OutputStatement(operator_id)
        close_promise.append_node(close_promise_node)
        return close_promise

    @abc.abstractmethod
    def get_channel(self):
        """Should return current channel"""
        pass

    def get_registry(self):
        """Return registry instance"""
        return self.registry

    @deprecated(version="1.0.0", reason="You should use notify_request function")
    def notify_oauth_redirect(self, authorization_response, **kwargs):
        return self.notify_request(authorization_response, **kwargs)

    def notify_request(self, authorization_response, **kwargs):
        state = state_from_response(authorization_response, **kwargs)
        user_id = user_id_from_state(state)
        if user_id:
            input_input = authorization_response
            input_flag = Flag.FLAG_STANDARD_INPUT
            input = InputStatement(user_id, input=input_input, flag=input_flag)
            self.select_processor(input)

    @abc.abstractmethod
    def on_cancel_intent(self, statement):
        """Should check if statement can cancel an ongoing skill

        Args:
            statement: An instance of main.Statement.InputStatement

        Returns:
            bool: True if the skill can be canceled, False otherwise.
        """
        pass

    @abc.abstractmethod
    def on_context(self):
        """Context of user bot channel"""
        pass

    @abc.abstractmethod
    def on_get_component_config(self, component):
        """Should return an instance of core.models.ConfigModel linked to component

        Args:
            component (str): The full name of the component, must include it's packages and modules,
                e.g. "apps.wordpress.WordpressComponent"

        Returns:
            A ConfigModel instance or None if no instance exists.
        """
        pass

    @abc.abstractmethod
    def on_get_skill(self, package):
        """This method should return the skill definition as a JSON string.

        Args:
            package (str): Skill package identifier.
        """
        pass

    @abc.abstractmethod
    def on_human_delegate(self, statement, human_delegates):
        pass

    @abc.abstractmethod
    def on_load_oauth_token(self, component, user_id):
        """This method should return oauth token against component for user_id"""
        pass

    @abc.abstractmethod
    def on_load_state(self):
        """Should return the current state of the outgoing skill."""
        pass

    @abc.abstractmethod
    def on_post_message(self, statement):
        """Should post statement to the current channel.

        Args:
            statement: An instance of main.Statement.OutputStatement.
        """
        pass

    @abc.abstractmethod
    def on_save_oauth_token(self, component, user_id, token):
        """This method should save oauth token against component for user_id"""
        pass

    @abc.abstractmethod
    def on_save_state(self, state_json):
        """Should replace the current state with state_json

        Args:
            state_json (str): A JSON string with the new state.
        """
        pass

    @abc.abstractmethod
    def on_select_human_delegate(self, statement):
        """This method should return an instance of human delegate if statement should create a
        channel with the delegate.
        """
        pass

    @abc.abstractmethod
    def on_select_human_delegate_skill(self, human_delegate, statement):
        """This method should check if the statement triggers a skill, but the skills are limited to
        those processed by the bot delegates owned by the human delegate.

        Returns:
            list: A list of the skills triggered.
        """
        pass

    @abc.abstractmethod
    def on_skill_intent(self, statement):
        """Should check if statement triggers a skill.
        Args:
            statement: An instance of main.Statement.InputStatement.

        Returns:
            The skill package (str), or None if not skill was found.
        """
        pass

    @abc.abstractmethod
    def on_standard_input(self, input, output):
        """Should process an standard input statement.

        Args:
            input: An instance of main.Statemnet.InputStatement.
            output: An instance of main.Statement.OutputStatement.
        """

    def post_message(self, statement):
        """Post message to channel"""
        self.on_post_message(statement)

    @abc.abstractmethod
    def process_utterance(self, statement):
        """ """
        pass

    def search_query(self, query=None):
        """Triggers a query search in the current skill block."""
        state = self.on_load_state()
        if state.is_active():
            user_id = state.user_id
            client = get_block_by_id(self, state.skill, state.block_id)
            items = client.on_search(self, user_id, query)
            return items
        else:
            pass
        return []

    # @silk_profile(name="Binder.select_processor")
    def select_processor(self, input):
        """Starts the correct processor for the input statement.

        Args:
            input: An instance of main.Statement.StandardInput
        """
        if input.text:
            Log.message("Message", input.text)
        # get flag from input
        flag_manager = FlagManager()
        statement, flag = flag_manager.load(self, input)
        Log.debug("Flag Detection", flag)
        Log.debug("Statement", statement)

        # based on flag select processor
        if flag == Flag.FLAG_START_SKILL:
            channel = self.get_channel()
            channel.reset_fails()
            StartSkill().on_process(self, statement)
        elif flag == Flag.FLAG_HUMAN_DELEGATE:
            self.on_human_delegate(**statement)
        elif flag == Flag.FLAG_SKILL_PROCESSOR:
            SkillProcessor().on_process(self, statement)
        elif flag == Flag.FLAG_CANCEL_SKILL:
            CancelSkill().on_process(self, statement)
        elif flag == Flag.FLAG_SELECT_BOT_DELEGATE:
            SelectDelegate().on_process(self, statement)
        else:
            StandardInput().on_process(self, statement)
