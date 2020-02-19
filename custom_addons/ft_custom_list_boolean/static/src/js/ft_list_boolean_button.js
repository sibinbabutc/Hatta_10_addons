odoo.define('ft_list_boolean_button.widget', function(require){
    "use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');

    var list_widget_registry = core.list_widget_registry;

    ListView.List.include({
        render: function () {
            this._super();
            var self = this;
            this.$current.delegate('.o_boolean_always_enabled', 'click', function(e){
                self.onclick_always_enabled_click(e, this);
            })
        },
        onclick_always_enabled_click: function(e, td, vals = {}){
            e.stopPropagation();
            var self = this;
            var record_id = parseInt(td.parentNode.dataset.id);
            vals[td.dataset.field] = $(td).find('div.selected').length ? false : true;
            this.dataset._model.call('write', [record_id, vals], {}).then(function(r){
                var record = self.records.get(record_id);
                self.reload_record(record);
                self.records.trigger('change', record);
                if (self.view.x2m){
                    self.view.x2m.view.reload()
                };
            })
        },
    });

    var ColumnBooleanListFT = ListView.Column.extend({
        init: function (id, tag, attrs) {
            this._super(id, tag, attrs);
            this.boolean_always_enabled = true;
            this.boolean_string = attrs.boolean_string ? JSON.parse(attrs.boolean_string.replace(/'/g, '"')) : false;
            this.icon = attrs.icon ? JSON.parse(attrs.icon.replace(/'/g, '"')) : false;
        },
        heading: function () {
            if (!this.icon){
                return ''
            } else {
                return _.str.sprintf('<i class="fa %s"/> / <i class="fa %s"/>', this.icon[1], this.icon[0]);
            }

        },
        _format: function (row_data, options) {
            return _.str.sprintf('<div class="o_checkbox o_ft_boolean %s">%s %s</div>',
                     row_data[this.id].value ? 'selected' : '',
                     row_data[this.id].value ? (this.icon ? _.str.sprintf('<i class="fa %s"></i>', this.icon[0]) : '') : (this.icon ? _.str.sprintf('<i class="fa %s"></i>', this.icon[1]) : ''),
                     row_data[this.id].value ? (this.boolean_string ? this.boolean_string[0] : '') : (this.boolean_string ? this.boolean_string[1]: ''),
                     );
        }
    });

    list_widget_registry
        .add('field.toggle_boolean_always_enabled', ColumnBooleanListFT)

});