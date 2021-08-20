from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from contrib.mixin import env
import json
from bigbot.models import InputPattern,ResponsePhrase
from core.models import BotDelegate,DelegateSkill,DelegateUtterance,DelegateIntent
from core.models import ApiKeys,Preference
from core.models import ServiceProvider
import uuid
from core.models import AccessToken
import yaml
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.http import HttpResponse,JsonResponse
from django.core.exceptions import SuspiciousOperation
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from contrib.mixin import env
from django.conf import settings

KEY_DEFAULT_HOST = 'KEY_DEFAULT_HOST'
VAL_DEFAULT_HOST = 'https://bigitsystems.com/bb/controller'
KEY_CANCEL_INTENT = 'KEY_CANCEL_INTENT'

KEY_PRIMARY_COLOR = 'KEY_PRIMARY_COLOR'
VAL_PRIMARY_COLOR = '#3BB9FF'


def login_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect('/dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request,user)
                return redirect('/dashboard')
    return render(request, 'login.html',{})

def logout_view(request, *args, **kwargs):
    logout(request)
    return redirect('/login')


def list_trainer_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            data_list = request.POST.getlist('data_list')
            if  data_list:
                from chatterbot import ChatBot
                from chatterbot.trainers import ListTrainer
                chatbot = ChatBot('', read_only = True,)
                trainer = ListTrainer(chatbot)
                print('===========================')
                print('============save===========')
                trainer.train(data_list)
                return redirect('/list-trainer/')
        elif action == 'clear':
            from chatterbot import ChatBot
            from chatterbot.trainers import ListTrainer
            chatbot = ChatBot('', read_only = True,)
            chatbot.storage.drop()
            print('===========================')
            print('============clear===========')


    return render(request, 'list_trainer.html',data)


def drop_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    data['delegates'] = BotDelegate.objects.filter(user_id__groups__name__in=['bot'])

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'upload':
            pass
        elif action == 'save':
            pass

        file = request.FILES['file']
        filename = file.name
        if filename.endswith('.yml'):
             corpus_data = yaml.load(file)

             categories = corpus_data['categories']
             conversations = corpus_data['conversations']
             delegate = request.POST.get('delegate',False)
             delegate = int(delegate) if delegate else False
             delegate = BotDelegate.objects.filter(id=delegate).first() if delegate else False
             print('=========================================')
             print(delegate)

             for record in conversations:
                 res_1 = record[0]
                 res_2 = record[1:]
                 object = InputPattern.get_singleton(res_1)
                 if delegate:
                     object.delegate_id = delegate
                     object.save()
                 for response in res_2:
                     responseObject = ResponsePhrase.get_singleton(response)
                     responseObject.delegate_id = delegate
                     object.response_ids.add(responseObject)

        return HttpResponse('OK')

    return render(request, 'drop.html', data)


def drop_app(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    if request.method == 'POST':
        file = request.FILES['file']
        filename = file.name
        if filename.endswith('.zip'):
            import zipfile
            import os
            os.system('chown -R 502 {}'.format(settings.BASE_DIR+'/apps'))
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(settings.BASE_DIR+'/apps')

    return render(request, 'drop_app.html', data)

def users_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')
    if view_type == 'form':
        return render(request, 'user-edit.html',data)

    data['tree_title'] = 'Portal Users'
    data['TREE_META_JSON'] = json.dumps({
        'filter':[],
        'limit':20,
        'offset':0,
        'sort':['id', 'desc'],
        'model':'res.users',
        'count': env('res.users').search_count(),
        'fields' : ['user_id','email','last_name','res_groups'],
        'heads':  [['user_id','Name'],['email','Email']],
    })
    return render(request, 'users.html',data)


def delegation_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')
    if view_type == 'form':
        id = int(request.GET.get('id')) if request.GET.get('id') else False
        record = BotDelegate.objects.filter(id=id).first()
        action_type = request.POST.get('action')
        if action_type == 'save':
            name = request.POST.get('name')
            confidence = int(request.POST.get('confidence'))
            default_response = request.POST.get('default_response')
            partner_id = int(request.POST.get('partner_id'))
            partner_id = User.objects.filter(id=partner_id).first()

            skill_ids = request.POST.getlist('delegate_skill')
            if record:
                record.confidence = confidence
                record.partner_id = partner_id
                record.default_response = default_response
                record.save()
            else:
                record = BotDelegate.objects.create(confidence=confidence,user_id=partner_id )

            record.skill_ids.clear()

            for skill in skill_ids:
                skill_id = int(skill)
                skill_obj = DelegateSkill.objects.filter(id=skill_id).first()
                if skill_obj:
                   record.skill_ids.add(skill_obj)
                   record.save()


            return redirect("/delegate/?id={record.id}&view_type=form".format(record=record))
        elif action_type == 'delete' and record:
            record.delete()
            return redirect('/delegate/')

        if record:
            data['record'] = record
            data['skill_ids'] = record.skill_ids.all()
        data['partner_ids'] = User.objects.filter(groups__name__in=['bot'])

        return render(request, 'add_delegate.html',data)
    else:
        data['tree_title'] = 'Delegate'
        data['TREE_META_JSON'] = json.dumps({
            'filter':[['classification',BotDelegate.DELEGATE_BOT]],
            'limit':20,
            'offset':0,
            'sort':['id', 'desc'],
            'model':'delegate',
            'count': env('delegate').search_count(),
            'fields' : ['default_response','user_id','confidence'],
            'heads':  [['user_id','User'],['confidence','Confidence'], ['default_response','Default Response']],
        })

        return render(request, 'users.html',data)



def intents_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')

    if view_type == 'form':
        id = int(request.GET.get('id')) if request.GET.get('id') else False
        record = DelegateIntent.objects.filter(id=id).first()
        action_type = request.POST.get('action')
        if action_type == 'save':
            name = request.POST.get('name')
            package = request.POST.get('skill')

            utterance_ids = []
            for utterance in request.POST.getlist('utterance'):
                utt_id = int(utterance)
                if utt_id:
                    utt_obj = DelegateUtterance.objects.filter(id=utt_id).first()
                    if utt_obj:
                        utterance_ids.append(utt_obj)

            skill_id = DelegateSkill.objects.filter(package=package).first()

            if record:
                record.name = name
                record.skill_id = skill_id
                record.save()
            else:
                record = DelegateIntent.objects.create(name = name,skill_id=skill_id)


            for utterance_id in DelegateUtterance.objects.filter(intent_id=record.id):
                utterance_id.intent_id = None
                utterance_id.save()

            for utterance_id in utterance_ids:
                utterance_id.intent_id = record
                utterance_id.save()


            return redirect("/intents/?id={record.id}&view_type=form".format(record=record))

        elif action_type == 'delete' and record:
            record.delete()
            return redirect('/intents/')

        if record:
            data['record'] = record
            data['utterance_ids'] = []
            for u in DelegateUtterance.objects.filter(intent_id=record.id):
                data['utterance_ids'].append({'body':u.body,'id':u.id})

        data['skill_ids'] = DelegateSkill.objects.filter().order_by('-id')
        #return render(request, 'add_intent.html',data)
        return render(request, 'add_intent_2.html',data)
    else:
        data['tree_title'] = 'Skill Intents'
        data['TREE_META_JSON'] = json.dumps({
            'filter':[],
            'limit':20,
            'offset':0,
            'sort':['id', 'desc'],
            'model':'delegate.intent',
            'count': env('delegate.intent').search_count(),
            'fields' : ['name','skill_id'],
            'heads':  [['skill_id','Skill']],
        })
        return render(request, 'users.html',data)

def utterances(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')

    if view_type == 'form':
        id = int(request.GET.get('id')) if request.GET.get('id') else False
        record = DelegateUtterance.objects.filter(id=id).first()
        action_type = request.POST.get('action')
        if action_type == 'save':
            body = request.POST.get('body')
            if record:
                record.body = body
                record.save()
            else:
                record = DelegateUtterance.get_record(body)
                #record = DelegateUtterance.objects.create(body = body)
            return redirect('/utterances/')
        elif action_type == 'delete' and record:
            record.delete()
            return redirect('/utterances/')
        if record:
            data['record'] = record

        return render(request, 'add_utterance.html',data)
    else:
        data['tree_title'] = 'Utterances'
        data['TREE_META_JSON'] = json.dumps({
            'filter':[],
            'limit':20,
            'offset':0,
            'sort':['id', 'desc'],
            'model':'delegate.utterance',
            'count': env('delegate.utterance').search_count(),
            'fields' : ['body'],
            'heads':  [['body','Body']],
        })
        return render(request, 'users.html',data)

def plain_pattern(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')

    if view_type == 'form':
        id = int(request.GET.get('id')) if request.GET.get('id') else False

        record = InputPattern.objects.filter(id=id).first()
        action_type = request.POST.get('action')
        if action_type == 'save':
            del_id = int(request.POST.get('delegate')) if request.POST.get('delegate') else False
            if del_id:
                del_id = BotDelegate.objects.get(id=del_id)
            string = request.POST.get('string')
            response_phrases = request.POST.getlist('response')

            if record:
                record.string = string
                for item in record.response_ids.all():
                    item.delete()
                for response_phrase in response_phrases:
                    if response_phrase:
                       record.response_ids.create(string = response_phrase)
                record.save()
            else:
                record = InputPattern.objects.create(string = string)
                for response_phrase in response_phrases:
                    if response_phrase:
                       record.response_ids.create(string = response_phrase)

            if del_id:
                record.delegate_id = del_id
                record.save()

            return redirect('/plain-pattern/')
        elif action_type == 'delete' and record:
            record.delete()
            return redirect('/plain-pattern/')
        elif action_type == 'delete_response' and record:
            response_id = request.POST.get('response_id')
            response = ResponsePhrase.objects.filter(id=response_id).first()
            if response:
                response.delete()
        if record:
            data['response_ids'] = record.response_ids.all()
            data['record'] = record
        data['delegates'] = BotDelegate.objects.all()


        return render(request, 'add_input.html',data)
    else:
        data['tree_title'] = 'Input Patterns'
        data['TREE_META_JSON'] = json.dumps({
            'filter':[],
            'limit':20,
            'offset':0,
            'sort':['id', 'desc'],
            'model':'input.pattern',
            'count': env('input.pattern').search_count(),
            'fields' : ['string','delegate_id'],
            'heads':  [['string','Pattern'],['delegate_id','Delegate']],
        })
        return render(request, 'users.html',data)

def import_skill(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    file = request.FILES['file']
    filename = file.name
    if filename.endswith('.json'):
            j_data = json.load(file)
            name = j_data['name']
            package = j_data['package']
            record = DelegateSkill.objects.filter(package=package).first()
            if record:
                record.name = name
                record.data = json.dumps(j_data)
                record.save()
            else:
                record = DelegateSkill.objects.create(data=json.dumps(j_data))


    return HttpResponse('OK')




def plain_skill(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    view_type = request.GET.get('view_type')

    if view_type == 'form':
        id = int(request.GET.get('id')) if request.GET.get('id') else False
        record = DelegateSkill.objects.filter(id=id).first()
        action_type = request.POST.get('action')

        if action_type == 'save':
            name = request.POST.get('name')
            package = request.POST.get('package')
            data = request.POST.get('data')
            active = True if request.POST.get('active_status') else False

            if record:
                record.name = name
                record.package = package
                record.data = data
                record.active = active
                record.save()
            else:
                record = DelegateSkill.objects.create(data=data )
            return redirect('/plain-skill/?id={}&view_type=form'.format(record.id))
        elif action_type == 'delete' and record:
            record.delete()
            return redirect('/plain-skill/')

        elif action_type == 'export' and record:
            json_str = json.dumps(json.loads(record.data), indent=1)
            response = HttpResponse(json_str, content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename={record.package}.json'.format(record=record)
            return response
        elif action_type == 'clone':
            record.package = record.package+"("+str(record.id+1)+")"
            record.name = record.name+"("+str(record.id+1)+")"
            record.provider = record.provider.code+"("+str(record.id+1)+")"
            record.pk = None
            record.save()
            return redirect("/plain-skill/?id={record.id}&view_type=form".format(record=record))

        if record:
            data['record'] = record

        return render(request, 'add_skill.html',data)
    else:
        data['tree_title'] = 'Delegate Skill'
        data['TREE_META_JSON'] = json.dumps({
            'filter':[],
            'limit':20,
            'offset':0,
            'sort':['id', 'desc'],
            'model':'delegate.skill',
            'count': env('delegate.skill').search_count(),
            'fields' : ['name','package'],
            'heads':  [['name','Name'],['package','Package']],
        })
        return render(request, 'tree_skill_view.html',data)

def partner_tree(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    data['tree_title'] = 'Sub Users'
    data['TREE_META_JSON'] = json.dumps({
        'filter':[],
        'limit':20,
        'offset':0,
        'sort':['id', 'desc'],
        'model':'res.partner',
        'count': env('res.partner').search_count(),
        'fields' : ['name','type'],
        'heads':  [['name','Name'],['type','Subtype']],
    })
    return render(request, 'users.html',data)

def delegate_tree(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    data['tree_title'] = 'Delegate'
    data['TREE_META_JSON'] = json.dumps({
        'filter':[],
        'limit':20,
        'offset':0,
        'sort':['id', 'desc'],
        'model':'delegate',
        'count': env('delegate').search_count(),
        'fields' : ['name','package'],
        'heads':  [['name','Name'],['package','Package']],
    })
    return render(request, 'users.html',data)


def documentation_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'documentation.html',data)


def skill_store_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    from contrib.application import get_apps_sources
    data['sources'] = []
    for src in get_apps_sources():
        mani = src.get_manifest()
        mani.update({
            'technical_name':src.name,
            'price':'Free',
        })
        data['sources'].append(mani)
    return render(request, 'skill_store.html',data)


def invoices_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'invoices.html',data)

def delegate_management_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)



def skill_builder_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)

def feature_request_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)

def hire_developer_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)


def forum_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)


def enterprise_support_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)


def corpora_visual_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request, 'content.html',data)





