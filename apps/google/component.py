from main.Component import SkillProvider, state_to_string, OAuthProvider
from requests_oauthlib import OAuth2Session
from django.utils import timezone
from dateutil import tz
import datetime
from oauthlib.oauth2 import TokenExpiredError
from django.template import Context, Template
import requests
import json
import uuid
import dateutil.parser
from main.Node import CarouselNode, IFrameNode, SearchNode
from .icon import icon
from urllib.parse import parse_qsl, urlparse, urlencode
import random
from main.Statement import OutputStatement
from .utils import create_map

class GoogleOAuthProvider(OAuthProvider):
    def __init__(self, config):
        self.CLIENT_ID = self.get_variable("com.big.bot.google", "CLIENT_ID")
        self.CLIENT_SECRET = self.get_variable("com.big.bot.google", "CLIENT_SECRET")
        self.TOKEN_URL = "https://www.googleapis.com/oauth2/v4/tokeninfo"
        self.AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
        self.scope = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/calendar",
        ]
        super(GoogleOAuthProvider, self).__init__(config)
        self.update_meta(
            {
                "icon":icon,
                "title" : "Google",
                "description": "You need to authorize your account. "
            }
        )

    def authorization_url(self,redirect_uri, user_id, **kwargs):
        oauth = OAuth2Session(self.CLIENT_ID, redirect_uri=redirect_uri, scope=self.scope)
        #prompt="select_account"
        prompt = "consent"
        authorization_url, state = oauth.authorization_url(
            self.AUTH_URL, 
            access_type="offline", 
            prompt=prompt
        )
        return authorization_url

    def is_authorized(self, oauth, **kwargs):
        req = oauth.get(self.TOKEN_URL)
        if req.status_code == 200:
            return True
        return False

    def fetch_token(self, redirect_uri, authorization_response, *args, **kwargs):
        parsed_url = urlparse(authorization_response)
        query = dict(parse_qsl(parsed_url.query))
        
        data = {}
        data["code"] = query["code"]
        data["client_id"] = self.CLIENT_ID
        data["client_secret"] = self.CLIENT_SECRET
        data["redirect_uri"] = redirect_uri
        data["grant_type"] = "authorization_code"

        r = requests.post(
            "https://oauth2.googleapis.com/token",
            headers={ "Content-Type": "application/x-www-form-urlencoded" },
            data=data
        )
        return json.loads(r.content.decode("utf-8"))

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
        google = OAuth2Session(self.CLIENT_ID, token=token)
        return google.refresh_token(refresh_url, **extra)

class GoogleCalendarEvent(SkillProvider):

    def __init__(self,config):
        self.oauth_component= 'apps.google.component.GoogleOAuthProvider'
        self.scope = ['https://www.googleapis.com/auth/calendar']
        super().__init__(config)

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        # oauth = self.get_provider(self.oauth_component, package, user).oauth()
        oauth = self.oauth(binder, user_id, GoogleOAuthProvider)
        # data = self.clean_data(data)
        url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
        params = {
            'sendUpdates':'all'
        }
        # req = oauth.post(url, json=data, params=params)
        response = oauth.post(package=package, method="execute_skill", values=data)
        result = response.json()

        return result["result"]
        node = kwargs["node"]
        if node['node'] == 'big.bot.core.text':
            t = Template(node['content'])
            c = Context({"user": user, "result":result, "input":input})
            output = t.render(c)
            return output
        elif node['node'] == 'big.bot.core.iframe':
            t = Template(node['content'])
            c = Context({"user": user, "result":result, "input":input})
            output = t.render(c)
            return output

    def on_search(self, binder, user_id, package, searchable, query, *args, **kwargs):
        return []

    def clean_data(self, data):
        final_data = {
            'end': {
                'timezone': 'Asia/Kolkata'
            },
            'start': {
                'timezone': 'Asia/Kolkata'
            },
            'attendees': []
        }
        final_data['end']['date'] = data['end_date']
        final_data['start']['date'] = data['start_date']
        final_data['end']['datetime'] = data['end_date'] + ' 00:00:00'
        final_data['start']['datetime'] =data['start_date'] + ' 00:00:00'
        for attendee in data['required_attendees'].split(','):
            final_data['attendees'].append({
                'email': attendee,
                'optional': False
            })
        if data["summary"]:
            final_data["summary"] = data["summary"]
        if data["description"]:
            final_data["description"] = data["description"]
        return final_data

