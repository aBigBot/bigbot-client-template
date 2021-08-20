import glob
import base64
import json
import os
import random
import re
import uuid
import yaml

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic.base import View
import requests
from sendgrid import SendGridAPIClient
from silk.profiling.profiler import silk_profile

from bigbot.models import InputPattern, ResponsePhrase
from contrib import permissions, processor, utils
from contrib.Bigbot import BaseBinder
from contrib.exceptions import JsonRPCException
from contrib.decorators import authenticate_api, keycloak_authenticate, verify_jsonrpc
from contrib.http import JsonRPCResponse
from contrib.keycloak import KeycloakController
from contrib.manager import JsonRPC
from contrib.processor import BotProcessor
from contrib.statement import Statement
from core.signals import revoke_chat_user
from mail.models import MailService
from main import Binder, Log

from .models import (
    AccessToken,
    ActiveChannel,
    ApiKeys,
    AppData,
    Attachment,
    BotDelegate,
    DelegateState,
    HumanDelegate,
    Integration,
    OauthAccess,
    ServiceProvider,
    TTSAudio,
    User,
    UserOTP,
    UserProfile,
)


HOST_META_KEY = "HTTP_X_REAL_IP"


def _merge_user(request, uuid, token, public_user, user):
    access_token = AccessToken.create_token(user)
    revoke_chat_user.send(sender=access_token, public_user=public_user, user=user)
    pass


def _setup_instance_if_required():
    user_groups = ["bot", "manager", "operator", "cross", "public"]
    for user_group in user_groups:
        if not Group.objects.filter(name=user_group).exists():
            Group.objects.create(name=user_group)
    delegate = BotDelegate.get_default_bot()
    path = settings.BASE_DIR + "/data/corpus"
    for file in os.listdir(path):
        if file.endswith(".yml"):
            corpus_file = os.path.join(path, file)
            f = open(corpus_file)
            corpus_data = yaml.load(f)
            categories = corpus_data["categories"]
            conversations = corpus_data["conversations"]
            for record in conversations:
                res_1 = record[0]
                res_2 = record[1:]
                object = InputPattern.get_singleton(res_1)
                object.delegate_id = delegate
                object.save()
                for response in res_2:
                    responseObject = ResponsePhrase.get_singleton(response)
                    responseObject.delegate_id = delegate
                    responseObject.save()
                    object.response_ids.add(responseObject)


@csrf_exempt
@require_POST
@verify_jsonrpc({"method": ["login", "logout", "refresh"]})
def authenticate(request):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    result = None
    if method == "login":
        password = params.get("password")
        username = params.get("username")
        result, _ = KeycloakController.openid_token(username, password)
    elif method == "logout":
        access_token = params.get("access_token")
        result = KeycloakController.logout(access_token)
    elif method == "refresh":
        access_token = params.get("access_token")
        token = params.get("token")
        uuid = params.get("uuid")
        access_token = KeycloakController.decode_token(access_token)
        refreshed_token, user = KeycloakController.refresh_token(access_token)
        if refreshed_token is None:
            return JsonRPCResponse(error="Invalid access token", status=401)
        encoded_token = KeycloakController.encode_token(refreshed_token)
        credentials = AccessToken.get_or_create_keycloak_user(user, token, uuid)
        result = {
            "refreshed_token": encoded_token,
            "token": credentials.access_token,
            "uuid": credentials.access_uuid,
        }

    return JsonRPCResponse(result)


@require_http_methods(["GET", "POST"])
def chat_login(request, *args, **kwargs):
    from main.Node import AuthNode

    uuid = request.GET.get("uuid")
    token = request.GET.get("token")
    public_user = AccessToken.authenticate(uuid, token)
    if not public_user:
        return HttpResponse(status=403)
    if not public_user.groups.filter(name="public").exists():
        return HttpResponse(status=403)

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        access_token, user = KeycloakController.openid_token(email, password)
        if token:
            credentials = AccessToken.get_or_create_keycloak_user(user, token, uuid)
            auth_node = AuthNode(
                {
                    "access_token": access_token,
                    "token": credentials.access_token,
                    "uuid": credentials.access_uuid,
                }
            )
            channel = ActiveChannel.get_channel(public_user)
            channel.post_message(
                public_user,
                "AuthNode",
                False,
                {
                    "text": "",
                    "confidence": 0,
                    "contents": [auth_node.serialize()],
                    "tags": {},
                    "uid": 1,
                },
            )
            return HttpResponse()
        return HttpResponse(status=400)

    data = {
        "uuid": uuid,
        "token": token,
    }
    return render(request, "chat_login_page.html", data)