def credential_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)

    object = ApiKeys.objects.filter().first()
    if not object:
        object = ApiKeys.objects.create(host='bigitsystems.com')

    if request.method == 'POST':
        action = request.POST.get('action')
        host = request.POST.get('host')
        if action == 'revoke':
            object = ApiKeys.objects.filter().first()
            object.api_key = str(uuid.uuid4())
            object.api_secret = str(uuid.uuid4())
            object.save()
        if action == 'save':
            object = ApiKeys.objects.filter().first()
            object.host = host
            object.save()


    data['object'] = object

    return render(request,'credential.html',data)


def dashboard_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'dashboard.html',data)



def operator_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'dashboard.html',data)

def adapter_config(request, *args, **kwargs):
    from contrib.processor import LOGICAL_ADAPTERS
    if not request.user.is_authenticated:
        return redirect('/login')
    if request.method == 'POST':
        body = request.POST.get('body')
        if body:
            data = json.loads(body)
            for item in data:
                for info in LOGICAL_ADAPTERS:
                    if info['package'] == item['package']:
                        item['name'] = info['name']
            Preference.put_value('LOGICAL_ADAPTERS',data)
        Preference.put_value(KEY_DEFAULT_HOST, request.POST.get('client_endpoint'))
        Preference.put_value(KEY_PRIMARY_COLOR, request.POST.get('themeColor'))
        Preference.put_value(KEY_CANCEL_INTENT, request.POST.get('skill_cancel').split(','))
        return redirect('/adapter_config/')

    data = get_data(request)
    data['adapters'] = Preference.get_value('LOGICAL_ADAPTERS',LOGICAL_ADAPTERS)
    data['themeColor'] =  Preference.get_value(KEY_PRIMARY_COLOR, VAL_PRIMARY_COLOR)
    data['confidence'] = 34
    data['name'] = 'Boat'
    data['skill_cancel_hidden'] = Preference.get_value(KEY_CANCEL_INTENT, ['cancel'])
    data['seer'] = 'surprise me'
    data['vueradio'] = 'google'
    data['comp_funct'] = 'chatterbot.comparisons.JaccardSimilarity'
    data['aws_access_id'] = '1213999'
    data['aws_secret_key'] = '12333333'
    data['google_tts_cred'] = 'google-jjjj'
    data['client_endpoint'] = Preference.get_value(KEY_DEFAULT_HOST,VAL_DEFAULT_HOST)
    data['default_response'] = 'lg remote'

    keys = ApiKeys.get_keys(request,request.user)
    data['api_key'] = keys.api_key
    data['api_secret'] = keys.api_secret

    return render(request,'settings.html',data)


