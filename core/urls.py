from django.conf.urls import url
from django.urls import path, include, re_path

from . import serializer
from . import views


urlpatterns = [
    path("api/misc/credential/", views.getMiscCredentials),
    path("api/v3/<str:endpoint>/<str:method>", views.proxy_jsonrpc),
    path("consumer/avatar", views.consumer_avatar),
    path("consumer/file", views.consumer_file),
    path("consumer/test", views.consumer_test),
    path("html/render", views.html_render),
    # remote api
    path("jsonrpc/1/instance/object", views.instance_object_v1),
    path("jsonrpc/1/instance/common", views.instance_common_v1),
    path("jsonrpc/auth", views.authenticate),
    path("jsonrpc/common", views.common),
    path("jsonrpc/consumer", views.consumer),
    path("jsonrpc/object", views.object),
    path("jsonrpc/registry", views.registry),
    path("jsonrpc/standalone", views.standalone),
    path("media/image", views.media_image),
    path("media/audio", views.tts_audio, name="tts_audio"),
    path("media/response/<int:id>", views.response_media, name="response_media"),
    # path('oauth/provider',views.oauth_provider),
    path("oauth/provider", views.oauth_redirect),
    path("payment/redirect", views.payment_redirect),
    # REST Framework TEMP
    url(r"^snippets/$", serializer.SnippetList.as_view()),
    url(r"^snippets/(?P<pk>[0-9]+)/$", serializer.SnippetDetail.as_view()),
    path("stack/createsuperuser", views.create_superuser),
    path("stack/info", views.info),
    path("stack/setup", views.stack_setup),
    path("stack/login", views.chat_login),
    path("stack/chat/send-otp", views.chat_send_otp),
    path("stack/chat/verify-otp", views.chat_verify_otp),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
    path("version/", views.version_view),
    path("webhook/", views.webhook_view),
]
