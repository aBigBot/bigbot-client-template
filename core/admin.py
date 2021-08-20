from django import forms
from django.contrib import admin
from django.db import models

from .models import (
    AccessToken,
    ActiveChannel,
    ApiKeys,
    AppData,
    Attachment,
    BotDelegate,
    ConfigModel,
    ComponentUserResource,
    DelegateIntent,
    DelegateSkill,
    DelegateState,
    DelegateUtterance,
    HumanDelegate,
    Integration,
    MailChannel,
    MailMessage,
    OauthAccess,
    OAuthTokenModel,
    Preference,
    ServiceProvider,
    SkillModel,
    StateModel,
    TTSAudio,
    UserOTP,
    UserProfile,
)


class BinaryFileInput(forms.ClearableFileInput):
    def is_initial(self, value):
        """
        Return whether value is considered to be initial value.
        """
        return bool(value)

    def format_value(self, value):
        """Format the size of the value in the db.

        We can't render it's name or url, but we'd like to give some information
        as to wether this file is not empty/corrupt.
        """
        if self.is_initial(value):
            return f"{len(value)} bytes"

    def value_from_datadict(self, data, files, name):
        """Return the file contents so they can be put in the db."""
        upload = super().value_from_datadict(data, files, name)
        if upload:
            return upload.read()


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    readonly_fields = ["access_token"]


@admin.register(ActiveChannel)
class ActiveChannelAdmin(admin.ModelAdmin):
    pass


@admin.register(ApiKeys)
class ApiKeysAdmin(admin.ModelAdmin):
    readonly_fields = ["api_key", "api_secret"]


@admin.register(AppData)
class AppDataAdmin(admin.ModelAdmin):
    pass


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    pass


@admin.register(BotDelegate)
class BotDelegateAdmin(admin.ModelAdmin):
    pass


@admin.register(ComponentUserResource)
class ComponentUserResourceAdmin(admin.ModelAdmin):
    pass


@admin.register(ConfigModel)
class ConfigModelAdmin(admin.ModelAdmin):
    pass


@admin.register(DelegateIntent)
class DelegateIntentAdmin(admin.ModelAdmin):
    pass


@admin.register(DelegateSkill)
class DelegateSkillAdmin(admin.ModelAdmin):
    pass


@admin.register(DelegateState)
class DelegateStateAdmin(admin.ModelAdmin):
    pass


@admin.register(DelegateUtterance)
class DelegateUtteranceAdmin(admin.ModelAdmin):
    pass


@admin.register(HumanDelegate)
class HumanDelegateAdmin(admin.ModelAdmin):
    pass


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    pass


@admin.register(MailChannel)
class MailChannelAdmin(admin.ModelAdmin):
    pass


@admin.register(MailMessage)
class MailMessageAdmin(admin.ModelAdmin):
    pass


@admin.register(OauthAccess)
class OauthAccessAdmin(admin.ModelAdmin):
    pass


@admin.register(OAuthTokenModel)
class OAuthTokenModelAdmin(admin.ModelAdmin):
    pass


@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    readonly_fields = []


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    pass


@admin.register(SkillModel)
class SkillModelAdmin(admin.ModelAdmin):
    pass


@admin.register(StateModel)
class StateModelAdmin(admin.ModelAdmin):
    readonly_fields = ["data", "reference_id"]


@admin.register(TTSAudio)
class TTSAudioAdmin(admin.ModelAdmin):
    pass


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    pass


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.BinaryField: {"widget": BinaryFileInput()},
    }