def user_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'user-view.html',data)

def user_edit(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'user-edit.html',data)

def add_new_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'add_input.html',data)

def add_new_skill(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'add_skill.html',data)

def index_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    return redirect('/dashboard')


def test_view(request, *args, **kwargs):
    return render(request, 'test.html', {})


@csrf_exempt
def test_paypal_view(request, *args, **kwargs):
    import braintree

    CHARGE_AMOUNT = "18.90"

    gateway = braintree.BraintreeGateway(
        braintree.Configuration(
            braintree.Environment.Sandbox,
            merchant_id="6prmfzmqnnymqdw5",
            public_key="pn59thtr4ds42c26",
            private_key="107ad206c5c56a673b717fbfd24ef002"
        )
    )

    if request.method == 'GET':
        client_token = gateway.client_token.generate({
        })
        return render(request, 'paypal_test_braintree.js', {'CLIENT_TOKEN_FROM_SERVER':client_token,'CHARGE_AMOUNT':CHARGE_AMOUNT})
    else:
        nonce_from_the_client = request.POST.get('payment_method_nonce')
        device_data_from_the_client = json.loads(request.POST.get('device_data'))
        print(request.POST.get('payment_method_nonce'), '================')
        result = gateway.transaction.sale({
            "amount": CHARGE_AMOUNT,
            "payment_method_nonce": nonce_from_the_client,
            "device_data": device_data_from_the_client,
            "options": {
                "submit_for_settlement": True
            }
        })
        return HttpResponse('OK')

