var edgeservices = angular.module('crmEngine.edgeservices',[]);


edgeservices.factory('Edge', function($http) {
  
  var Edge = function(data) {
    angular.extend(this, data);
  }


 
   Edge.insert = function($scope,params){
      $scope.isLoading = true;
      gapi.client.crmengine.edges.insert(params).execute(function(resp) {
         if(!resp.code){

            $scope.edgeInserted();
            $scope.isLoading = false;

            $scope.$apply();
         
         }else{
          console.log(resp.code);
         }
      });
     $scope.isLoading=false;

  };

  

  Edge.delete = function($scope,params){
    $scope.isLoading = true;
    gapi.client.crmengine.edges.delete(params).execute(function(resp){
        $scope.isLoading = false;
        $scope.runTheProcess();
      })
     $scope.isLoading=false;
    
  };


  

return Edge;
});
