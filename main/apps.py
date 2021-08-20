import os
import signal
import sys

from django.apps import AppConfig

from main import Log


class MainAppConfig(AppConfig):
    chat_bots = []
    name = "main"

    def ready(self):
        if not "manage.py" in sys.argv[0] or (len(sys.argv) >= 2 and sys.argv[1] == "runserver"):
            self.start_bots()

    def start_bots(self):
        from contrib.Bigbot import get_apps_sources
        from main.Component import ChatPlatform

        disabled = os.getenv("DISABLE_BOTS", False)
        if disabled:
            Log.debug("Bots disabled")
            return

        for source in get_apps_sources():
            try:
                app = source.get_application()
            except Exception as e:
                continue

            for component in app.components:
                if not issubclass(component, ChatPlatform):
                    continue

                component_path = f"{component.__module__}.{component.__name__}"

                exists = False
                for c, _ in MainAppConfig.chat_bots:
                    if c == component_path:
                        exists = True
                        break

                if exists:
                    continue

                bot = component(None)
                bot.connect()
                Log.debug("Bot started", component_path)
                MainAppConfig.chat_bots.append((component_path, bot))


def on_exit(*args, **kwargs):
    for i, item in enumerate(MainAppConfig.chat_bots):
        component, bot = item
        if bot:
            Log.debug("Stoping bot", component)
            MainAppConfig.chat_bots[i] = (component, None)
            bot.disconnect()
            Log.debug("Bot stopped", component)
    sys.exit()


signal.signal(signal.SIGINT, on_exit)
signal.signal(signal.SIGTERM, on_exit)
