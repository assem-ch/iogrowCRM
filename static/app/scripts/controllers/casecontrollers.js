app.controller('CaseListCtrl', ['$scope','Auth','Case','Account','Contact','Casestatus','Tag','Edge',
    function($scope,Auth,Case,Account,Contact,Casestatus,Tag,Edge) {
    
     document.title = "Cases: Home";
     $("ul.page-sidebar-menu li").removeClass("active");
     $("#id_Cases").addClass("active");
     $scope.isSignedIn = false;
     $scope.immediateFailed = false;
     $scope.nextPageToken = undefined;
     $scope.prevPageToken = undefined;
     $scope.isLoading = false;
     $scope.pagination = {};
     $scope.casepagination={};
     $scope.currentPage = 01;
     $scope.pages = [];
     //HKA 11.12.2013 Manage Next & Prev
     $scope.casepagination = {};
     $scope.caseCurrentPage=01;
     $scope.casepages=[];

     $scope.cases = [];
     $scope.casee = {};
     $scope.casee.access ='public';
     $scope.casee.status = 'pending';
     $scope.casee.priority = 4;
     $scope.casee.account_name = undefined;
     $scope.casee.contact_name = undefined;
     $scope.order = '-updated_at';
     $scope.selected_tags = [];
     $scope.draggedTag=null;
     
      // What to do after authentication
       $scope.runTheProcess = function(){
            var params = {'order' : $scope.order,'limit':6}
            Case.list($scope,params);
            Casestatus.list($scope,{});
            var paramsTag = {'about_kind':'Case'};
            Tag.list($scope,paramsTag);
       };
        // We need to call this to refresh token when user credentials are invalid
       $scope.refreshToken = function() {
            Auth.refreshToken();
       };
     
     $scope.listNextPageItems = function(){
                    
        var nextPage = $scope.caseCurrentPage + 1;
        var params = {};
          if ($scope.casepages[nextPage]){
            params = {'order' : $scope.order,'limit':6,
                      'pageToken':$scope.casepages[nextPage]
                     }
          }else{
            params = {'order' : $scope.order,'limit':6}
          }
          console.log('in listNextPageItems');
          $scope.caseCurrentPage = $scope.caseCurrentPage + 1 ; 
          Case.list($scope,params);
     }
     $scope.listPrevPageItems = function(){
                
       var prevPage = $scope.caseCurrentPage - 1;
       var params = {};
          if ($scope.casepages[prevPage]){
            params = {'order' : $scope.order,'limit':6,
                      'pageToken':$scope.casepages[prevPage]
                     }
          }else{
            params = {'order' : $scope.order,'limit':6}
          }
          $scope.caseCurrentPage = $scope.caseCurrentPage - 1 ;
          Case.list($scope,params);
     }
     
     
     
     $scope.showModal = function(){
        console.log('button clicked');
        $('#addCaseModal').modal('show');

      };
      
    
    $scope.save = function(casee){
        
        
        
        if (typeof(casee.account)=='object'){
          
          casee.account_name = casee.account.name;
          casee.account = casee.account.entityKey;
          console.log('in cases.save - account') ;
          console.log(casee.account);
          console.log(casee);
          
          if (typeof(casee.contact)=='object'){
              
              casee.contact_name = casee.contact.firstname + ' '+ casee.contact.lastname ;
              casee.contact = casee.contact.entityKey;
              console.log('in cases.save - contact');
              console.log(casee.contact);
              console.log(casee);

          }
          Case.insert($scope,casee);

        }else if($scope.searchAccountQuery.length>0){
            // create a new account with this account name
            var params = {'name': $scope.searchAccountQuery,
                          'access': casee.access
            };
            $scope.casee = casee;
            Account.insert($scope,params);


        };

        
        $('#addCaseModal').modal('hide');
      };
      $scope.addCaseOnKey = function(casee){
        if(event.keyCode == 13 && casee.name){
            $scope.save(casee);
        }
      };
      $scope.accountInserted = function(resp){
          $scope.casee.account = resp;
          $scope.save($scope.casee);
      };
      
     var params_search_account ={};
     $scope.contactResult = undefined;
     $scope.accountResult = undefined;
     $scope.q = undefined;
     
      $scope.$watch('searchAccountQuery', function() {
        if ($scope.searchAccountQuery.length>1){
         params_search_account['q'] = $scope.searchAccountQuery;
         gapi.client.crmengine.accounts.search(params_search_account).execute(function(resp) {
            console.log("in accouts.search api");
            console.log(params_search_account);

            console.log(resp);
            if (resp.items){
              $scope.accountsResults = resp.items;
              
              $scope.$apply();
            };
            
          });
         }
      });
      $scope.selectAccount = function(){
        $scope.casee.account = $scope.searchAccountQuery;

     };
     var params_search_contact ={};
     $scope.$watch('searchContactQuery', function() {
        if($scope.searchContactQuery.length>1){
         params_search_contact['q'] = $scope.searchContactQuery;
         gapi.client.crmengine.contacts.search(params_search_contact).execute(function(resp) {
            
            if (resp.items){
              $scope.contactsResults = resp.items;
              
              $scope.$apply();
            };
            
          });
         }
        
      });
     $scope.selectContact = function(){
        $scope.casee.contact = $scope.searchContactQuery;
        var account = {'entityKey':$scope.searchContactQuery.account,
                      'name':$scope.searchContactQuery.account_name};
        $scope.casee.account = account;
        $scope.searchAccountQuery = $scope.searchContactQuery.account_name;
      };
    // Quick Filtering
     var searchParams ={};
     $scope.result = undefined;
     $scope.q = undefined;
     
     $scope.$watch('searchQuery', function() {
         searchParams['q'] = $scope.searchQuery;
         searchParams['limit'] = 7;
         if ($scope.searchQuery){
         Case.search($scope,searchParams);
       };
     });
     $scope.selectResult = function(){
          window.location.replace('#/cases/show/'+$scope.searchQuery.id);
     };
     $scope.executeSearch = function(searchQuery){
        if (typeof(searchQuery)=='string'){
           var goToSearch = 'type:Case ' + searchQuery;
           window.location.replace('#/search/'+goToSearch);
        }else{
          window.location.replace('#/cases/show/'+searchQuery.id);
        }
        $scope.searchQuery=' ';
        $scope.$apply();
     };
     // Sorting
     $scope.orderBy = function(order){
        var params = { 'order': order,
                        'limit':6};
        $scope.order = order;
        Case.list($scope,params);
     };
     $scope.filterByOwner = function(filter){
        if (filter){
          var params = { 'owner': filter,
                         'order': $scope.order, 
                         'limit':6}
        }
        else{
          var params = {
              'order': $scope.order, 
              
              'limit':6}
        };
        $scope.isFiltering = true;
        Case.list($scope,params);
     };
     $scope.filterByStatus = function(filter){
        if (filter){
          var params = { 'status': filter,
                         'order': $scope.order, 
                         'limit':6}
        }
        else{
          var params = {
              'order': $scope.order, 
              
              'limit':6}
        };
        $scope.isFiltering = true;
        Case.list($scope,params);
     };

    
    /***********************************************
      HKA 19.02.2014  tags 
***************************************************************************************/
$scope.listTags=function(){
      var paramsTag = {'about_kind':'Case'}
      Tag.list($scope,paramsTag);
     };
$scope.edgeInserted = function () {
       $scope.listcases();
     };
$scope.listcases = function(){
  var params = { 'order': $scope.order,
                        'limit':6}
          Case.list($scope,params);
};


$scope.addNewtag = function(tag){
       var params = {   
                          'name': tag.name,
                          'about_kind':'Case',
                          'color':$('#tag-col-pick').val()
                      }  ;
       Tag.insert($scope,params);
        $scope.tag.name='';
        $('#tag-col-pick').val('#8fff00');
        var paramsTag = {'about_kind':'Case'};
        Tag.list($scope,paramsTag);
        
     }
$scope.updateTag = function(tag){
            params ={ 'id':tag.id,
                      'title': tag.name,
                      'status':tag.color
            };
      Tag.patch($scope,params);
  };
  $scope.deleteTag=function(tag){
          params = {
            'entityKey': tag.entityKey
          }
          Tag.delete($scope,params);
          
      };


 
$scope.selectTag= function(tag,index,$event){
      if(!$scope.manage_tags){
         var element=$($event.target);
         if(element.prop("tagName")!='LI'){
              element=element.parent();
              element=element.parent();
         }
         var text=element.find(".with-color");
         if($scope.selected_tags.indexOf(tag) == -1){
            $scope.selected_tags.push(tag);
            element.css('background-color', tag.color+'!important');
            text.css('color',$scope.idealTextColor(tag.color));

         }else{
            element.css('background-color','#ffffff !important');
            $scope.selected_tags.splice($scope.selected_tags.indexOf(tag),1);
             text.css('color','#000000');
         }
         ;
         $scope.filterByTags($scope.selected_tags);

      }

    };
  $scope.filterByTags = function(selected_tags){
         var tags = [];
         angular.forEach(selected_tags, function(tag){
            tags.push(tag.entityKey);
         });
         var params = {
          'tags': tags,
          'order': $scope.order,
                        'limit':6
         }
        $scope.isFiltering = true;
         Case.list($scope,params);

  };

$scope.unselectAllTags= function(){
        $('.tags-list li').each(function(){
            var element=$(this);
            var text=element.find(".with-color");
             element.css('background-color','#ffffff !important');
             text.css('color','#000000');
        });
     };
//HKA 19.02.2014 When delete tag render account list
 $scope.tagDeleted = function(){
    $scope.listcases();

 };


$scope.manage=function(){
        $scope.unselectAllTags();
      };
$scope.tag_save = function(tag){
          if (tag.name) {
             Tag.insert($scope,tag);
             
           };
      };

$scope.editTag=function(tag){
        $scope.edited_tag=tag;
     }
$scope.doneEditTag=function(tag){
        $scope.edited_tag=null;
        $scope.updateTag(tag);
     }
$scope.addTags=function(){
      var tags=[];
      var items = [];
      tags=$('#select2_sample2').select2("val");
      
      angular.forEach($scope.selected_tasks, function(selected_task){
          angular.forEach(tags, function(tag){
            var edge = {
              'start_node': selected_task.entityKey,
              'end_node': tag,
              'kind':'tags',
              'inverse_edge': 'tagged_on'
            };
            items.push(edge);
          });
      });

      params = {
        'items': items
      }
      
      Edge.insert($scope,params);
      $('#assigneeTagsToTask').modal('hide');

     };

     var handleColorPicker = function () {
          if (!jQuery().colorpicker) {
              return;
              
          }
          $('.colorpicker-default').colorpicker({
              format: 'hex'
          });
      }
      handleColorPicker();
     
      $('#addMemberToTask > *').on('click', null, function(e) {
            e.stopPropagation();
        });
      $scope.idealTextColor=function(bgColor){
        var nThreshold = 105;
         var components = getRGBComponents(bgColor);
         var bgDelta = (components.R * 0.299) + (components.G * 0.587) + (components.B * 0.114);

         return ((255 - bgDelta) < nThreshold) ? "#000000" : "#ffffff";  
      }
      function getRGBComponents(color) {       

          var r = color.substring(1, 3);
          var g = color.substring(3, 5);
          var b = color.substring(5, 7);

          return {
             R: parseInt(r, 16),
             G: parseInt(g, 16),
             B: parseInt(b, 16)
          };
      }
      $scope.dragTag=function(tag){
        $scope.draggedTag=tag;
         $scope.$apply();
      };
      $scope.dropTag=function(casee){
        var items = [];
        
        var edge = {
             'start_node': casee.entityKey,
              'end_node': $scope.draggedTag.entityKey,
              'kind':'tags',
              'inverse_edge': 'tagged_on'
        };
        items.push(edge);
        params = {
          'items': items
        };
                Edge.insert($scope,params);
        $scope.draggedTag=null;
      }; 
    

   // Google+ Authentication 
     Auth.init($scope);

    
}]);

