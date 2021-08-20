from django.contrib.auth import authenticate, get_user_model
from rest_framework import (
    authentication,
    exceptions,
    filters,
    generics,
    permissions,
    routers,
    serializers,
    viewsets,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication

from core.models import User


class ExampleAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):

        # Get the username and password
        username = request.data.get("username", None)
        password = request.data.get("password", None)

        if not username or not password:
            raise exceptions.AuthenticationFailed("No credentials provided.")

        credentials = {get_user_model().USERNAME_FIELD: username, "password": password}

        user = authenticate(**credentials)

        if user is None:
            raise exceptions.AuthenticationFailed("Invalid username/password.")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return (user, None)  # authentication successful


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class IsOwnerFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """

    def filter_queryset(self, request, queryset, view):
        return queryset.filter()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True
        # Write permissions are only allowed to the owner of the snippet.
        return True

    # def has_permission(self, request, view):
    #     return False


class SnippetList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = (IsOwnerFilterBackend,)
    authentication_classes = (
        SessionAuthentication,
        ExampleAuthentication,
    )


class SnippetDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    authentication_classes = (
        SessionAuthentication,
        ExampleAuthentication,
    )