def chat_send_otp(request, *args, **kwargs):
    if request.method != "POST":
        return HttpResponse(status=503)

    uuid = request.POST.get("uuid")
    token = request.POST.get("token")
    public_user = AccessToken.authenticate(uuid, token)
    if not public_user and not public_user.groups.filter(name="public").exists():
        return HttpResponse(status=403)

    email = utils.get_email(request, "email")
    if not email:
        return HttpResponse(status=400)
    user = User.objects.filter(email=email).first()
    if user and not user.groups.filter(name="cross").exists():
        return HttpResponse(status=400)

    if not user:
        user = User.objects.create(email=email)
        user.groups.add(Group.objects.get(name="cross"))
        user.save()
    delegate = BotDelegate.get_default_bot()
    sender = delegate.user_id
    template = None
    data = None
    receipts = [user]
    otp = UserOTP.get_otp(user)
    content = utils.build_otp_mail_content(otp.otp)
    MailService.simple_send("One time password", content, user)
    return HttpResponse(status=200)


def chat_verify_otp(request, *args, **kwargs):
    if request.method != "POST":
        return HttpResponse(status=503)
    uuid = request.POST.get("uuid")
    token = request.POST.get("token")
    public_user = AccessToken.authenticate(uuid, token)
    if not public_user and not public_user.groups.filter(name="public").exists():
        return HttpResponse(status=403)

    email = utils.get_email(request, "email")
    password = utils.get_string(request, "password")
    if not email or not password:
        return HttpResponse(status=400)
    user = User.objects.filter(email=email).first()

    if user and not user.groups.filter(name="cross").exists():
        return HttpResponse(status=400)
    user = UserOTP.authenticate(email, password)
    if not user:
        return HttpResponse(status=403)
    _merge_user(request, uuid, token, public_user, user)
    return HttpResponse("OK", status=200)


@csrf_exempt
@require_POST
@keycloak_authenticate()
@verify_jsonrpc()
def common(request, *args, **kwargs):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]
    manager = JsonRPC(request.keycloak_user)
    result = getattr(manager, method)(*params[2:])
    return result


@csrf_exempt
@require_POST
# @silk_profile(name="views.consumer")
@verify_jsonrpc()
def consumer(request, *args, **kwargs):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]
    access_id = params[0]
    access_token = params[1]
    keycloak_user = request.keycloak_user
    user = AccessToken.authenticate(access_id, access_token, keycloak_user)
    if not user:
        return HttpResponse("Invalid credentials", status=401)
    manager = JsonRPC(user)
    callback = getattr(manager, method)
    if method == "authenticate":
        result = callback(access_id, access_token, keycloak_user)
        return JsonRPCResponse(result)
    elif method == "enable_bots":
        result = callback(keycloak_user, *params[2:])
    else:
        result = callback(*params[2:])
    return result


@csrf_exempt
@require_POST
def consumer_avatar(request, *args, **kwargs):
    files = request.FILES.getlist("file")
    user_uuid = request.POST.get("uuid")
    user_token = request.POST.get("token")
    user = AccessToken.authenticate(user_uuid, user_token)
    if user:
        return JsonRPCResponse("OK")
    return HttpResponse(status=405)


