from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, JsonResponse
from silk.profiling.profiler import silk_profile

from contrib.http import JsonRPCResponse
from contrib.message import Message
from contrib.processor import BotProcessor
from core.models import (
    AccessToken,
    ActiveChannel,
    ArchivedChannel,
    BotDelegate,
    HumanDelegate,
    MailChannel,
    MailMessage,
    LocationPattern,
    OauthAccess,
    Preference,
    User,
)
from main import Log

from . import mixin


class JsonRPC:
    def __init__(self, user):
        self.user = user
        self.request = mixin

    # -----CHECKED-----------
    #  BOT-Consumer user can call this JS
    # @silk_profile()
    def authenticate(self, uuid, token, keycloak_user=None):
        if keycloak_user is None:
            return {"token": token, "uuid": uuid}
        credentials = AccessToken.get_or_create_keycloak_user(keycloak_user, token, uuid)
        return {"token": credentials.access_token, "uuid": credentials.access_uuid}

    # @silk_profile()
    def close_channel(self, channel_id):
        """ """
        try:
            channel = MailChannel.objects.get(id=channel_id)
        except:
            return JsonRPCResponse(error="Channel does not exists", status=400)

        channels = MailChannel.get_channels(self.user)
        active_channel = ActiveChannel.get_channel(self.user)
        if channels.count() <= 1:
            return JsonRPCResponse(error="Can not archive only active channel", status=400)

        human_delegate = HumanDelegate.objects.filter(user_id=self.user).first()
        if human_delegate is None:
            return JsonRPCResponse(error="User is not part of channel", status=400)

        archived_channel = ArchivedChannel.objects.filter(channel=channel, user=self.user).first()
        if archived_channel is not None:
            return JsonRPCResponse(error="Channel already is archived", status=400)

        archived_channel = ArchivedChannel.objects.create(channel=channel, user=self.user)

        if active_channel.id == channel_id:
            channels = channels.exclude(id__in=[channel_id])
            ActiveChannel.set_channel(self.user, channels.first())

        return JsonRPCResponse(True)

    #  API-KEYS bearer user should call
    # @silk_profile()
    def create_authenticated_user(
        self, username, first_name, provider, access_token, refresh_token=None, expired_in=0
    ):
        # if not self.in_group(['manager']):
        #     return HttpResponse(status=403)
        record = User.objects.filter(username=username).first()
        if not record:
            record = User.objects.create(username=username, first_name=first_name)
        else:
            record.first_name = first_name
        record.groups.add(self.get_group("cross"))
        record.save()
        item = AccessToken.create_token(record)
        OauthAccess.add_oauth(record, provider, access_token, refresh_token, expired_in)
        return self.response(item.serialize())

    # @silk_profile()
    def create_public_user(self, first_name):
        # if not self.in_group(['manager']):
        #     return HttpResponse(status=403)
        record = User.objects.create(first_name=first_name)
        record.groups.add(self.get_group("public"))
        record.save()
        item = AccessToken.create_token(record)
        return self.response(item.serialize())

    # @silk_profile()
    def create_public_standalone(self, first_name):
        record = User.objects.create(first_name=first_name)
        record.groups.add(self.get_group("public"))
        record.save()
        item = AccessToken.create_token(record)
        return self.response(item.serialize())

    #  API-KEYS bearer user should call
    # @silk_profile()
    def delete_user(self, username):
        # if not self.in_group(['manager']):
        #     return HttpResponse(status=403)
        target = User.objects.filter(username=username).first()
        if not target:
            return HttpResponse(status=400)
        target.delete()
        return self.response("OK")

    # @silk_profile()
    def enable_bots(self, keycloak_user, channel_id, enable):
        # TODO: Check if user has permissions or is owner of the channel
        try:
            channel = MailChannel.objects.get(id=channel_id)
            channel.bots_enabled = enable
            channel.save()
            return JsonRPCResponse(enable)
        except Exception as e:
            Log.error("disable_bots", e)
            return JsonRPCResponse(error=e, status=400)

    # RPC
    # @silk_profile()
    def execute_kw(self, model, method, params, id=None):
        """Methods:

        * create: Creates a database record.
            + Params:
                - 0: Values (dict) - New record values, e.g. {"field": "value", ...}
        * name_search: Search if record's name field cotains the query. Only works if the Model has
          a CharField or TextField called name.
            + Params:
                - 0: query (str)
        * read: Returns a single database record.
            + Params:
                - 0: Id (int) - Record's id.
        * search_count: This method seems unfinished.
        * search_read: Returns multiple database records.
            + Params:
                - 0: filter (list) - List of Django filters, e.g. [["id__in", [1, 2, 3]], ...]
                - 1: limit (int) - Number of records ro return, 0 = all
                - 2: offset (int) - Records offset
                - 3: sort (list) - List, e.g ["id", "asc"]
        * unlink: Deletes a database record
            + Params:
                - 0: Id (int) - Record's id.
        * write: Updates a databse record.
            + Params:
                - 0: Id (int) - Record's id.
                - 1: Values (dict) - Updated record fields, e.g. {"field": "value", ...}

        Any other method not listed must be defined in the Model.
        """
        if method == "create":
            record = self.request.env(model).create(params[0])
            if record:
                return record.id

        elif method == "name_search":
            return self.request.env(model).name_search(params[0])

        elif method == "read":
            result = self.request.env(model).read(params[0])
            if result:
                fields = params[1]["fields"] if (len(params) == 2 and "fields" in params[1]) else []
                return result.serialize(fields)

        elif method == "search_count":
            return self.request.env(model).search_count()

        elif method == "search_read":
            result = []
            fields = params[1]["fields"] if (len(params) == 2 and "fields" in params[1]) else []
            limit = params[1]["limit"] if (len(params) == 2 and "limit" in params[1]) else 0
            offset = params[1]["offset"] if (len(params) == 2 and "offset" in params[1]) else 0
            sort = (
                params[1]["sort"] if (len(params) == 2 and "sort" in params[1]) else ["id", "desc"]
            )
            for item in self.request.env(model).search(params[0], limit, offset, sort):
                result.append(item.serialize(fields))
            return result

        elif method == "unlink":
            for item in params[0]:
                obj = self.request.env(model).read(item)
                obj.unlink()
            return True

        elif method == "write":
            record = self.request.env(model).read(params[0])
            if record:
                return record.write(params[1])

        else:
            if not id:
                class_ = self.request.env(model, option="name_to_class")
                self.request.check_permissions(self.user, class_.Permissions, "all")
                if len(params) == 1 and isinstance(params[0], dict):
                    return getattr(class_, method)(**params[0])
                elif isinstance(params, list):
                    return getattr(class_, method)(*params)

        return False

    # @silk_profile()
    def get_active_channel(self, current_page_url=None):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        if current_page_url:
            match_location_patten = LocationPattern.match_location(location=current_page_url)
            if match_location_patten:
                if match_location_patten.type == "BOT":
                    bot_delegate = match_location_patten.get_resource()
                    if bot_delegate:
                        bot_channel = MailChannel.ensure_bot_delegate_channel(
                            self.user, bot_delegate
                        )
                        ActiveChannel.set_channel(self.user, bot_channel)
                elif match_location_patten.type == "HUMAN":
                    human_delegate = match_location_patten.get_resource()
                    if human_delegate:
                        human_channel = MailChannel.ensure_human_delegate_channel(
                            self.user, human_delegate
                        )
                        ActiveChannel.set_channel(self.user, human_channel)

        item = ActiveChannel.get_channel(self.user)
        return self.response(item.serialize(self.user))

    # @silk_profile()
    def get_archived_channels(self, params: dict = {}):
        page = params.get("page", 1)
        per_page = params.get("per_page", 20)
        channels = ArchivedChannel.objects.filter(user=self.user).order_by("-channel__updated_at")
        count = channels.count()
        channels = channels[(page - 1) * per_page : page * per_page]
        data = [c.channel.serialize(self.user) for c in channels]
        return JsonRPCResponse(
            {
                "channels": data,
                "has_more": page * per_page < count,
                "page": page,
                "per_page": per_page,
            }
        )

    #  BOT-Consumer user can call this JS
    # @silk_profile()
    def get_channels(self):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        data = []
        for item in MailChannel.get_channels(self.user):
            data.append(item.serialize(self.user))
        return self.response(data)

    # @silk_profile()
    def get_group(self, name):
        group = Group.objects.get(name=name)
        return group

    #  BOT-Consumer user can call this JS
    # @silk_profile()
    def get_messages(self, channel_uuid, page=1, per_page=20):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        channel = MailChannel.find_channel(self.user, channel_uuid)
        if not channel:
            return HttpResponse(status=403)
        data = []
        try:
            message_page = Paginator(channel.get_messages(), per_page).page(page)
        except EmptyPage:
            return self.response(
                {"messages": [], "has_next_page": False, "page": page, "per_page": per_page}
            )
        for item in message_page.object_list:
            data.append(item.serialize(self.user))
        result = {}
        result["messages"] = data
        result["has_next_page"] = message_page.has_next()
        result["page"] = page
        result["per_page"] = per_page
        return self.response(result)

    # @silk_profile()
    def get_style(self):
        data = {"primary_color": Preference.get_value("KEY_PRIMARY_COLOR", "#3bb9ff")}
        return self.response(data)

    #  BOT-Consumer user can call this JS
    # @silk_profile()
    def get_suggestions(self, channel_uuid, query):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        channel = MailChannel.find_channel(self.user, channel_uuid)
        if not channel:
            return JsonResponse(error="Invalid channel", status=404)
        if not channel.bots_enabled:
            return self.response([])
        processor = BotProcessor(self.user)
        data = processor.find_suggestions(query)
        return self.response(data)

    def has_group(self, name):
        if self.user.groups.filter(name=name).exists():
            return True
        return False

    def in_group(self, names):
        """Checks if self.user is part of the groups.

        Args:
            names (list[str]): Group names.
        """
        return True

    # @silk_profile()
    def open_sender_channel(self, message_id):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        item = MailMessage.objects.filter(message_id=message_id).first()
        if not item:
            return HttpResponse(status=403)
        if item.sender.id == self.user.id:
            return self.response("OK")

        bot_delegate = BotDelegate.objects.filter(user_id=item.sender.id).first()
        if bot_delegate:
            channel = MailChannel.ensure_bot_delegate_channel(self.user, bot_delegate)
            ActiveChannel.set_channel(self.user, channel)

        return self.response("OK")

    #  BOT-Consumer user can call this JS
    # @silk_profile(name="JsonRPC.post_message")
    def post_message(self, object):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        message = Message(**object)
        data = []
        processor = BotProcessor(self.user)
        processor.process(message)
        for mssg in processor.message_ids:
            data.append(mssg.serialize(self.user))
        return self.response(data)

    def response(self, result):
        return JsonRPCResponse(result)

    # @silk_profile()
    def set_active_channel(self, channel_uuid):
        if not self.in_group(["cross", "public"]):
            return HttpResponse(status=403)
        item = MailChannel.find_channel(self.user, channel_uuid)
        if not item:
            return HttpResponse(status=403)
        ActiveChannel.set_channel(self.user, item)
        data = []
        for msg in item.get_messages()[:20]:
            data.append(msg.serialize(self.user))
        return self.response(data)

    # @silk_profile()
    def unarchive_channel(self, channel_id):
        archived_channel = ArchivedChannel.objects.filter(
            channel=channel_id, user=self.user
        ).first()

        if archived_channel is None:
            return JsonRPCResponse(error="Archived channel does not exist", status=400)

        channel = archived_channel.channel
        archived_channel.delete()
        channel.save()

        return self.set_active_channel(channel.channel_uuid)
