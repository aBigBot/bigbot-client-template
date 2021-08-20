from contrib.application import OAuthProvider
from requests_oauthlib import OAuth2Session
from contrib.application import SkillProvider
from django.utils import timezone
import datetime
from oauthlib.oauth2 import TokenExpiredError
from django.template import Context, Template
import dateutil.parser

#update this
# import os
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
# os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'
#

class OutlookOAuthProvider(OAuthProvider):
    def __init__(self,config):
        self.AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.CLIENT_ID = self.get_variable('com.big.bot.outlook',"CLIENT_ID")
        self.CLIENT_SECRET = self.get_variable('com.big.bot.outlook',"CLIENT_SECRET")
        self.SCOPE = []
        super().__init__(config)

    def authorization_url(self, redirect_uri, user_id, **kwargs):
        oauth = OAuth2Session(self.CLIENT_ID, redirect_uri=redirect_uri, scope=self.SCOPE)
        prompt="select_account"
        #prompt = "consent"
        authorization_url, state = oauth.authorization_url(
            self.AUTH_URL,
            access_type="offline",
            prompt=prompt
        )
        return authorization_url

    def fetch_token(self, redirect_uri, authorization_response,*args,**kwargs):
        oauth = OAuth2Session(self.CLIENT_ID, redirect_uri=redirect_uri, scope=self.SCOPE)
        return oauth.fetch_token(
            self.TOKEN_URL,
            authorization_response=authorization_response,
            client_secret=self.CLIENT_SECRET
        )

    def build_oauth(self, token, **kwargs):
        return OAuth2Session(token=token)

    def is_authorized(self, oauth, **kwargs):
        req = oauth.get(self.TOKEN_URL)
        if req.status_code == 200:
            return True
        return False

    def is_expired(self, user_id, token, *args, **kwargs):
        oauth = self.build_oauth(token)
        try:
            oauth.get('{0}/contacts'.format('https://graph.microsoft.com/v1.0/me'), params='')
        except TokenExpiredError:
            return True
        return False

    def refresh_token(self, user_id, token, **kwargs):
        refresh_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        extra = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }
        outlook = OAuth2Session(self.CLIENT_ID, token=token)
        return outlook.refresh_token(refresh_url, **extra)


class OutlookCalendarEvent(SkillProvider):

    def __init__(self, config):
        self.oauth_component= 'apps.outlook.component.OutlookOAuthProvider'
        self.scope = ["openid","profile","offline_access","user.read","Contacts.ReadWrite","Calendars.ReadWrite"]
        self.graph_url = 'https://graph.microsoft.com/v1.0/me'
        super().__init__(config)


    def auth_providers(self, package, user, *args, **kwargs):
        return [OAuthProvider.get(self.oauth_component, user, self.scope)]

    def on_execute(self, binder, user, package, data, *args, **kwargs):
        oauth = self.get_provider(self.oauth_component, package, user).oauth()
        response = self.create_event(package, data, oauth)
        if 'error' in response:
            return {
                'executed':False,
            }
        response['executed'] = True
        return response

    def create_event(self, package, data, oauth):
        # data required by outlook
        event = {
            "subject": data["summary"],
            "body": {
                "contentType": "HTML",
                "content": data["description"]
            },
            "start": {
                "dateTime": data['start_date']+' 00:00:00',
                "timeZone": "Pacific Standard Time"
            },
            "end": {
                "dateTime":data['end_date']+' 00:00:00',
                "timeZone": "Pacific Standard Time"
            },
            "location":{
                "displayName":data["location"]
            },
        }
        print('==========',event)
        print('=====going for=====',package)

        if package == 'com.bits.google.create.event':
            event['start']['dateTime'] = data['start_date']
            event['end']['end_date'] = data['end_date']

        attendees = []

        for attendee in data["required_attendees"].split(","):
            name = attendee.split("<")[0].strip()
            mail = attendee.split("<")[-1].replace(">", "").strip()
            attendees.append(
                {
                    "emailAddress": {
                        "address": mail,
                        "name": name
                    }
                }
            )

        event["attendees"] = attendees

        headers = { 'Content-Type':'application/json' }
        response = oauth.post('{0}/events'.format(self.graph_url), json=event, headers=headers)
        result =  response.json()
        print('====RESULT FINAL======',result)
        return result



    def build_text(self, package, user, content, result, *args, **kwargs):
        template = Template(content)
        content = Context({"user": user, "result":result})
        return template.render(content)

    def build_result(self, package, user, node, result, *args, **kwargs):
        if node['node'] == 'big.bot.core.text':
            template = Template(node['content'])
            content = Context({"user": user, "result":result})
            return template.render(content)

    def on_search(self, package, user, node, query, *args, **kwargs):
        oauth = self.get_provider(self.oauth_component, package, user).oauth()
        contacts = oauth.get('{0}/contacts'.format(self.graph_url), params=query)
        data = []
        for item in contacts.json()["value"]:
            data.append(self.create_search_item(text=item["displayName"],value=item["emailAddresses"][0]["address"],extra={}))
        return data
    
    
    
