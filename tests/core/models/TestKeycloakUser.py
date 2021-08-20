from contrib.keycloak import KeycloakController, KeycloakUserModel
from core.models import KeycloakUser
from django.contrib.auth import get_user_model
import pytest

# ------------------------------------------------
# Setup
# ------------------------------------------------


# ------------------------------------------------
# Tests
# ------------------------------------------------


class TestAddGroup:
    pass


class TestGetOrCreate:
    @pytest.mark.django_db
    def test_anonymous_user(self, mocker):
        User = get_user_model()
        user = User.objects.create(username="test")

        assert user.keycloak_profile is not None
        assert user.keycloak_profile.keycloak_user_id is None

    @pytest.mark.django_db
    def test_user_with_email(self, mocker):
        def get_user(*args):
            user = KeycloakUserModel({"id": None})
            user.id = "0"
            return user

        mocker.patch.object(KeycloakController, "get_user_by_email", new=get_user)

        User = get_user_model()
        user = User.objects.create(username="test", email="mail@test.com")

        assert user.keycloak_profile is not None
        assert user.keycloak_profile.keycloak_user_id == "0"


class TestInGroup:
    @pytest.mark.django_db
    def test_in_group(self):
        User = get_user_model()
        user = User.objects.create(username="test")
        assert KeycloakUser.in_group(user, "cross")

    @pytest.mark.django_db
    def test_not_in_group(self):
        User = get_user_model()
        user = User.objects.create(username="test")
        assert not KeycloakUser.in_group(user, "manager")

    @pytest.mark.django_db
    def test_registered_user(self, mocker):
        def get_user(*args):
            user = KeycloakUserModel()
            user.id = "0"
            user.groups = ["manager"]
            return user

        mocker.patch.object(KeycloakController, "get_user", new=get_user)

        User = get_user_model()
        user = User.objects.create(username="test", email="mail@test.com")
        keycloak_user = KeycloakUser.get_or_create(user)
        keycloak_user.keycloak_user_id = "709e7379-91cb-4f80-9a9c-cb30fb11aeee"
        keycloak_user.save()

        assert KeycloakUser.in_group(user, "manager")
