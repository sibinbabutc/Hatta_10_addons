odoo.define('web_widget_many2many_tags_multi_selection.multiple_tags', function (require) {
    "use strict";

    var FormCommon = require('web.form_common');
    var core = require('web.core');
    var data = require('web.data');
    var _t = core._t;

//    For MultiSelection in many2many_tag widget
    FormCommon.CompletionFieldMixin._search_create_popup = function(view, ids, context) {
        var self = this;
        debugger;
        new FormCommon.SelectCreateDialog(this, {
            res_model: self.field.relation,
            domain: self.build_domain(),
            context: new data.CompoundContext(self.build_context(), context || {}),
            title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
            initial_ids: ids ? _.map(ids, function(x) {return x[0];}) : undefined,
            initial_view: view,
            disable_multiple_selection: this.field.type != 'many2many',
            no_create: this.options.no_create || false,
            on_selected: function(element_ids) {
                for(var i=0, len=element_ids.length; i<len;i++) {
                    self.add_id(element_ids[i]);
                    if (self.field.type != 'many2many') {
                        break;
                    }
                }
                self.focus();
            }
        }).open();
        var domain = self.build_domain();

        if (self.field.type == 'many2many') {
            var selected_ids = self.get_search_blacklist();
            if (selected_ids.length > 0) {
                domain = new data.CompoundDomain(domain, ["!", ["id", "in", selected_ids]]);
            }
        }

    }

    var SuperFormCommonCompletionFieldMixin_init = FormCommon.CompletionFieldMixin.init;
    var SuperFormCommonCompletionFieldMixin_get_search_result = FormCommon.CompletionFieldMixin.get_search_result;
    FormCommon.CompletionFieldMixin.init = function() {
        SuperFormCommonCompletionFieldMixin_init.call(this);
        this.get_search_result = function(search_val) {
            if (!this.options.direct_search){
                return SuperFormCommonCompletionFieldMixin_get_search_result.call(this, search_val);
            }
            var self = this;

            var dataset = new data.DataSet(this, this.field.relation, self.build_context());
            this.last_query = search_val;
            var exclusion_domain = [], ids_blacklist = this.get_search_blacklist();
            if (!_(ids_blacklist).isEmpty()) {
                exclusion_domain.push(['id', 'not in', ids_blacklist]);
            }

            return this.orderer.add(dataset.name_search(
            search_val, new data.CompoundDomain(self.build_domain(), exclusion_domain), 'ilike', 160, self.build_context())
            .done(function(_data) {
                                self._search_create_popup("search", _data);
                            }));

        };
    }

});
