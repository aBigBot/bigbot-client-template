from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import core.signals
        from core.views import _setup_instance_if_required

        try:
            _setup_instance_if_required()
        except Exception as e:
            print(e)