def get_data(request):
    data = {
        'user':request.user,
        'uri':request.META['PATH_INFO'],
        'SERVER_HOST':settings.SERVER_HOST,
    }
    data['notifications'] = [{
        'title':'Hello!',
        'body':'Welcome to big bot portal.',
        'sub_title':'moment ago',
        'href':'#'
    }]
    return data



def handler404(request, *args, **argv):
    response = render(request, '404.html', {})
    response.status_code = 404
    return response


def socket_server(request, *args, **kwargs):
    #return render(request, 'vue_test.html',{})
    return render(request, 'test_socket.html',{})



@csrf_exempt
@require_http_methods(["POST"])
def rpc_object(request, *args, **kwargs):
    json_sting = request.POST.get('json', False)
    if json_sting:
        try:
            root = json.loads(json_sting)
        except:
            raise SuspiciousOperation('Invalid JSON format.')

        if request.user.is_authenticated:
            user = request.user
        elif 'access_id' in root and 'access_token' in root:
            access_id = root['access_id']
            access_token = root['access_token']
            user = AccessToken.authenticate(access_id,access_token)
            if not user:
                raise PermissionDenied()
        else:
            raise PermissionDenied()
        if  'model' in root and 'method' in root and 'params' in root:
            model = root['model']
            method = root['method']
            params = root['params']
            return JsonResponse(execute(user.id, model, method, params))
        else:
            raise SuspiciousOperation('Invalid request')

