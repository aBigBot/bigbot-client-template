import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
from main.Component import OAuthProvider,SkillProvider
from main import Log

class GoogleOauth(OAuthProvider):

    def __init__(self, config):
        super(GoogleOauth, self).__init__(config)
        self.update_meta({
            "icon":"data:image/webp;base64,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",
            "title":"Google",
            "description":"You need to authorize your account first."
        })

    def is_authorized(self, oauth, **kwargs):
        try:
            oauth.get('https://www.googleapis.com/oauth2/v1/tokeninfo')
            return True
        except TokenExpiredError:
            pass
        return False

    def is_expired(self, user_id, token, **kwargs):
        try:
            oauth = OAuth2Session(token=token)
            oauth.get('https://www.googleapis.com/oauth2/v1/tokeninfo')
        except TokenExpiredError:
            return True
        return False

    def refresh_token(self, user_id, token, **kwargs):
        refresh_url = "https://accounts.google.com/o/oauth2/token"
        config = self.get_config()
        extra = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
        }
        oauth = OAuth2Session(config['client_id'], token=token)
        return oauth.refresh_token(refresh_url, **extra)

    def authorization_url(self, redirect_uri, user_id,  **kwargs):
        url = 'https://accounts.google.com/o/oauth2/auth'
        scope = ['https://www.googleapis.com/auth/calendar']
        client_id = self.get_config().get('client_id')
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, state = oauth.authorization_url(url, access_type="offline", prompt="consent")
        return authorization_url

    def fetch_token(self, redirect_uri, authorization_response, **kwargs):
        url = 'https://accounts.google.com/o/oauth2/token'
        scope = ['https://www.googleapis.com/auth/calendar']
        client_id = self.get_config().get('client_id')
        client_secret = self.get_config().get('client_secret')
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        return oauth.fetch_token(url,authorization_response=authorization_response, client_secret=client_secret)

class GoogleEvent(SkillProvider):

    def on_execute(self, binder, user_id, data, **kwargs):
        skill = kwargs.get('skill')
        oauth = self.oauth(binder, user_id, skill, 'ip_google_oauth')
        r = oauth.get('https://www.googleapis.com/oauth2/v1/tokeninfo')
        if r.status_code == 200:
            res  = r.json()
            Log.info('on_execute', res)
            return res
        else:
            Log.error('on_execute', str(r.status_code))