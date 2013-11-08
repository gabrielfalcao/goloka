var APP = angular.module('goloka', []).
    filter('dashify', function() {
        return function(input) {
            return input.replace("/", "-");
        }
    }).
    filter('length', function() {
        return function(input) {
            return input.length;
        }
    });;


$(function(){

    function url_for(name, formatting) {
        var $src = $("#dashboard-meta");
        var URLS = {
            "context_url":             $src.data("context-ajax-url"),
            "save_build_url":          $src.data("save-build-ajax-url"),
            "run_build_url":           $src.data("run-build-ajax-url"),
            "manage_builds_url":       $src.data("manage-builds-ajax-url"),
            "create_hook_url":         $src.data("create-hook-ajax-url"),
            "show_repository_commits": $src.data("show-repo-commits-url")
        };

        var url = URLS[name];
        if (typeof formatting  === 'object')
        for (var key in formatting) {
            var pattern = encodeURIComponent('<' + key + '>');
            var replacement = formatting[key];
            url = url.replace(pattern, replacement);
        }

        return url;
    };

    var ADDRESS = $("body").data("socketaddress");
    var username = $("#socket-meta").data("username");

    var socket = io.connect(ADDRESS);
    var scope = angular.element($("body")).scope();

    function SelectOrganizationTab (owner) {
        $.getJSON(url_for("context_url", {"owner": owner}), function(data){
            scope.$apply(function(){
                scope.current_organization = owner;
                scope.repositories[owner] = data.repositories;
                scope.repositories_by_name[owner] = data.repositories_by_name;

                $(".ajax-loader."+owner).hide();
            });
        });
    };
    function CreateBuild (organization, repository) {
        var modal = new $.UIkit.modal.Modal("#create-build-modal");
        scope.current_project = repository;
        scope.current_organization = organization;
        scope.new_build = {
            repository: repository,
            owner: organization
        };

        modal.show();
    };
    function ManageBuilds (repository) {
        var modal = new $.UIkit.modal.Modal("#manage-build-modal");
        var url = url_for("manage_builds_url", {"owner": repository.owner.login, "repository": repository.name});

        $.get(url, function(data){
            $("#manage-build-modal .modal-content").html(data);
            modal.show();
        });
    };
    function ScheduleBuildNow (token) {
        var url = url_for("run_build_url", {"token": token});
        $.ajax({
            url:url,
            type:"POST",
            data:JSON.stringify({
                'token': token,
            }),
            contentType:"application/json; charset=utf-8",
            dataType:"json",
            success: function(data){
                console.log("DONE WITH", data);
            }
        });

        humane.log("Build scheduled successfully:" + repository.full_name)
    };
    function SaveBuild (new_build) {
        var url = url_for("save_build_url", {"owner": new_build.owner.login, "repository": new_build.repository.name});
            console.log(url);

        $.ajax({
            url:url,
            type:"POST",
            data:JSON.stringify(new_build),
            contentType:"application/json; charset=utf-8",
            dataType:"json",
            success: function(data){
                var modal = new $.UIkit.modal.Modal("#create-build-modal");
                modal.hide();
                humane.log("Created build " + data.environment_name);
            }
        });
    }
    scope.$apply(function(){
        scope.repositories = {};
        scope.repositories_by_name = {};
        scope.current_organization = false;
        scope.username = username;
        scope.SelectOrganizationTab = SelectOrganizationTab;
        scope.CreateBuild = CreateBuild;
        scope.SaveBuild = SaveBuild;
        scope.ManageBuilds = ManageBuilds;
        scope.ScheduleBuildNow = ScheduleBuildNow;
    });
    socket.on('connect', function() {
        console.log('connected');
        socket.emit('listen');
    });
    socket.on('notification', function(data) {
        if (data.notification) {
            humane.log(data.notification.message)
        }
        if (data.log) {
            $("#console").prepend('<code>'+data.log.message+'</code>')
        }
        socket.emit('listen');
    });
    socket.on('error', function(e) {
        console.log('error', e);
    });
    socket.on('disconnect', function() {
        console.log('disconnected');
        $(".live-stats-repository").removeClass("active");
        scope.$apply(function(){
            scope.visitors = null;
        });
    });
    $(function(){
    });

});

APP.controller("DashboardController", function($scope){
    $scope.current_organization = false;
    $scope.new_build = {};
    $scope.builds = {};
});