@csrf_exempt
def consumer_file(request, *args, **kwargs):
    if request.method == "POST":
        files = request.FILES.getlist("file")
        user_uuid = request.POST.get("uuid")
        user_token = request.POST.get("token")
        user = AccessToken.authenticate(user_uuid, user_token)
        if user:
            bp = BotProcessor(user)
            stm = Statement(text="", uid=user.id)
            message = bp.post_message(stm)
            for file in files:
                Attachment.add_message_file(message.message_id, file)

            message.save()

            return HttpResponse("OK")
    elif request.method == "GET":
        checksum = request.GET.get("checksum")
        file_uuid = request.GET.get("file_uuid")
        if checksum and file_uuid:
            return Attachment.get_message_file(checksum, file_uuid)
    return HttpResponse(status=405)


def consumer_test(request, *args, **kwargs):
    data = {}
    return render(request, "consumer_test.html", data)


@csrf_exempt
@require_POST
def create_superuser(request, *args, **kwargs):
    # if request.META[HOST_META_KEY] not in settings.TRUST_SERVERS:
    #     return HttpResponse(status=403)

    username = request.POST.get("username")
    if not username:
        return HttpResponse(status=400)
    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create(
            username=username,
            is_superuser=True,
            is_staff=True,
        )
        # user.set_password(password)
    user.save()
    token = AccessToken.create_token(user)
    data = {
        "uuid": token.access_uuid,
        "token": token.access_token,
    }
    return JsonResponse(data)


def custom_page_not_found_view(request, *args, **kwargs):
    return redirect(settings.REDIRECT_404)


@csrf_exempt
@require_POST
@keycloak_authenticate()
@verify_jsonrpc(
    {
        "method": [
            "data_exchange",
            "intents",
            "oauth_providers",
            "payment_providers",
            "skill_providers",
        ]
    }
)
def registry(request):
    """Returns data stored in the registry."""

    method = request.jsonrpc["method"]

    hd = HumanDelegate.get_by_keycloak_user(request.keycloak_user.id)
    processor = BotProcessor(hd.user_id)
    binder = BaseBinder(processor, None)
    registry = binder.local_registry()

    if method == "data_exchange":
        result = []

        for _, component, name, description, input_, output in registry.data_exchange:
            result.append(
                {
                    "component": component,
                    "description": description,
                    "input": input_,
                    "name": name,
                    "output": output,
                }
            )

        return JsonRPCResponse(result)

    if method == "intents":
        from main.Intent import all

        return JsonRPCResponse([i.serialize() for i in all])

    if method == "oauth_providers":
        from main.Component import OAuthProvider

        result = []

        for component in registry.components:
            if issubclass(component, OAuthProvider):
                result.append(
                    {
                        "text": component.__name__,
                        "value": f"{component.__module__}.{component.__name__}",
                    }
                )

        return JsonRPCResponse(result)

    if method == "payment_providers":
        from main.Component import PaymentProvider

        result = []

        for component in registry.components:
            if issubclass(component, PaymentProvider):
                result.append(
                    {
                        "text": component.__name__,
                        "value": f"{component.__module__}.{component.__name__}",
                    }
                )

        return JsonRPCResponse(result)

    if method == "skill_providers":
        from main.Component import SkillProvider

        result = []

        for component in registry.components:
            if issubclass(component, SkillProvider):
                result.append(
                    {
                        "text": component.__name__,
                        "value": f"{component.__module__}.{component.__name__}",
                    }
                )

        return JsonRPCResponse(result)

    return JsonRPCResponse(error="Invalid request", status=400)


@csrf_exempt
def getMiscCredentials(request, *args, **kwargs):
    return JsonResponse(
        [
            {
                "name": "AWS",
                "data": {
                    "region": "ap-southeast-1",
                    "IdentityPoolId": "ap-southeast-1:3ce438cc-3814-4b14-a505-9a465b61b7cc",
                },
            },
            {"name": "GOOGLE", "data": {"public": "", "private": ""}},
        ],
        safe=False,
    )


@csrf_exempt
def html_render(request, *args, **kwargs):
    from main.Component import state_from_response

    authorization_response = request.get_full_path()
    state = state_from_response(authorization_response)
    user_id = state["user_id"]
    operator_id = state["operator_id"]
    user = User.objects.get(id=user_id)
    bp = processor.BotProcessor(user)
    bb = BaseBinder(bp, operator_id)
    object = bb.get_registry().get_component(bb, state["component_name"])
    html = object.build_payment_page(bb, state)
    return HttpResponse(html)


