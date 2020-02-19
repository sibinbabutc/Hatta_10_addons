odoo.define('hatta_trading.multiple_attachments', function(require){
'use strict';

    var core = require('web.core');
    var _t = core._t;
    var framework = require('web.framework');
    var Sidebar = require('web.Sidebar');

    Sidebar.include({
        on_attachment_changed: function(e) {
        var form = $(this);
        var csrf_token = $("input[name=csrf_token]").val();
        var session_id = $("input[name=session_id]").val();
        var callback = $("input[name=callback]").val();
        var model = $("input[name=model]").val();
        var id = $("input[name=id]").val();
        var $target = $(event.target);
        var retmsg = '';
        var $e = $(e.target);
        if ($e.val() !== '') {
            var submitted =0;
            _.each($target[0].files, function(file){
                var querydata = new FormData();
                querydata.append('csrf_token', csrf_token);
                querydata.append('session_id', session_id);
                querydata.append('callback', callback);
                querydata.append('ufile',file);
                querydata.append('model', model);
                querydata.append('id', id);
                var ret = $.ajax({
                    url: '/web/binary/upload_attachment',
                    type: 'POST',
                    data: querydata,
                    cache: false,
                    processData: false,
                    contentType: false,
                    success: function(msg) {
                        submitted+=1;
                        if(submitted==$target[0].files.length){
                            var iframe = $('iframe').first();
                            if ($(iframe).attr('id').indexOf("oe_fileupload") >= 0){
                                $(iframe).contents().find('body').html(msg);
                            }
                        }
                    }
                });
            });
            $e.parent().find('input[type=file]').prop('disabled', true);
            $e.parent().find('button').prop('disabled', true).find('img, span').toggle();
            this.$('.o_sidebar_add_attachment a').text(_t('Uploading...'));
            framework.blockUI();
        }
    },
    });

});