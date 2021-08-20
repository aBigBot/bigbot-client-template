from django.contrib import admin
from .models import ResponsePhrase,InputPattern

@admin.register(ResponsePhrase)
class ResponsePhraseAdmin(admin.ModelAdmin):
    pass

@admin.register(InputPattern)
class InputPatternAdmin(admin.ModelAdmin):
    pass