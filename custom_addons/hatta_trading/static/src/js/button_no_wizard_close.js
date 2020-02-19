odoo.define('hatta_trading.act_window_no_close', function(require){
"use strict";

var ActionManager = require('web.ActionManager')

ActionManager.include({
    ir_actions_act_window_no_close: function (action, options) {
        return $.when();
    },
})


});
