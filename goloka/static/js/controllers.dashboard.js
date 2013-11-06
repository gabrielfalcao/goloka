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
        var URLS = {
            "context_url": $("#dashboard-meta").data("context-ajax-url"),
            "create_hook_url": $("#dashboard-meta").data("create-hook-ajax-url"),
            "show_repository_commits": $("#dashboard-meta").data("show-repo-commits-url")
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
    function CreateHook (repository) {
        $.post(url_for("create_hook_url"), {
            "repository": repository,
            "username": username
        }, function(data){
            scope.$apply(function(){
                var selector = ".row";
                $(selector).each(function(){
                    var $el = $(this);

                    var full_name = $el.data("full-name");
                    if (full_name === repository.full_name) {
                        $el.text(data.url);
                    }
                });

            });
        });
    };
    function ShowCommits (organization, repository) {
        $.getJSON(url_for("show_repository_commits", {"owner": organization, "name": repository.name}), {
            "repository": repository,
            "username": username
        }, function(data){
            humane.log(data.message);
        });
    };
    scope.$apply(function(){
        scope.repositories = {};
        scope.repositories_by_name = {};
        scope.current_organization = false;
        scope.username = username;
        scope.SelectOrganizationTab = SelectOrganizationTab;
        scope.CreateHook = CreateHook;
        scope.ShowCommits = ShowCommits;
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
});