class OutlookScheduleAppointment(SkillProvider):
    def __init__(self):
        self.oauth_component= 'apps.outlook.component.OutlookOAuthProvider'
        self.scope = ["openid","profile","offline_access","user.read","Contacts.ReadWrite","Calendars.ReadWrite"]
        self.graph_url = 'https://graph.microsoft.com/v1.0/me'
        self.timeZone = 'Asia/Singapore'
        super().__init__(Descriptor('Outlook owner appointment.'))
        
    def auth_providers(self, package, user):
        if package == 'com.bigbot.outlook.appointment.schedule':
            return [OAuthProvider.get(self.oauth_component, user, self.scope)]
        return []
    
    def on_execute(self, package, user, data, *args, **kwargs):
        if package == 'com.bigbot.outlook.appointment.schedule':
            oauth = self.get_provider(self.oauth_component, package, user).oauth()
            return self._create_schedule(oauth, user, data, *args, **kwargs)
        elif package == 'com.bigbot.outlook.appointment.booking':
            # Warning need to change in framework
            # Warning not safe could throw error
            # Warning refresh
            user = self.services.get_user(data['user_id'])
            oauth = OAuthProvider.get(self.oauth_component, user, self.scope)._authenticate()
            return self._book_schedule(oauth, user, data, *args, **kwargs)
        
    def on_search(self, package, user, node, query, *args, **kwargs):
        if package == 'com.bigbot.outlook.appointment.schedule':
            oauth = self.get_provider(self.oauth_component, package, user).oauth()
            if node['model'] == 'outlook.calendar':
                return self._get_calendarList(oauth,query)
        elif package == 'com.bigbot.outlook.appointment.booking':
            if node['model'] == 'res.users':
                search_result = []
                for item in self.services.search_users(query, ['event']):
                    search_result.append(self.create_search_item(item[1],item[0]))
                return search_result
            elif node['model'] == 'outlook.calendar':
                data = kwargs.get('data')
                user = self.services.get_user(data['user_id'])
                # Warning need to change in framework
                # Warning not safe could throw error
                # Warning refresh
                oauth = OAuthProvider.get(self.oauth_component, user, self.scope)._authenticate()
                return self._get_calendarList(oauth,query)
            elif node['model'] == 'calendar.events':
                data = kwargs.get('data')
                user = self.services.get_user(data['user_id'])
                oauth = OAuthProvider.get(self.oauth_component, user, self.scope)._authenticate()
                calendar_id = data['calendar_id']
                return self._get_groupEventList(oauth,query,calendar_id)
            elif node['model'] == 'event.slot':
                data = kwargs.get('data')
                user = self.services.get_user(data['user_id'])
                oauth = OAuthProvider.get(self.oauth_component, user, self.scope)._authenticate()
                calendar_id = data['calendar_id']
                return self._get_slotList(oauth,query,calendar_id,data['group_id'])

        return []
    
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
            'location': {
                "displayName": data['location'] if data['location'] else None
            },
            'subject': data['summary'] if data['summary'] else None,
            'body': {
                "contentType": "HTML",
                "content": data['description'] if data['description'] else None
            },
            "allowNewTimeProposals" : True,
        }
        if data['teams'] == '1':
            clean_data['isOnlineMeeting'] =  True,
            clean_data["onlineMeetingProvider"]: "teamsForBusiness"
            
        filtered = {k: v for k, v in clean_data.items() if v is not None}
        clean_data.clear()
        clean_data.update(filtered)
        print('==================input=============')
        print(clean_data)
        print('==================output=============')
        
        headers = { 'Content-Type':'application/json' }
        response = oauth.post('{}/calendars/{}/events'.format(self.graph_url,calendarId), json=clean_data, headers=headers)    
        return response.json()
    
    
    def _book_schedule(self, oauth, oauth_user, data, *args, **kwargs):
        url = "{}/calendars/{}/events/{}".format(self.graph_url, data['calendar_id'], data['event_id'])
        clean_data = {
            "attendees": [
                    {
                    "emailAddress": {
                        "address":data['email'],
                    },
                    "type": "required"
                    }
                ],
        }
        
        headers = { 'Content-Type':'application/json' }
        req = oauth.patch(url, json=clean_data, headers=headers)
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
        url = "{}/calendars".format(self.graph_url)
        req = oauth.get(url)
        response = req.json()
        refine_data = []
        for item in response['value']:
            ref = {
                'id':item['id'],
                'name':item['name'],
            }
            refine_data.append([ref['id'],ref['name']])
        for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
            data.append(self.create_search_item(item[1],item[0]))
        return data
    
    def _get_groupEventList(self, oauth, query, calendar_id):
        data = []
        url = "{}/calendars/{}/events".format(self.graph_url,calendar_id)
        params = {
        }
        req = oauth.get(url, params=params)
        response = req.json()
        refine_data = []
        refine_dict = {}
        for item in response['value']:
            ref = {
                'id':item['id'],
                'subject':item['subject'],
                'start':item['start'],
                'end':item['end'],
                'webLink':item['webLink'],
                'location':item['location']["displayName"] if 'location' in item else False,
            }
            print(ref,'-------<<<<')
            # only list with status
            # if ref['status'] == 'tentative' and 'extendedProperties' in ref and \
            #         'private' in ref['extendedProperties'] and 'slot_id' in ref['extendedProperties']['private']:
            #     slot_id =  ref['extendedProperties']['private']['slot_id']
            #     refine_dict[slot_id] = ref['subject']

        # for k,v in refine_dict.items():
        #     refine_data.append([k,v])

        # query filter
        # for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
        #     data.append(self.create_search_item(item[1],item[0]))
        return data
    
    def _get_slotList(self, oauth, query, calendar_id, select_group_id):
        data = []
        url = "{}/calendars/{}/events".format(self.graph_url, calendar_id)
        params = {
        }
        req = oauth.get(url, params=params)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id':item['id'],
                'subject':item['subject'],
                'start':item['start'],
                'end':item['end'],
                'webLink':item['webLink'],
                'location':item['location']["displayName"] if 'location' in item else False,
                # 'extendedProperties':item['extendedProperties'] if 'extendedProperties' in item else False,
                # 'entryPoints':item['entryPoints'] if 'entryPoints' in item else False,
            }
            print(ref,'-------<<<<')
            # only list with status
        #     if ref['status'] == 'tentative' and 'extendedProperties' in ref and \
        #             'private' in ref['extendedProperties'] and 'slot_id' in ref['extendedProperties']['private']:
        #         slot_id =  ref['extendedProperties']['private']['slot_id']
        #         if slot_id == select_group_id:
        #             start = ref['start'].get('dateTime', ref['start'].get('date'))
        #             start = dateutil.parser.parse(start).strftime("%H:%M %p")
        #             end = ref['end'].get('dateTime', ref['end'].get('date'))
        #             end = dateutil.parser.parse(end).strftime("%H:%M %p")
        #             refine_data.append([ref['id'], "{}-{}".format(start,end)])

        # # query filter
        # for item in [i for i in  refine_data if query.lower() in i[1].lower()] if query else refine_data:
        #     data.append(self.create_search_item(item[1],item[0]))
        # if not data:
        #     for item in refine_data:
        #         data.append(self.create_search_item(item[1],item[0]))
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
    def __init__(self, config):
        self.timeZone = 'Asia/Singapore'
        self.oauth_component= 'apps.outlook.component.OutlookOAuthProvider'
        self.appointment_model = 'user.appointment'
        self.scope = ["openid","profile","offline_access","user.read","Contacts.ReadWrite","Calendars.ReadWrite"]
        self.graph_url = 'https://graph.microsoft.com/v1.0/me'
        super().__init__(config)
        
    def auth_providers(self, package, user):
        if package == 'com.outlook.appointment.preference.create':
            return [OAuthProvider.get(self.oauth_component, user, self.scope)]
        elif package == 'com.outlook.appointment.preference.book':
            return []
        return super().auth_providers(package, user)

    def on_execute(self, package, user, data, *args, **kwargs):
        if package == 'com.outlook.appointment.preference.create':
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
            # resource_id = str(uuid.uuid4())
            resource_data = {
                # 'resource_id':resource_id,
                'user_id':user.id,
                'meeting_type':data['meeting_type'],
                'calendar_id':data['calendar_id'],
                'calendar_ids':data['calendar_ids'],
                'slot_duration':data['slot_duration'],
                'from_date':data['from_date'],
                'till_date':data['till_date'],
                'teams':data['teams'],
                'location':data['location'] if data['location'] else '',
                'description':data['description'] if data['description'] else '',
                'slot_interval':data['slot_interval'] if data['slot_interval'] else 0.0,
                'start_time':start_time,
                'end_time':end_time,
            }
            self.services.create_resource(user, self.appointment_model, resource_id, resource_data)
            return data
        elif package == 'com.outlook.appointment.preference.book':
            meeting_type = data['meeting_type']
            resource = self.services.read_resource('user.appointment',meeting_type)
            other_user = self.services.get_user(resource['user_id'])
            other_oauth = OAuthProvider.get(self.oauth_component, other_user, self.scope)._authenticate()
            calendar_id = resource['calendar_id']
            appointment_slot = data['appointment_slot']
            self._create_slot(other_oauth,calendar_id,appointment_slot[0],appointment_slot[1],resource,data['email'])

        return super().on_execute(package, user, data, *args, **kwargs)
    
    
    def on_search(self, package, user, node, query, *args, **kwargs):
        if package == 'com.outlook.appointment.preference.create':
            oauth = self.get_provider(self.oauth_component, package, user).oauth()
            if node['model'] == 'outlook.calendar':
                saved_data = kwargs.get('data')
                return self._get_calendarList(oauth,query,saved_data,'calendar_ids')
            elif node['model'] == 'outlook.calendar.selection':
                saved_data = kwargs.get('data')
                return self._get_calendarList(oauth,query,saved_data,None)
        elif package == 'com.outlook.appointment.preference.book':
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

        return super().on_search(package, user, node, query, *args, **kwargs)
    
    def match_input(self, package, user, node, input, body, *args, **kwargs):
        search_items = self.on_search(package,user,node,body,*args,**kwargs)
        for item in search_items:
            if item['text'].lower() == body.lower():
                return item['value']
        return None
    
    def _get_calendarList(self, oauth, query, saved_data, match_field):
        data = [self.create_search_item('Submit',"\()")]
        url = "{}/calendars".format(self.graph_url)
        req = oauth.get(url)
        response = req.json()
        refine_data = []
        for item in response['items']:
            ref = {
                'id':item['id'],
                'name':item['name'],
            }
            refine_data.append([ref['id'],ref['name']])

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
        freebusyurl = '{}/calendar/getSchedule '.format(self.graph_url)
        data = {
            "startTime": {
                    "dateTime": start_datetime,
                    "timeZone": self.timeZone
                },
            "endTime": {
                    "dateTime": end_datetime,
                    "timeZone": self.timeZone
                },
            "availabilityViewInterval": 60,
            "schedules": [],
        }
        for c_id in calendar_id:
            data['items'].append({'id': c_id})

        req = oauth.post(freebusyurl, json=data).json()
        for c_id in calendar_id:
            if req['calendars'][c_id]['busy']:
                return False
        return True