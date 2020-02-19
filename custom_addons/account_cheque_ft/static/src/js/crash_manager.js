//odoo.define('account_cheque_ft.CrashManager', function (require) {
//"use strict";
//
//var ajax = require('web.ajax');
//var core = require('web.core');
//var Dialog = require('web.Dialog');
//var CrashManager = require('web.CrashManager');
//var session = require('web.session')
//
//var QWeb = core.qweb;
//var _t = core._t;
//var _lt = core._lt;
//
//var RedirectWarningHandler = Dialog.extend({
//    init: function(parent, error) {
//        this._super(parent);
//        this.error = error;
//    },
//    display: function() {
//        var self = this;
//        var error = this.error;
//        var loc = window.location.href
//        error.data.message = error.data.arguments[0];
//
//        new Dialog(this, {
//            size: 'medium',
//            title: "Odoo " + (_.str.capitalize(error.type) || "Warning"),
//            buttons: [
//                {text: error.data.arguments[2], classes : "btn-primary", click: function() {
//                    if (error.data.arguments[1] == 'function') {
//                        session.rpc('/web/dataset/call_button', error.data.arguments[3]).then(function(r){});
//                        window.location.reload();
//                    } else {
//                        window.location.href = '#action='+error.data.arguments[1];
//                    }
//                    self.destroy();
//                }},
//                {text: _t("Cancel"), click: function() { self.destroy(); }, close: true}
//            ],
//            $content: QWeb.render('CrashManager.warning', {error: error}),
//        }).open();
//    }
//});
//
//core.crash_registry.add('odoo.exceptions.RedirectWarning', RedirectWarningHandler);
//
//});
