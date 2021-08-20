import json
import re

from contrib.keycloak import KeycloakController
from main import Log


token_regex = re.compile(r"^bearer (?P<token>.+)$", re.I)


class KeycloakUserMiddleware:
    """Reads the keycloak access token from the request headers and sets the adds the user to the
    request object.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.META.get("HTTP_AUTHORIZATION")
        refreshed_token = None
        if token:
            match = token_regex.match(token)
            if match:
                token = match.group("token")
                user, refreshed_token = KeycloakController.authenticate(token)
                if user is not None:
                    request.keycloak_user = user
                else:
                    request.keycloak_user = None
        else:
            request.keycloak_user = None

        response = self.get_response(request)

        if refreshed_token:
            response["Access-Token"] = KeycloakController.encode_token(refreshed_token)

        return response
