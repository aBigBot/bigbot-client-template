from django.urls import path, include
from . import views
from . import openapi

urlpatterns = [
   path('login/',views.login_view,),
   path('logout/',views.logout_view,),
   path('users/',views.users_view,),
   path('dashboard/',views.dashboard_view,),
   path('profile/',views.user_view,),
   path('operator/',views.operator_view,),
   path('adapter_config/',views.adapter_config,),
   path('delegate/',views.delegation_view,),
   path('intents/',views.intents_view,),
   path('profile/edit/',views.user_edit,),
   path('dashboard/',views.dashboard_view,),
   path('utterances/',views.utterances,),
   path('plain-pattern/',views.plain_pattern,),
   path('drop/',views.drop_view,),
   path('plain-pattern/add/',views.add_new_view,),
   path('plain-skill/',views.plain_skill,),
   path('plain-skill/add/',views.add_new_skill,),
   path('import_skill/',views.import_skill,),
   path('partner-tree/',views.partner_tree,),
   path('credential-view/',views.credential_view,),
   path('test/',views.test_view,),
   path('test-paypal/',views.test_paypal_view,),
   path('',views.index_view,),

   path('documentation/',views.documentation_view,),
   path('skill-store/',views.skill_store_view,),
   path('invoices/',views.invoices_view,),
   path('delegate-management/',views.delegate_management_view,),
   path('corpora-visual/',views.corpora_visual_view,),
   path('skill-builder/',views.skill_builder_view,),
   path('feature-request/',views.feature_request_view,),
   path('hire-developer/',views.hire_developer_view,),
   path('forum/',views.forum_view,),
   path('enterprise-support/',views.enterprise_support_view,),
   path('list-trainer/',views.list_trainer_view,),
   path('test/socket/',views.socket_server,),


   path('rpc/object',views.rpc_object),
   path('app/drop',views.drop_app),




   # INTERNAL APIS
   # path('rpc/openapi/status',views.rpc_status),
   # path('rpc/openapi/session/authenticate',views.rpc_session_authenticate),
   # path('rpc/openapi/session',views.rpc_session),

   # EXP
   # path('rpc/openapi/fields/list',openapi.list_fields(methods=['GET']).process),
   # path('rpc/openapi/name/search',openapi.name_search(methods=['GET']).process),
   # path('rpc/openapi/trainer/list',openapi.list_trainer(methods=['POST','DELETE']).process),
   # path('rpc/openapi/corpus/file',openapi.corpus_file(methods=['POST']).process),
   # path('rpc/openapi/settings',openapi.settings(methods=['GET','POST']).process),
   # path('rpc/openapi/model/image',openapi.model_image(methods=['GET']).process),
   #
   #
   # path('rpc/openapi/apikeys',openapi.apikey(methods=['GET','POST']).process),
   # path('rpc/openapi/utterance',openapi.utterance(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/utterance/search/read',openapi.utterance_search(methods=['POST']).process),
   # path('rpc/openapi/skill',openapi.skill(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/skill/search/read',openapi.skill_search(methods=['POST']).process),
   # path('rpc/openapi/skill/export',openapi.skill_export(methods=['GET']).process),
   # path('rpc/openapi/skill/import',openapi.skill_import(methods=['POST']).process),
   # path('rpc/openapi/skill/clone',openapi.skill_clone(methods=['POST']).process),
   #
   # path('rpc/openapi/user',openapi.user(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/user/search/read',openapi.user_search(methods=['POST']).process),
   # path('rpc/openapi/delegate',openapi.delegate(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/delegate/search/read',openapi.delegate_search(methods=['POST']).process),
   # path('rpc/openapi/intent',openapi.intent(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/intent/search/read',openapi.intent_search(methods=['POST']).process),
   # path('rpc/openapi/corpus',openapi.corpus(methods=['GET','POST','PUT','DELETE']).process),
   # path('rpc/openapi/corpus/search/read',openapi.corpus_search(methods=['POST']).process),


   path('web/model/<str:model>',views.remote_view),


   # remove
   path('mail/',views.mail_template),
   path('date/',views.date_template),

   path('store/app/data/import/<str:name>',views.app_data_import),
   path('test/chat',views.test_chat,),

]
