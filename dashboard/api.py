from abc import ABC, abstractmethod
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import AccessToken,ApiKeys
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import QueryDict


POLICY_NONE = 0
POLICY_PARTNER = 1
POLICY_USER = 2
POLICY_API_KEYS = 3

class POST:

    def __init__(self,request):
        self.request = request

    def get_bool(self,key):
        object = self.request.POST.get(key)
        if not object:
            return False
        else:
            if object.lower() == 'true':
                return True
        return False

    def get_int(self,key):
        object = self.request.POST.get(key)
        if object:
            return int(object)
        return 0

    def get_float(self,key):
        object = self.request.POST.get(key)
        if object:
            return float(object)
        return 0.0

    def get_string(self,key):
        object = self.request.POST.get(key,False)
        if not object:
            return False
        elif len(object.strip()) != 0:
            return object
        return False

    def get_email(self,key):
        object = self.request.POST.get(key,False)
        if not object:
            return False
        try:
            validate_email(object)
        except ValidationError as e:
            return False
        else:
            return object

    def get_date(self, key):
        object = self.request.POST.get(key,False)
        if not object:
            return False
        import datetime
        date_format = '%Y-%m-%d'
        try:
            datetime.datetime.strptime(object, date_format)
            return object
        except ValueError:
            return False

    def get_body(self):
        if self.request.META.get('CONTENT_TYPE', '').lower() == 'application/json' and len(self.request.body) > 0:
            try:
                return json.loads(self.request.body)
            except Exception as e:
                pass
        return False

class GET:

    def __init__(self,request):
        self.request = request

    def get_bool(self,key):
        object = self.request.GET.get(key)
        if not object:
            return False
        else:
            if object.lower() == 'true':
                return True
        return False

    def get_int(self,key):
        object = self.request.GET.get(key)
        if object:
            return int(object)
        return False

    def get_float(self,key):
        object = self.request.GET.get(key)
        if object:
            return float(object)
        return False

    def get_string(self,key):
        object = self.request.GET.get(key,False)
        if not object:
            return False
        elif len(object.strip()) != 0:
            return object
        return False

    def get_email(self,key):
        object = self.request.GET.get(key,False)
        if not object:
            return False
        try:
            validate_email(object)
        except ValidationError as e:
            return False
        else:
            return object

    def get_date(self, key):
        object = self.request.GET.get(key,False)
        if not object:
            return False
        import datetime
        date_format = '%Y-%m-%d'
        try:
            datetime.datetime.strptime(object, date_format)
            return object
        except ValueError:
            return False

class PUT:
    def __init__(self,request):
        self.request = request
        self.body = QueryDict(request.body)

    def get_bool(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        else:
            if object.lower() == 'true':
                return True
        return False

    def get_int(self,key):
        object = self.body[key] if key in self.body else False
        if object:
            return int(object)
        return 0

    def get_float(self,key):
        object = self.body[key] if key in self.body else False
        if object:
            return float(object)
        return 0.0

    def get_string(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        elif len(object.strip()) != 0:
            return object
        return False

    def get_email(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        try:
            validate_email(object)
        except ValidationError as e:
            return False
        else:
            return object

    def get_date(self, key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        import datetime
        date_format = '%Y-%m-%d'
        try:
            datetime.datetime.strptime(object, date_format)
            return object
        except ValueError:
            return False

    def get_body(self):
        if self.request.body:
            return json.loads(self.request.body)
        return False

class DELETE:

    def __init__(self,request):
        self.request = request
        self.body = QueryDict(request.body)

    def get_bool(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        else:
            if object.lower() == 'true':
                return True
        return False

    def get_int(self,key):
        object = self.body[key] if key in self.body else False
        if object:
            return int(object)
        return 0

    def get_float(self,key):
        object = self.body[key] if key in self.body else False
        if object:
            return float(object)
        return 0.0

    def get_string(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        elif len(object.strip()) != 0:
            return object
        return False

    def get_email(self,key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        try:
            validate_email(object)
        except ValidationError as e:
            return False
        else:
            return object

    def get_date(self, key):
        object = self.body[key] if key in self.body else False
        if not object:
            return False
        import datetime
        date_format = '%Y-%m-%d'
        try:
            datetime.datetime.strptime(object, date_format)
            return object
        except ValueError:
            return False

    def get_body(self):
        if self.request.body:
            return json.loads(self.request.body)
        return False


class route(ABC):



    def __init__(self,methods, auth = POLICY_USER):
        self.methods = methods
        self.auth = auth
        super().__init__()

    @csrf_exempt
    def process(self, request, *args, **kwargs):
        self.request = request
        self.POST = POST(request)
        self.GET = GET(request)
        self.PUT = PUT(request)
        self.DELETE = DELETE(request)

        if request.method in self.methods:
            partner = False
            user = False
            UUID = request.GET.get('UUID',False)
            TOKEN = request.GET.get('TOKEN',False)
            API_KEY = request.GET.get('API_KEY', False)
            API_SECRET = request.GET.get('API_SECRET', False)

            if self.auth == POLICY_API_KEYS:
                if not ApiKeys.is_valid(request, API_KEY, API_SECRET):
                    return HttpResponse(status=401)
            elif self.auth == POLICY_PARTNER:

                token = AccessToken.objects.filter(access_id=UUID, access_token=TOKEN).first()
                if not token:
                    return HttpResponse(status=403)
                if not token.partner_id:
                    return HttpResponse(status=403)
                partner = token.partner_id

            elif self.auth == POLICY_USER:
                token = AccessToken.objects.filter(access_id=UUID, access_token=TOKEN).first()
                if not token:
                    return HttpResponse(status=403)
                if not token.partner_id:
                    return HttpResponse(status=403)
                partner = token.partner_id
                user = partner.user_id
                if not user:
                    return HttpResponse(status=403)


            try:
                if request.method == 'GET':
                    return self.on_get(request,user=user,partner=partner)
                elif request.method == 'POST':
                    return self.on_post(request,user=user,partner=partner)
                elif request.method == 'PUT':
                    return self.on_put(request,user=user,partner=partner)
                elif request.method == 'DELETE':
                    return self.on_delete(request,user=user,partner=partner)
            except ValidationError as e:
                return HttpResponse(str(e),status=406)

        return HttpResponse(status=405)

    @abstractmethod
    def on_get(self, request, *arg, **kwargs):
        return HttpResponse(status=501)

    @abstractmethod
    def on_post(self, request, *arg, **kwargs):
        return HttpResponse(status=501)

    @abstractmethod
    def on_put(self, request, *arg, **kwargs):
        return HttpResponse(status=501)

    @abstractmethod
    def on_delete(self, request, *arg, **kwargs):
        return HttpResponse(status=501)