def execute(uid, model, method, params):
    if method == 'search_read':
        filter = params[0]
        offset = params[1]['offset']
        limit = params[1]['limit']
        sort = params[1]['sort']
        fields = params[1]['fields']
        records = env(model).search(filter=filter,limit=limit,offset=offset,sort=sort)
        result = []
        for record in records:
            result.append(record.get_fields_value(fields))
        return {'result':result, 'count': env(model).search_count(filter)}
    elif method == 'unlink':
        ids = params[0]
        for record in env(model).search(filter=[['pk__in',ids]]):
            record.unlink()
        return {'result':True}
    elif method == 'read':
        id = params[0]
        record = env(model).read(id)
        return {'result':record}
    elif method == 'create':
        values = params[0]
        record = env(model).create(values)
        return {'result':record.id}
    elif method == 'write':
        id = params[0]
        values = params[1]
        record = env(model).read(id)
        if record:
            record.write(values)
            return {'result':True}
        return {'result':False}
    elif method == 'name_search':
        name = params[0]
        limit = params[1]
        return env(model).name_search(name, limit)
    elif method == 'search_count':
        filter = params[0]
        return env(model).search_count(filter)


    return False


# Remote views
@csrf_exempt
@require_http_methods(["POST","GET"])
def remote_view(request, model, *args, **kwargs):
    view_type = request.GET.get('view_type','tree')
    if view_type == 'tree':
       model_columns = {
           'delegate':[['user_id','Name']],
           'input.pattern':[['string','Body']],
           'delegate.skill':[['name','Name'],['package','Package']],
           'delegate.intent':[['skill_id','Skill']],
           'delegate.utterance':[['string','Body']],
       }
       model_titles = {
           'delegate':'Delegate',
           'input.pattern':'Input Patterns',
           'delegate.skill':'Delegate Skill',
           'delegate.intent':'Delegate Intent',
           'delegate.utterance':'Utterance',
       }
       return render_tree(request, model,model_columns[model],title=model_titles[model])

    return HttpResponse(status=400)

