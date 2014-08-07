from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.api import search
from protorpc import messages
from search_helper import tokenize_autocomplete,SEARCH_QUERY_MODEL
from endpoints_proto_datastore.ndb import EndpointsModel
from iomodels.crmengine.tags import Tag,TagSchema
from iomodels.crmengine.opportunitystage import OpportunitystageSchema
from iograph import Node,Edge,InfoNodeListResponse
from iomodels.crmengine.documents import Document,DocumentListResponse
from iomodels.crmengine.notes import Note,TopicListResponse
from iomodels.crmengine.tasks import Task,TaskRequest,TaskListResponse
from iomodels.crmengine.events import Event,EventListResponse
from endpoints_helper import EndpointsHelper
import model
import iomessages
import datetime

class UpdateStageRequest(messages.Message):
    entityKey = messages.StringField(1,required=True)
    stage = messages.StringField(2,required=True)

class AccountSchema(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    name = messages.StringField(3)

class ListRequest(messages.Message):
    limit = messages.IntegerField(1)
    pageToken = messages.StringField(2)

class OpportunityGetRequest(messages.Message):
    id = messages.IntegerField(1,required = True)
    topics = messages.MessageField(ListRequest, 2)
    tasks = messages.MessageField(ListRequest, 3)
    events = messages.MessageField(ListRequest, 4)
    documents = messages.MessageField(ListRequest, 5)

class OpportunityInsertRequest(messages.Message):
    name = messages.StringField(1)
    stage = messages.StringField(3)
    account = messages.StringField(4)
    contact = messages.StringField(5)
    access = messages.StringField(6)
    opportunity_type = messages.StringField(7)
    duration =  messages.IntegerField(8)
    duration_unit  = messages.StringField(9)
    currency = messages.StringField(10)
    amount_per_unit = messages.IntegerField(11)
    amount_total = messages.IntegerField(12)
    closed_date = messages.StringField(13)
    competitor = messages.StringField(14)
    description = messages.StringField(15)
    infonodes = messages.MessageField(iomessages.InfoNodeRequestSchema,16,repeated=True)


class OpportunitySchema(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    name = messages.StringField(3)
    source = messages.StringField(4)
    current_stage = messages.MessageField(OpportunitystageSchema,5)
    stages = messages.MessageField(OpportunitystageSchema,6,repeated = True)
    infonodes = messages.MessageField(InfoNodeListResponse,7)
    topics = messages.MessageField(TopicListResponse,8)
    tasks = messages.MessageField(TaskListResponse,9)
    events = messages.MessageField(EventListResponse,10)
    documents = messages.MessageField(DocumentListResponse,11)
    tags = messages.MessageField(TagSchema,12, repeated = True)
    created_at = messages.StringField(13)
    updated_at = messages.StringField(14)
    access = messages.StringField(15)
    closed_date = messages.StringField(16)
    competitor = messages.StringField(17)
    reason_lost = messages.StringField(18)
    description = messages.StringField(19)
    opportunity_type = messages.StringField(20)
    duration =  messages.IntegerField(21)
    duration_unit  = messages.StringField(22)
    currency = messages.StringField(23)
    amount_per_unit = messages.IntegerField(24)
    amount_total = messages.IntegerField(25)
    account = messages.MessageField(AccountSchema,26)
    contact = messages.MessageField(iomessages.ContactSchema,27)
    owner = messages.MessageField(iomessages.UserSchema,28)

class OpportunityListRequest(messages.Message):
    limit = messages.IntegerField(1)
    pageToken = messages.StringField(2)
    order = messages.StringField(3)
    tags = messages.StringField(4,repeated = True)
    owner = messages.StringField(5)
    stage = messages.StringField(6)

class OpportunityListResponse(messages.Message):
    items = messages.MessageField(OpportunitySchema, 1, repeated=True)
    nextPageToken = messages.StringField(2)

class OpportunitySearchResult(messages.Message):
    id = messages.StringField(1)
    entityKey = messages.StringField(2)
    title = messages.StringField(3)
    amount = messages.IntegerField(4)
    account_name = messages.StringField(5)

class OpportunitySearchResults(messages.Message):
    items = messages.MessageField(OpportunitySearchResult, 1, repeated=True)
    nextPageToken = messages.StringField(2)

class Opportunity(EndpointsModel):
    owner = ndb.StringProperty()
    organization = ndb.KeyProperty()
    folder = ndb.StringProperty()
    account = ndb.KeyProperty()
    account_name = ndb.StringProperty()
    account_id = ndb.StringProperty()
    contact = ndb.KeyProperty()
    contact_name = ndb.StringProperty()
    contact_id = ndb.StringProperty()
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    industry = ndb.StringProperty()
    closed_date = ndb.DateTimeProperty()
    reason_lost = ndb.StringProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_by = ndb.KeyProperty()
    last_modified_by = ndb.KeyProperty()
    address = ndb.StringProperty()
    stagename = ndb.StringProperty()
    stage_probability = ndb.IntegerProperty()
    competitor = ndb.StringProperty()
    source = ndb.StringProperty()
    opportunity_type = ndb.StringProperty()
    duration =  ndb.IntegerProperty()
    duration_unit  = ndb.StringProperty()
    currency = ndb.StringProperty()
    amount_per_unit = ndb.IntegerProperty()
    amount_total = ndb.IntegerProperty()
    # public or private
    access = ndb.StringProperty()



    def put(self, **kwargs):
        ndb.Model.put(self, **kwargs)
        print kwargs
        self.put_index()
        self.set_perm()

    def set_perm(self):
        about_item = str(self.key.id())

        perm = model.Permission(about_kind='Opportunity',
                         about_item=about_item,
                         type = 'user',
                         role = 'owner',
                         value = self.owner)
        perm.put()



    def put_index(self,data=None):
        """ index the element at each"""
        empty_string = lambda x: x if x else ""
        organization = str(self.organization.id())
        title_autocomplete = ','.join(tokenize_autocomplete(self.name))
        if data:
            search_key = ['infos','opportunities','tags','collaborators']
            for key in search_key:
                if key not in data.keys():
                    data[key] = ""
            my_document = search.Document(
            doc_id = str(data['id']),
            fields=[
                search.TextField(name=u'type', value=u'Opportunity'),
                search.TextField(name='organization', value = empty_string(organization) ),
                search.TextField(name='access', value = empty_string(self.access) ),
                search.TextField(name='owner', value = empty_string(self.owner) ),
                search.TextField(name='collaborators', value = data['collaborators']  ),
                search.TextField(name='title', value = empty_string(self.name) ),
                search.TextField(name='stagename', value = empty_string(self.stagename) ),
                search.TextField(name='description', value = empty_string(self.description)),
                search.TextField(name='account_name', value = empty_string(self.account_name)),
                search.NumberField(name='amount_total', value = int(self.amount_total)),
                search.DateField(name='created_at', value = self.created_at),
                search.TextField(name='infos', value= data['infos']),
                search.TextField(name='tags', value= data['tags']),
                search.TextField(name='opportunities', value= data['opportunities']),
                search.TextField(name='title_autocomplete', value = empty_string(title_autocomplete)),
            ])
        else:
            my_document = search.Document(
            doc_id = str(self.key.id()),
            fields=[
                search.TextField(name=u'type', value=u'Opportunity'),
                search.TextField(name='organization', value = empty_string(organization) ),
                search.TextField(name='access', value = empty_string(self.access) ),
                search.TextField(name='owner', value = empty_string(self.owner) ),

                search.TextField(name='title', value = empty_string(self.name) ),
                search.TextField(name='stagename', value = empty_string(self.stagename) ),
                search.TextField(name='description', value = empty_string(self.description)),
                search.TextField(name='account_name', value = empty_string(self.account_name)),
                search.NumberField(name='amount_total', value = int(self.amount_total)),
                #search.DateField(name='closed_date', value = self.closed_date),
                search.DateField(name='created_at', value = self.created_at),
                #search.DateField(name='reason_lost', value = self.reason_lost),
                search.TextField(name='title_autocomplete', value = empty_string(title_autocomplete)),
            ])
        my_index = search.Index(name="GlobalIndex")
        my_index.put(my_document)

    @classmethod
    def get_schema(cls,user_from_email,request):
        opportunity = Opportunity.get_by_id(int(request.id))
        if opportunity is None:
            raise endpoints.NotFoundException('Opportunity not found.')
        if not Node.check_permission( user_from_email, opportunity ):
            raise endpoints.UnauthorizedException('You don\'t have permissions.')
        parents_edge_list = Edge.list(
                                    start_node = opportunity.key,
                                    kind = 'parents'
                                    )
        account_schema = None
        contact_schema = None
        for parent in parents_edge_list['items']:
            if parent.end_node.kind() == 'Account':
                account = parent.end_node.get()
                if account is not None:
                    account_schema = AccountSchema(
                                            id = str( account.key.id() ),
                                            entityKey = account.key.urlsafe(),
                                            name = account.name
                                            )
            elif parent.end_node.kind() == 'Contact':
                contact = parent.end_node.get()
                if contact is not None:
                    contact_schema = iomessages.ContactSchema(
                                            id = str( contact.key.id() ),
                                            entityKey = contact.key.urlsafe(),
                                            firstname = contact.firstname,
                                            lastname = contact.lastname,
                                            title = contact.title
                                            )
        #list of tags related to this account
        tag_list = Tag.list_by_parent(opportunity.key)
        # list of infonodes
        infonodes = Node.list_info_nodes(
                                        parent_key = opportunity.key,
                                        request = request
                                        )
        #list of topics related to this account
        topics = None
        if request.topics:
            topics = Note.list_by_parent(
                                        parent_key = opportunity.key,
                                        request = request
                                        )
        tasks = None
        if request.tasks:
            tasks = Task.list_by_parent(
                                        parent_key = opportunity.key,
                                        request = request
                                        )
        events = None
        if request.events:
            events = Event.list_by_parent(
                                        parent_key = opportunity.key,
                                        request = request
                                        )
        documents = None
        if request.documents:
            documents = Document.list_by_parent(
                                        parent_key = opportunity.key,
                                        request = request
                                        )
        opportunity_stage_edges = Edge.list(
                                                start_node = opportunity.key,
                                                kind = 'stages',
                                                limit = 1
                                                )
        current_stage_schema = None
        if len(opportunity_stage_edges['items'])>0:
            current_stage = opportunity_stage_edges['items'][0].end_node.get()
            current_stage_schema = OpportunitystageSchema(
                                                        name=current_stage.name,
                                                        probability= current_stage.probability,
                                                        stage_changed_at=opportunity_stage_edges['items'][0].created_at.isoformat()
                                                        )
        closed_date = None
        if opportunity.closed_date:
            closed_date = opportunity.closed_date.strftime("%Y-%m-%dT%H:%M:00.000")
        owner = model.User.get_by_gid(opportunity.owner)
        owner_schema = iomessages.UserSchema(
                                            id = str(owner.id),
                                            email = owner.email,
                                            google_display_name = owner.google_display_name,
                                            google_public_profile_photo_url=owner.google_public_profile_photo_url,
                                            google_public_profile_url=owner.google_public_profile_url,
                                            google_user_id = owner.google_user_id
                                            )
        opportunity_schema = OpportunitySchema(
                                  id = str( opportunity.key.id() ),
                                  entityKey = opportunity.key.urlsafe(),
                                  access = opportunity.access,
                                  account = account_schema,
                                  contact = contact_schema,
                                  name = opportunity.name,
                                  opportunity_type = opportunity.opportunity_type,
                                  duration = opportunity.duration,
                                  duration_unit = opportunity.duration_unit,
                                  amount_per_unit = opportunity.amount_per_unit,
                                  amount_total = opportunity.amount_total,
                                  currency = opportunity.currency,
                                  closed_date = closed_date,
                                  competitor = opportunity.competitor,
                                  reason_lost = opportunity.reason_lost,
                                  description = opportunity.description,
                                  source = opportunity.source,
                                  current_stage = current_stage_schema,
                                  tags = tag_list,
                                  topics = topics,
                                  tasks = tasks,
                                  events = events,
                                  documents = documents,
                                  infonodes = infonodes,
                                  created_at = opportunity.created_at.strftime("%Y-%m-%dT%H:%M:00.000"),
                                  updated_at = opportunity.updated_at.strftime("%Y-%m-%dT%H:%M:00.000"),
                                  owner = owner_schema
                                )
        return  opportunity_schema
    @classmethod
    def list(cls,user_from_email,request):
        curs = Cursor(urlsafe=request.pageToken)
        if request.limit:
            limit = int(request.limit)
        else:
            limit = 10
        items = list()
        you_can_loop = True
        count = 0
        while you_can_loop:
            if request.order:
                ascending = True
                if request.order.startswith('-'):
                    order_by = request.order[1:]
                    ascending = False
                else:
                    order_by = request.order
                attr = cls._properties.get(order_by)
                if attr is None:
                    raise AttributeError('Order attribute %s not defined.' % (attr_name,))
                if ascending:
                    opportunities, next_curs, more =  cls.query().filter(cls.organization==user_from_email.organization).order(+attr).fetch_page(limit, start_cursor=curs)
                else:
                    opportunities, next_curs, more = cls.query().filter(cls.organization==user_from_email.organization).order(-attr).fetch_page(limit, start_cursor=curs)
            else:
                opportunities, next_curs, more = cls.query().filter(cls.organization==user_from_email.organization).fetch_page(limit, start_cursor=curs)
            for opportunity in opportunities:
                if count<= limit:
                    is_filtered = True
                    if request.tags and is_filtered:
                        end_node_set = [ndb.Key(urlsafe=tag_key) for tag_key in request.tags]
                        if not Edge.find(start_node=opportunity.key,kind='tags',end_node_set=end_node_set,operation='AND'):
                            is_filtered = False
                    if request.owner and opportunity.owner!=request.owner and is_filtered:
                        is_filtered = False
                    if request.stage and is_filtered:
                        is_filtered = False
                        opportunity_stage_edges = Edge.list(
                                                            start_node = opportunity.key,
                                                            kind = 'stages',
                                                            limit = 1
                                                            )
                        if len(opportunity_stage_edges['items'])>0:
                            current_stage_key = opportunity_stage_edges['items'][0].end_node
                            if current_stage_key.urlsafe() == request.stage:
                                is_filtered = True
                    if is_filtered and Node.check_permission( user_from_email, opportunity ):
                        count = count + 1
                        #list of tags related to this opportunity
                        tag_list = Tag.list_by_parent(parent_key = opportunity.key)
                        closed_date = None
                        if opportunity.closed_date:
                            closed_date = opportunity.closed_date.strftime("%Y-%m-%dT%H:%M:00.000")
                        opportunity_stage_edges = Edge.list(
                                                                start_node = opportunity.key,
                                                                kind = 'stages',
                                                                limit = 1
                                                                )
                        current_stage_schema = None
                        if len(opportunity_stage_edges['items'])>0:
                            current_stage = opportunity_stage_edges['items'][0].end_node.get()
                            current_stage_schema = OpportunitystageSchema(
                                                                        name=current_stage.name,
                                                                        probability= current_stage.probability,
                                                                        stage_changed_at=opportunity_stage_edges['items'][0].created_at.isoformat()
                                                                        )
                        parents_edge_list = Edge.list(
                                                    start_node = opportunity.key,
                                                    kind = 'parents'
                                                    )
                        account_schema = None
                        contact_schema = None
                        for parent in parents_edge_list['items']:
                            if parent.end_node.kind() == 'Account':
                                account = parent.end_node.get()
                                if account is not None:
                                    account_schema = AccountSchema(
                                                            id = str( account.key.id() ),
                                                            entityKey = account.key.urlsafe(),
                                                            name = account.name
                                                            )
                            elif parent.end_node.kind() == 'Contact':
                                contact = parent.end_node.get()
                                if contact is not None:
                                    contact_schema = iomessages.ContactSchema(
                                                            id = str( contact.key.id() ),
                                                            entityKey = contact.key.urlsafe(),
                                                            firstname = contact.firstname,
                                                            lastname = contact.lastname,
                                                            title = contact.title
                                                            )
                        opportunity_schema = OpportunitySchema(
                                  id = str( opportunity.key.id() ),
                                  entityKey = opportunity.key.urlsafe(),
                                  name = opportunity.name,
                                  opportunity_type = opportunity.opportunity_type,
                                  duration = opportunity.duration,
                                  duration_unit = opportunity.duration_unit,
                                  amount_per_unit = opportunity.amount_per_unit,
                                  amount_total = opportunity.amount_total,
                                  currency = opportunity.currency,
                                  closed_date=closed_date,
                                  current_stage = current_stage_schema,
                                  account = account_schema,
                                  contact = contact_schema,
                                  tags = tag_list,
                                  created_at = opportunity.created_at.strftime("%Y-%m-%dT%H:%M:00.000"),
                                  updated_at = opportunity.updated_at.strftime("%Y-%m-%dT%H:%M:00.000")
                                )
                        items.append(opportunity_schema)
            if (count == limit):
                you_can_loop = False
            if more and next_curs:
                curs = next_curs
            else:
                you_can_loop = False
        if next_curs and more:
            next_curs_url_safe = next_curs.urlsafe()
        else:
            next_curs_url_safe = None
        return  OpportunityListResponse(items = items, nextPageToken = next_curs_url_safe)

    @classmethod
    def list_by_parent(cls,user_from_email,parent_key,request):
        opportunity_list = []
        you_can_loop = True
        count = 0
        if request.opportunities.limit:
            limit = int(request.opportunities.limit)
        else:
            limit = 10
        opportunity_next_curs = request.opportunities.pageToken
        while you_can_loop:
            edge_limit = int(request.opportunities.limit) - count
            if edge_limit>0:
                opportunity_edge_list = Edge.list(
                                    start_node = parent_key,
                                    kind='opportunities',
                                    limit=request.opportunities.limit,
                                    pageToken=request.opportunities.pageToken
                                )
                for edge in opportunity_edge_list['items']:
                    opportunity = edge.end_node.get()
                    if Node.check_permission(user_from_email,opportunity):
                        tag_list = Tag.list_by_parent(parent_key = opportunity.key)
                        opportunity_stage_edges = Edge.list(
                                                            start_node = opportunity.key,
                                                            kind = 'stages',
                                                            limit = 1
                                                            )
                        current_stage_schema = None
                        if len(opportunity_stage_edges['items'])>0:
                            current_stage = opportunity_stage_edges['items'][0].end_node.get()
                            current_stage_schema = OpportunitystageSchema(
                                                                    name=current_stage.name,
                                                                    probability= int(current_stage.probability),
                                                                    stage_changed_at=opportunity_stage_edges['items'][0].created_at.isoformat()
                                                                    )
                        count = count + 1
                        closed_date = None
                        if opportunity.closed_date:
                            closed_date = opportunity.closed_date.strftime("%Y-%m-%dT%H:%M:00.000")
                        opportunity_schema = OpportunitySchema(
                                              id = str( opportunity.key.id() ),
                                              entityKey = opportunity.key.urlsafe(),
                                              name = opportunity.name,
                                              opportunity_type = opportunity.opportunity_type,
                                              duration = opportunity.duration,
                                              duration_unit = opportunity.duration_unit,
                                              amount_per_unit = opportunity.amount_per_unit,
                                              amount_total = opportunity.amount_total,
                                              currency = opportunity.currency,
                                              current_stage = current_stage_schema,
                                              tags = tag_list,
                                              closed_date=closed_date,
                                              created_at = opportunity.created_at.strftime("%Y-%m-%dT%H:%M:00.000"),
                                              updated_at = opportunity.updated_at.strftime("%Y-%m-%dT%H:%M:00.000")
                                            )
                        opportunity_list.append(opportunity_schema)

                if opportunity_edge_list['next_curs'] and opportunity_edge_list['more']:
                    opportunity_next_curs = opportunity_edge_list['next_curs'].urlsafe()
                else:
                    you_can_loop = False
                    opportunity_next_curs = None
            if (count == limit):
                you_can_loop = False

        return OpportunityListResponse(
                                    items = opportunity_list,
                                    nextPageToken = opportunity_next_curs
                                )

    @classmethod
    def search(cls,user_from_email,request):
        organization = str(user_from_email.organization.id())
        index = search.Index(name="GlobalIndex")
        #Show only objects where you have permissions
        query_string = SEARCH_QUERY_MODEL % {
                               "type": "Opportunity",
                               "query": request.q,
                               "organization": organization,
                               "owner": user_from_email.google_user_id,
                               "collaborators": user_from_email.google_user_id
                               }
        #print query_string
        search_results = []
        if request.limit:
            limit = int(request.limit)
        else:
            limit = 10
        next_cursor = None
        if request.pageToken:
            cursor = search.Cursor(web_safe_string=request.pageToken)
        else:
            cursor = search.Cursor(per_result=True)
        if limit:
            options = search.QueryOptions(limit=limit, cursor=cursor)
        else:
            options = search.QueryOptions(cursor=cursor)
        query = search.Query(query_string=query_string, options=options)
        try:
            if query:
                result = index.search(query)
                if len(result.results) == limit + 1:
                    next_cursor = result.results[-1].cursor.web_safe_string
                else:
                    next_cursor = None
                results = result.results[:limit]
                for scored_document in results:
                    kwargs = {
                        'id': scored_document.doc_id
                    }
                    for e in scored_document.fields:
                        if e.name in ["title", "amount", "account_name"]:
                            if e.name == "amount":
                                kwargs[e.name] = int(e.value)
                            else:
                                kwargs[e.name] = e.value
                    search_results.append(OpportunitySearchResult(**kwargs))

        except search.Error:
            logging.exception('Search failed')
        return OpportunitySearchResults(
                                        items=search_results,
                                        nextPageToken=next_cursor
                                        )

    @classmethod
    def insert(cls,user_from_email,request):
        if request.opportunity_type=='fixed_bid':
            amount_total = request.amount_total
        elif request.amount_per_unit and request.duration:
            amount_total = request.amount_per_unit * request.duration
        closed_date = None
        if request.closed_date:
            closed_date = datetime.datetime.strptime(
                                                    request.closed_date,
                                                    "%Y-%m-%d"
                                                )

        opportunity = cls(
                    owner = user_from_email.google_user_id,
                    organization = user_from_email.organization,
                    access = request.access,
                    name = request.name,
                    opportunity_type = request.opportunity_type,
                    amount_total = request.amount_total,
                    amount_per_unit = request.amount_per_unit,
                    duration = request.duration,
                    duration_unit = request.duration_unit,
                    currency = request.currency,
                    closed_date = closed_date,
                    competitor = request.competitor,
                    description = request.description
                    )
        print opportunity
        opportunity_key = opportunity.put_async()
        opportunity_key_async = opportunity_key.get_result()
        # taskqueue.add(
        #             url='/workers/createobjectfolder',
        #             params={
        #                     'kind': "Opportunity",
        #                     'folder_name': request.name,
        #                     'email': user_from_email.email,
        #                     'obj_key':opportunity_key_async.urlsafe()
        #                     }
        #             )
        indexed = False
        if request.stage:
            stage_key = ndb.Key(urlsafe=request.stage)
            # insert edges
            Edge.insert(start_node = opportunity_key_async ,
                      end_node = stage_key,
                      kind = 'stages',
                      inverse_edge = 'related_opportunities')
        if request.contact:
            contact_key = ndb.Key(urlsafe=request.contact)
            # insert edges
            Edge.insert(start_node = contact_key,
                      end_node = opportunity_key_async,
                      kind = 'opportunities',
                      inverse_edge = 'parents')
            EndpointsHelper.update_edge_indexes(
                                            parent_key = opportunity_key_async,
                                            kind = 'opportunities',
                                            indexed_edge = str(contact_key.id())
                                            )
            parents_edge_list = Edge.list(
                                start_node = contact_key,
                                kind = 'parents',
                                limit = 1
                                )
            if len(parents_edge_list['items'])>0:
                request.account = parents_edge_list['items'][0].end_node.urlsafe()
            indexed = True
        if request.account:
            account_key = ndb.Key(urlsafe=request.account)
            # insert edges
            Edge.insert(start_node = account_key,
                      end_node = opportunity_key_async,
                      kind = 'opportunities',
                      inverse_edge = 'parents')
            EndpointsHelper.update_edge_indexes(
                                            parent_key = opportunity_key_async,
                                            kind = 'opportunities',
                                            indexed_edge = str(account_key.id())
                                            )
            indexed = True

        for infonode in request.infonodes:
            Node.insert_info_node(
                            opportunity_key_async,
                            iomessages.InfoNodeRequestSchema(
                                                            kind = infonode.kind,
                                                            fields = infonode.fields
                                                        )
                                                    )
        if not indexed:
            data = {}
            data['id'] = opportunity_key_async.id()
            opportunity.put_index(data)

        opportunity_schema = OpportunitySchema(
                                  id = str( opportunity_key_async.id() ),
                                  entityKey = opportunity_key_async.urlsafe(),
                                  name = opportunity.name,
                                  amount_total = opportunity.amount_total,
                                  created_at = opportunity.created_at.strftime("%Y-%m-%dT%H:%M:00.000"),
                                  updated_at = opportunity.updated_at.strftime("%Y-%m-%dT%H:%M:00.000")
                                )
        return opportunity_schema
    @classmethod
    def update_stage(cls,user_from_email,request):
        opportunity_key =  ndb.Key(urlsafe=request.entityKey)
        stage_key = ndb.Key(urlsafe=request.stage)
        # insert edges
        Edge.insert(start_node = opportunity_key,
                  end_node = stage_key,
                  kind = 'stages',
                  inverse_edge = 'related_opportunities')
