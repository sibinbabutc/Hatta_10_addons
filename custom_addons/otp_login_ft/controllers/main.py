# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Session


class Session(Session):

    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        test = request.session
        request.env['res.users'].sudo().logout(test)
        request.session._suicide = True
        super(Session, self).destroy()

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self):
        test = request.session
        request.env['res.users'].sudo().logout(test)
        request.session._suicide = True
        return super(Session, self).logout()