app.controller('CaseShowCtrl', ['$scope','$filter', '$route','Auth','Case', 'Topic','Note','Task','Event','Permission','User','Casestatus','Email','Attachement','InfoNode',
    function($scope,$filter,$route,Auth,Case,Topic,Note,Task,Event,Permission,User,Casestatus,Email,Attachement,InfoNode) {
      $("ul.page-sidebar-menu li").removeClass("active");
      $("#id_Cases").addClass("active");
      
     $scope.selectedTab = 2;
     $scope.isSignedIn = false;
     $scope.immediateFailed = false;
     $scope.nextPageToken = undefined;
     $scope.prevPageToken = undefined;
     $scope.isLoading = false;
     $scope.pagination = {};
      //HKA 10.12.2013 Var topic to manage Next & Prev
     $scope.topicCurrentPage=01;
     $scope.topicpagination={};
     $scope.topicpages = [];
     $scope.nextPageToken = undefined;
     $scope.prevPageToken = undefined;
     $scope.status_selected={};
     $scope.currentPage = 01;
     $scope.pages = [];
     $scope.cases = [];
     $scope.users = [];
     $scope.user = undefined;
     $scope.slected_memeber = undefined;
     $scope.email = {};
     
   
     // What to do after authentication
       $scope.runTheProcess = function(){
          var caseid = {'id':$route.current.params.caseId};
          Case.get($scope,caseid);
          User.list($scope,{});
          Casestatus.list($scope,{});
       };
        // We need to call this to refresh token when user credentials are invalid
       $scope.refreshToken = function() {
            Auth.refreshToken();
       };
     $scope.TopiclistNextPageItems = function(){
         
        
        var nextPage = $scope.topicCurrentPage + 1;
        var params = {};
          if ($scope.topicpages[nextPage]){
            params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5,
                      'pageToken':$scope.topicpages[nextPage]
                     }
          }else{
            params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5}
          }
          console.log('in listNextPageItems');
          $scope.topicCurrentPage = $scope.topicCurrentPage + 1 ; 
          Topic.list($scope,params);
     }
     $scope.TopiclistPrevPageItems = function(){
       
       var prevPage = $scope.topicCurrentPage - 1;
       var params = {};
          if ($scope.topicpages[prevPage]){
            params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5,
                      'pageToken':$scope.topicpages[prevPage]
                     }
          }else{
            params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5}
          }
          $scope.topicCurrentPage = $scope.topicCurrentPage - 1 ;
          Topic.list($scope,params);
          
     }
    
     $scope.listTopics = function(casee){
        var params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5
                      };
        Topic.list($scope,params);

     }
     $scope.hilightTopic = function(){
        
       $('#topic_0').effect( "bounce", "slow" );
       $('#topic_0 .message').effect("highlight","slow");
     }

    
     $scope.selectMember = function(){
        console.log('slecting user yeaaah');
        $scope.slected_memeber = $scope.user;
        $scope.user = $scope.slected_memeber.google_display_name;

     };
     $scope.share = function(slected_memeber){
        console.log('permissions.insert share');
        console.log(slected_memeber);
        $scope.$watch($scope.casee.access, function() {
         var body = {'access':$scope.casee.access};
         var id = $scope.account.id;
         var params ={'id':id,
                      'access':$scope.casee.access};
          console.log('patching');
          console.log(params);
         Case.patch($scope,params);
        });
        $('#sharingSettingsModal').modal('hide');

        if (slected_memeber.email){
        var params = {  'type': 'user',
                        'role': 'writer',
                        'value': slected_memeber.email,
                        'about_kind': 'Case',
                        'about_item': $scope.account.id

                        
          };
          Permission.insert($scope,params); 
          
          
        }else{ 
          alert('select a user to be invited');
        };


     };
     
     $scope.updateCollaborators = function(){
         
          Case.get($scope,$scope.case.id);

     };
     $scope.showModal = function(){
        console.log('button clicked');
        $('#addCaseModal').modal('show');

      };
      
    $scope.addNote = function(note){
      console.log('debug addNote');
      
      var params ={
                  'about_kind': 'Case',
                  'about_item': $scope.casee.id,
                  'title': note.title,
                  'content': note.content
      };
      console.log(params);
      Note.insert($scope,params);
      $scope.note.title = '';
      $scope.note.content = '';
    };
      



    $scope.editcase = function() {
       $('#EditCaseModal').modal('show');
    }
