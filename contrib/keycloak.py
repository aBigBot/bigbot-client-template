import base64
import json
import time

from django.conf import settings
import jwt
from keycloak import KeycloakAdmin, KeycloakOpenID
import requests

from contrib import permissions, utils
from main import Log


class KeycloakController:
    _singleton = None

    def __init__(self):
        admin_password = settings.KEYCLOAK_CONFIG["KEYCLOAK_ADMIN_PASSWORD"]
        admin_username = settings.KEYCLOAK_CONFIG["KEYCLOAK_ADMIN_USERNAME"]
        client_id = settings.KEYCLOAK_CONFIG["KEYCLOAK_CLIENT_ID"]
        realm_name = settings.KEYCLOAK_CONFIG["KEYCLOAK_REALM"]
        server_url = settings.KEYCLOAK_CONFIG["KEYCLOAK_SERVER_URL"]

        try:
            self.keycloak_openid = KeycloakOpenID(
                client_id=client_id,
                realm_name=realm_name,
                server_url=server_url,
            )
        except Exception as e:
            Log.error("KeycloakOpenID", e)

        try:
            self.keycloak_admin = KeycloakAdmin(
                auto_refresh_token=["delete", "get", "post", "put"],
                password=admin_password,
                realm_name=realm_name,
                server_url=server_url,
                username=admin_username,
                verify=True,
            )
        except Exception as e:
            Log.error("KeycloakAdmin", e)

    @staticmethod
    def add_user_to_group(user_id, group):
        """Add user to group."""
        kc = KeycloakController.get_singleton()
        group = KeycloakController.get_group(group)
        kc.keycloak_admin.group_user_add(user_id, group["id"])

    @staticmethod
    def authenticate(token_encoded):
        try:
            kc = KeycloakController.get_singleton()
            token = KeycloakController.decode_token(token_encoded)
            user = kc.verify_token(token)
            if user is None:
                token, user = kc.refresh_token(token)
            else:
                user = KeycloakUser(user, from_token=True)
            return user, token
        except Exception as e:
            Log.error("KeycloakController.authenticate", e)
        return None, None

    @staticmethod
    def create_user(user_representation):
        """Adds user to keycloak instance"""
        email = user_representation.get("email")
        username = user_representation.get("username")
        if email is None or username is None:
            raise Exception("user_representation must include an email and username")
        cleaned, _ = KeycloakUser.clean(user_representation)
        cleaned["enabled"] = True
        cleaned["requiredActions"] = [
            "UPDATE_PASSWORD",
            "UPDATE_PROFILE",
            "VERIFY_EMAIL",
        ]
        kc = KeycloakController.get_singleton()
        kc.keycloak_admin.create_user(cleaned)
        user = kc.keycloak_admin.get_users({"email": email, "username": username})[0]
        KeycloakController.add_user_to_group(user["id"], "cross")
        KeycloakController.add_user_to_group(user["id"], "public")
        groups = kc.keycloak_admin.get_user_groups(user["id"])
        kc.keycloak_admin.send_verify_email(user["id"])
        return KeycloakUser(user, groups)

    @staticmethod
    def decode_token(encoded_token):
        return json.loads(utils.base64_decode(encoded_token))

    @staticmethod
    def encode_token(token):
        return utils.base64_encode(json.dumps(token, separators=(",", ":")))

    @staticmethod
    def get_group(group_name):
        """Gets group by name."""
        kc = KeycloakController.get_singleton()
        groups = kc.keycloak_admin.get_groups()
        for group in groups:
            if group["name"] == group_name:
                return group

    @staticmethod
    def get_or_create_groups(groups):
        kc = KeycloakController.get_singleton()
        available_groups = kc.keycloak_admin.get_groups()
        result = []

        for pending_group in groups:
            group = None
            for existing_group in available_groups:
                if existing_group["name"] == pending_group.lower():
                    group = existing_group
                    break

            if group:
                result.append(group)
            else:
                kc.keycloak_admin.create_group({"name": pending_group.lower()}, skip_exists=True)
                group = KeycloakController.get_group(pending_group.lower())
                if group:
                    result.append(group)

        return result

    def get_public_key(self):
        try:
            public_key = requests.get(
                settings.KEYCLOAK_CONFIG["KEYCLOAK_SERVER_URL"]
                + "realms/"
                + settings.KEYCLOAK_CONFIG["KEYCLOAK_REALM"]
            ).json()["public_key"]
            self.public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        except Exception as e:
            Log.error("KeycloackController.get_public_key", e)
            self.public_key = None

    @staticmethod
    def get_singleton():
        """Returns a singleton instance of KeycloakController"""
        if KeycloakController._singleton is None:
            kc = KeycloakController()
            KeycloakController._singleton = kc
        return KeycloakController._singleton

    @staticmethod
    def get_user(user_id, get_groups=False):
        try:
            kc = KeycloakController.get_singleton()
            user = kc.keycloak_admin.get_user(user_id)
            if get_groups:
                groups = kc.keycloak_admin.get_user_groups(user_id)
                user["groups"] = [group["name"] for group in groups]
            return KeycloakUser(user)
        except Exception as e:
            Log.error("KeycloakController.get_user", e)

    @staticmethod
    def get_users(query=None):
        try:
            kc = KeycloakController.get_singleton()
            users = kc.keycloak_admin.get_users(query)
            result = []
            for user in users:
                if user.get("email") == settings.KEYCLOAK_CONFIG["KEYCLOAK_ADMIN_USERNAME"]:
                    continue
                result.append(KeycloakUser(user))
            return result
        except Exception as e:
            Log.error("KeycloakController.get_users", e)
            return []

    @staticmethod
    def get_user_by_email(email):
        try:
            kc = KeycloakController.get_singleton()
            users = kc.keycloak_admin.get_users()
            user = {}
            for u in users:
                if u["email"] == email:
                    user = u
                    break
            groups = kc.keycloak_admin.get_user_groups(user["id"])
            user["groups"] = groups
            return KeycloakUser(user)
        except Exception as e:
            Log.error("KeycloakController.get_user_by_email", e)

    @staticmethod
    def is_user_in_role(user_id, role_name):
        """Checks if a user is member of a keycloak role

        Args:
            user_id (uuid): keycloak user id
            role_name (str): keycloak role name

        Returns:
            True if user is a member, False otherwise
        """
        is_member = False
        kc = KeycloakController.get_singleton()
        try:
            members = kc.keycloak_admin.get_realm_role_members(role_name)
            for member in members:
                if member["id"] == user_id:
                    is_member = True
                    break
        except:
            pass
        return is_member

    @staticmethod
    def logout(token_encoded):
        try:
            kc = KeycloakController.get_singleton()
            token = KeycloakController.decode_token(token_encoded)
            kc.keycloak_openid.logout(token["refresh_token"])
            return True
        except Exception as e:
            Log.error("KeycloakController.logout", e)
            return False

    @staticmethod
    def openid_token(username, password):
        try:
            kc = KeycloakController.get_singleton()
            token = kc.keycloak_openid.token(username, password)
            token["created_at"] = time.time()
            token["rlm"] = settings.KEYCLOAK_CONFIG["KEYCLOAK_REALM"]
            user = kc.verify_token(token)
            return KeycloakController.encode_token(token), KeycloakUser(user, from_token=True)
        except Exception as e:
            Log.error("KeycloakController.openid_token", e)

    @staticmethod
    def refresh_token(token):
        kc = KeycloakController.get_singleton()
        user = kc.verify_token(token)
        try:
            if user:
                return token, KeycloakUser(user, from_token=True)
            token = kc.keycloak_openid.refresh_token(token["refresh_token"])
            token["created_at"] = time.time()
            token["rlm"] = settings.KEYCLOAK_CONFIG["KEYCLOAK_REALM"]
            user = kc.verify_token(token)
            return token, KeycloakUser(user, from_token=True)
        except Exception as e:
            Log.error("KeycloakController.refresh_token", e)
        return None, None

    @staticmethod
    def remove_user(user_id):
        """Removes user from keycloak instance"""
        kc = KeycloakController.get_singleton()
        kc.keycloak_admin.delete_user(user_id)

    @staticmethod
    def remove_user_from_group(user_id, group):
        """Removes user from group."""
        kc = KeycloakController.get_singleton()
        group = KeycloakController.get_group(group)
        kc.keycloak_admin.group_user_remove(user_id, group["id"])

    @staticmethod
    def update_user(user_id, payload):
        """Updates a keycloak user"""
        cleaned, groups_to_process = KeycloakUser.clean(payload)
        kc = KeycloakController.get_singleton()
        user_groups = kc.keycloak_admin.get_user_groups(user_id)
        groups_to_add = []
        groups_to_remove = []

        for key, value in groups_to_process.items():
            in_group = False
            group = None
            for ug in user_groups:
                if key == ug["name"]:
                    group = ug
                    in_group = True
                    break
            # value is True of False
            if in_group and not value and group:
                groups_to_remove.append(group)
            elif not in_group and value and group:
                groups_to_add.append(group)
            elif value:
                groups_to_add.append(KeycloakController.get_group(key))

        for group in groups_to_add:
            kc.keycloak_admin.group_user_add(user_id, group["id"])
        for group in groups_to_remove:
            kc.keycloak_admin.group_user_remove(user_id, group["id"])

        kc.keycloak_admin.update_user(user_id, cleaned)
        user = kc.keycloak_admin.get_user(user_id)
        groups = kc.keycloak_admin.get_user_groups(user_id)
        user["groups"] = groups

        return KeycloakUser(user).serialize()

    @staticmethod
    def update_user_credentials(user_id, enabled=None, groups=[]):
        data = {}
        kc = KeycloakController.get_singleton()

        if isinstance(enabled, bool):
            data["enabled"] = enabled
            if enabled and "__operator__" not in groups:
                groups.append("__operator__")
            elif not enabled and "__operator__" in groups:
                groups = list(filter(lambda x: x != "__operator__", groups))

        KeycloakController.update_user_groups(user_id, groups)
        kc.keycloak_admin.update_user(user_id, data)

    @staticmethod
    def update_user_groups(user_id, groups):
        """Adds and removes the user from groups"""
        kc = KeycloakController.get_singleton()
        new_groups = KeycloakController.get_or_create_groups(groups)
        user_groups = kc.keycloak_admin.get_user_groups(user_id)
        ngs = set([i["id"] for i in new_groups])
        ugs = set([i["id"] for i in user_groups])
        add = []
        remove = []

        def get_group(name):
            for group in new_groups:
                if group["name"] == name:
                    return group

        if len(user_groups) == 0:
            add = new_groups
        else:
            diff = (ngs - ugs) | (ugs - ngs)
            add_set = diff.intersection(ngs)
            remove_set = diff.intersection(ugs)
            add = list(filter(lambda x: x["id"] in add_set, new_groups))
            remove = list(filter(lambda x: x["id"] in remove_set, user_groups))

        for group in add:
            kc.keycloak_admin.group_user_add(user_id, group["id"])
        for group in remove:
            if group["name"] != "__superuser__":
                kc.keycloak_admin.group_user_remove(user_id, group["id"])

    def verify_token(self, token):
        if getattr(self, "public_key", None) is None:
            self.get_public_key()
        try:
            payload = jwt.decode(
                token["access_token"], self.public_key, algorithms=["RS256"], audience="account"
            )
            return payload
        except Exception as e:
            Log.error("KeycloakController.verify_token", e)


