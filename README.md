# Big Bot Developer Guide

This developer guide is intended to help build custom integrations using the Big Bot framework. Big Bot supports two key components for custom integrations.

* Logic Adapters (used to implement custom business logic.)
* Skill Provider (used to implement more complex Big Bot skills )

These are the two key components exposed to developers for customising their own Big Bot.

## Big Bot Integration Structure

To start with Big Bot integration/app, you need to create some essential files:

```
.
├── component.py
├── init.py
└── manifest.json
```

Below is a functional description for these essential files.



##### manifest.json

This file holds meta information about your Big Bot app.

```json
{
  "name": "Google event",
  "version": 1.0,
  "maintainer" : "Jonathan Lee <jon@bigitsystems.com>, Ashish Sahu <ashish.s@bigitsystems.com>",
  "summary": "Big Bot Google Calendar",
  "description": "Google Calendar is a time-management and scheduling calendar service.",
  "category": "productivity",
  "author": "BIG BOTS (PRIVATE LIMITED)",
  "website": "https://bigitsystems.com",
  "auto_install": true
}
```



##### component.py

Use this file to create your Big Bot components. All of your components and business logic goes here. Here is an example that provides sections for Authorization, Skills and other required logic.

```python
from contrib.application import OAuthProvider
from requests_oauthlib import OAuth2Session
from contrib.application import SkillProvider
from contrib.application import LogicAdapter

#
# You can import the required packages here
#


class GoogleOAuthProvider(OAuthProvider):
    # OAuthProvider is used for authorization 
    pass


class GoogleSkillProvider(SkillProvider):
    # your skill provider logic
    pass

class GoogleFAQ(LogicAdapter):
    # your logic adapters
    pass
```



### Authorization using OAuthProvider 

