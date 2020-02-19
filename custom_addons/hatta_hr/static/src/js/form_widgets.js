odoo.define('hatta_hr.form_widgets', function(require){
    "use strict";

    var core = require('web.core');
    var framework = require('web.framework');
    var crash_manager = require('web.crash_manager');
    var FormWidget = require('web.form_widgets');
    var Dialog = require('web.Dialog');

    FormWidget.WidgetButton.include({
        execute_action: function() {
            var self = this;
            var exec_action = function() {
                if (self.node.attrs.confirm) {
                    var def = $.Deferred();
                    Dialog.confirm(self, self.node.attrs.confirm, { confirm_callback: self.on_confirmed })
                          .on("closed", null, function() { def.resolve(); });
                    return def.promise();
                } else {
                    return self.on_confirmed();
                }
            };
            var export_data = function() {
                return self.export_data();
            };
            if (this.node.attrs.button_sif) {
                return this.view.recursive_save().then(exec_action).then(export_data);
            } else if (!this.node.attrs.special) {
                return this.view.recursive_save().then(exec_action);
            } else {
                return exec_action();
            }
        },
        export_data: function() {
            var self = this;

            framework.blockUI();
            this.session.get_file({
                url: '/web/export/sif',
                data: {data: JSON.stringify({
                    model: 'hr.payslip.run',
                    datarecord: this.view.datarecord,
                    context: this.view.dataset.context
                })},
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager),
            });
        },
    });
});