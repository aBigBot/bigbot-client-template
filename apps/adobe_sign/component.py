from main.Component import SkillProvider, OAuthProvider
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError

import json, requests

#**************************************************************************
# Authorization
#**************************************************************************

class AdobeSignAuthProvider(OAuthProvider):
    def __init__(self, config):
        self.AUTH_URL =  "https://secure.in1.adobesign.com/public/oauth?"
        self.TOKEN_URL = "http://api.adobesign.com/oauth/token?"
        self.CLIENT_ID = self.get_variable('com.big.bot.adobe',"CLIENT_ID")
        self.CLIENT_SECRET = self.get_variable('com.big.bot.adobe',"CLIENT_SECRET")
        self.scope = [
            'user_login:self+agreement_send:account',
        ]
        super().__init__(config)
    #**************************************************************************
    # Authorization url - Adobe Sign Parameters
    # Scope used : user_login : self and agreement_send: send on behalf of any user in the account.
    # Keep scope similar to the ones you have registered. Scope is space-delimited so encode else use '+'
    # redirect_url : Set as per the requirement
    # respone_type : 'code', this will always be the same
    # client_id : Client ID
    #**************************************************************************

    def authorization_url(self, redirect_uri, user_id, **kwargs):
        oauth = OAuth2Session(client_id = self.CLIENT_ID,
                                response_type = 'code',
                                redirect_uri = redirect_uri,
                                scope= self.scope
                            )

        #**************************************************************************
        # BASE AUTH URL NOTE:
        # Please keep the base url similar to your Adobe Sign dashboard link
        # else it will show "Invalid Request Error". Else check for 'n1/eu1' etc.
        #**************************************************************************
        auth_url = self.AUTH_URL

        authorization_url, state = oauth.authorization_url(auth_url)
        return authorization_url

    def is_authorized(self, oauth, **kwargs):
        req = oauth.get(self.TOKEN_URL)
        if req.status_code == 200:
            return True
        return False

    #**************************************************************************
    # Fetch Access Token
    # code : Authorization Code
    # client_secret : Available in your Adobe Account
    #**************************************************************************

    def fetch_token(self, redirect_uri, authorization_response, *args, **kwargs):
        oauth = OAuth2Session(code = authorization_response["code"],
                                client_id = self.CLIENT_ID,
                                client_secret = self.CLIENT_SECRET,
                                redirect_uri = redirect_uri,
                                grant_type = 'authorization_code HTTP/1.1',
                            )

        token_url = self.TOKEN_URL
        return oauth.fetch_token(token_url)

    def build_oauth(self, token, **kwargs):
        return OAuth2Session(token=token)

    # update required this logic not efficient
    def is_expired(self, user_id, token, **kwargs):
        try:
            oauth = OAuth2Session(token=token)
            oauth.get(self.TOKEN_URL)
        except TokenExpiredError:
            return True
        return False

    def refresh_token(self, user_id, token, **kwargs):
        refresh_url = self.TOKEN_URL
        extra = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }
        adobe = OAuth2Session(self.CLIENT_ID, token=token)
        return adobe.refresh_token(refresh_url, **extra)

#**************************************************************************
# SkillProvider
#**************************************************************************

class AdobeSignSkill(SkillProvider):

    def __init__(self, config):
        self.oauth_component = 'apps.adobe_sign.component.AdobeSignAuthProvider'
        super().__init__(config)

    #
    #**************************************************************************
    #

    def auth_providers(self, package, user,*args, **kwargs):
        return [OAuthProvider.get(self.oauth_component, user,)]


    #**************************************************************************
    # this method execute when all required data collected from user
    #**************************************************************************

    def on_execute(self,binder, user_id, package, data, *args, **kwargs):
        oauth = self.get_providers(package, user_id).oauth()

        action_type = data['action_type']
        result = {
            'action_type': action_type,
        }
        email = data['email']
        result.update({'email':email})
        result.update({'oauth':oauth})

        #**************************************************************************
        # Build Result & Send Agreement
        #**************************************************************************
        resp = self.send_agreement(self, result, *args, **kwargs)
        return result


    #**************************************************************************
    # GET Access Point URL
    #**************************************************************************

    def get_access_point_url(self, *args, **kwargs):
        base_url = "https://api.adobesign.com/api/rest/v6/baseUris"

        res = requests.get(base_url)
        result = res.json()

        return result["apiAccessPoint"]


    #**************************************************************************
    # Send Agreement : Using Adobe Sign API
    #**************************************************************************

    def send_agreement(self, result, *args, **kwargs):

        # File path of the uploading file
        filepath = ""
        api_access_point = self.get_access_point_url()
        accessToken = result["oauth"]["accessToken"]
        oauth = result["oauth"]


        # Correct Access Point is required, this comes with access_token
        transient_url = api_access_point+"/api/rest/v6/transientDocuments"
        params = {
            'Authorization':'Bearer '+accessToken,
            'File': filepath,
            'Mime-Type' : '.pdf'
        }
        req = oauth.post(transient_url, params=params)
        response = req.json()

        #
        # "code":"Error Codes",
        # "message":"Request must be made to correct API access point (e.g. use GET /baseUris)."
        # if response contains "transientDocumentId" then
        #
        #

        if 'message' in response:
            return {'executed':False,}
        else:
            if 'transientDocumentId' in response:

                #****************************************************
                # For sending Agreements 2 parameters are required
                # Authorization - access_token
                # AgreementInfo - Information about the agreement, should be json
                #****************************************************

                agreement_url = api_access_point+"/api/rest/v6/agreements"
                params = {
                    'Authorization':'Bearer '+accessToken,
                }

                agreement_info = {
                    "fileInfos": [{
                        "transientDocumentId": response["transientDocumentId"]
                    }],
                    "name": "MyTestAgreement",
                    "participantSetsInfo": [{
                        "memberInfos": [{
                            "email": result["email"]
                        }],
                        "order": 1,
                        "role": "SIGNER"
                    }],
                    "signatureType": "ESIGN",
                    "state": "IN_PROCESS"
                }

                req = oauth.post(agreement_url, json=agreement_info, params=params)

                response = req.json()

                if 'code' in response:
                    return {'executed':False,}
                response['executed'] = True
                return response
        return response


    #**************************************************************************
    # Check Agreement Status
    #**************************************************************************

    def check_agreement_status(self, api_access_point, accessToken, agreement_id, *args, **kwargs):
        oauth = self.get_provider(self.oauth_component, package, user).oauth()

        api_access_point = self.get_access_point_url()

        agreement_url = api_access_point++"/api/rest/v6/agreements/"+agreement_id
        params = {"Authorization":'Bearer '+accessToken}

        req = oauth.get(agreement_url, params=params)
        return req.json()


    #**************************************************************************
    # Create Webhook
    #**************************************************************************

    def create_webhook(self, *args, **kwargs):
        oauth = self.get_provider(self.oauth_component, package, user).oauth()
        pass
