odoo.define('hatta_trading.webkanban', function(require){
"use strict";

var core = require('web.core');
var KanbanRecord = require('web_kanban.Record');
var form_relational = require('web.form_relational');
var common = require('web.form_common');
var form_widgets = require('web.form_widgets');
var utils = require('web.utils');
var Model = require('web.DataModel');
var data = require('web.data');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var ListView = require('web.ListView');

var list_widget_registry = core.list_widget_registry;

var _t = core._t;

var ColumnHtml = ListView.Column.extend({
    replacement: '*',
    /**
     * If password field, only display replacement characters (if value is
     * non-empty)
     */
    _format: function (row_data, options) {
        var value = row_data[this.id].value;
        if (value){
            return value.replace(/<\/?[^>]+>/ig, " ");
        };
    }
});

list_widget_registry
    .add('field.html', ColumnHtml)

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
        if (!this.options.no_icon){
            this.$('i').attr('class', ('fa ' + this.fa_icon + ' ' + class_name));
        }
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


KanbanRecord.include({
    renderElement: function(){
        this._super();
        if (this.$el.find('.oe_kanban_content .enquiry')){
            this.$el.find('.oe_kanban_content .enquiry').on('click', this.proxy('on_click_enquiry'));
        }
    },
    on_click_enquiry: function(){
        var action = {
            name: 'Enquiry Details',
            res_model: 'enquiry.details',
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            view_type: "form",
            view_mode: "form"
        }
        if (this.record.enquiry_id.raw_value.length){
            action.res_id = this.record.enquiry_id.raw_value[0];
        } else {
            action.context = {'default_crm_lead_id': this.record.id.raw_value}
        }
        this.do_action(action);
    }
});

var FieldMany2ManyMultiLine = form_relational.FieldMany2ManyTags.extend({
    tag_template: "FieldMany2ManyMultiLine",
});


var FieldExchangeRate = form_widgets.FieldFloat.extend({
    template: 'FieldExchangeRate',
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.on_update = false;
    },
    initialize_content: function() {
        var self = this;
        if(!this.get('effective_readonly') && !this.$input) {
            this.$input = this.$el.filter('input');
        }
        this.$el.filter('.update').on('click', function(e){self.onclick_update(); e.stopPropagation();})
        this.$el.filter('.save').on('click', function(){self.onclick_save(); e.stopPropagation();})
        this.$el.filter('.cancel').on('click', function(){self.onclick_cancel(); e.stopPropagation();})

        this.setupFocus(this.$el);
    },
    destroy_content: function() {
        this.$input = undefined;
    },
    save_exchange_rate: function(){
        var self = this;
        this.view.dataset._model.call('set_exchange_rate',
            [this.view.fields[self.options["currency"]].get('value'), this.exchange_rate])
            .then(function(result){
                self.field_manager.fields[self.options["currency"]].trigger('changed_value');
            });
    },
    render_value: function() {
        var self = this;
        var show_value = this.format_value(this.get('value'), '');
        this.$el.hide();
        if (this.on_update){
            this.$el.filter('input').show();
            this.$el.filter('button.save').show();
            this.$el.filter('button.cancel').show();
        } else {
            this.$el.filter('span').show();
            this.$el.filter('button.update').show();
        }
        this.$el.filter('span').text(show_value);
        this.$el.filter('input').val(show_value);
    },
    onclick_update: function(){
        this.on_update = true;
        this.render_value();
    },
    onclick_save: function(){
        this.on_update = false;
        this.render_value();
    },
    onclick_cancel: function(){
        this.on_update = false;
        this.render_value();
    },
    set_value: function(value_) {
        if (value_ === false || value_ === undefined) {
            value_ = 0; // As in GTK client, floats default to 0
        }
        if (this.digits !== undefined && this.digits.length === 2) {
            value_ = utils.round_decimals(value_, this.digits[1]);
        }
        this._super(value_);
    },
    format_value: function(val, def) {
        return formats.format_value(parseFloat(val), {type: "float", digits: [12, 6]}, def);
    },
});


var ExchangeRateDialog = Dialog.extend({
    template: 'ExchangeRateDialog',
    init: function (parent, options) {
        this._super(parent, options);
        this.currency = options.currency || false;
        this.exchange_rate = options.rate || 0.0;
    },
    renderElement: function(){
        this._super();
        this.$input = this.$el.find('input')
    },
    format_value: function(val, def) {
        return formats.format_value(parseFloat(val), {type: "float", digits: [12, 6]}, def);
    },
})


var FieldExchangeRate = form_widgets.FieldFloat.extend({
    template: 'FieldExchangeRate',
    init: function (field_manager, node) {
        this._super(field_manager, node);
         if (this.options["currency"]) {
            var currency = this.options["currency"];
        };
    },
    initialize_content: function() {
        var self = this;
        this._super();
        this.$el.filter('button').on('click', function(e){
            self.show_dialog(e)
        })
    },
    show_dialog: function(e){
        e.preventDefault();
        e.stopPropagation();
        var self = this;
        var $e = $(e.currentTarget);
        var options = {
            currency: this.view.fields[self.options["currency"]],
            rate: this.format_value(this.get_value(), 0.0),
            confirm_callback: function () {
                var dialog = this;
                self.view.dataset._model.call('set_exchange_rate',
                    [dialog.currency.get('value'), self.format_value(dialog.$input.val(), 0.0)])
                    .then(function(result){
                        dialog.close();
                        self.field_manager.fields[self.options["currency"]].trigger('changed_value');
                    });
            }
        };
        var buttons = [
            {
                text: _t("Update Exchange Rate"),
                classes: 'btn-primary',
                close: false,
                click: options && options.confirm_callback
            },
            {
                text: _t("Cancel"),
                close: true,
                click: options && options.cancel_callback
            }
        ];
        return new ExchangeRateDialog(this, _.extend({
            size: 'medium',
            buttons: buttons,
            $content: false,
            title: _t("Currency Exchange Rate Update"),
        }, options)).open();
    },
    render_value: function() {
        var show_value = this.format_value(this.get('value'), '');
        this.$el.filter('span').text(show_value);
    },
});

core.form_widget_registry
    .add('toggle_button_with_string', FieldToggleBooleanAdv)
    .add('many2many_multi_line', FieldMany2ManyMultiLine)
    .add('exchange_rate_changer', FieldExchangeRate)

})