@csrf_exempt
def info(request, *args, **kwargs):
    data = {"REMOTE_ADDR": request.META["REMOTE_ADDR"]}
    return JsonResponse(data)


@csrf_exempt
def instance_common_v1(request, *args, **kwargs):
    """View to setup the server

    Methods:
        invoke_super_access: Gives access to the instance to an external user.
            Params:
                - 0: None
                - 1: None
                - 2: Username (str)
                - 3: Password (str)
            Returns:
                A list with the API crendentials for the user.
                    - 0: API key (str)
                    - 1: API secret (str)
        setup: Creates the required database records for the proper functioning of the server.
            Params:
                - 0: API key (str)
                - 1: API secret (str)
    """

    if request.method != "POST":
        return HttpResponse(status=405)
    body = utils.get_body(request)
    jsonrpc_version = body["jsonrpc"]
    if jsonrpc_version != "2.0":
        return HttpResponse(status=400)
    method = body["method"]
    id = body["id"]
    params = body["params"]
    if method not in ["invoke_super_access", "setup"]:
        return HttpResponse("no such method " + method, status=400)

    # user = ApiKeys.authenticate(params[0],params[1])
    # if not user:
    #     return HttpResponse(status=401)
    # if not user.is_superuser:
    #     return HttpResponse(status=403)

    # eg. [API_KEY, API_SECRET, username, alias_email, password_key]
    if method == "invoke_super_access":
        username = params[2]
        password = params[3]
        user = User.objects.filter(
            username=username,
        ).first()
        if not user:
            user = User.objects.create(
                username=username,
            )
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        key = ApiKeys.get_key(user)
        data = {
            "api_key": key.api_key,
            "api_secret": key.api_secret,
        }
        return JsonResponse({"jsonrpc": "2.0", "result": data, "id": None})
    # eg. [API_KEY, API_SECRET]
    elif method == "setup":
        _setup_instance_if_required()
    return JsonResponse({"jsonrpc": "2.0", "result": True, "id": None})


@csrf_exempt
@require_POST
@keycloak_authenticate()
@verify_jsonrpc({"method": "execute_kw"}, 4)
def instance_object_v1(request, *args, **kwargs):
    if "multipart/form-data" in request.META.get("CONTENT_TYPE"):
        return instance_object_multipart_v1(request, *args, **kwargs)

    id = request.jsonrpc["id"]
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    model = params[2]
    model_method = params[3]
    if model not in [
        "app.data",
        "bot.delegate",
        "delegate.skill",
        "delegate.intent",
        "delegate.utterance",
        "keycloak.user",
        "input.pattern",
        "integration",
        "location.pattern",
        "response.phrase",
        "tts.audio",
        "user.group",
    ]:
        return JsonRPCResponse(error=f"Invalid model", status=403)

    try:
        result = JsonRPC(request.keycloak_user).execute_kw(model, model_method, params[4:], id)
        return JsonRPCResponse(result)
    except PermissionDenied as e:
        Log.error("instance_object_v1", e)
        return JsonRPCResponse(error=e, status=403)
    except Exception as e:
        Log.error("instance_object_v1", e)
        return JsonRPCResponse(error=e, status=400)