class EmptyProvider(SkillProvider):

    def __init__(self, config):
        super().__init__(config)

    def auth_providers(self, package, user, *args, **kwargs):
        return []

    def on_search(self, package, user, node, query, *args, **kwargs):
        return []

class UserCalendarEvent(SkillProvider):

    def __init__(self, config):
        super().__init__(config)

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        action_type = data['action_type']
        result = {
            'action_type': action_type,
        }
        if action_type == 'event_signup':
            email = data['attendee_email']
            attendee_name = data['attendee_name']
            event_id = data['event_id']
            values = {
                'email':email,
                'attendee_name':attendee_name,
                'event_name': event_id,
            }
            result.update({'email':email})
            result.update(self._event_signup(values))
        elif action_type == 'need_link':
            email = data['email_link']
            result.update({'email':email})
            result.update(self._need_link(email))
        elif action_type == 'event_feed':
            email = data['certificate_email']
            event_done_action = data['event_done_action']
            event_done_id = data['event_done_id']
            result.update({'email':email,'event_done_action':event_done_action})
            result.update(self._event_feed(email, event_done_action,event_done_id))
        return result

    def _event_signup(self, data):
        form_id = '1FAIpQLSd1Yx9e9yfq8t_hn3Yjn9k30Y8VgXaRvIMuDw5qJExZAdlBpg'
        url = 'https://docs.google.com/forms/d/e/{}/formResponse'.format(form_id)
        form_data = {'emailAddress':data["email"],
                     'entry.1384712452':data["attendee_name"],
                     'entry.114972673':data["event_name"],
                     'draftResponse':[],
                     'pageHistory':0
                     }
        user_agent = {'Referer':'https://docs.google.com/forms/d/e/{}/viewform','User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36".format(form_id)}
        r = requests.post(url, data=form_data, headers=user_agent)
        return {}

    def _need_link(self, email):
        self.services.send_email('Bigbot Event', email, 'Here is event link: '+'https://www.google.com/calendar/about/')
        return {}

    def _event_feed(self, email, event_done_action,event_done_id):
        if event_done_action == 'certificate':
            self.services.send_email('Bigbot Event', email, 'Here is your Certificate for event: '+event_done_id)
        else:
            self.services.send_email('Bigbot Event', email, 'Here is your details for event: '+event_done_id)
        return {}

    def on_search(self, binder, user_id, package, searchable, query, *args, **kwargs):
        # node = kwargs["node"]
        if searchable['model'] == 'google.calendar':
            scope = []
            oauth = self.services.get_oauth_provider('events', 'apps.google.component.GoogleOAuthProvider', scope)

        return super().on_search(package, user_id, searchable, query, *args, **kwargs)

class GoogleScheduleAppointment(SkillProvider):

    def __init__(self, config):
        self.oauth_component= 'apps.google.component.GoogleOAuthProvider'
        self.scope = ['https://www.googleapis.com/auth/calendar']
        self.timeZone = 'Asia/Singapore'
        super().__init__(config)

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):

        oauth = self.oauth(binder, user_id, GoogleOAuthProvider)

        if package == 'com.bigbot.google.appointment.schedule':
            oauth = self.oauth(binder, user_id, GoogleOAuthProvider)
            return self._create_schedule(oauth, user_id, data, *args, **kwargs)
        elif package == 'com.bigbot.google.appointment.booking':
            # Warning need to change in framework
            # Warning not safe could throw error
            # Warning refresh
            user = self.services.get_user(data['user_id'])
            return self._book_schedule(oauth, user, data, *args, **kwargs)

    def on_search(self, binder, user_id, package, searchable, query, *args, **kwargs):
        
        model = searchable.property_value("model")
        # domain = searchable.property_value("domain")
        if package == 'com.bigbot.google.appointment.schedule':
            oauth = self.oauth(binder, user_id, GoogleOAuthProvider)
            # oauth = self.get_provider(self.oauth_component, package, user_id).oauth()
            if model == 'google.calendar':
                return self._get_calendarList(oauth,query)
        
        elif package == 'com.bigbot.google.appointment.booking':
            if model == 'res.users':
                search_result = []
                for item in self.services.search_users(query, ['event']):
                    search_result.append(self.create_search_item(item[1],item[0]))
                return search_result
            elif model == 'google.calendar':
                user_id = self.services.get_user(user_id)
                # Warning need to change in framework
                # Warning not safe could throw error
                # Warning refresh
                return self._get_calendarList(oauth,query)
            elif model == 'calendar.events':
                user_id = self.services.get_user(user_id)
                # oauth = OAuthProvider.get(self.oauth_component, user_id, self.scope)._authenticate()
                calendar_id = data['calendar_id']
                return self._get_groupEventList(oauth,query,calendar_id)
            elif model == 'event.slot':
                data = kwargs.get('data')
                user_id = self.services.get_user(user_id)
                # oauth = OAuthProvider.get(self.oauth_component, user_id, self.scope)._authenticate()
                calendar_id = data['calendar_id']
                return self._get_slotList(oauth,query,calendar_id,data['group_id'])
        items = []
        # result = oauth.post(package=package, method="name_search", query=query, model=model, domain=domain).json()["result"]
        # for item in result:
        #     items.append(SearchNode.wrap_text(item["name"], item["id"]))
        return items
        

        # return []

    def _create_schedule(self, oauth, user, data, *args, **kwargs):
        input_data = kwargs.get('input')
        calendar_id = data['calendar_id']
        all_day = True if data['all_day'] == '1' else False
        if all_day:
            event_slots = self._compute_slot(data['start_date'], data['end_date'], int(data['interval']), all_day)
        else:
            event_slots = self._compute_slot(data['start_datetime'], self._compute_endtime(data['start_datetime'],data['duration']), int(data['interval']), all_day)

        slot_id = str(uuid.uuid4())
        result = []
        for item in event_slots:
            output = self._create_slot(oauth, calendar_id, item[0], item[1], slot_id, data)
            print(output, '<<<<<<<<<<<<<<<')
            result.append(output)

        return result

    def _create_slot(self, oauth, calendarId, start, end, slot_id, data):
        start_datetime = str(datetime.datetime.strptime(str(start), '%Y-%m-%d %H:%M:%S').isoformat())+"Z"
        end_datetime = str(datetime.datetime.strptime(str(end), '%Y-%m-%d %H:%M:%S').isoformat())+"Z"
        clean_data = {
            'start': {
                'timeZone':self.timeZone,
                'dateTime':start_datetime,
            },
            'end': {
                'timeZone':self.timeZone,
                'dateTime':end_datetime,
            },
            'colorId':'5',
            'location':data['location'] if data['location'] else None,
            'summary': data['summary'] if data['summary'] else None,
            'description': data['description'] if data['description'] else None,
            'status':'tentative',
            "extendedProperties": {
                "private": {
                    "slot_id": slot_id,
                }
            },
        }
        if data['google_meet'] == '1':
            clean_data['conferenceDataVersion'] =  1,
            clean_data['conferenceData'] =  {
                "createRequest":{
                    "requestId":  str(uuid.uuid4()),
                    "conferenceSolutionKey":{
                        "type": "hangoutsMeet",
                    }
                }
            }
        filtered = {k: v for k, v in clean_data.items() if v is not None}
        clean_data.clear()
        clean_data.update(filtered)
        print('==================input=============')
        print(clean_data)
        print('==================output=============')
        url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events'.format(calendarId)
        params = {
            'sendUpdates':'none',
            'conferenceDataVersion':1,
        }
        req = oauth.post(url, json=clean_data, params=params)
        return req.json()

    def _book_schedule(self, oauth, oauth_user, data, *args, **kwargs):
        url = "https://www.googleapis.com/calendar/v3/calendars/{}/events/{}".format(data['calendar_id'], data['event_id'])
        clean_data = {
            'status':'confirmed',
            'colorId':'10',
            'attendees':[{
                'email': data['email'],
                'optional': False
            }]
        }
        params = {
            'sendUpdates':'all'
        }
        req = oauth.patch(url, json=clean_data, params=params)
        response = req.json()
        print('=======booked=======',req.url)
        print('=======booked=======',req.json())

        start = response['start'].get('dateTime', response['start'].get('date'))
        start = dateutil.parser.parse(start).strftime("%H:%M %p")
        end = response['end'].get('dateTime', response['end'].get('date'))
        end = dateutil.parser.parse(end).strftime("%H:%M %p")
        message = "{} appointment, slot has been booked by {}, from {} to {}".format(response['summary'],data['email'],start, end)
        self.services.send_notification(oauth_user,message)
        return response

    def _get_calendarList(self, oauth, query):
        data = []
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        req = oauth.get(url)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id':item['id'],
                'timeZone':item['timeZone'],
                'summary':item['summary'],
                'accessRole':item['accessRole'],
                'primary': item['primary'] if 'primary' in item else False,
            }
            refine_data.append([ref['id'],ref['summary']])
        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            data.append(self.create_search_item(item[1],item[0]))
        return data

    def _get_groupEventList(self, oauth, query, calendar_id):
        data = []
        url = "https://www.googleapis.com/calendar/v3/calendars/{}/events".format(calendar_id)
        params = {
        }
        req = oauth.get(url, params=params)
        response = req.json()
        refine_data = []
        refine_dict = {}
        for item in response['items']:
            ref = {
                'id':item['id'],
                'status':item['status'],
                'summary':item['summary'],
                'start':item['start'],
                'end':item['end'],
                'htmlLink':item['htmlLink'],
                'location':item['location'] if 'location' in item else False,
                'extendedProperties':item['extendedProperties'] if 'extendedProperties' in item else False,
                'entryPoints':item['entryPoints'] if 'entryPoints' in item else False,
            }
            print(ref,'-------<<<<')
            # only list with status
            if ref['status'] == 'tentative' and 'extendedProperties' in ref and \
                    'private' in ref['extendedProperties'] and 'slot_id' in ref['extendedProperties']['private']:
                slot_id =  ref['extendedProperties']['private']['slot_id']
                refine_dict[slot_id] = ref['summary']

        for k,v in refine_dict.items():
            refine_data.append([k,v])

        # query filter
        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            data.append(self.create_search_item(item[1],item[0]))
        return data

    def _get_slotList(self, oauth, query, calendar_id, select_group_id):
        data = []
        url = "https://www.googleapis.com/calendar/v3/calendars/{}/events".format(calendar_id)
        params = {
        }
        req = oauth.get(url, params=params)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id':item['id'],
                'status':item['status'],
                'summary':item['summary'],
                'start':item['start'],
                'end':item['end'],
                'htmlLink':item['htmlLink'],
                'location':item['location'] if 'location' in item else False,
                'extendedProperties':item['extendedProperties'] if 'extendedProperties' in item else False,
                'entryPoints':item['entryPoints'] if 'entryPoints' in item else False,
            }
            print(ref,'-------<<<<')
            # only list with status
            if ref['status'] == 'tentative' and 'extendedProperties' in ref and \
                    'private' in ref['extendedProperties'] and 'slot_id' in ref['extendedProperties']['private']:
                slot_id =  ref['extendedProperties']['private']['slot_id']
                if slot_id == select_group_id:
                    start = ref['start'].get('dateTime', ref['start'].get('date'))
                    start = dateutil.parser.parse(start).strftime("%H:%M %p")
                    end = ref['end'].get('dateTime', ref['end'].get('date'))
                    end = dateutil.parser.parse(end).strftime("%H:%M %p")
                    refine_data.append([ref['id'], "{}-{}".format(start,end)])

        # query filter
        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            data.append(self.create_search_item(item[1],item[0]))
        if not data:
            for item in refine_data:
                data.append(self.create_search_item(item[1],item[0]))
        return data

    def _compute_slot(self, start_datetime, end_datetime, interval, all_day=False):
        result = []
        if all_day:
            start = datetime.datetime.strptime(str(start_datetime), '%Y-%m-%d')
            end = datetime.datetime.strptime(str(end_datetime), '%Y-%m-%d')
        else:
            start = datetime.datetime.strptime(str(start_datetime), '%Y-%m-%d %H:%M:%S')
            end = datetime.datetime.strptime(str(end_datetime), '%Y-%m-%d %H:%M:%S')
        while(start < end):
            temp = start + datetime.timedelta(minutes=interval)
            result.append([str(start), str(temp)])
            start = temp
        return result

    def _compute_endtime(self, start_time, duration):
        hrs = int(str(duration).split('.')[0])
        min = int(int(str(duration).split('.')[1])*60/100)
        start = datetime.datetime.strptime(str(start_time), '%Y-%m-%d %H:%M:%S')
        end = start + datetime.timedelta(hours=hrs, minutes=min)
        str_end = str(end)
        return str_end

