import abc

from core.models import AppData


class AppConfig(abc.ABC):
    def __init__(self, source, *args, **kwargs):
        self.components = []
        self.data_exchange = []
        self.source = source
        self.variables = []
        self.init(source)

    def init(self, source):
        self.registry()

    @abc.abstractmethod
    def registry(self):
        pass

    def register(self, object):
        self.components.append(object)

    def register_data_exchange(self, component, name, description, input=None, output=None):
        """Registers a function for the data exchange API.

        Args:
            component (obj): The data exchange function.
            name (str): Human readable name for the function.
            description (str): Function's description.
            input (list):
            output (list):

        Example:
        """
        self.data_exchange.append(
            (
                component,
                f"{component.__module__}.{component.__name__}",
                name,
                description,
                input,
                output,
            )
        )

    def register_variable(self, component, key, description, type=str, value=None):
        """Registers a custom variable for the integration. Users will be able to set the value of
        the variable in the web interface.

        Variables will be accessible to the integration components through the instance method
        MyProvider.get_variable("my.component", "variable_key").

        Args:
            component (str): Integration's indetifier.
            key (str): Variable key.
            description (str): Key's description.
            type: Variable type. Can be one of the following built-in types: bool, dict float, int,
                list, or str. Any non valid type will be treated as a str. Defaults to str.
            value: (Optional) Initial value of the variable, must be an instance of type.

        Example:
            self.register_variable(
                "com.bigitsystems.wordpress",
                "FETCH_UNPUBLISHED",
                "Tells the bot to also fetch unpublished posts",
                bool,
                False,
            )
        """
        self.variables.append((component, key))
        AppData.put_data(component, key, type_=type, data=value, description=description)

    def remove_variables(self):
        """This method removes the registered variables when the integrations is uninstalled."""
        for component, key in self.variables:
            AppData.remove_data(component, key)