###### Reference : 
1. [https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html](https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html) <br />
2. [https://www.kite.com/python/docs/requests_oauthlib.OAuth2Session](https://www.kite.com/python/docs/requests_oauthlib.OAuth2Session)


```python
class ExampleAuthProvider():
 
    #
    # GET AUTHORIZATION URL
    # We are using OAuth2 for authorization, fetching access token, refresh access token 

    # scope : It is the scope of oauth. It is a list by default. Scope for example could be Google Calender, Paypal Payments, etc.
    # redirect_uri : This points to the default endpoint as configured in Bigbot for authorization. 
    # settings : This dictionary, contains authorization credentials, and extra required parameters in key value pair. It is stored in json format in the backend.
    
    # NOTE:
    # scope, redirect_url and settings are required arguments.

    def authorization_url(self, scope, redirect_uri, settings):
        oauth = OAuth2Session(settings['client_id'], redirect_uri=redirect_uri, scope=scope)

        auth_url = 'https://github.com/login/oauth/authorize'

        authorization_url, state = oauth.authorization_url(auth_url)

        return authorization_url


    #
    # METHOD TO FETCH ACCESS TOKEN
    # This method will fetch an access token from the token endpoint.
    #
    # authorization_response : This is the full redirect url. For example the url will be like "/oauth/provider?state=abc&access_token=ndjqwh3edb3u" 
    #
    # NOTE:
    # Follow the requests reference link for more examples
    #
    # return : Access Token 
    #
    # Reference : https://gitlab.com/gitops-big-it-systems-ltd/Integration/-/blob/lawrence-dev/google/component.py#L31

    def fetch_token(self, scope, redirect_uri, settings, authorization_response, *args, **kwargs):
        pass


    #
    # METHOD : is_scope_authorized
    # This method checks if user is authorised to access a particular scope or not , sometimes a scope gets changes on bases of requirements. 
    # By default it is an array/list. If scope does't change dynamically, then you can simply return True or False on this override method
    
    # return : True/False
    # True : If user is authorised then no need to ask user to authenticate
    # False : prompt the user to authenticate his oauth account

    # Bigbot calls this method when oauth is needed in upcoming stages , basically it's a validation

    def is_scope_authorized(self, oauth, scope):
        pass


    #
    # Method : build_oauth
    # token : Access token 
    # This is for returning an oauth object
    # we can pass an access token to this method, and it returns an oauth object. This object can be used later if required
    #
    # Reference : https://gitlab.com/gitops-big-it-systems-ltd/Integration/-/blob/lawrence-dev/google/component.py#L38 

    def build_oauth(self, token):
        return OAuth2Session(token=token)


    #
    # Method : is_expired
    # This method is used to check whether the access token has expired or not
    # return : True/False

    # Access tokens come with a time to expire, if the token has expired, then TokenExpiredError exception will be raised. 
    # For access you have to refresh the access token if the token has expired.
    # For raising the exception please import "from oauthlib.oauth2 import TokenExpiredError"
    
    # Note :
    # Tokens can be updated or refreshed automatically, please follow the documentation given in the reference links for more information
    #
    # Reference : https://gitlab.com/gitops-big-it-systems-ltd/Integration/-/blob/lawrence-dev/myinfo/component.py#L79

    def is_expired(self, token, settings):
        pass


    #
    # Method : refresh_token
    # This method is used to refresh the access token, and return the new token.
    #
    # Please use OAuth2Session "refresh_token" method to achieve this

    def refresh_token(self, token, settings):
        pass


```

### Key points to note while creating a AuthProvider

In the below given image we can see how the settings parameter is stored in the django backend.

**Component :** This is a unique, fully qualified name.  
**Key :** value is set as **"oauth_settings"**. <br /> 
**Data :** **"settings"** details is stored as a dictionary in this field. It contains all the necessary details like credentials and other required details for authorization.

![Screenshot](images/settings.jpg)


##### init.py

This python script helps you to register your Big Bot components. It can be considered as registry object of your Big Bot application.

Additionally you can quickly unregistered your components by commenting or removing them. This will not trigger errors and comes in handy when debugging your application.

```python
from contrib.application import AppConfig
from .component import GoogleSkillProvider,GoogleFAQ

class Application(AppConfig):

    def init(self, config):
        pass

    def registry(self, object):
        object.register(GoogleSkillProvider())
        object.register(GoogleFAQ())
```

Two components has been registered in this snippet, GoogleSkillProvider and GoogleFAQ.



> Make sure directory name is unique across other directory for these files.



###  Oauth provider List

* google

* odoo



## Output node List

* big.bot.core.text  (displays text)
* big.bot.core.image (display single image)
* big.bot.core.iframe (displays iframe)



## Skill Provider Functional Methods

* get_oauth(user, 'google') :  returns oauth object, client id , access_token can be obtained



# Getting started

To demonstrate we will create a Google Calendar app. Start by creating new directory called google_event and create a manifest.json file in this directory. This file holds basic meta information of your Big Bot app.

##### manifest.json

```json
{
  "name": "Google event",
  "version": "1.0.0",
  "maintainer" : "Jonathan Lee <jon@bigitsystems.com>, Ashish Sahu <ashish.s@bigitsystems.com>",
  "summary": "Big Bot Google Calendar",
  "description": "Google Calendar is a time-management and scheduling calendar service.",
  "category": "productivity",
  "author": "BIG BOTS (PRIVATE LIMITED)",
  "website": "https://bigitsystems.com",
  "auto_install": true,
  "signed_packages":["com.bits.google.create.event"]
}
```



> After creating manifest.json, add requirement.txt file, add external dependencies along and specify the version to use. This step is optional, and dependencies may not be required in many instances.

```text
requests==2.23.0
google-auth-oauthlib==0.4.1
google-api-python-client==1.10.0
```



##### init.py

Create init.py python create , we need this file to register our components.

```python
from contrib.application import AppConfig

class Application(AppConfig):

    def init(self, config):
        pass

    def registry(self, object):
        # register components here
        pass
```



We will register our components under registry function later. At this point your app is recognised by Big Bot framework.



#### component.py

This file is critical to your integration. It contains all of the business logic your Big Bot will rely on. We can create one or more components in this file. Start by creating blank file named component.py. There are many types of components. In this example we need only one, called SkillProvider.

```python
from contrib.application import SkillProvider
from contrib.application import OauthProvider

class GoogleEventProvider(SkillProvider):

    def __init__(self):
        pass

    # abc method
    def auth_providers(self, package):
        # package is unique skill package
        # multiple auth can be used, if your skill provider required more than one type of authentication
        return [OauthProvider.get('google')]

    # abc method
    def on_execute(self, package, data, *args, **kwargs):
        # this method execute when all required data collected from user
        # package is unique skill package
        # data is dictionary object of given user inputs
        pass

    # abc method
    def build_result(self, result, node, *args, **kwargs):
        # result is object that return from on_execute
        # node represent the output result format eg. result can be used for simple text like response or charts
        pass

    # abc method
    def on_event(self, event, *args, **kwargs):
        # this is special method to handle Big Bot events
        # don't get confused with it's name it is not realted to calendar event it is generic method instead
        # useful method for webhooks or other event.
        pass

```



###### SkillProvider Component

This component can be used to build a Big Bot skill. For our google event integration we need to accept various user inputs, e.g. event date, name, attendees. User inputs can only be defined via the skill builder, bot trainer or by manually creating a data.json file. Here is some sample training data. This data can be added directly into your Big Bot integration folder, in our case google_event. You can add more than one skill here.

##### data.json

Important guidance:

* 'package' name must be unique, this identifies your skill globally.
* 'input_arch' represents a sequence of user inputs from chat interface. If not required, set to false, users will then be able to skip this input.
* 'response_arch' is an array of output nodes. Outputs can be formatted in multiple view types. For instance, an output can be a combination of image and text, together. For text like input we recommend using the built-in jinja template engine.

```json
[
  {
 "name": "Add Event (Google)",
 "package": "com.bits.google.create.event",
 "input_arch": [
  {
   "field": "summary",
   "type": "text",
   "string": "Please enter a title for your event.",
   "required": false
  },
  {
   "field": "description",
   "type": "text",
   "string": "Please enter a description for your event.",
   "required": false
  },
  {
   "field": "start_date",
   "type": "date",
   "string": "Please enter a start date for your event.",
   "required": true
  },
  {
   "field": "end_date",
   "type": "date",
   "string": "Please enter end date for your event.",
   "required": true
  },
  {
   "field": "required_attendees",
   "type": "text",
   "string": "Please enter attendees email address.",
   "required": true
  }
 ],
 "response_arch": [
  {
   "node": "big.bot.core.text",
   "content": "{% if result.success %} Your event has been created successfully. {% else %} We got an error while creating your event: {{result.error}} {% endif %}"
  }
 ]
}
]
```



> This training data can be discarded or modified by the user. This data.txt file is optional, since skill can be created via skill builder as well. It is good practice to add minimal/reference skill training data this way.



At this point we are ready to add our integration business logic. Assuming this skill has been triggered by Big Bot and required user input has been collected. For more clarity please refer to the Big Bot operation flow chart.



![Skill Provider Component Workflow](Big Bot-skill-provider-workflow.png)



Create event on google calendar under GoogleEventProvider.

```python
    from django.template import Context, Template
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # handle all business logic here
    def on_execute(self, package, data, *args, **kwargs):
        # chat user id
        user = kwargs.get('user')
        google_oauth = self.get_oauth(user, 'google')
        # data is user inputs collected by Big Bot
        result = self.create_event(data,google_oauth)
        return result

    # this method to create google event using google's calendar api
    def create_event(self, data, oauth):
        data = self.clean_data(data)
        google_credentials = Credentials.from_authorized_user_info({
            "client_id": oauth.CLIENT_ID,
            "client_secret": oauth.CLIENT_SECRET,
            "access_token": oauth.access_token,
            "refresh_token": oauth.refresh_token
        }, scopes=['https://www.googleapis.com/auth/calendar'])
        calendarService = build('calendar', 'v3', credentials=google_credentials)
        result = calendarService.events().insert(calendarId='primary', body=data, sendUpdates="all").execute()
        return result

    # this method helps to build formatted results
    def build_result(self, result, node, *args, **kwargs):
        # result is object that return from on_execute
        # node represent the output result format eg. result can be used for simple text like response or charts
        user = kwargs.get('user')
        if node['node'] == 'big.bot.core.text':
            template = Template(node['content'])
            content = Context({"user": user, "result":result})
            return template.render(content)

    # this method for cleaning our event data, this is optional in many cases
    def clean_data(self, data):
        final_data = {
            'end': {
                'timezone': 'Europe/Zurich'
            },
            'start': {
                'timezone': 'Europe/Zurich'
            },
            'attendees': []
        }
        final_data['end']['date'] = data['end_date']
        final_data['start']['date'] = data['start_date']
        final_data['end']['datetime'] = data['end_date'] + ' 00:00:00'
        final_data['start']['datetime'] =data['start_date'] + ' 00:00:00'
        for attendee in data['required_attendees']:
            final_data['attendees'].append({
                'email': attendee,
                'optional': False
            })
        if data["summary"]:
            final_data["summary"] = data["summary"]
        if data["description"]:
            final_data["description"] = data["description"]
        return final_data

    # abc method
    def on_event(self, event, *args, **kwargs):
        # this is special method to handle Big Bot events
        # don't get confused with it's name it is not realted to calendar event it is generic method instead
        # useful method for webhooks or other event.
        pass
```



Our business logic has now been added to our component. Now we will register this component in our registry.

```python
from contrib.application import AppConfig
from .component import GoogleEventProvider

class Application(AppConfig):

    def init(self, config):
        pass

    def registry(self, object):
        object.register(GoogleEventProvider())
```



## Misc Info

* manifest.json has field name "signed_packages", this is only useful while Big Bot module is published to store.



# Setting Up the Application. 

1. Download the latest version of **customer-bigbot-template**.  
2. Install the required python packages from **requirements.txt**. In some systems during package installation errors occur while installation, please try their respective latest versions.  
3. Make changes in the settings present in **project/settings.py** accordingly as envirnoment variables are set in the file.    
4. Migrate and then create a superuser to login into the **Admin Panel**.  
5. In the **Admin panel**, under **"AUTHENTICATION AND AUTHORIZATION"**, create the following **Groups** : **"bots", "cross", "events", "public", "operator" and "manager"**.




# Registering APIs in the portal for testing

In order to test the api integrations in bigbot, we have to register the api in the portal. Please follow the steps given below:


#### STEP 1 : SET API CREDENTIALS

Login into the admin portal to store the API credentials. Click on ** App datas ** in the menu. Then click on ** ADD APP DATA ** button present in the top right position of the page. Then fill the form accordingly. 

This section sets the AuthProvider component for your API.    
**Component :** This field contains the component's name. It should always be unique.<br/>
**Key :** Always set it as **oauth_settings**<br/>
**Data :** This field contains the api credentials as key, value pairs. This is always set in the json format.

The below given image is shown as the reference for the **STEP 1**


![API Credentials Settings](images/pic1.png)



#### STEP 2 : REGISTER API IN SKILL STORE 

Login into the portal. Then click on **Skill Store** in the menu. Then click on the **Settings** icon, present on the top right corner on the page. Image for reference is given below.
<br />


![API Registration In Portal](images/pic2.png)



On clicking the **settings** icon, the file uploading page will open, as shown below



![API Registration In Portal](images/pic3.png)



Please upload the bigbot api integration in zip format. After the upload, you will find the API listed in the **"Skill Store"** page. Image for reference is given below.



![API Registration In Portal](images/pic4.png)



#### STEP 3 : IMPORT SKILL PROVIDER COMPONENT DATA

Click on the **"Import Data"** button present in the API listed in the **"SKILL STORE"**. Image for reference is given below.
<br />


![API Registration In Portal](images/pic5.png)


Click on **"Skill Interchange"** to check if the API is imported in it or not. If successful then it will be present in the list. Image for reference is given below.
<br />


![API Registration In Portal](images/pic6.png)


  
If you do not see the api listed in **"Skill Interchange"**, then login into the admin portal and click on **"Delegate skills"**. If your api is listed in **"Delegate skills"** then it is successfully imported. Image for reference is given below.



![API Registration In Portal](images/pic8.png)




#### STEP 4 : POINTING THE API SKILLS USING SKILL PROVIDER


**Skills** are the functions or operations that an api will perform, for example create, retrieve, update and delete records. The below given image shows how we point some skill to some skill provider in the admin portal.



![API Registration In Portal](images/Screenshot_2020-11-12_at_9.09.52_PM.png)



##### NOTE : You may have to update the skill import api bit if this field is not created automatically. 

The above can also be achieved from the portal. Clicking on the api listed in **"Skill Interchange"**, the page will open the section as shown in the image given below.



![API Registration In Portal](images/pic9.png)



#### Sample Input Architecture

    "input_arch": [{
        "field" : "summary",
        "type" : "text",
        "string" : "Please enter a title for your event.",
        "required" : false
    },
    {
        "field" : "location",
        "type" : "text",
        "string" : "Please enter a location for your event.",
        "required" : false
    },
    {
        "field" : "start_date",
        "type" : "date",
        "string" : "Please enter a start date for your event.",
        "required" : true
    },
    {
        "field" : "end_date",
        "type" : "date",
        "string" : "Please enter end date for your event.",
        "required" : true
    }]

**"field" :** Name of the field.  
**"type" :** Datatype of the field.  
**"string" :** Placeholder string for the field.  
**"required" :** True/False, if the field is required or is optional.  

##### NOTE : The Input and Response Architecture should be always in JSON format



#### Sample Response Architecture

    "response_arch": [{
        "node" : "big.bot.core.text",
        "content" : "{% if result.executed %}\n Your event has been created successfully.\n{% else %}\n We got an error while creating your event.\n{% endif %}"
    }]
**"node" :** The response type. It can be **"text"**,**"iframe"**, **"image"**, etc.  
**"content" :** The final message that will be displayed on the template. 
