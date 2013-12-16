import endpoints
from google.appengine.ext import ndb
from google.appengine.api import search 
from protorpc import remote
from google.appengine.datastore.datastore_query import Cursor
from endpoints_proto_datastore.ndb import EndpointsAliasProperty
from endpoints_proto_datastore.ndb import EndpointsModel
from iomodels.crmengine.accounts import Account
from iomodels.crmengine.contacts import Contact
from iomodels.crmengine.notes import Note,Topic
from iomodels.crmengine.tasks import Task
from iomodels.crmengine.opportunities import Opportunity
from iomodels.crmengine.events import Event
from iomodels.crmengine.documents import Document
from iomodels.crmengine.shows import Show
from iomodels.crmengine.leads import Lead
from iomodels.crmengine.cases import Case
from iomodels.crmengine.products import Product
from iomodels.crmengine.comments import Comment
from iomodels.crmengine.opportunitystage import Opportunitystage
from iomodels.crmengine.leadstatuses import Leadstatus
from iomodels.crmengine.casestatuses import Casestatus
from model import User,Userinfo,Group,Member,Permission,Contributor
import model
import logging
from google.appengine.api import mail
import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run
from apiclient import errors
from protorpc import messages
from protorpc import message_types
from google.appengine.api import memcache


# The ID of javascript client authorized to access to our api
# This client_id could be generated on the Google API console
CLIENT_ID = '987765099891.apps.googleusercontent.com'
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/calendar']
OBJECTS = {'Account': Account,'Contact': Contact,'Case':Case,'Lead':Lead,'Opportunity':Opportunity}
FOLDERS = {'Account': 'accounts_folder','Contact': 'contacts_folder','Lead':'leads_folder','Opportunity':'opportunities_folder','Case':'cases_folder','Show':'shows_folder'}
DISCUSSIONS= {'Task':{'title':'task','url':'/#/tasks/show/'},'Event':{'title':'event','url':'/#/events/show/'},'Note':{'title':'discussion','url': '/#/notes/show/'}}

# The message class that defines the Search Request attributes
class SearchRequest(messages.Message):
    q = messages.StringField(1)
    limit = messages.IntegerField(2)
    pageToken = messages.StringField(3)
# The message class that defines the Search Result attributes
class SearchResult(messages.Message):
    id = messages.StringField(1)
    title = messages.StringField(2)
    type = messages.StringField(3)
    rank = messages.IntegerField(4)
# The message class that defines a set of search results
class SearchResults(messages.Message):
    items = messages.MessageField(SearchResult, 1, repeated=True)
    nextPageToken = messages.StringField(2)
# The message class that defines the accounts.search response 
class AccountSearchResult(messages.Message):
    id = messages.StringField(1)
    entityKey  = messages.StringField(2)
    name = messages.StringField(3)
# The message class that defines a set of accounts.search results
class AccountSearchResults(messages.Message):
    items = messages.MessageField(AccountSearchResult, 1, repeated=True)
    nextPageToken = messages.StringField(2)
# The message class that defines the contacts.search response 
class ContactSearchResult(messages.Message):
    id = messages.StringField(1)
    entityKey  = messages.StringField(2)
    firstname = messages.StringField(3)
    lastname = messages.StringField(4)
    account_name = messages.StringField(5)
    account = messages.StringField(6)
# The message class that defines a set of contacts.search results
class ContactSearchResults(messages.Message):
    items = messages.MessageField(ContactSearchResult, 1, repeated=True)
    nextPageToken = messages.StringField(2)
# The message class that defines the schema of Attachment 
class AttachmentSchema(messages.Message):
    id = messages.StringField(1)
    title = messages.StringField(2)
    mimeType = messages.StringField(3)
    embedLink = messages.StringField(4)
# The message class that defines the attributes of request to attache multiples files 
class MultipleAttachmentRequest(messages.Message):
    about_kind = messages.StringField(1)
    about_item = messages.StringField(2)
    items = messages.MessageField(AttachmentSchema, 3, repeated=True)
# The message class that defines the author schema
class AuthorSchema(messages.Message):
    google_user_id = messages.StringField(1)
    display_name = messages.StringField(2)
    google_public_profile_url = messages.StringField(3)
    photo = messages.StringField(4)
# The message class that defines the related to discussion about
class DiscussionAboutSchema(messages.Message):
    kind = messages.StringField(1)
    id = messages.StringField(2)
    name = messages.StringField(3)
