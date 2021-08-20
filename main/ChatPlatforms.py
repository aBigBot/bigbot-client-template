import base64
import json

from asgiref.sync import sync_to_async
from telethon import events, functions
from telethon.errors.rpcerrorlist import PhoneNumberInvalidError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from core.models import ProfileLink, User


class TelegramBot:
    def __init__(self, api_id, api_hash, token):
        self.client = TelegramClient("main_session", api_id, api_hash).start(bot_token=token)
        self.handlers = [
            (self.start_handler, events.NewMessage(pattern="/start(?: \w+)")),
            (self.message_handler, events.NewMessage(incoming=True)),
        ]
        self.register_handlers()
        with self.client:
            self.client.run_until_disconnected()
        print("Telegram bot started")

    # method valid with bot
    def _get_messages(self, message_ids: list):
        result = self.client(functions.messages.GetMessagesRequest(id=message_ids))
        return {
            "messages": [
                {
                    "sender_id": msg.from_id.user_id if msg.from_id else msg.peer_id.user_id,
                    "sender_username": self.client.get_entity(msg.from_id.user_id).username
                    if msg.from_id
                    else self.client.get_entity(msg.peer_id.user_id).username,
                    "text": msg.message,
                    "date": msg.date,
                    "is_self": True if msg.from_id else False,
                }
                for msg in result.messages
            ]
        }

    # method valid with bot
    def _send_message(self, chat_id, message):
        sent_message = self.client.send_message(chat_id, message)
        return {
            "message_id": sent_message.id,
            "receiver_id": sent_message.peer_id.user_id,
            "text": sent_message.message,
            "date": sent_message.date,
        }

    # method invalid with bot
    def chat_list(self):
        chats = self.client.iter_dialogs()
        return {
            "chat_list": [
                {
                    "name": dialog.name,
                    "id": dialog.id,
                }
                for dialog in chats
            ]
        }

    def disconnect(self):
        if self.client:
            self.client.disconnect()
        else:
            return

    @sync_to_async
    def get_linked_user(self, sender):
        return ProfileLink.objects.filter(
            platform="telegram", platform_user_id=str(sender.id)
        ).first()

    def get_me(self):
        me = self.client.get_me()
        return me.__dict__

    # method invalid with bot
    def get_message(self, chat_id, message_count=None):
        messages = self.client.iter_messages(chat_id, limit=message_count)
        return {
            "messages": [
                {
                    "sender_id": msg._sender_id,
                    "sender_username": msg._sender.username,
                    "text": msg.text,
                    "date": msg.date,
                }
                for msg in messages
            ]
        }

    def make_connection(self):
        self.client = TelegramClient(StringSession(self.session), self.API_ID, self.API_HASH)
        self.client.connect()
        if not self.client.is_user_authorized():
            phone = input("please enter your Telegram number ")
            sent = self.client.send_code_request(phone, force_sms=True)
            print(sent)
            self.client.sign_in(phone, input("Enter the code=  "))
            self.session = self.client.session.save()
        return {"token": self.session}

    async def message_handler(self, event):
        # TODO: process the incoming message and respond to it
        sender = await event.get_sender()
        user_data = await self.get_linked_user(sender)
        if user_data is None:
            await event.respond(
                "Unregistered user, initiate the chat using the link provide by bigbot first"
            )
        else:
            await event.respond("**TODO**")

    def register_handlers(self):
        for handler, event in self.handlers:
            self.client.add_event_handler(handler, event)

    @sync_to_async
    def register_user(self, sender, payload):
        try:
            user_id = int(base64.b64decode(payload))
        except:
            return None

        try:
            user = User.objects.get(id=user_id)
        except:
            return None

        link = ProfileLink.objects.filter(
            platform="telegram", platform_user_id=str(sender.id), user_id=user
        ).first()

        if link is None:
            link = ProfileLink.objects.create(
                platform="telegram", platform_user_id=str(sender.id), user_id=user
            )

        return link

    # method invalid with bot
    def send_message(self, chat_id, message):
        self.client.send_message(chat_id, message)
        return self.get_message(chat_id=chat_id, message_count=1)

    async def start_handler(self, event):
        sender = await event.get_sender()
        text_chunks = event.message.raw_text.split()

        payload = None
        if text_chunks[1] == text_chunks[-1]:
            payload = text_chunks[1]

        user = await self.register_user(sender, payload)

        if user is None:
            await event.respond("Invalid payload, please try again")
        else:
            await event.respond("Bridge stablished successfully")

    def setup(self):
        pass