class ScheduleAppointment(SkillProvider):

    def __init__(self,config):
        self.timeZone = 'Asia/Singapore'
        self.oauth_component= 'apps.google.component.GoogleOAuthProvider'
        self.scope = ['https://www.googleapis.com/auth/calendar']
        self.appointment_model = 'user.appointment'
        super().__init__(config)

    def auth_providers(self, package, user, *args, **kwargs):
        if package == 'com.google.appointment.preference.create':
            return [OAuthProvider.get(self.oauth_component, user, self.scope)]
        elif package == 'com.google.appointment.preference.book':
            return []
        return super().auth_providers(package, user, *args, **kwargs)

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        if package == 'com.google.appointment.preference.create':
            # from pre defined time range
            start_time = str(datetime.time(00, 00, 00))
            end_time = str(datetime.time(23, 59, 59))
            if data['slot_time_range'] :
                if data['slot_time_range'] == "0":
                   start_time = str(datetime.time(10, 00, 00))
                   end_time = str(datetime.time(16, 00, 00))
                elif data['slot_time_range'] == "1":
                   start_time = str(datetime.time(12, 00, 00))
                   end_time = str(datetime.time(18, 00, 00))
                elif data['slot_time_range'] == "2":
                   start_time = str(datetime.time(14, 00, 00))
                   end_time = str(datetime.time(20, 00, 00))
                elif data['slot_time_range'] == "3":
                    start_time = str(datetime.time(16, 00, 00))
                    end_time = str(datetime.time(22, 00, 00))
            resource_id = str(uuid.uuid4())
            resource_data = {
                'resource_id':resource_id,
                'user_id':user_id,
                'meeting_type':data['meeting_type'],
                'calendar_id':data['calendar_id'],
                'calendar_ids':data['calendar_ids'],
                'slot_duration':data['slot_duration'],
                'from_date':data['from_date'],
                'till_date':data['till_date'],
                'google_meet':data['google_meet'],
                'location':data['location'] if data['location'] else '',
                'description':data['description'] if data['description'] else '',
                'slot_interval':data['slot_interval'] if data['slot_interval'] else 0.0,
                'start_time':start_time,
                'end_time':end_time,
            }
            self.services.create_resource(user_id, self.appointment_model, resource_id, resource_data)
            return data
        elif package == 'com.google.appointment.preference.book':
            meeting_type = data['meeting_type']
            resource = self.services.read_resource('user.appointment',meeting_type)
            other_user = self.services.get_user(resource['user_id'])
            other_oauth = OAuthProvider.get(self.oauth_component, other_user, self.scope)._authenticate()
            calendar_id = resource['calendar_id']
            appointment_slot = data['appointment_slot']
            self._create_slot(other_oauth,calendar_id,appointment_slot[0],appointment_slot[1],resource,data['email'])

        return super().on_execute(package, user_id, data, *args, **kwargs)

    def on_search(self, binder,user_id, package, searchable, query, *args, **kwargs):
        node = kwargs["node"]
        if package == 'com.google.appointment.preference.create':
            oauth = self.get_provider(self.oauth_component, package, user_id).oauth()
            if node['model'] == 'google.calendar':
                saved_data = kwargs.get('data')
                return self._get_calendarList(oauth,query,saved_data,'calendar_ids')
            elif node['model'] == 'google.calendar.selection':
                saved_data = kwargs.get('data')
                return self._get_calendarList(oauth,query,saved_data,None)
        elif package == 'com.google.appointment.preference.book':
            if node['model'] == 'user.appointment':
                search_resources = self.services.search_resource(None,node['model'])
                search_items = []
                refine_data = []
                for item in search_resources:
                    meeting_type = item['meeting_type']
                    resource_id = item['resource_id']
                    refine_data.append([resource_id,meeting_type])
                for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
                    search_items.append(self.create_search_item(item[1],item[0]))
                return search_items
            elif node['model'] == 'appointment.slot':
                data = kwargs.get('data')
                anchor_date = data['anchor_date']
                meeting_type = data['meeting_type']
                resource = self.services.read_resource('user.appointment',meeting_type)
                calendar_ids = resource['calendar_ids']
                calendar_id = resource['calendar_id']
                slot_duration = self._to_minutes(resource['slot_duration'])
                slot_interval = self._to_minutes(resource['slot_interval'])

                slots = self._compute_slots(anchor_date, resource['from_date'], resource['till_date'],
                                            resource['start_time'],resource['end_time'], slot_duration, slot_interval)
                other_user = self.services.get_user(resource['user_id'])
                other_oauth = OAuthProvider.get(self.oauth_component, other_user, self.scope)._authenticate()
                search_items = []
                search_items_max = 4
                for item in slots:
                    if len(search_items) == search_items_max:
                        break
                    if self._is_free(other_oauth,calendar_ids,item[0],item[1]):
                        st = datetime.datetime.strptime(item[0], "%Y-%m-%d %H:%M:%S")
                        st = st.strftime("%I:%M")
                        ed = datetime.datetime.strptime(item[1], "%Y-%m-%d %H:%M:%S")
                        ed = ed.strftime("%I:%M %p %d %b")
                        value = item
                        text = st+"-"+ed
                        search_items.append(self.create_search_item(text, value))
                return search_items

        return super().on_search(package, user_id, node, query, *args, **kwargs)

    def match_input(self, package, user, node, input, body, *args, **kwargs):
        search_items = self.on_search(package,user,node,body,*args,**kwargs)
        for item in search_items:
            if item['text'].lower() == body.lower():
                return item['value']
        return None

    def _get_calendarList(self, oauth, query, saved_data, match_field):
        data = [self.create_search_item('Submit',"\()")]
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        req = oauth.get(url)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id':item['id'],
                'timeZone':item['timeZone'],
                'summary':item['summary'],
                'accessRole':item['accessRole'],
                'primary': item['primary'] if 'primary' in item else False,
            }
            refine_data.append([ref['id'],ref['summary']])

        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            if match_field is not None:
                if saved_data and match_field in saved_data:
                    if item[0] in saved_data[match_field]:
                        continue
            data.append(self.create_search_item(item[1],item[0]))

        return data

    def _compute_slots(self, anchor_date, from_date, to_date, start_time, end_time, duration, interval, boundary):
        result = []
        from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").date()
        anchor_date = datetime.datetime.strptime(anchor_date, "%Y-%m-%d").date()
        start_time = datetime.datetime.strptime(start_time, "%H:%M:%S").time()
        end_time = datetime.datetime.strptime(end_time, "%H:%M:%S").time()

        temp_date = anchor_date
        left = True
        shifter = 1
        count = 0
        while from_date <= to_date:
            if count == boundary:
                break
            temp_slot = 0
            start_datetime = str(temp_date)+" "+str(start_time)
            end_datetime = str(temp_date)+" "+str(end_time)

            datetime_start = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
            end = datetime.datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
            while(datetime_start < end):
                datetime_end = datetime_start + datetime.timedelta(minutes=duration)
                if datetime.datetime.now() < datetime_start:
                    result.append([str(datetime_start), str(datetime_end)])
                datetime_start = datetime_end + datetime.timedelta(minutes=interval)

            from_date += datetime.timedelta(days=1)

            if left and temp_date >= from_date:
                temp_date = anchor_date + datetime.timedelta(days=-shifter)
                left = False
            else:
                if temp_date < to_date:
                    temp_date = anchor_date + datetime.timedelta(days=shifter)
                    shifter += 1
                    left = True

        return result

    def _is_free(self, oauth, calendar_id,  start, end):
        start_datetime = str(datetime.datetime.strptime(str(start), '%Y-%m-%d %H:%M:%S').isoformat())+"+08:00"
        end_datetime = str(datetime.datetime.strptime(str(end), '%Y-%m-%d %H:%M:%S').isoformat())+"+08:00"
        freebusyurl = 'https://www.googleapis.com/calendar/v3/freeBusy'
        data = {
            "timeMin": start_datetime,
            "timeMax": end_datetime,
            "timeZone": self.timeZone,
            "groupExpansionMax": 100,
            "calendarExpansionMax": 50,
            "items": [
            ]
        }
        for c_id in calendar_id:
            data['items'].append({'id': c_id})

        req = oauth.post(freebusyurl, json=data).json()
        for c_id in calendar_id:
            if req['calendars'][c_id]['busy']:
                return False
        return True

    def _to_minutes(self, duration):
        hrs = int(str(duration).split('.')[0])
        min = int(int(str(duration).split('.')[1])*60/100)
        return (hrs*60)+min

    def _create_slot(self, oauth, calendarId, start, end, data, email):
        start_datetime = str(datetime.datetime.strptime(str(start), '%Y-%m-%d %H:%M:%S').isoformat())+"+08:00"
        end_datetime = str(datetime.datetime.strptime(str(end), '%Y-%m-%d %H:%M:%S').isoformat())+"+08:00"
        clean_data = {
            'start': {
                'timeZone':self.timeZone,
                'dateTime':start_datetime,
            },
            'end': {
                'timeZone':self.timeZone,
                'dateTime':end_datetime,
            },
            'colorId':'5',
            'location':data['location'] if 'location' in data and data['location'] else None,
            'summary': data['meeting_type'] if 'meeting_type' in data and data['meeting_type'] else None,
            'description': data['description'] if 'description' in data and data['description'] else None,
            'status':'confirmed',
            'attendees':[{
                'email': email,
                'optional': False
            }],
            "extendedProperties": {
                "private": {

                }
            },
        }


        if 'google_meet' in data and data['google_meet'] == '1':
            clean_data['conferenceDataVersion'] =  1,
            clean_data['conferenceData'] =  {
                "createRequest":{
                    "requestId":  str(uuid.uuid4()),
                    "conferenceSolutionKey":{
                        "type": "hangoutsMeet",
                    }
                }
            }

        filtered = {k: v for k, v in clean_data.items() if v is not None}
        clean_data.clear()
        clean_data.update(filtered)
        print('==================input=============')
        print(clean_data)
        print('==================output=============')
        url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events'.format(calendarId)
        params = {
            'sendUpdates':'all',
            'conferenceDataVersion':1,
        }
        req = oauth.post(url, json=clean_data, params=params)
        print(req,'========final===')
        return req.json()

