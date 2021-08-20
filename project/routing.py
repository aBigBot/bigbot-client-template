from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import OriginValidator
from project.consumer import WebSocketConsumer,WebSocketDebug
from django.conf import settings

application = ProtocolTypeRouter({
    'websocket': OriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                [
                    path('', WebSocketConsumer),
                    path('debug/', WebSocketDebug),
                ]
            )
        ),
        settings.ALLOWED_HOSTS,
    )
})
