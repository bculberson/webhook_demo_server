$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    updater.poll();
});

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

var updater = {
    errorSleepTime: 500,
    cursor: null,

    poll: function() {
        var args = {"_xsrf": getCookie("_xsrf")};
        if (updater.cursor) args.cursor = updater.cursor;
        $.ajax({url: "/a/watch", type: "POST", dataType: "text",
                data: $.param(args), success: updater.onSuccess,
                error: updater.onError});
    },

    onSuccess: function(response) {
        try {
            updater.newNotifications(eval("(" + response + ")"));
        } catch (e) {
            updater.onError();
            return;
        }
        updater.errorSleepTime = 500;
        window.setTimeout(updater.poll, 0);
    },

    onError: function(response) {
        updater.errorSleepTime *= 2;
        console.log("Poll error; sleeping for", updater.errorSleepTime, "ms");
        window.setTimeout(updater.poll, updater.errorSleepTime);
    },

    newNotifications: function(response) {
        if (!response.notifications) return;
        updater.cursor = response.cursor;
        var notifications = response.notifications;
        updater.cursor = notifications[notifications.length - 1].id;
        console.log(notifications.length, "new notifications, cursor:", updater.cursor);
        for (var i = 0; i < notifications.length; i++) {
            updater.showNotification(notifications[i]);
        }
    },

    showNotification: function(notification) {
        var existing = $("#n" + notification.id);
        if (existing.length > 0) return;
        var node = $(notification.html);
        node.hide();
        $("#inbox").prepend(node);
        node.slideDown();
    }
};