class KeycloakUser:
    class Permissions:
        all = permissions.ADMIN

    def __init__(self, user={}, from_token=False):
        if from_token:
            self.email = user["email"]
            self.emailVerified = user["email_verified"]
            self.enabled = user.get("enabled", False)
            self.firstName = user["given_name"]
            self.groups = user["groups"]
            self.id = user["sub"]
            self.lastName = user["family_name"]
            self.username = user["preferred_username"]
        else:
            self.email = user.get("email")
            self.emailVerified = user.get("emailVerified")
            self.enabled = user.get("enabled", False)
            self.firstName = user.get("firstName", "")
            self.groups = user.get("groups", [])
            self.id = user.get("id")
            self.lastName = user.get("lastName", "")
            self.username = user.get("username")

    def __repr__(self):
        return f"<KeycloakUser: {self.id}>"

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def add_group(user_id, group):
        KeycloakController.add_user_to_group(user_id, group)

    @staticmethod
    def clean(data):
        """Removes """
        attributes = dir(KeycloakUser)
        cleaned = {}
        groups = {}
        for key in data:
            if key in attributes:
                if key[:3] == "is_":
                    groups[key[3:]] = data[key]
            else:
                cleaned[key] = data[key]
        if "groups" in cleaned:
            del cleaned["groups"]
        return cleaned, groups

    @staticmethod
    def create(payload):
        return KeycloakController.create_user(payload)

    @staticmethod
    def get_profile():
        from django_middleware_global_request.middleware import get_request
        from core.models import User

        request = get_request()

        keycloak_user = request.keycloak_user
        user = User.get_keycloak_user(keycloak_user)
        keycloak_user.avatar = user.get_avatar_url()
        return keycloak_user.serialize("__all__")

    @staticmethod
    def get_user(user_id):
        from core.models import DelegateUtterance, HumanDelegate, User

        try:
            internal_user = User.objects.filter(keycloak_user=user_id).first()
            user = KeycloakController.get_user(user_id, True)
            if internal_user is None and user:
                internal_user = User.objects.create(
                    email=user.email,
                    first_name=user.firstName,
                    keycloak_user=user.id,
                    last_name=user.lastName,
                    username=user.username,
                )
            delegate = getattr(internal_user, "human_delegate", None)
            if delegate is None:
                user.is_delegate = False
                user.offline_skill = None
                user.utterances = []
            else:
                user.utterances = [u.body for u in delegate.utterances.all()]
                user.is_delegate = len(user.utterances) > 0
                if delegate.offline_skill:
                    user.offline_skill = delegate.offline_skill.id
                else:
                    user.offline_skill = None

            result = user.serialize("__all__")
            return result
        except Exception as e:
            Log.error("KeycloakUser.get_user", e)
            raise e

    def in_group(self, *groups):
        for group in groups:
            if group in self.groups:
                return True
        return False

    @staticmethod
    def read(user_id):
        pass

    @staticmethod
    def remove(user_id):
        pass

    @staticmethod
    def remove_group(user_id, group_id):
        pass

    @staticmethod
    def search(*args, **kwargs):
        return KeycloakController.get_users()

    def serialize(self, fields):
        res = {}
        for key in dir(self):
            if "__" in key:
                continue
            attr = getattr(self, key)
            if type(attr) not in [bool, dict, float, int, list, str]:
                continue
            if key in fields or fields == "__all__":
                res[key] = getattr(self, key)
        return res

    @staticmethod
    def update(**payload):
        from core.models import AccessToken, DelegateSkill, DelegateUtterance, HumanDelegate

        enabled = payload.get("enabled", True)
        is_delegate = payload.get("is_delegate", False)
        groups = payload.get("groups", [])
        offline_skill = payload.get("offline_skill")
        user_id = payload.get("id")
        utterances = payload.get("utterances", [])

        try:
            KeycloakController.update_user_credentials(user_id, enabled=enabled, groups=groups)
        except Exception as e:
            Log.error("KeycloakUser.update", e)

        delegate = HumanDelegate.get_by_keycloak_user(user_id)
        if is_delegate:
            delegate.utterances.clear()
            for utterance in utterances:
                u = DelegateUtterance.get_record(utterance)
                delegate.utterances.add(u)
        else:
            delegate.utterances.clear()

        try:
            if offline_skill:
                skill = DelegateSkill.objects.get(id=offline_skill)
                delegate.offline_skill = skill
                delegate.save()
        except Exception as e:
            Log.error("update", e)

        at = AccessToken.objects.filter(user_id=delegate.user_id).first()
        if at:
            # Update the internal user data
            at.save()

        return True

    @staticmethod
    def update_profile(**payload):
        from django_middleware_global_request.middleware import get_request
        from core.models import User

        request = get_request()

        avatar = payload.get("avatar")
        if avatar is None:
            raise Exception("Invalid avatar")

        keycloak_user = request.keycloak_user
        internal_user = User.get_keycloak_user(keycloak_user)
        internal_user.update_avatar_base64(avatar)

        return True
