# -*- encoding: utf-8 -*-
from odoo import api, fields, models

from datetime import datetime
from odoo import http

openerpweb = http


class LoginLogView(models.Model):
    _name = 'login.log.view'
    _description = 'Login Log'

    user_id = fields.Many2one('res.users', 'User')
    login_date = fields.Datetime('Login Date')
    logout_date = fields.Datetime('Logout Date')
    status = fields.Selection([('proper', 'User Logout'),
                               ('im_proper', 'System Logout'),
                               ('in_use', 'In Use')],
                              'Logout Type')
    date_today = fields.Datetime(string='Today', default=fields.datetime.now())

    @api.model
    def logout_users(self):
        otp_ids = self.env['hatta.login.otp'].search([])
        otp_user_ids = [x.user_id.id for x in otp_ids]
        pending_logout = self.search([('logout_date', '=', False), ('user_id', 'in', otp_user_ids)])
        inuse_logout = self.search([('logout_date', '=', False), ('user_id', 'not in', otp_user_ids)])
        now = datetime.now()
        if pending_logout:
            pending_logout.write({'logout_date': now, 'status': 'im_proper'})

        if inuse_logout:
            inuse_logout.write({'logout_date': now, 'status': 'in_use'})
        all_log = self.search([], limit=1)
        if all_log:
            template_id = self.env['ir.model.data'].get_object_reference('otp_login_ft', 'user_access_email')[1]
            mail_template = self.env['mail.template'].browse(template_id)
            if mail_template:
                mail_template.send_mail(all_log.id, force_send=True)
        return True
