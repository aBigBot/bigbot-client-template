from core.models import ApiKeys
from contrib.exceptions import JsonRPCException
from contrib.http import JsonRPCResponse
from contrib.utils import base64_decode, get_body
from main import Log


def authenticate_api(func):
    """Method decorator to authenticate the API credentials. If the authentication was successful
    the decorator removes the credentials from the request and adds the logged user to the jsonrpc
    object in the request:

    request.jsonrpc["user"] = user

    This decorator must be used after the verify_jsonrpc decorator:

    @verify_jsonrpc
    @authenticate_api
    def view(request):
        pass
    """

    def authenticate(request, *args, **kwargs):
        if request.method != "POST":
            return JsonRPCResponse(
                JsonRPCException(f"Invalid request method {request.method}"), status=405
            )

        try:
            params = request.jsonrpc.get("params", [])
            api_key = params[0]
            api_secret = params[1]
            user = ApiKeys.authenticate(api_key, api_secret)
            if not user:
                return JsonRPCResponse(error=JsonRPCException("Invalid credentials"), status=401)
            request.jsonrpc["params"] = params[2:]
            request.jsonrpc["user"] = user
            return func(request, *args, **kwargs)
        except Exception as e:
            return JsonRPCResponse(error=JsonRPCException("Could not read credentials"), status=401)

    return authenticate


def keycloak_authenticate(*permissions):
    """Checks if a keycloack user was logged in (done in the middleware) and if the user has the
    required permissions.

    Args:
        permissions (args): Name of the groups the user must belong to call the view.
    """

    def decorator(func):
        def authenticate(request, *args, **kwargs):
            keycloak_user = getattr(request, "keycloak_user", None)

            if keycloak_user is None:
                return JsonRPCResponse(error="Forbidden", status=401)

            for group in permissions:
                if not request.keycloak_user.in_group(group):
                    return JsonRPCResponse(error="Unauthorized", status=403)

            return func(request, *args, **kwargs)

        return authenticate

    return decorator


def verify_jsonrpc(match={}, params_length=None):
    """Method decorator. Verifies that the body of the request contains the neccesary JSONRPC
    fields. The JSONRPC object is added to the request if the verification succeeds.

    Args:
        match (dict): Any key in the dictionary must have a perfect match in the body. Defaults to
            an empty dictionary. If the field value is a list the body field must be one of the
            values in the list.
        params_length (int): Length of the params

    Example:
        @verify_jsonrpc()
        def view(request):
            # Body must have the fields "id", "jsonrpc", "method", and "params". "jsonrpc" must be
            # "2.0"
            # JSONRPC object is accesible in request.jsonrpc
            pass

        @verify_jsonrpc({"method": "executekw"})
        def another_view(request):
            # Similar to the previus example but "method" must also be equal to "executekw"
            pass
    """

    def decorator(func):
        def verify(request, *args, **kwargs):
            body = get_body(request)
            values = {**match, **{"jsonrpc": "2.0"}}

            if body:
                errors = []
                fields = ["id", "jsonrpc", "method", "params"]
                for key in body:
                    if key in fields:
                        fields.remove(key)
                        if (
                            key == "params"
                            and params_length
                            and len(body["params"]) < params_length
                        ):
                            errors.append(JsonRPCException("One ore more parameters missing"))
                        elif key in values and isinstance(values[key], list):
                            if body[key] not in values[key]:
                                errors.append(JsonRPCException(f"Invalid {key}"))
                        elif key in values:
                            if values[key] != body[key]:
                                errors.append(JsonRPCException(f"Invalid {key}"))
                    else:
                        errors.append(JsonRPCException(f"{key} is not a valid field."))
                if len(fields) > 0:
                    for key in fields:
                        errors.append(JsonRPCException(f"field '{key}' is required"))
                if errors:
                    return JsonRPCResponse(error=errors)
                request.jsonrpc = body
            else:
                return JsonRPCResponse(
                    error=JsonRPCException("Request does not contains a JSONRPC object")
                )

            return func(request, *args, **kwargs)

        return verify

    return decorator
