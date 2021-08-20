from .api import route
from core.models import ApiKeys
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from contrib.mixin import env
from django.core.exceptions import ValidationError
from core.models import BotDelegate,DelegateSkill,DelegateIntent,DelegateUtterance
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
import yaml
from bigbot.models import InputPattern,ResponsePhrase
import json

class name_search(route):

    def on_get(self, request, *arg, **kwargs):
        model = self.GET.get_string('model')
        query = self.GET.get_string('query')
        if not model:
            return HttpResponse(status=406)
        if not query:
            query = ""
        records = env(model).name_search(query)
        return JsonResponse(records,safe=False)


    def on_post(self, request, *arg, **kwargs):
        return super().on_post(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)


class list_fields(route):

    def on_get(self, request, *arg, **kwargs):
        model = self.GET.get_string('model')
        if not model:
            return HttpResponse(status=406)
        if model == 'delegate.utterance':
            data = {
                'fields':[{'name':'body','type':'CharField'}],
                'search_count': DelegateUtterance.objects.filter().count(),
                'limit': 20,
                'order':['id','desc']
            }
            return JsonResponse(data)
        elif model == 'res.users':
            data = {
                'fields':[{'name':'first_name','type':'CharField'},
                          {'name':'last_name','type':'CharField'},
                          {'name':'email','type':'EmailField'},
                          {'name':'is_superuser','type':'BooleanField'},
                          {'name':'is_active','type':'BooleanField'}],
                'search_count': User.objects.filter().count(),
                'limit': 20,
                'order':['id','desc']
            }
            return JsonResponse(data)
        elif model == 'input.pattern':
            data = {
                'fields':[{'name':'string','type':'CharField'},
                          {'name':'delegate_id','type':'CharField'},],
                'search_count': InputPattern.objects.filter().count(),
                'limit': 20,
                'order':['id','desc']
            }
            return JsonResponse(data)
        elif model == 'delegate.skill':
            data = {
                'fields':[{'name':'name','type':'CharField'},
                          {'name':'package','type':'CharField'},
                          {'name':'active','type':'BooleanField'},
                          {'name':'input_arch','type':'TextField'},
                          {'name':'response_arch','type':'TextField'}],
                'search_count': DelegateSkill.objects.filter().count(),
                'limit': 20,
                'order':['id','desc']
            }
            return JsonResponse(data)
        elif model == 'delegate':
            data = {
                'fields':[{'name':'partner_id','type':'ForeignKey'}],
                'search_count': Delegate.objects.filter().count(),
                'limit': 20,
                'order':['id','desc']
            }
            return JsonResponse(data)


        return HttpResponse(status=406)

    def on_post(self, request, *arg, **kwargs):
        return super().on_post(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class apikey(route):

    def on_get(self, request, *arg, **kwargs):
        record = ApiKeys.get_keys()
        data = {
            'api_key':record.api_key,
            'api_secret':record.api_secret
        }
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        record = ApiKeys.get_keys()
        if record:
            record.delete()
        record = ApiKeys.get_keys()
        data = {
            'api_key':record.api_key,
            'api_secret':record.api_secret
        }
        return JsonResponse(data)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class utterance(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateUtterance.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = {
            'id':record.id,
            'body':record.body
        }
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        record =  DelegateUtterance.get_record(body=body['body'])
        return HttpResponse(str(record.id))

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateUtterance.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)

        record.body = body['body']
        record.save()
        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateUtterance.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')

class utterance_search(route):

    def on_get(self, request, *arg, **kwargs):

        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        data = []
        records = env('delegate.utterance').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data.append(record.get_fields_value(fields))

        return JsonResponse(data,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class skill(route):


    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateSkill.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = record.get_fields_value(['name','package','active','input_arch','response_arch'])
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        record = DelegateSkill.objects.create(name=body['name'],package=body['package'],active=body['active'],
                                                response_arch=body['response_arch'],input_arch=body['input_arch'])
        return HttpResponse(str(record.id))

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateSkill.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)

        record.name = body['name']
        record.package = body['package']
        record.active = body['active']
        record.input_arch = body['input_arch']
        record.response_arch = body['response_arch']
        record.save()

        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateSkill.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')

class skill_search(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        data = []
        records = env('delegate.skill').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data.append(record.get_fields_value(fields))

        return JsonResponse(data,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class skill_import(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        file = request.FILES['file']
        if not file:
            return HttpResponse(status=406)
        if not file.name.endswith('.json'):
            return HttpResponse(status=406)
        j_data = json.load(file)
        name = j_data['name']
        package = j_data['package']
        input_arch = json.dumps(j_data['input_arch'])
        response_arch = json.dumps(j_data['response_arch'])

        record = DelegateSkill.objects.filter(package=package).first()
        if record:
            record.name = name
            record.input_arch = input_arch
            record.response_arch = response_arch
            record.save()
        else:
            DelegateSkill.objects.create(name=name,package=package,input_arch=input_arch,response_arch=response_arch)

        return HttpResponse('OK')

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class skill_export(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateSkill.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)

        json_obj = {'name':record.name,'package':record.package,}
        json_obj['input_arch'] = json.loads(record.input_arch) if record.input_arch else []
        json_obj['response_arch'] = json.loads(record.response_arch) if record.response_arch else []
        json_str = json.dumps(json_obj, indent=1)
        response = HttpResponse(json_str, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename={record.package}.json'.format(record=record)
        return response

    def on_post(self, request, *arg, **kwargs):
        return super().on_post(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class skill_clone(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateSkill.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.package = record.package+"("+str(record.id+1)+")"
        record.name = record.name+"("+str(record.id+1)+")"
        record.pk = None
        record.save()

        return HttpResponse('OK')

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)


class user(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  User.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = record.get_fields_value(['first_name','last_name','email','is_active','is_superuser'])
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        record = User.objects.create(first_name=body['first_name'],last_name=body['last_name'],email=body['email'],
                                         is_active=body['is_active'],is_superuser=body['is_superuser'])
        return HttpResponse(str(record.id))

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  User.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)

        record.first_name = body['first_name']
        record.last_name = body['last_name']
        record.is_active = body['is_active']
        record.is_superuser = body['is_superuser']
        record.save()

        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  User.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')

class user_search(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        data = []
        records = env('res.users').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data.append(record.get_fields_value(fields))

        return JsonResponse(data,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class delegate(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  BotDelegate.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = record.get_fields_value(['partner_id','confidence','default_response','delegate_skill_ids','is_human'])
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        partner_id = User.objects.filter(id=body['partner_id']).first()
        if not partner_id:
            raise ValidationError('Partner ID not existed')
        record = BotDelegate.objects.create(partner_id=partner_id,confidence=body['confidence'],default_response=body['default_response'])
        for delegate_skill_id in body['delegate_skill_ids']:
            delegate_skill = DelegateSkill.objects.filter(id=delegate_skill_id).first()
            record.delegate_skill_ids.add(delegate_skill)
        record.save()
        return HttpResponse(str(record.id))

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  BotDelegate.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)

        record.confidence = body['confidence']
        record.default_response = body['default_response']
        record.delegate_skill_ids.clear()
        for delegate_skill_id in body['delegate_skill_ids']:
            delegate_skill = DelegateSkill.objects.filter(id=delegate_skill_id).first()
            record.delegate_skill_ids.add(delegate_skill)

        record.save()
        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  BotDelegate.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')

class delegate_search(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        data = []
        records = env('delegate').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data.append(record.get_fields_value(fields))

        return JsonResponse(data,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class intent_search(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        data = []
        records = env('delegate.intent').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data.append(record.get_fields_value(fields))

        return JsonResponse(data,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class intent(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateIntent.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = record.get_fields_value(['name','skill_id','delegate_utterance_ids'])
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        skill_id = DelegateSkill.objects.filter(id=body['skill_id']).first()
        if not skill_id:
            raise ValidationError('SKill ID not existed')
        record = DelegateIntent.objects.create(name=body['name'],skill_id=skill_id)
        for item in body['delegate_utterance_ids']:
            item_object = DelegateUtterance.objects.filter(id=item).first()
            item_object.intent_id = record
            item_object.save()
        return HttpResponse(str(record.id))

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateIntent.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)
        skill_id = DelegateSkill.objects.filter(id=body['skill_id']).first()
        if not skill_id:
            raise ValidationError('SKill ID not existed')

        record.name = body['name']
        record.skill_id = skill_id
        record.save()

        for item in  DelegateUtterance.objects.filter(intent_id=record.id):
            item.intent_id = None
            item.save()

        for item in body['delegate_utterance_ids']:
            item_object = DelegateUtterance.objects.filter(id=item).first()
            item_object.intent_id = record
            item_object.save()

        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  DelegateIntent.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')


class corpus(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  InputPattern.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        data = record.get_fields_value(['string','delegate_id','response_ids'])
        response_text = []
        if data['response_ids']:
            for item in ResponsePhrase.objects.filter(id__in = data['response_ids']):
                response_text.append(item.string)
        data['response_ids'] = response_text
        return JsonResponse(data)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        delegate = None
        if 'delegate_id' in body:
            delegate = BotDelegate.objects.filter(id=body['delegate_id']).first()
        record = InputPattern.get_singleton(body['string'])
        if not record:
            record = InputPattern.objects.create(string=body['string'])
        for item in record.response_ids.all():
            item.delete()
        for item in body['response_ids']:
            record.response_ids.create(string = item)
        record.delegate_id = delegate
        record.save()

        return HttpResponse('OK')

    def on_put(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  InputPattern.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)

        body = self.PUT.get_body()
        if not body:
            return HttpResponse(status=406)
        delegate = None
        if 'delegate_id' in body:
            delegate = Delegate.objects.filter(id=body['delegate_id']).first()

        record.string = body['string']
        record.delegate_id = delegate
        for item in record.response_ids.all():
            item.delete()
        for item in body['response_ids']:
            record.response_ids.create(string = item)
        record.save()

        return HttpResponse('OK')

    def on_delete(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        if not id:
            return HttpResponse(status=406)
        record =  InputPattern.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)
        record.delete()
        return HttpResponse('OK')

class corpus_search(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        filter = body[0]
        context = body[1]
        limit = context['limit']
        offset = context['offset']
        sort = context['order']
        fields = context['fields']

        results = []
        records = env('input.pattern').search(filter=filter,limit=limit,offset=offset,sort=sort)
        for record in records:
            data = record.get_fields_value(fields)
            response_text = []
            if data['response_ids']:
                for item in ResponsePhrase.objects.filter(id__in = data['response_ids']):
                    response_text.append(item.string)
            data['response_ids'] = response_text
            results.append(data)

        return JsonResponse(results,safe=False)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class corpus_file(route):
    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        file = request.FILES['file']
        if not file:
            return HttpResponse(status=406)
        if not file.name.endswith('.yml'):
            return HttpResponse(status=406)

        corpus_data = yaml.load(file)
        categories = corpus_data['categories']
        conversations = corpus_data['conversations']
        delegate_id = self.POST.get_int('delegate_id')
        delegate = False
        if delegate_id:
            delegate = BotDelegate.objects.filter(id=delegate_id).first()

        for record in conversations:
            res_1 = record[0]
            res_2 = record[1:]
            object = InputPattern.get_singleton(res_1)
            if delegate:
                object.delegate_id = delegate
                object.save()
            for response in res_2:
                responseObject = ResponsePhrase.get_singleton(response)
                object.response_ids.add(responseObject)

        return HttpResponse('OK')

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)

class list_trainer(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        chatbot = ChatBot('', read_only = True,)
        chatbot.storage.drop()
        return HttpResponse('OK')

    def on_post(self, request, *arg, **kwargs):
        body = self.POST.get_body()
        if not body:
            return HttpResponse(status=406)
        if body:
            chatbot = ChatBot('', read_only = True,)
            trainer = ListTrainer(chatbot)
            trainer.train(body)
        return HttpResponse('OK')


class model_image(route):

    def on_get(self, request, *arg, **kwargs):
        id = self.GET.get_int('id')
        model = self.GET.get_string('model')
        if not id or not model:
            return HttpResponse(status=406)
        record = False
        if model == 'res.partner':
            record =  User.objects.filter(id=id).first()
        if not record:
            return HttpResponse(status=410)

        return HttpResponse(request.scheme+"://"+request.META['HTTP_HOST']+record.image.url)

    def on_post(self, request, *arg, **kwargs):
        return super().on_post(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)


class settings(route):

    def on_get(self, request, *arg, **kwargs):
        return super().on_get(request, *arg, **kwargs)

    def on_post(self, request, *arg, **kwargs):
        return super().on_post(request, *arg, **kwargs)

    def on_put(self, request, *arg, **kwargs):
        return super().on_put(request, *arg, **kwargs)

    def on_delete(self, request, *arg, **kwargs):
        return super().on_delete(request, *arg, **kwargs)