# The message class that defines Discussion Response for notes.get API
class DiscussionResponse(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    title = messages.StringField(3)
    content = messages.StringField(4)
    comments = messages.IntegerField(5)
    about = messages.MessageField(DiscussionAboutSchema,6)
    author = messages.MessageField(AuthorSchema,7)
# The message class that defines Customized Task Response for tasks.get API
class TaskResponse(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    title = messages.StringField(3)
    due = messages.StringField(4)
    status = messages.StringField(5)
    comments = messages.IntegerField(6)
    about = messages.MessageField(DiscussionAboutSchema,7)
    author = messages.MessageField(AuthorSchema,8)
    completed_by = messages.MessageField(AuthorSchema,9)
# The message class that defines Customized Event Response for events.get API
class EventResponse(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    title = messages.StringField(3)
    starts_at = messages.StringField(4)
    ends_at = messages.StringField(5)
    where = messages.StringField(6)
    comments = messages.IntegerField(7)
    about = messages.MessageField(DiscussionAboutSchema,8)
    author = messages.MessageField(AuthorSchema,9)

class EndpointsHelper(EndpointsModel):
    INVALID_TOKEN = 'Invalid token'
    INVALID_GRANT = 'Invalid grant'
    NO_ACCOUNT = 'You don\'t have a i/oGrow account'
    @classmethod
    def require_iogrow_user(cls):
        user = endpoints.get_current_user()
        if user is None:
            raise endpoints.UnauthorizedException(cls.INVALID_TOKEN)
        user_from_email = model.User.query(model.User.email == user.email()).get()
        if user_from_email is None:
            raise endpoints.UnauthorizedException(cls.NO_ACCOUNT)
        return user_from_email

    @classmethod
    def insert_folder(cls,user,folder_name):
        try:
            credentials = user.google_credentials
            http = credentials.authorize(httplib2.Http(memcache))
            service = build('drive', 'v2', http=http)
            organization = user.organization.get()

            # prepare params to insert
            folder_params = {
                        'title': folder_name,
                        'mimeType':  'application/vnd.google-apps.folder'         
            }#get the accounts_folder or contacts_folder or .. 
            
            parent_folder = organization.accounts_folder
            if parent_folder:
                folder_params['parents'] = [{'id': parent_folder}]
            
            # execute files.insert and get resource_id
            created_folder = service.files().insert(body=folder_params).execute()
        except:
            raise endpoints.UnauthorizedException(cls.INVALID_GRANT)
        return created_folder

@endpoints.api(name='iogrowlive', version='v1', description='i/oGrow Live APIs',allowed_client_ids=[CLIENT_ID,
                                   endpoints.API_EXPLORER_CLIENT_ID],scopes=SCOPES)
class LiveApi(remote.Service):

  ID_RESOURCE = endpoints.ResourceContainer(
            message_types.VoidMessage,
            id=messages.StringField(1))
  # Accounts APIs
  # accounts.insert api
  @Account.method(user_required=True,path='accounts', http_method='POST', name='accounts.insert')
  def AccountInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      created_folder = EndpointsHelper.insert_folder(user_from_email,my_model.name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
    
@endpoints.api(name='crmengine', version='v1', description='I/Ogrow CRM APIs',allowed_client_ids=[CLIENT_ID,
                                   endpoints.API_EXPLORER_CLIENT_ID],scopes=SCOPES)
class CrmEngineApi(remote.Service):

  ID_RESOURCE = endpoints.ResourceContainer(
            message_types.VoidMessage,
            id=messages.StringField(1))
  # Accounts APIs
  # accounts.insert api
  @Account.method(user_required=True,path='accounts', http_method='POST', name='accounts.insert')
  def AccountInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      created_folder = EndpointsHelper.insert_folder(user_from_email,my_model.name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
  # accounts.list api
  @Account.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='accounts', name='accounts.list')
  def Account_List(self, query):
      user_from_email = EndpointsHelper.require_iogrow_user()
      return query.filter(ndb.OR(ndb.AND(Account.access=='public',Account.organization==user_from_email.organization),Account.owner==user_from_email.google_user_id, Account.collaborators_ids==user_from_email.google_user_id)).order(Account._key)
  # accounts.get api
  @Account.method(request_fields=('id',),path='accounts/{id}', http_method='GET', name='accounts.get')
  def AccountGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Account not found.')
    return my_model
  # accounts.update
  @Account.method(user_required=True,
                http_method='PUT', path='accounts/{id}', name='accounts.update')
  def AccountUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # accounts.patch api
  @Account.method(user_required=True,
                http_method='PATCH', path='accounts/{id}', name='accounts.patch')
  def AccountPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      if not my_model.from_datastore:
          raise endpoints.NotFoundException('Account not found.')
      patched_model_key = my_model.entityKey
      patched_model = ndb.Key(urlsafe=patched_model_key).get()
      print patched_model
      print my_model
      properties = Account().__class__.__dict__
      for p in properties.keys():
         
            if (eval('patched_model.'+p) != eval('my_model.'+p))and(eval('my_model.'+p)):
                exec('patched_model.'+p+'= my_model.'+p)
      patched_model.put()
      return patched_model
  
  # accounts.search api
  @endpoints.method(SearchRequest, AccountSearchResults,
                      path='accounts/search', http_method='POST',
                      name='accounts.search')
  def account_search(self, request):
      user_from_email = EndpointsHelper.require_iogrow_user()
      
      #prepare the query
      query_string = request.q 
      query_string_next = unicode(request.q) + u"\ufffd"
      if request.limit:
          limit = int(request.limit)
      else:
          limit = 10

      query = Account.query(ndb.AND(Account.name>=query_string,Account.name<query_string_next,ndb.OR(ndb.AND(Account.access=='public',Account.organization==user_from_email.organization),Account.owner==user_from_email.google_user_id, Account.collaborators_ids==user_from_email.google_user_id))).order(Account.name,Account._key)
      if request.pageToken:
          curs = Cursor(urlsafe=request.pageToken)
          results, next_curs, more = query.fetch_page(limit, start_cursor=curs)
      else:
          results, next_curs, more = query.fetch_page(limit)

      search_results = []
      for result in results:
          kwargs = {'id':str(result.key.id()),
                  'entityKey': result.key.urlsafe(),
                  'name': result.name}
          search_results.append(AccountSearchResult(**kwargs))

      nextPageToken = None
      if more and next_curs:
          nextPageToken = next_curs.urlsafe()
        
      return AccountSearchResults(items = search_results,nextPageToken=nextPageToken) 
  # Contacts APIs
  # contacts.insert api
  @Contact.method(user_required=True,path='contacts', http_method='POST', name='contacts.insert')
  def ContactInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # OAuth flow
      folder_name = my_model.firstname + ' ' + my_model.lastname
      created_folder = EndpointsHelper.insert_folder(user_from_email,folder_name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
  # contacts.list api
  @Contact.query_method(user_required=True,query_fields=('limit', 'order','account','account_name', 'pageToken'),path='contacts', name='contacts.list')
  def ContactList(self, query):
      user_from_email = EndpointsHelper.require_iogrow_user()
      return query.filter(ndb.OR(ndb.AND(Contact.access=='public',Contact.organization==user_from_email.organization),Contact.owner==user_from_email.google_user_id, Contact.collaborators_ids==user_from_email.google_user_id)).order(Contact._key)
  # contacts.get api        
  @Contact.method(request_fields=('id',),
                  path='contacts/{id}', http_method='GET', name='contacts.get')
  def ContactGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Contact not found.')
    return my_model
  # contacts.update api
  @Contact.method(user_required=True,
                http_method='PUT', path='contacts/{id}', name='contacts.update')
  def ContactUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  
  # contacts.patch api
  @Contact.method(user_required=True,
                http_method='PATCH', path='contacts/{id}', name='contacts.patch')
  def ContactPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions

      my_model.put()
      return my_model
  
  #contacts.search api
  @endpoints.method(SearchRequest, ContactSearchResults,
                      path='contacts/search', http_method='POST',
                      name='contacts.search')
  def contact_search(self, request):
      user_from_email = EndpointsHelper.require_iogrow_user()
      
      #prepare the query
      query_string = request.q 
      query_string_next = unicode(request.q) + u"\ufffd"
      if request.limit:
          limit = int(request.limit)
      else:
          limit = 10

      query = Contact.query(ndb.AND(Contact.display_name>=query_string,Contact.display_name<query_string_next),ndb.OR(ndb.AND(Contact.access=='public',Contact.organization==user_from_email.organization),Contact.owner==user_from_email.google_user_id, Contact.collaborators_ids==user_from_email.google_user_id)).order(Contact.display_name,Contact._key)
      if request.pageToken:
          curs = Cursor(urlsafe=request.pageToken)
          results, next_curs, more = query.fetch_page(limit, start_cursor=curs)
      else:
          results, next_curs, more = query.fetch_page(limit)

      search_results = []
      for result in results:
          kwargs = {'id':str(result.key.id()),
                  'entityKey': result.key.urlsafe(),
                  'firstname': result.firstname,
                  'lastname':result.lastname,
                  'account_name':result.account_name,
                  'account':result.account.urlsafe()}
          search_results.append(ContactSearchResult(**kwargs))

      nextPageToken = None
      if more and next_curs:
          nextPageToken = next_curs.urlsafe()
        
      return ContactSearchResults(items = search_results,nextPageToken=nextPageToken)

  # Opportunities APIs
  # opportunities.insert
  @Opportunity.method(user_required=True,path='opportunities',http_method='POST',name='opportunities.insert')
  def OpportunityInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # OAuth flow
      created_folder = EndpointsHelper.insert_folder(user_from_email,my_model.name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
  # opportunities.list api
  @Opportunity.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken','account','account_name','contact'),path='opportunities', name='opportunities.list')
  def opportunity_list(self, query):
      user_from_email = EndpointsHelper.require_iogrow_user()      
      return query.filter(ndb.OR(ndb.AND(Opportunity.access=='public',Opportunity.organization==user_from_email.organization),Opportunity.owner==user_from_email.google_user_id, Opportunity.collaborators_ids==user_from_email.google_user_id)).order(Opportunity._key)
  # opportunities.get api
  @Opportunity.method(request_fields=('id',),path='opportunities/{id}', http_method='GET', name='opportunities.get')
  def OpportunityGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Opportunity not found')
    return my_model
  # opportunities.get api
  @Opportunity.method(user_required=True,
                http_method='PUT', path='opportunities/{id}', name='opportunities.update')
  def OpportunityUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # opportunities.update api 
  @Opportunity.method(user_required=True,
                http_method='PATCH', path='opportunities/{id}', name='opportunities.patch')
  def OpportunityPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  #HKA 11.12.2013 Opportunitystage APIs
  @Opportunitystage.method(user_required=True,path='opportunitystage',http_method='POST',name='opportunitystages.insert')
  def OpportunitystageInsert(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.owner = user_from_email.google_user_id
    my_model.organization = user_from_email.organization
    my_model.put()
    return my_model
  @Opportunitystage.query_method(user_required=True,query_fields=('limit','order','pageToken'),path='opportunitystage',name='opportunitystages.list')
  def OpportunitystageList(self,query):
    user_from_email = EndpointsHelper.require_iogrow_user()
    return query
  @Opportunitystage.method(user_required=True,
    http_method='PATCH',path='opportunitystage/{id}',name='opportunitystages.patch')
  def OpportuntystagePatch(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.put()
    return my_model


  # Leads APIs
  # leads.insert api
  @Lead.method(user_required=True,path='leads',http_method='POST',name='leads.insert')
  def LeadInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # OAuth flow
      folder_name = my_model.firstname + ' ' + my_model.lastname
      created_folder = EndpointsHelper.insert_folder(user_from_email,folder_name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model

  # leads.list api
  @Lead.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='leads',name='leads.list')
  def LeadList(self,query):
      user_from_email = EndpointsHelper.require_iogrow_user()
      return query.filter(ndb.OR(ndb.AND(Lead.access=='public',Lead.organization==user_from_email.organization),Lead.owner==user_from_email.google_user_id, Lead.collaborators_ids==user_from_email.google_user_id)).order(Lead._key)
  # leads.get api
  @Lead.method(request_fields=('id',),path='leads/{id}', http_method='GET', name='leads.get')
  def LeadGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Lead not found')
    return my_model
  # leads.update api
  @Lead.method(user_required=True,
                http_method='PUT', path='leads/{id}', name='leads.update')
  def LeadUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # leads.patch api
  @Lead.method(user_required=True,
                http_method='PATCH', path='leads/{id}', name='leads.patch')
  def LeadPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model

  #HKA 14.12.2013 Lead status APIs
  @Leadstatus.method(user_required=True,path='leadstatuses',http_method='POST',name='leadstatuses.insert')
  def LeadstatusInsert(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.owner = user_from_email.google_user_id
    my_model.organization = user_from_email.organization
    my_model.put()
    return my_model
  @Leadstatus.query_method(user_required=True,query_fields=('limit','order','pageToken'),path='leadstatuses',name='leadstatuses.list')
  def LeadstatusList(self,query):
    user_from_email = EndpointsHelper.require_iogrow_user()
    return query
  @Leadstatus.method(user_required=True,
    http_method='PATCH',path='leadstatuses/{id}',name='leadstatuses.patch')
  def LeadstatusPatch(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.put()
    return my_model
  # Cases API 
  # cases.insert api 
  @Case.method(user_required=True,path='cases',http_method='POST',name='cases.insert')
  def CaseInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      created_folder = EndpointsHelper.insert_folder(user_from_email,my_model.name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
  # cases.list api
  @Case.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken','account','description','type_case','priority','status','contact'),path='cases',name='cases.list')
  def CaseList(self,query):
      user_from_email = EndpointsHelper.require_iogrow_user()
      return query.filter(ndb.OR(ndb.AND(Case.access=='public',Case.organization==user_from_email.organization),Case.owner==user_from_email.google_user_id, Case.collaborators_ids==user_from_email.google_user_id)).order(Case._key)
  # cases.get api
  @Case.method(request_fields=('id',),path='cases/{id}', http_method='GET', name='cases.get')
  def CaseGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Case not found')
    return my_model
  # cases.update api
  @Case.method(user_required=True,
                http_method='PUT', path='cases/{id}', name='cases.update')
  def CaseUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # cases.patch api
  @Case.method(user_required=True,
                http_method='PATCH', path='cases/{id}', name='cases.patch')
  def CasePatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      if not my_model.from_datastore:
          raise endpoints.NotFoundException('Account not found.')
      patched_model_key = my_model.entityKey
      patched_model = ndb.Key(urlsafe=patched_model_key).get()
      print patched_model
      print my_model
      properties = Case().__class__.__dict__
      for p in properties.keys():
         
            if (eval('patched_model.'+p) != eval('my_model.'+p))and(eval('my_model.'+p)):
                exec('patched_model.'+p+'= my_model.'+p)
      

      patched_model.put()
      return patched_model
      #*******************************************#
  #HKA 14.12.2013 Case status APIs
  @Casestatus.method(user_required=True,path='casestatuses',http_method='POST',name='casestatuses.insert')
  def CasestatusInsert(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.owner = user_from_email.google_user_id
    my_model.organization = user_from_email.organization
    my_model.put()
    return my_model
  @Casestatus.query_method(user_required=True,query_fields=('limit','order','pageToken'),path='casestatuses',name='casestatuses.list')
  def CasestatusList(self,query):
    user_from_email = EndpointsHelper.require_iogrow_user()
    return query
  @Casestatus.method(user_required=True,
    http_method='PATCH',path='casestatuses/{id}',name='casestatuses.patch')
  def CasestatusPatch(self,my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    my_model.put()
    return my_model
  # Shows API
  # shows.insert api
  @Show.method(user_required=True,path='shows',http_method='POST',name='shows.insert')
  def shows_insert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # OAuth flow
      created_folder = EndpointsHelper.insert_folder(user_from_email,my_model.name)
      # Todo: Check permissions
      my_model.owner = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      organization = user_from_email.organization.get()
      my_model.organization_name = organization.name
      my_model.folder = created_folder['id']
      my_model.put()
      return my_model
  # shows.list api
  @Show.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='shows', name='shows.list')
  def shows_list(self, query):
      user_from_email = EndpointsHelper.require_iogrow_user()      
      return query.filter(ndb.OR(ndb.AND(Show.access=='public',Show.organization==user_from_email.organization),Show.owner==user_from_email.google_user_id, Show.collaborators_ids==user_from_email.google_user_id)).order(Show._key)
  # shows.get api
  @Show.method(request_fields=('id',),path='shows/{id}', http_method='GET', name='shows.get')
  def shows_get(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Show not found.')
    return my_model
  # shows.patch api
  @Show.method(user_required=True,
                http_method='PATCH', path='shows/{id}', name='shows.patch')
  def shows_patch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      if not my_model.from_datastore:
          raise endpoints.NotFoundException('Show not found.')
      patched_model_key = my_model.entityKey
      patched_model = ndb.Key(urlsafe=patched_model_key).get()
      print patched_model
      print my_model
      properties = Show().__class__.__dict__
      for p in properties.keys():
         
            if (eval('patched_model.'+p) != eval('my_model.'+p))and(eval('my_model.'+p)):
                exec('patched_model.'+p+'= my_model.'+p)
      

      patched_model.put()
      return patched_model
  # topics.list api
  @Topic.query_method(user_required=True,query_fields=('about_kind','about_item', 'limit', 'order', 'pageToken'),path='topics', name='topics.list')
  def TopicList(self, query):
      return query
  # comments.insert api 
  @Comment.method(user_required=True,path='comments',http_method='POST',name='comments.insert')
  def CommentInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      #discussion_key = ndb.Key(urlsafe=my_model.discussion)
      #my_model.discussion = discussion_key
      comment_author = model.Userinfo()
      comment_author.display_name = user_from_email.google_display_name
      comment_author.photo = user_from_email.google_public_profile_photo_url
      my_model.author = comment_author
      my_model.owner = user_from_email.google_user_id
      my_model.put()
      return my_model
  # comments.list api
  @Comment.query_method(user_required=True,query_fields=('limit', 'order','discussion','updated_at', 'pageToken'),path='comments',name='comments.list')
  def CommentList(self,query):
     return query
  # comments.get api
  @Comment.method(request_fields=('id',),path='comments/{id}', http_method='GET', name='comments.get')
  def CommentGet(self, my_model):
      if not my_model.from_datastore:
        raise endpoints.NotFoundException('Comment not found')
      return my_model
      
  # comments.update api
  @Comment.method(user_required=True,
                http_method='PUT', path='comments/{id}', name='comments.update')
  def CommentUpdate(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      #my_model.owner = user_from_email.google_user_id
      #my_model.organization =  user_from_email.organization

      my_model.put()
      return my_model
  # comments.patch api 
  @Comment.method(user_required=True,
                http_method='PATCH', path='comments/{id}', name='comments.patch')
  def CommentPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model

  # contributors.insert api
  @Contributor.method(user_required=True,path='contributors', http_method='POST', name='contributors.insert')
  def insert_contributor(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      
      # Todo: Check permissions
      my_model.created_by = user_from_email.google_user_id
      my_model.organization = user_from_email.organization
      discussion_key = my_model.discussionKey
      discussion_kind = discussion_key.kind() 
      discussion =  discussion_key.get()
      my_model.put()
      confirmation_url = "http://gcdc2013-iogrow.appspot.com"+DISCUSSIONS[discussion_kind]['url']+str(discussion_key.id())
      print confirmation_url
      sender_address =  my_model.name + " <notifications@gcdc2013-iogrow.appspotmail.com>"
      subject = "You're involved in this "+ DISCUSSIONS[discussion_kind]['title'] +": "+discussion.title
      print subject
      body = """
      %s involved you in this %s 

      %s
      """ % (user_from_email.google_display_name,DISCUSSIONS[discussion_kind]['title'],confirmation_url)
      mail.send_mail(sender_address, my_model.value , subject, body)
      return my_model
  # contributors.list api
  @Contributor.query_method(user_required=True,query_fields=('discussionKey', 'limit', 'order', 'pageToken'),path='contributors', name='contributors.list')
  def contributor_list(self, query):
      return query
  
  # notes.insert api
  @Note.method(user_required=True,path='notes', http_method='POST', name='notes.insert')
  def NoteInsert(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    note_author = model.Userinfo()
    note_author.display_name = user_from_email.google_display_name
    note_author.photo = user_from_email.google_public_profile_photo_url
    my_model.author = note_author
    my_model.owner = user_from_email.google_user_id
    my_model.organization =  user_from_email.organization
    my_model.put()
    return my_model


  # notes.get api
  @endpoints.method(ID_RESOURCE, DiscussionResponse,
                      path='notes/{id}', http_method='GET',
                      name='notes.get')
  def NoteGet(self, request):
        user_from_email = EndpointsHelper.require_iogrow_user()
        try:
            note = Note.get_by_id(int(request.id))
            about_item_id = int(note.about_item)
            try:
                about_object = OBJECTS[note.about_kind].get_by_id(about_item_id)
                if note.about_kind == 'Contact' or note.about_kind == 'Lead':
                    about_name = about_object.firstname + ' ' + about_object.lastname
                else:
                    about_name = about_object.name
                about_response = DiscussionAboutSchema(kind=note.about_kind,
                                                       id=note.about_item,
                                                       name=about_name)
                author = AuthorSchema(google_user_id = note.author.google_user_id,
                                      display_name = note.author.display_name,
                                      google_public_profile_url = note.author.google_public_profile_url,
                                      photo = note.author.photo)
                

                response = DiscussionResponse(id=request.id,
                                              entityKey= note.key.urlsafe(),
                                              title= note.title,
                                              content= note.content,
                                              comments=note.comments,
                                              about=about_response,
                                              author= author)
                return response
            except (IndexError, TypeError):
                raise endpoints.NotFoundException('About object %s not found.' %
                                                  (request.id,))
            
            

            
        except (IndexError, TypeError):
            raise endpoints.NotFoundException('Note %s not found.' %
                                              (request.id,))

  # notes.update api
  @Note.method(user_required=True,
                http_method='PUT', path='notes/{id}', name='notes.update')
  def NoteUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # notes.patch api
  @Note.method(user_required=True,
                http_method='PATCH', path='notes/{id}', name='notes.patch')
  def NotePatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions

      my_model.put()
      return my_model
  # Documents APIs
  # documents.insert api
  @Document.method(user_required=True,path='documents', http_method='POST', name='documents.insert')
  def DocumentInsert(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # prepare google drive service
    credentials = user_from_email.google_credentials
    http = httplib2.Http()
    service = build('drive', 'v2', http=http)
    credentials.authorize(http)
    organization = user_from_email.organization.get()

    # prepare params to insert
    document = {
                'title': my_model.title,
                'mimeType': my_model.mimeType        
    }#get the accounts_folder or contacts_folder or .. 
    about_item_id = int(my_model.about_item)
    parent_object = OBJECTS[my_model.about_kind].get_by_id(about_item_id)
    if parent_object:
        parent_folder = parent_object.folder
        if parent_folder:
            document['parents'] = [{'id': parent_folder}]
    
    # execute files.insert and get resource_id
    created_document = service.files().insert(body=document).execute()
    my_model.resource_id = created_document['id']
    my_model.embedLink = created_document['embedLink']
    # insert in the datastore
    
    # Todo: Check permissions
    author = model.Userinfo()
    author.google_user_id = user_from_email.google_user_id
    author.display_name = user_from_email.google_display_name
    author.photo = user_from_email.google_public_profile_photo_url
    my_model.author = author
    my_model.comments = 0
    my_model.owner = user_from_email.google_user_id
    my_model.organization = user_from_email.organization
    my_model.put()
    
    return my_model
  # documents.attachfiles api
  @endpoints.method(MultipleAttachmentRequest, message_types.VoidMessage,
                      path='documents/attachfiles', http_method='POST',
                      name='documents.attachfiles')
  def attach_files(self, request):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      items = request.items
      author = model.Userinfo()
      author.google_user_id = user_from_email.google_user_id
      author.display_name = user_from_email.google_display_name
      author.photo = user_from_email.google_public_profile_photo_url
      
      for item in items:
          document = Document(about_kind = request.about_kind,
                              about_item = request.about_item,
                              title = item.title,
                              resource_id = item.id,
                              mimeType = item.mimeType,
                              embedLink = item.embedLink,
                              owner = user_from_email.google_user_id,
                              organization = user_from_email.organization,
                              author=author,
                              comments = 0
                              )
          document.put()
      return message_types.VoidMessage()
  
  # documents.list api
  @Document.query_method(user_required=True,query_fields=('about_kind','about_item', 'limit', 'order', 'pageToken'),path='documents', name='documents.list')
  def DocumentList(self, query):
    return query 
  # documents.get api
  @endpoints.method(ID_RESOURCE, DiscussionResponse,
                      path='documents/{id}', http_method='GET',
                      name='documents.get')
  def document_get(self, request):
        user_from_email = EndpointsHelper.require_iogrow_user()
        try:
            document = Document.get_by_id(int(request.id))
            if document is None:
                raise endpoints.NotFoundException('Document not found.' %
                                              (request.id,))

            about_item_id = int(document.about_item)
            try:
                about_object = OBJECTS[document.about_kind].get_by_id(about_item_id)
                if document.about_kind == 'Contact' or document.about_kind == 'Lead':
                    about_name = about_object.firstname + ' ' + about_object.lastname
                else:
                    about_name = about_object.name
                about_response = DiscussionAboutSchema(kind=document.about_kind,
                                                       id=document.about_item,
                                                       name=about_name)
                author = AuthorSchema(google_user_id = document.author.google_user_id,
                                      display_name = document.author.display_name,
                                      google_public_profile_url = document.author.google_public_profile_url,
                                      photo = document.author.photo)
                

                response = DiscussionResponse(id=request.id,
                                              entityKey= document.key.urlsafe(),
                                              title= document.title,
                                              content= document.embedLink,
                                              comments=document.comments,
                                              about=about_response,
                                              author= author)
                return response
            except (IndexError, TypeError):
                raise endpoints.NotFoundException('About object %s not found.' %
                                                  (request.id,))
            
            

            
        except (IndexError, TypeError):
            raise endpoints.NotFoundException('Note %s not found.' %
                                              (request.id,))
  # documents.update api
  @Document.method(user_required=True,
                http_method='PUT', path='documents/{id}', name='documents.update')
  def DocumentUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # documents.patch api
  @Document.method(user_required=True,
                http_method='PATCH', path='documents/{id}', name='documents.patch')
  def DocumentPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  # Tasks APIs
  # tasks.insert api
  @Task.method(user_required=True,path='tasks', http_method='POST', name='tasks.insert')
  def TaskInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      if my_model.due:
          #insert an event on google calendar
          try:
                credentials = user_from_email.google_credentials
                http = credentials.authorize(httplib2.Http(memcache))
                service = build('calendar', 'v3', http=http)
                # prepare params to insert
                params = {
                 "start": 
                  {
                    "date": my_model.due.strftime("%Y-%m-%d")
                  },
                 "end": 
                  {
                    "date": my_model.due.strftime("%Y-%m-%d")
                  },
                  "summary": my_model.title,
                  
                                
                }
                
                created_event = service.events().insert(calendarId='primary',body=params).execute()
          except:
                raise endpoints.UnauthorizedException('Invalid grant' )
                return
      
      my_model.owner = user_from_email.google_user_id
      my_model.organization =  user_from_email.organization
      author = model.Userinfo()
      author.google_user_id = user_from_email.google_user_id
      author.display_name = user_from_email.google_display_name
      author.photo = user_from_email.google_public_profile_photo_url
      my_model.author = author
      my_model.put()
      return my_model
  # tasks.list api
  @Task.query_method(user_required=True,query_fields=('about_kind','about_item','status','id', 'due', 'limit', 'order', 'pageToken'),path='tasks', name='tasks.list')
  def TaskList(self, query):
      return query
  # tasks.get api
  @endpoints.method(ID_RESOURCE, TaskResponse,
                      path='tasks/{id}', http_method='GET',
                      name='tasks.get')
  def task_get(self, request):
        user_from_email = EndpointsHelper.require_iogrow_user()
        try:
            task = Task.get_by_id(int(request.id))
            about_item_id = int(task.about_item)
            try:
                about_object = OBJECTS[task.about_kind].get_by_id(about_item_id)
                if task.about_kind == 'Contact' or task.about_kind == 'Lead':
                    about_name = about_object.firstname + ' ' + about_object.lastname
                else:
                    about_name = about_object.name
                about_response = DiscussionAboutSchema(kind=task.about_kind,
                                                       id=task.about_item,
                                                       name=about_name)
                author = AuthorSchema(google_user_id = task.author.google_user_id,
                                      display_name = task.author.display_name,
                                      google_public_profile_url = task.author.google_public_profile_url,
                                      photo = task.author.photo)
                completed_by = None
                if completed_by:
                    completed_by = AuthorSchema(google_user_id = task.completed_by.google_user_id,
                                      display_name = task.completed_by.display_name,
                                      google_public_profile_url = task.completed_by.google_public_profile_url,
                                      photo = task.completed_by.photo)

                

                response = TaskResponse(id=request.id,
                                              entityKey = task.key.urlsafe(),
                                              title = task.title,
                                              due = task.due.isoformat(),
                                              status = task.status,
                                              comments = task.comments,
                                              about = about_response,
                                              author = author,
                                              completed_by = completed_by )
                return response
            except (IndexError, TypeError):
                raise endpoints.NotFoundException('About object %s not found.' %
                                                  (request.id,))
            
            

            
        except (IndexError, TypeError):
            raise endpoints.NotFoundException('Note %s not found.' %
                                              (request.id,))
  # events.insert api
  @Event.method(user_required=True,path='events', http_method='POST', name='events.insert')
  def EventInsert(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #insert an event on google calendar
    #insert an event on google calendar
    try:
        credentials = user_from_email.google_credentials
        http = credentials.authorize(httplib2.Http(memcache))
        service = build('calendar', 'v3', http=http)
              # prepare params to insert
        
        params = {
               "start": 
                {
                  "dateTime": my_model.starts_at.strftime("%Y-%m-%dT%H:%M:00.000+01:00")
                },
               "end": 
                {
                  "dateTime": my_model.ends_at.strftime("%Y-%m-%dT%H:%M:00.000+01:00")
                },
                "summary": my_model.title,
                "location": my_model.where,
                "reminders": 
                {
                  "overrides": 
                  [
                    {
                      "method": 'email',
                      "minutes": 30
                    }
                  ],
                  "useDefault": False
                }

        }
        
        created_event = service.events().insert(calendarId='primary',body=params).execute()
        
    except:
        raise endpoints.UnauthorizedException('Invalid grant' )
        return    
    author = model.Userinfo()
    author.google_user_id = user_from_email.google_user_id
    author.display_name = user_from_email.google_display_name
    author.photo = user_from_email.google_public_profile_photo_url
    my_model.author = author
    my_model.comments = 0
    my_model.owner = user_from_email.google_user_id
    my_model.organization =  user_from_email.organization
    my_model.put()
    

    return my_model
  # events.list api
  @Event.query_method(user_required=True,query_fields=('about_kind','about_item','id','status', 'starts_at','ends_at', 'limit', 'order', 'pageToken'),path='events', name='events.list')
  def EventList(self, query):
      return query     
  # events.get api
  @endpoints.method(ID_RESOURCE, EventResponse,
                      path='events/{id}', http_method='GET',
                      name='events.get')
  def event_get(self, request):
        user_from_email = EndpointsHelper.require_iogrow_user()
        try:
            event = Event.get_by_id(int(request.id))
            about_item_id = int(event.about_item)
            try:
                about_object = OBJECTS[event.about_kind].get_by_id(about_item_id)
                if event.about_kind == 'Contact' or event.about_kind == 'Lead':
                    about_name = about_object.firstname + ' ' + about_object.lastname
                else:
                    about_name = about_object.name
                about_response = DiscussionAboutSchema(kind=event.about_kind,
                                                       id=event.about_item,
                                                       name=about_name)
                author = AuthorSchema(google_user_id = event.author.google_user_id,
                                      display_name = event.author.display_name,
                                      google_public_profile_url = event.author.google_public_profile_url,
                                      photo = event.author.photo)
                response = EventResponse(id=request.id,
                                              entityKey = event.key.urlsafe(),
                                              title = event.title,
                                              starts_at = event.starts_at.isoformat(),
                                              ends_at = event.ends_at.isoformat(),
                                              where = event.where,
                                              comments = event.comments,
                                              about = about_response,
                                              author = author)
                return response
            except (IndexError, TypeError):
                raise endpoints.NotFoundException('About object %s not found.' %
                                                  (request.id,))
               
        except (IndexError, TypeError):
            raise endpoints.NotFoundException('EVent %s not found.' %
                                              (request.id,))

        
  # users.insert api
  @User.method(path='users', http_method='POST', name='users.insert')
  def UserInsert(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # OAuth flow
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json',
            scope=SCOPES)

        
        credentials = user_from_email.google_credentials

        if credentials is None or credentials.invalid:
            new_credentials = run(flow, credentials)
        else:
            new_credentials = credentials
        http = new_credentials.authorize(httplib2.Http(memcache))
        organization = user_from_email.organization.get()
        folderid = organization.org_folder
        new_permission = {
                         'value': my_model.email,
                         'type': 'user',
                         'role': 'writer'                  
        }
        service = build('drive', 'v2', http=http)
        service.permissions().insert(fileId=folderid,sendNotificationEmails= False, body=new_permission).execute()
    except:
        raise endpoints.UnauthorizedException('Invalid grant' )
        return 

    invited_user = model.User.query(model.User.email == my_model.email).get()
    
    if invited_user is not None:
        if invited_user.organization == user_from_email.organization or invited_user.organization is None:
            invited_user.organization = user_from_email.organization
            invited_user.status = 'invited'
            profile = model.Profile.query(model.Profile.name=='Standard User', model.Profile.organization==user_from_email.organization).get()
            invited_user.init_user_config(user_from_email.organization,profile.key)
            invited_user_id = invited_user.key.id()
            my_model.id = invited_user_id
            invited_user.put()
        elif invited_user.organization is not None:
            raise endpoints.UnauthorizedException('User exist within another organization' )
            return

            
    else:
        my_model.organization = user_from_email.organization
        my_model.status = 'invited'
        profile = model.Profile.query(model.Profile.name=='Standard User', model.Profile.organization==user_from_email.organization).get()
        my_model.init_user_config(user_from_email.organization,profile.key)
        
        my_model.put()
        invited_user_id = my_model.id
        
    confirmation_url = "http://gcdc2013-iogrow.appspot.com//sign-in?id=" + str(invited_user_id) + '&'
    sender_address = "ioGrow notifications <notifications@gcdc2013-iogrow.appspotmail.com>"
    subject = "Confirm your registration"
    body = """
    Thank you for creating an account! Please confirm your email address by
    clicking on the link below:

    %s
    """ % confirmation_url

    mail.send_mail(sender_address, my_model.email , subject, body)
    return my_model
  # users.list api
  @User.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='users', name='users.list')
  def UserList(self, query):
    user_from_email = EndpointsHelper.require_iogrow_user()
    organization = user_from_email.organization
    return query.filter(model.User.organization == organization)
  # users.get api
  @User.method(request_fields=('id',),path='users/{id}', http_method='GET', name='users.get')
  def UserGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Account not found.')
    return my_model
  # users.update api
  @User.method(user_required=True,
                http_method='PUT', path='users/{id}', name='users.update')
  def UserUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # users.patch api
  @User.method(user_required=True,
                http_method='PATCH', path='users/{id}', name='users.patch')
  def UserPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  # Groups API
  # groups.insert api
  @Group.method(user_required=True,path='groups', http_method='POST', name='groups.insert')
  def GroupInsert(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    my_model.organization = user_from_email.organization
    
    my_model.put()
    
    return my_model
  # groups.list api
  @Group.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='groups', name='groups.list')
  def GroupList(self, query):
    return query
  # groups.get api
  @Group.method(request_fields=('id',),path='groups/{id}', http_method='GET', name='groups.get')
  def GroupGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Account not found.')
    return my_model
  # groups.update api
  @Group.method(user_required=True,
                http_method='PUT', path='groups/{id}', name='groups.update')
  def GroupUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # groups.patch api
  @Group.method(user_required=True,
                http_method='PATCH', path='groups/{id}', name='groups.patch')
  def GroupPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  # members.insert api
  @Member.method(user_required=True,path='members', http_method='POST', name='members.insert')
  def MemberInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.organization = user_from_email.organization
      
      my_model.put()
      
      return my_model
  # members.list api
  @Member.query_method(user_required=True,query_fields=('limit', 'order','groupKey', 'pageToken'),path='members', name='members.list')
  def MemberList(self, query):
    return query
  # members.get api
  @Member.method(request_fields=('id',),path='members/{id}', http_method='GET', name='members.get')
  def MemberGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Account not found.')
    return my_model
  # members.update api
  @Member.method(user_required=True,
                http_method='PUT', path='members/{id}', name='members.update')
  def MemberUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # members.patch api
  @Member.method(user_required=True,
                http_method='PATCH', path='members/{id}', name='members.patch')
  def MemberPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  # Permissions APIs (Sharing Settings)
  # permissions.insert api
  @Permission.method(user_required=True,path='permissions', http_method='POST', name='permissions.insert')
  def PermissionInsert(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      
      my_model.organization = user_from_email.organization
      my_model.created_by = user_from_email.google_user_id
      #Check if the user has permission to invite people
      perm_object = Permission()
      perm = perm_object.get_user_perm(user_from_email,my_model.about_kind,my_model.about_item)
      print perm
      if perm is None or perm.role == 'readonly':
          raise endpoints.UnauthorizedException('You dont have permission to share this')
      if my_model.type == 'user':
          #try to get informations about this user and check if is in the same organization
          invited_user = model.User.query(model.User.email == my_model.value,model.User.organization==user_from_email.organization).get()
          if invited_user is None:
              raise endpoints.UnauthorizedException('The user does not exist')
         
          my_model.value = invited_user.google_user_id
          my_model.organization = user_from_email.organization
          my_model.put()
              #update collaborators on this objects:
          item_id = int(my_model.about_item)
          item = OBJECTS[my_model.about_kind].get_by_id(item_id)
          userinfo = Userinfo()
          if item.collaborators_ids:
            item.collaborators_ids.append(invited_user.google_user_id)
            new_collaborator = userinfo.get_basic_info(invited_user)
            item.collaborators_list.append(new_collaborator)

          else:
            collaborators_ids = list()
            collaborators= list()
            collaborators_ids.append(invited_user.google_user_id)
            item.collaborators_ids = collaborators_ids
            new_collaborator = userinfo.get_basic_info(invited_user)
            collaborators.append(new_collaborator)
            item.collaborators_list = collaborators

          print item
          item.put()
      #Todo Check if type is group
      return my_model

  # permissions.list api
  @Permission.query_method(user_required=True,query_fields=('limit', 'order', 'pageToken'),path='permissions',name='permissions.list')
  def PermissionList(self,query):
     return query 
  # permissions.get api
  @Permission.method(request_fields=('id',),path='permissions/{id}', http_method='GET', name='permissions.get')
  def PermissionGet(self, my_model):
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('Permission not found')
    return my_model
  # permissions.update api
  @Permission.method(user_required=True,
                http_method='PUT', path='permissions/{id}', name='permissions.update')
  def PermissionUpdate(self, my_model):
    user_from_email = EndpointsHelper.require_iogrow_user()
    # Todo: Check permissions
    #my_model.owner = user_from_email.google_user_id
    #my_model.organization =  user_from_email.organization

    my_model.put()
    return my_model
  # permissions.patch api
  @Permission.method(user_required=True,
                http_method='PATCH', path='permissions/{id}', name='permissions.patch')
  def PermissionPatch(self, my_model):
      user_from_email = EndpointsHelper.require_iogrow_user()
      # Todo: Check permissions
      my_model.put()
      return my_model
  # Search API
  @endpoints.method(SearchRequest, SearchResults,
                      path='search', http_method='POST',
                      name='search')
  def search_method(self, request):
      user_from_email = EndpointsHelper.require_iogrow_user()
      organization = str(user_from_email.organization.id())


      index = search.Index(name="GlobalIndex")
      #Show only objects where you have permissions
      query_string = request.q + ' AND (organization:' +organization+ ' AND (access:public OR (owner:'+ user_from_email.google_user_id +' OR collaborators:'+ user_from_email.google_user_id+')))'
      print query_string
      search_results = []
      count = 1
      limit = request.limit
      next_cursor = None
      if request.pageToken:
          cursor = search.Cursor(web_safe_string=request.pageToken)
      else:
          cursor = search.Cursor(per_result=True)
      if limit:
          options = search.QueryOptions(limit=limit,cursor=cursor)
      else:
          options = search.QueryOptions(cursor=cursor)    
      query = search.Query(query_string=query_string,options=options)
      try:
          if query:
              results = index.search(query)
              total_matches = results.number_found
              
              # Iterate over the documents in the results
              for scored_document in results:
                  kwargs = {
                      "id" : scored_document.doc_id, 
                      "rank" : scored_document.rank
                  }
                  for e in scored_document.fields:
                      if e.name in ["title","type"]:
                          kwargs[e.name]=e.value
                  search_results.append(SearchResult(**kwargs))
                  
                  next_cursor = scored_document.cursor.web_safe_string
              if next_cursor:
                  next_query_options = search.QueryOptions(limit=1,cursor=scored_document.cursor)
                  next_query = search.Query(query_string=query_string,options=next_query_options)
                  if next_query:
                      next_results = index.search(next_query)
                      if len(next_results.results)==0:
                          next_cursor = None


                      
                      
               
      except search.Error:
          logging.exception('Search failed')
      return SearchResults(items = search_results,nextPageToken=next_cursor)