def render_tree(request, model, columns, title='Overview',limit=0,sort=['id', 'desc']):
    fields = []
    for item in columns:
        fields.append(item[0])
    data = get_data(request)
    data['MODEL'] = model
    data['tree_title'] = title
    data['TREE_META_JSON'] = json.dumps({
        'uri':'http://192.168.1.16:9000/jsonrpc/object',
        'filter':[],
        'limit':limit,
        'offset':0,
        'sort':sort,
        'model':model,
        'count': env(model).search_count(),
        'fields' : fields,
        'heads':  columns,
    })
    return render(request, 'tree.html',data)


def mail_template(request,  *args, **kwargs):
    data = {
        'title':'One time password',
        'summary':'You can use this one time password to authenticate your account. Do not share this with anyone.',
        'button':'578992',
    }
    return render(request,'mail-content.html',data)

def date_template(request,  *args, **kwargs):
    return HttpResponse('')


def app_data_import(request, name):
    from contrib.application import import_app_data
    import_app_data(name)
    return HttpResponse('OK')

def test_chat(request):
    html = """
    <html>
    <head>
    </head>
    <footer>
       <script  src="/static/core/standalone/base.js" type="text/javascript"></script>
       <script  src="/static/client/standalone/bigbot.js" type="text/javascript"></script>
    </footer>
    </html> 
    """
    return HttpResponse(html)
