from contrib import utils
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
import django.dispatch
import uuid
from .models import (
    BotDelegate,
    HumanDelegate,
    MailChannel,
    MailMessage,
    UserProfile,
)


revoke_chat_user = django.dispatch.Signal(providing_args=["public_user","user"])

def pre_user(sender, instance, **kwargs):
    utils.log('============pre_user==================')
    if not instance.username:
        instance.username = uuid.uuid4().hex[:8]
    if instance.pk:
        pass

def post_user(sender, instance, created, **kwargs):
    utils.log('============post_user==================')
    # if created:
    #     UserProfile.objects.create(user_id=instance)
    if instance.groups.filter(name__in = ['cross','public']).exists():
       human_delegate = HumanDelegate.find(instance)
       MailChannel.ensure_default(human_delegate)


pre_save.connect(pre_user, sender=settings.AUTH_USER_MODEL)
post_save.connect(post_user, sender=settings.AUTH_USER_MODEL)


def user_display_name(self):
    if self.first_name:
        return self.first_name
    return self.username

User.add_to_class("__str__", user_display_name)


def user_get(self):
    return self

User.add_to_class("get", user_get)
