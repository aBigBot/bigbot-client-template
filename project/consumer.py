import asyncio
import json
import traceback
from urllib.parse import parse_qs
from uuid import uuid4

from asgiref.sync import sync_to_async, async_to_sync
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.signals import request_finished
from django.db.models.signals import post_save, pre_save
import django.dispatch
from django.dispatch import receiver
from silk.profiling.profiler import silk_profile

from core.models import (
    AccessToken,
    ActiveChannel,
    HumanDelegate,
    MailChannel,
    MailMessage,
    StateModel,
)
from core.signals import revoke_chat_user
from main import Log


class WebSocketConsumer(AsyncConsumer):
    def active_channel_post_save(self, sender, instance, **kwargs):
        if instance.user_id.id == self.user.id:
            history = []
            for item in instance.channel_id.get_messages()[:50]:
                history.append(item.serialize(self.user))
            self.send_data(
                {
                    "event": "channel",
                    "channel": instance.channel_id.serialize(self.user),
                    "history": history,
                }
            )

    @database_sync_to_async
    def authenticate(self, uuid, token):
        user = AccessToken.authenticate(uuid, token)
        return user

    @database_sync_to_async
    def connect_user(self):
        HumanDelegate.add_user_client(self.user, self.uuid)

    @database_sync_to_async
    def disconnect_user(self):
        HumanDelegate.remove_user_client(self.user, self.uuid)

    # @silk_profile(name="WebSocketConsumer.message_post_save")
    def message_post_save(self, sender, instance, **kwargs):
        # if instance.sender.id != self.user.id:
        channel = instance.channel_id
        human_delegate = self.user.human_delegate
        state = StateModel.objects.filter(reference_id=channel.id).first()
        skill_id = None

        if state and state.data:
            state_data = json.loads(state.data)
            skill_data = state_data.get("skill")
            if type(skill_data) == dict:
                skill_id = skill_data.get("id")

        if channel:
            archived_channels = self.user.archived_channels
            archived_channel = archived_channels.filter(channel=channel).first()
            archived_channels = archived_channels.values_list("channel", flat=True)
            if archived_channel:
                archived_channel.delete()

            val_channel = None
            val_message = None
            val_channels = []
            try:
                val_channel = channel.serialize(self.user)
            except Exception:
                print("=======val_channel==========")
                print(traceback.print_exc())

            try:
                val_message = instance.serialize(self.user)
            except Exception:
                print("=======val_message==========")
                print(traceback.print_exc())

            try:
                channels = human_delegate.mail_channels.exclude(id__in=archived_channels)
                for item in channels:
                    val_channels.append(item.serialize(self.user))
            except Exception:
                print("=======val_message==========")
                print(traceback.print_exc())

            if val_channel and val_message:
                try:
                    self.send_data(
                        {
                            "event": "message",
                            "channel": val_channel,
                            "message": val_message,
                            "channels": val_channels,
                            "skill": skill_id,
                        }
                    )
                    HumanDelegate.add_user_client(self.user, self.uuid)
                except Exception:
                    print("=======send_data==========")
                    print(traceback.print_exc())

    @database_sync_to_async
    def notify_partner(self, user, connected=True):
        pass

    def on_revoke_chat_user(self, sender, **kwargs):
        public_user = kwargs.get("public_user")
        user = kwargs.get("user")
        if self.user.id == public_user.id:
            self.send_data(
                {"event": "revoke", "uuid": sender.access_uuid, "token": sender.access_token}
            )

    def send_data(self, data):
        async_to_sync(self.send)(
            {
                "type": "websocket.send",
                "text": json.dumps(data),
            }
        )

    async def websocket_connect(self, event):
        params = parse_qs(self.scope["query_string"].decode("utf8"))
        uuid = params["uuid"][0]
        token = params["token"][0]
        self.user = await self.authenticate(uuid, token)
        self.uuid = str(uuid4())
        if self.user:
            await self.connect_user()
            await self.send(
                {
                    "type": "websocket.accept",
                }
            )
            post_save.connect(self.message_post_save, sender=MailMessage)
            post_save.connect(self.active_channel_post_save, sender=ActiveChannel)
            revoke_chat_user.connect(self.on_revoke_chat_user)

        # post_save.connect(self.message_post_save,  sender=DelegateChannel )
        # print('=============CONNECTED=========================')
        # user = self.scope['user']
        # await self.notify_partner(user,True)
        # await self.send({'type':'websocket.send','text':json.dumps({'message':'welcome'})})
        # await self.send_socket_data(data)
        pass

    async def websocket_disconnect(self, event):
        await self.disconnect_user()
        post_save.disconnect(sender=MailMessage)
        post_save.disconnect(sender=ActiveChannel)
        # print('=============DISCONNECTED=========================')
        # user = self.scope['user']
        # await self.notify_partner(user,False)
        pass

    async def websocket_receive(self, object):
        # user = self.scope['user']
        # message = json.loads(object['text'])
        # event = message['event']
        # data = message['data']
        # if event == 'typing':
        #     pass
        pass


class WebSocketDebug(AsyncConsumer):
    async def websocket_connect(self, event):
        # params = parse_qs(self.scope['query_string'].decode('utf8'))
        # uuid = params['uuid'][0]
        # token = params['token'][0]
        await self.send(
            {
                "type": "websocket.accept",
            }
        )
        await self.send({"type": "websocket.send", "text": "You are connected!"})
        pass

    async def websocket_receive(self, object):
        await self.send({"type": "websocket.send", "text": "Hello ! from backend!"})

    async def websocket_disconnect(self, event):
        pass
