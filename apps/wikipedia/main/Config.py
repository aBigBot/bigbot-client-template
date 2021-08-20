import abc


class AppConfig(abc.ABC):
    def __init__(self, source=None, *args, **kwargs):
        self.components = []
        self.intents = []
        self.source = source
        self.init(source)

    def init(self, source):
        self.registry()

    def link_intent(self, intent, component, kwargs={}):
        self.intents.append((intent(), component, kwargs))

    @abc.abstractmethod
    def registry(self):
        pass

    def register(self, object):
        self.components.append(object)

    def register_variable(self, component, key, description, type=str, value=None):
        pass