@csrf_exempt
@require_POST
def instance_object_multipart_v1(request, *args, **kwargs):
    if request.POST.get("jsonrpc") != "2.0":
        return HttpResponse("Invalid jsonrpc version", status=400)

    files = request.FILES.getlist("files", [])
    method = request.POST.get("method")
    params = json.loads(request.POST.get("params", "[]"))
    user = ApiKeys.authenticate(params[0], params[1])
    try:
        id = int(request.POST.get("id", "0"))
    except (TypeError, ValueError):
        id = 0

    if not user:
        return HttpResponse("Unauthorized", status=401)
    if not user.is_superuser:
        return HttpResponse("Forbidden", status=403)
    if method not in ["execute_kw"]:
        return HttpResponse('The method "{}" is not valid'.format(method), status=400)

    if len(params) < 4:
        return HttpResponse("Missing parameters", status=400)

    model = params[2]
    model_method = params[3]
    parameters = params[4:]

    if len(parameters) == 3:
        parameters = parameters[:1] + [parameters[1][0]["delegate"]["value"]] + parameters[1:]

    if model not in [
        "bot.delegate" "delegate.intent",
        "delegate.skill",
        "delegate.utterance",
        "input.pattern",
        "response.phrase",
    ]:
        return HttpResponse('The model "{}" is not valid'.format(model), status=403)

    index = 0
    try:
        for i, r in enumerate(parameters[2]):
            index = i
            if "file" in r:
                r["file"] = files[r["file"]]
    except IndexError:
        return HttpResponse(
            "Missing files, a ResponsePhrase requires a file that was not included in the request",
            status=400,
        )

    try:
        result = JsonRPC(request.keycloak_user).execute_kw(
            model, model_method, params[4:], id, user
        )
        return JsonRPCResponse(result)
    except PermissionDenied as e:
        return JsonRPCResponse(error=e, status=403)
    except Exception as e:
        return JsonRPCException(error=e, status=400)


@csrf_exempt
@require_GET
def media_image(request, *args, **kwargs):
    reference = int(request.GET.get("token"))
    if reference:
        reference = UserProfile.objects.get(id=reference)
        base64_img_bytes = reference.image.encode("utf-8")
        decoded_image_data = base64.decodebytes(base64_img_bytes)
        return HttpResponse(decoded_image_data, content_type="image/jpeg")
    return HttpResponse(status=400)


@csrf_exempt
def oauth_provider(request, *args, **kwargs):
    from contrib.application import OAuthProvider

    authorization_response = request.get_full_path()
    if request.method == "POST":
        body = utils.get_body(request)
        provider = OAuthProvider._dump_token_post(body, request)
    else:
        provider = OAuthProvider._dump_token(authorization_response, request)
    # temp
    active_channel = ActiveChannel.get_channel(provider.user)
    if active_channel:
        active_state = DelegateState.get_state(active_channel)
        if active_state:
            bot_delegate = active_channel.bot_delegate_ids.first()
            if bot_delegate:
                bp = processor.BotProcessor(provider.user)
                bp.revoke_skill(bot_delegate, active_state)
    #
    html = """<script>var obj = window.self;obj.opener = window.self;obj.close();</script>"""
    return HttpResponse(html)


@csrf_exempt
def oauth_redirect(request, *args, **kwargs):
    from main.Component import state_from_response

    authorization_response = request.get_full_path()
    # this is odoo oauth , this need to improve -----start-------
    if request.method == "POST":
        body = utils.get_body(request)
        authorization_response = (
            authorization_response
            + "?state="
            + body["state"]
            + "&access_token="
            + body["access_token"]
        )
    # ------end----------
    state = state_from_response(authorization_response)
    user_id = state["user_id"]
    operator_id = state["operator_id"]
    user = User.objects.get(id=user_id)
    bp = processor.BotProcessor(user)
    bb = BaseBinder(bp, operator_id)
    bb.notify_oauth_redirect(authorization_response)

    html = """<script>var obj = window.self;obj.opener = window.self;obj.close();</script>"""
    return HttpResponse(html)


@csrf_exempt
@require_POST
@keycloak_authenticate()
@verify_jsonrpc({"method": "execute_kw"}, 4)
def object(request, *args, **kwargs):
    id = request.jsonrpc["id"]
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    model = params[2]
    model_method = params[3]

    try:
        result = JsonRPC(request.keycloak_user).execute_kw(model, model_method, params[4:], id)
        return JsonRPCResponse(result)
    except PermissionDenied as e:
        return JsonRPCResponse(error=e, status=403)
    except Exception as e:
        return JsonRPCResponse(error=e, status=400)


