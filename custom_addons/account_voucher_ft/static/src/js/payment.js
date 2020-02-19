odoo.define('account_voucher_ft.payment_widget', function (require) {
"use strict";

var core = require('web.core');
var common = require('web.form_common');

var _t = core._t;

var FieldToggleBooleanAdv = common.AbstractField.extend({
    template: "toggle_button",
    events: {
        'click': 'set_toggle_button'
    },
    init: function() {
        this._super.apply(this, arguments);
        this.fa_icon = this.node.attrs.icon === undefined ? 'fa-circle' : this.node.attrs.icon;
        if (this.options["terminology"]) {
            var terms = this.options["terminology"];
            this.string_false = _t(terms[0] || "False" )
            this.string_true = _t(terms[1] || "True");
        };
    },
    render_value: function () {
        var class_name = this.get_value() ? 'o_toggle_button_success' : 'text-muted';
        this.$('i').attr('class', ('fa ' + this.fa_icon + ' ' + class_name));
        if (this.options.terminology) {
            var strings = this.get_value() ? this.string_true : this.string_false;
            this.$('i').empty().append(strings)
        }
    },
    set_toggle_button: function () {
        var self = this;
        var toggle_value = !this.get_value();
        if (this.view.get('actual_mode') == 'view') {
            var rec_values = {};
            rec_values[self.node.attrs.name] = toggle_value;
            return this.view.dataset._model.call(
                    'write', [
                        [this.view.datarecord.id],
                        rec_values,
                        self.view.dataset.get_context()
                    ]).done(function () { self.reload_record(); });
        }
        else {
            this.set_value(toggle_value);
        }
    },
    reload_record: function () {
        this.view.reload();
    },
    is_false: function() {
        return false;
    },
});

core.form_widget_registry
    .add('toggle_button_with_string', FieldToggleBooleanAdv)

});