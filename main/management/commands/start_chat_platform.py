import importlib
from subprocess import Popen

from django.core.management.base import BaseCommand, CommandError

from main.Component import ChatPlatform


class Command(BaseCommand):
    help = "Starts a valid ChatPlatform"

    def add_arguments(self, parser):
        parser.add_argument("component", help="Full to ChatPlatform component", type=str)

    def handle(self, *args, **kwargs):
        component = kwargs.get("component").split(".")
        module_path = ".".join(component[:-1])
        class_name = component[-1]
        module = importlib.import_module(module_path)
        bot_class = getattr(module, class_name)

        if not issubclass(bot_class, ChatPlatform):
            raise CommandError("Class is not an instance of ChatPlatform")

        bot = bot_class(None)
        bot.connect()