//HKA 09.11.2013 Add a new Task
   $scope.addTask = function(task){
      
        $('#myModal').modal('hide');
        var params ={}

        console.log('adding a new task');
        console.log(task);
        
        if (task.due){

            var dueDate= $filter('date')(task.due,['yyyy-MM-dd']);
            dueDate = dueDate +'T00:00:00.000000'
            params ={'title': task.title,
                      'due': dueDate,
                      'about':$scope.casee.entityKey
            }
            console.log(dueDate);
        }else{
            params ={'title': task.title,
                     'about':$scope.casee.entityKey}
        };
        Task.insert($scope,params);
     }

     $scope.hilightTask = function(){
        
        $('#task_0').effect("highlight","slow");
        $('#task_0').effect( "bounce", "slow" );
       
     }
     $scope.listTasks = function(){
        var params = {'about':$scope.casee.entityKey,
                      'order': '-updated_at',
                      
                      };
        Task.list($scope,params);

     }
 //HKA 10.11.2013 Add event 
 $scope.addEvent = function(ioevent){
      
        $('#newEventModal').modal('hide');
        var params ={}       
        
        if (ioevent.starts_at){
            if (ioevent.ends_at){
              params ={'title': ioevent.title,
                      'starts_at': $filter('date')(ioevent.starts_at,['yyyy-MM-ddTHH:mm:00.000000']),
                      'ends_at': $filter('date')(ioevent.ends_at,['yyyy-MM-ddTHH:mm:00.000000']),
                      'where': ioevent.where,
                      'about_kind':'Case',
                      'about_item':$scope.casee.id
              }

            }else{
              params ={'title': ioevent.title,
                      'starts_at': $filter('date')(ioevent.starts_at,['yyyy-MM-ddTHH:mm:00.000000']),
                      'where': ioevent.where,
                      'about_kind':'Case',
                      'about_item':$scope.casee.id
              }
            }
            console.log('inserting the event');
            console.log(params);
            Event.insert($scope,params);

            
        };
     }
     $scope.hilightEvent = function(){
        console.log('Should higll');
        $('#event_0').effect("highlight","slow");
        $('#event_0').effect( "bounce", "slow" );
       
     }
     $scope.listEvents = function(){
        var params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': 'starts_at',
                      'limit': 5
                      };
        Event.list($scope,params);

     }
  //HKA 11.11.2013 Add Note
  $scope.addNote = function(note){
    var params = {'title':$scope.note.title,
                  'content':$scope.note.content,
                  'about_item':$scope.casee.id,
                  'about_kind':'Case' };
    Note.insert($scope,params);
    $scope.note.title='';
    $scope.note.content='';
  }