@csrf_exempt
def payment_redirect(request, *args, **kwargs):
    from main.Component import state_from_response

    authorization_response = request.get_full_path()
    state = state_from_response(authorization_response)
    user_id = state["user_id"]
    operator_id = state["operator_id"]
    user = User.objects.get(id=user_id)
    bp = processor.BotProcessor(user)
    bb = BaseBinder(bp, operator_id)
    bb.notify_request(authorization_response)

    html = """<script>var obj = window.self;obj.opener = window.self;obj.close();</script>"""
    return HttpResponse(html)


@csrf_exempt
def proxy_jsonrpc(request, endpoint, method, *args, **kwargs):
    if endpoint not in ["common", "consumer"]:
        return HttpResponse(status=404)
    if request.method not in ["POST", "GET", "PUT", "DELETE"]:
        return HttpResponse(status=405)
    params = utils.get_body(request) or []

    if endpoint == "common":
        user = ApiKeys.authenticate(request.GET.get("API_KEY"), request.GET.get("API_SECRET"))
        if not user:
            return HttpResponse(status=401)
    elif endpoint == "consumer":
        user = AccessToken.authenticate(request.GET.get("uuid"), request.GET.get("token"))
        if not user:
            return HttpResponse(status=401)
    else:
        return HttpResponse(status=401)

    proxy_method = re.sub("(?<!^)(?=[A-Z])", "_", method).lower()
    manager = JsonRPC(user)
    result = getattr(manager, proxy_method)(*params)
    if isinstance(result, JsonResponse):
        return JsonResponse(json.loads(result.content)["result"], safe=False)
        pass
    return result


def response_media(request, id):
    """Returs a response linked media"""
    try:
        record = ResponsePhrase.objects.get(id=id)
    except ResponsePhrase.DoesNotExist:
        return HttpResponse("Response does not exist", status=404)

    if record.attachment is None:
        return HttpResponse("Response does not have any attachment", status=404)

    return HttpResponse(record.attachment.data, content_type=record.attachment.mime_type)


@csrf_exempt
def stack_setup(request, *args, **kwargs):
    # if request.method != 'POST':
    #     return HttpResponse(status=405)
    # if request.META[HOST_META_KEY] not in settings.TRUST_SERVERS:
    #     return HttpResponse(status=403)
    uuid = request.POST.get("uuid")
    token = request.POST.get("token")
    user = AccessToken.authenticate(uuid, token)
    # if not user:
    #     return HttpResponse(status=403)
    # if not user.is_superuser:
    #     return HttpResponse(status=401)
    user_groups = ["bot", "manager", "operator", "cross", "public"]
    for user_group in user_groups:
        if not Group.objects.filter(name=user_group).exists():
            Group.objects.create(name=user_group)
    delegate = BotDelegate.get_default_bot()
    path = settings.BASE_DIR + "/data/corpus"
    for file in os.listdir(path):
        if file.endswith(".yml"):
            corpus_file = os.path.join(path, file)
            f = open(corpus_file)
            corpus_data = yaml.load(f)
            categories = corpus_data["categories"]
            conversations = corpus_data["conversations"]
            for record in conversations:
                res_1 = record[0]
                res_2 = record[1:]
                object = InputPattern.get_singleton(res_1)
                object.delegate_id = delegate
                object.save()
                for response in res_2:
                    responseObject = ResponsePhrase.get_singleton(response)
                    object.response_ids.add(responseObject)

    return HttpResponse("OK", status=200)


@csrf_exempt
@require_POST
@verify_jsonrpc()
def standalone(request, *args, **kwargs):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]
    manager = JsonRPC(False)
    result = getattr(manager, method)(*params[2:])
    return result