class RouteForScheduleProvider(SkillProvider):
    def __init__(self,config):
        self.oauth_component = GoogleOAuthProvider(config)
        self.api_key = self.get_variable("com.big.bot.google", "API_KEY")
        self.country = self.get_variable("com.big.bot.google", "ORIGIN_COUNTRY")
        self.geocode_api = "https://maps.googleapis.com/maps/api/geocode/json"
        self.direction_api = "https://maps.googleapis.com/maps/api/directions/json"
        self.calendar_colors = []
        super().__init__(config)

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        loading = OutputStatement(user_id)
        loading.append_text("Generating the results. Please wait.")
        binder.post_message(loading)

        token = self.oauth_component.load_token(binder, binder.on_load_state().user_id)
        oauth = self.oauth_component.build_oauth(token)
        self._update_calendar_colors(oauth)

        calendar_id = data["calendar_id"]
        start_datetime = data["start_datetime"]
        start_place = self._get_geocode_from_postal(data["start_place"] + " " + self.country)
        loop_exists = True if data.get("loop_1") else False
        destination = (
            data["loop_1"]["loop_data"]["destination"] if loop_exists
            else data["destination"]
        )
        destination_title = (
            data["loop_1"]["loop_data"]["title"] if loop_exists
            else data["title"]
        )
        destination_duration = (
            data["loop_1"]["loop_data"]["duration"] if loop_exists
            else data["duration"]
        )
        loop_count = data["loop_1"]["loop_count"] if loop_exists else 0
    
        places = [start_place]
        routes = []
        events = []
        colors = []
        if loop_count == 0:
            destination_geocode = self._get_geocode_from_postal(destination + " " + self.country)
            places.append(destination_geocode)
            route = self._get_route(start_place["place_id"], destination_geocode["place_id"])
            routes.append(route)
            start = {
                "dateTime": self._convert_to_datetime_string(
                    self._get_datetime_from_string(start_datetime)
                )
            }
            end = {
                "dateTime": self._convert_to_datetime_string(
                    self._get_end_datetime(start_datetime, destination_duration)
                )
            }
            color_id = random.randint(1, len(self.calendar_colors))
            colors.append(self.calendar_colors[str(color_id)])
            event = self._create_calendar_event(
                oauth,
                calendar_id,
                start = start,
                end = end,
                summary = destination_title,
                location = destination_geocode["address"],
                color_id = str(color_id)
            )
            events.append(event)
        else:
            last_start_place = start_place
            last_start_datetime = start_datetime
            for i in range(loop_count):
                destination_geocode = (
                    self._get_geocode_from_postal(destination[i] + " " + self.country)
                )
                places.append(destination_geocode)
                route = self._get_route(
                    last_start_place["place_id"], destination_geocode["place_id"]
                )
                routes.append(route)
                start = {
                    "dateTime": self._convert_to_datetime_string(
                        self._get_datetime_from_string(last_start_datetime)
                        + datetime.timedelta(seconds=route["duration"]["value"])
                    )
                }
                end = {
                    "dateTime": self._convert_to_datetime_string(
                        self._get_end_datetime(
                            start["dateTime"],
                            destination_duration[i]
                        )
                    )
                }
                color_id = random.randint(1, len(self.calendar_colors))
                colors.append(self.calendar_colors[str(color_id)])
                event = self._create_calendar_event(
                    oauth,
                    calendar_id,
                    start = start,
                    end = end,
                    summary = destination_title[i],
                    location = destination_geocode["address"],
                    color_id = str(color_id)
                )
                events.append(event)
                last_start_place = destination_geocode
                last_start_datetime = end["dateTime"]

        output = OutputStatement(user_id)
        output.append_text("Here's the routes for your schedule.")
        output.append_node(
            IFrameNode(
                create_map(self.api_key, start_datetime, routes, places, events, colors),
                {"type": "map"}
            ),
        )
        output.append_text("Here are the schedules in your calendar.")
        for i in range(len(events)):
            events[i]["color"] = colors[i]
        output.append_node(
            CarouselNode(
                events,
                {"type": "google_event"}
            )
        )
        binder.post_message(output)
        print("ROUTES", routes, sep=">>>")
        print("EVENTS", events, sep=">>>")
        print("COLORS", colors, sep=">>>")
        print("PLACES", places, sep=">>>")
        return "Success"

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        token = self.oauth_component.load_token(binder, user_id)
        oauth = self.oauth_component.build_oauth(token)
        saved_data = kwargs.get('data')
        return self._get_calendarList(oauth,query, saved_data, None)

    def _update_calendar_colors(self, oauth):
        url = "https://www.googleapis.com/calendar/v3/colors"
        r = oauth.get(url)
        if r.status_code == 200:
            body = r.json()
            self.calendar_colors = body["event"]
        else:
            self.calendar_colors = []

    def _get_calendarList(self, oauth, query, saved_data, match_field):
        data = []
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        req = oauth.get(url)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id': item['id'],
                'timeZone': item['timeZone'],
                'summary': item['summary'],
                'accessRole': item['accessRole'],
                'primary': item['primary'] if 'primary' in item else False,
            }
            refine_data.append([ref['id'],ref['summary']])

        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            if match_field is not None:
                if saved_data and match_field in saved_data:
                    if item[0] in saved_data[match_field]:
                        continue
            data.append(SearchNode.wrap_text(item[1], item[0]))
        return data

    def _get_geocode_from_postal(self, postal_code):
        params = {"address": postal_code, "key": self.api_key}
        query = "?" + urlencode(params)
        url = self.geocode_api + query
        r = requests.get(url=url)
        if r.status_code == 200:
            body = json.loads(r.content.decode("utf-8"))
            result = body["results"][0]
            return {
                "address": result["formatted_address"],
                "location": result["geometry"]["location"],
                "place_id": result["place_id"]
            }
        else:
            # raise exception or logs error
            return None

    def _get_route(self, start, end):
        params = {
            "origin": "place_id:" + start,
            "destination": "place_id:" + end,
            "key": self.api_key
        }
        query = "?" + urlencode(params)
        url = self.direction_api + query
        r = requests.get(url=url)
        if r.status_code == 200:
            body = json.loads(r.content.decode("utf-8"))
            result = body["routes"][0]
            return {
                    "overview_polyline": result["overview_polyline"],
                    "duration": result["legs"][0]["duration"],
                    "distance": result["legs"][0]["distance"],
            }
        else:
            # raise exception or logs error
            return None

    def _get_datetime_from_string(self, datetime_string):
        datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        return datetime.datetime.strptime(datetime_string, datetime_format)

    def _get_end_datetime(self, start, duration):
        start = self._get_datetime_from_string(start)
        return (
            start
            + datetime.timedelta(hours=duration[0], minutes=duration[1])
        )

    def _convert_to_datetime_string(self, datetime_obj):
        datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        return datetime_obj.strftime(datetime_format)

    def _create_calendar_event(self, oauth, calendar_id, **kwargs):
        url = "https://www.googleapis.com/calendar/v3/calendars/" + calendar_id + "/events"
        data = {
            "start": kwargs.get("start"),
            "end": kwargs.get("end"),
            "summary": kwargs.get("summary"),
            "description": "Event added automatically by Big Bot",
            "location": kwargs.get("location"),
            "colorId": kwargs.get("color_id")
        }
        r = oauth.post(url, json=data)
        if r.status_code == 200:
            body = r.json()
            return {
                "id": body["id"],
                "summary": body["summary"],
                "description": body["description"],
                "status": body["status"],
                "htmlLink": body["htmlLink"],
                "created": body["created"],
                "colorId": body["colorId"],
                "start": body["start"],
                "end": body["end"],
                "location": body["location"]
            }
        else:
            # raise exception or logs error
            return None