//HKA 22.11.2013 Update Case
$scope.updatCasetHeader = function(casee){
 
  params = {'id':$scope.casee.id,
             'name':casee.name,
             'priority' :casee.priority,
           'status':$scope.status_selected.status,
           'type_case':casee.type_case}
  Case.patch($scope,params);
  /*$scope.$watch($scope.casee.priority, function() {
      var paramsNote = {
                  'about_kind': 'Case',
                  'about_item': $scope.casee.id,
                  'title': 'status updated to '+ casee.priority
                  
      };
      console.log('inserting a new note');
      console.log(paramsNote);
      
      Note.insert($scope,paramsNote);
   });*/
  
 $('#EditCaseModal').modal('hide');
};
    $('#some-textarea').wysihtml5();
      
      $scope.sendEmail = function(email){
        email.body = $('#some-textarea').val();
        
        var params = {
                  'to': email.to,
                  'cc': email.cc,
                  'bcc': email.bcc,
                  'subject': email.subject,
                  'body': email.body,

                  'about_item':$scope.casee.id,
                  'about_kind':'Case' };
        
        Email.send($scope,params);
      };


//HKA 29.12.2013 Delet Case
 $scope.editbeforedelete = function(){
     $('#BeforedeleteCase').modal('show');
   };
$scope.deletecase = function(){
     var caseid = {'id':$route.current.params.caseId};
     Case.delete($scope,caseid);
     $('#BeforedeleteCase').modal('hide');
     };

     $scope.listDocuments = function(){
        var params = {'about_kind':'Case',
                      'about_item':$scope.casee.id,
                      'order': '-updated_at',
                      'limit': 5
                      };
        Attachement.list($scope,params);

     };
     $scope.showCreateDocument = function(type){
        
        $scope.mimeType = type;
        $('#newDocument').modal('show');
     };
     $scope.createDocument = function(newdocument){
        var mimeType = 'application/vnd.google-apps.' + $scope.mimeType;
        var params = {'about_kind':'Case',
                      'about_item': $scope.casee.id,
                      'title':newdocument.title,
                      'mimeType':mimeType };
        Attachement.insert($scope,params);

     };
     $scope.createPickerUploader = function() {
          var projectfolder = $scope.casee.folder;
          var docsView = new google.picker.DocsView()
              .setIncludeFolders(true) 
              .setSelectFolderEnabled(true);
          var picker = new google.picker.PickerBuilder().
              addView(new google.picker.DocsUploadView().setParent(projectfolder)).
              addView(docsView).
              setCallback($scope.uploaderCallback).
              setAppId(12345).
                enableFeature(google.picker.Feature.MULTISELECT_ENABLED).
              build();
          picker.setVisible(true);
      };
      // A simple callback implementation.
      $scope.uploaderCallback = function(data) {
        

        if (data.action == google.picker.Action.PICKED) {
                var params = {'about_kind': 'Case',
                                      'about_item':$scope.casee.id};
                params.items = new Array();
               
                 $.each(data.docs, function(index) {
                      console.log(data.docs);
                      /*
                      {'about_kind':'Account',
                      'about_item': $scope.account.id,
                      'title':newdocument.title,
                      'mimeType':mimeType };
                      */
                      var item = { 'id':data.docs[index].id,
                                  'title':data.docs[index].name,
                                  'mimeType': data.docs[index].mimeType,
                                  'embedLink': data.docs[index].url

                      };
                      params.items.push(item);
                
                  });
                 Attachement.attachfiles($scope,params);
                    
                    console.log('after uploading files');
                    console.log(params);
                }
      };

   //01.03.2014 Edit Close date, Reason lost, Main competitor, Type, Description, Source : show Modal
    /* $scope.editclosedate = function(){
     $('#EditCloseDate').modal('show')
     };
     $scope.editcompetitor = function(){
     $('#EditCompetitor').modal('show')
     };
     $scope.editreasonlost = function(){
     $('#EditReasonLost').modal('show')
     };*/
     $scope.editdescription = function(){
     $('#EditDescription').modal('show')
     };
      $scope.edittype = function(){
     $('#EditType').modal('show')
     };
     /*$scope.editsource = function(){
     $('#EditSource').modal('show')
     };*/
      

    $scope.updateType = function(casem){
      params = {'id':$scope.casee.id,
              'type_case':casem.type_case};
      Case.patch($scope,params);
      $('#EditType').modal('hide');
     };
     $scope.updateDescription = function(casem){
      params = {'id':$scope.casee.id,
              'description':casem.description};
      Case.patch($scope,params);
      $('#EditDescription').modal('hide');
     };
      

//HKA 11.03.2014 Add Custom field

    $scope.addCustomField = function(customField){
      params = {'parent':$scope.casee.entityKey,
            'kind':'customfields',
            'fields':[
                {
                  "field": customField.field,
                  "value": customField.value
                }
            ]
  };
  InfoNode.insert($scope,params);

  $('#customfields').modal('hide');
  
};

$scope.listInfonodes = function(kind) {
     params = {'parent':$scope.casee.entityKey,
               'connections': kind
              };
     InfoNode.list($scope,params);
   
 };

     // Google+ Authentication 
     Auth.init($scope);

}]);