def tts_audio(request):
    """Returns a records audio data.

    Arguments are passed on the query string.

    Args:
        API_KEY: REQUIRED. User's API key.
        API_SECRET: REQUIRED. User's API secret.
        uuid: REQUIRED.  UUID of the record.
        service: Service to generate the audio if it doesn't exist. 0 for Amazon
            Polly; 1 for Google TTS. Default: 0.
        engine: TTS engine to use: 'neural', or 'standard' (Amazon Polly Only).
        format: Format for the audio, is only used if the audio doesn't exist.
            Can be 'mp3' or 'ogg_vorgis'. Default:'mp3'.
        lang: Language code of the audio. Only used if the audio doesn't exist.
            Check the documentation for TTSAudio.generate_data for more details.
            Default: 'en-US'.
        voice: Voice of the audio. Only used if the audio doesn't exist. Check
            the documentation fro TTSAudio.generate_data for more details.
            Default: 'Joanna' for Amazon Polly; 'FEMALE' for Google TTS.
    """
    import botocore.exceptions
    from core.exceptions import TTSException
    from django.core.exceptions import ObjectDoesNotExist, ValidationError

    # api_key = request.GET.get('API_KEY')
    # api_secret = request.GET.get('API_SECRET')
    # user = ApiKeys.authenticate(api_key, api_secret)
    # if not user:
    #     return HttpResponse('Unauthorized', status=401)

    if request.method != "GET":
        return HttpResponse(status=405)
    uuid = request.GET.get("uuid", None)
    service = request.GET.get("service", TTSAudio.AMAZON_POLLY)

    kwargs = {}
    if "engine" in request.GET:
        kwargs["engine"] = request.GET["engine"]
    if "format" in request.GET:
        kwargs["format"] = request.GET["format"]
    if "lang" in request.GET:
        kwargs["lang"] = request.GET["lang"]
    if "voice" in request.GET:
        kwargs["voice"] = request.GET["voice"]

    if uuid is None:
        return HttpResponse("Request must include an UUID in the querystring", status=400)
    # Debug --- start---
    data, mimetype = TTSAudio.generate_data(uuid, service, **kwargs)
    return HttpResponse(data, content_type=mimetype)
    # ------end---------
    try:
        data, mimetype = TTSAudio.generate_data(uuid, service, **kwargs)
    except botocore.exceptions.BotoCoreError as e:
        print(e)
        return HttpResponse("Invalid AWS credentials", status=500)
    except ObjectDoesNotExist:
        return HttpResponse("Record does not exist", status=400)
    except TTSException:
        return HttpResponse("Unable to process data, please try again later", status=500)
    except ValidationError:
        return HttpResponse("UUID is not valid", status=400)
    except Exception as e:
        print("=" * 5, "ERROR:", type(e), "=>", e, "=" * 5)
        return HttpResponse("Unknown error", status=500)
    return HttpResponse(data, content_type=mimetype)


def version_view(request, *args, **kwargs):
    return HttpResponse(settings.RELEASE_VERSION)


TELEGRAM = "telegram"
WHATSAPP = "whatsapp"
UNKNOWN = None


@csrf_exempt
def webhook_view(request, *args, **kwargs):
    # instead of catching all webhook requests in one view
    # would dedicated view for each platform be better?
    listening_from = [TELEGRAM, WHATSAPP]  # maybe get these values from user setting
    integrated_apps = Integration.objects.filter(enabled=True)
    # should also check metadata of the request, e.g. HTTP_X_FORWARDED_FOR
    # but it's hard to keep track of ip addresses since they are expected to be changed frequently
    platform = _which_platform(request.body.decode("utf-8"))

    if platform is UNKNOWN:
        return HttpResponse("Cannot recognise sender origin", status=403)

    for app in integrated_apps:
        if app.label in listening_from and app.label == platform:
            if platform == TELEGRAM:
                from apps.telegram.component import TelegramWebhookListener

                token = AppData.get_data("com.big.bot.telegram", "BOT_TOKEN")
                telegram = TelegramWebhookListener(token)
                telegram.respond_to_event(request.body.decode("utf-8"))
            elif platform == WHATSAPP:
                pass
    return HttpResponse("OK", status=200)


def _which_platform(event):
    """Decides which platform webhook request is coming from"""
    event_obj = json.loads(event)

    if event_obj.get("update_id") and event_obj.get("message"):
        return TELEGRAM
    elif event_obj.get("messages"):
        return WHATSAPP
    else:
        return UNKNOWN
