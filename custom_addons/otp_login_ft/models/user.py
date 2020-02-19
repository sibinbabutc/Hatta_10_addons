# -*- encoding: utf-8 -*-
from odoo import api, fields, models, registry, SUPERUSER_ID, http
import random
from datetime import datetime
from odoo.addons.web.controllers.main import Session

from odoo.http import request


class HattaLoginOtp(models.Model):
    _name = 'hatta.login.otp'
    _rec_name = 'user_id'

    @api.multi
    def _get_now(self):
        res = {}
        for id in self:
            res[id] = datetime.strftime(datetime.now(), "%d/%m/%Y")
        return res

    user_id = fields.Many2one('res.users', 'User')
    user_otp = fields.Char('Password', size=32)
    active = fields.Boolean('Active', default=True)
    date_today = fields.Date(compute='_get_now', string='Today', size=128)
    manual_reset = fields.Boolean('Manual Reset')

    _sql_constraints = [
        ('user_uniq', 'unique(user_id)', 'User already exists!!'),
    ]

    @api.multi
    def reset_password(self, manual=False):
        for user in self:
            password = random.randrange(10001, 99999)
            self._cr.execute('update res_users set password=%s where id=%s', (password, user.user_id.id))
            self._cr.execute('update hatta_login_otp set user_otp=%s where user_id=%s', (password, user.user_id.id))
            if manual:
                user.manual_reset = True
        return True

    @api.multi
    def generate_otp_cron(self):
        records = self.env['hatta.login.otp'].sudo().search([])
        for otp_user_obj in records:
            if otp_user_obj.manual_reset:
                otp_user_obj.write({'manual_reset': False})
            else:
                otp_user_obj.reset_password()
        return True

    @api.model
    def generate_otp_cron_email(self):
        login_otp_pool = self.env['hatta.login.otp'].search([], limit=1)
        if login_otp_pool:
            template_id = self.env['ir.model.data'].get_object_reference('otp_login_ft', 'email_user_password')[1]
            mail_template = self.env['mail.template'].browse(template_id)
            if mail_template:
                mail_template.send_mail(login_otp_pool.id, force_send=True)
        return True

    def print_report(self):
        return self.env['report'].get_action(self, 'otp_login_ft.user_password_print')


class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def _login(cls, db, login, password):
        cr = registry(db).cursor()
        env = api.Environment(cr, SUPERUSER_ID, {})
        log_pool = env['login.log.view']
        res = super(ResUsers, cls)._login(db, login, password)
        if res:
            pending_logout = log_pool.search([('user_id', '=', res), ('logout_date', '=', False)])
            if not pending_logout:
                cr.autocommit(True)
                now = datetime.now()
                vals = {
                    'user_id': res,
                    'login_date': now
                }
                log_pool.create(vals)
        return res

    def logout(self, session):
        log_pool = self.env['login.log.view']
        pending_logout = log_pool.search([('user_id', '=', session.uid), ('logout_date', '=', False)])
        if pending_logout:
            now = datetime.now()
            pending_logout.write({'logout_date': now, 'status': 'proper'})
        return True


class OtpLoginLogReport(models.AbstractModel):
    _name = 'report.otp_login_ft.user_password_print'

    @api.multi
    def render_html(self, docids, data=None):
        otp_log_details = self.env['hatta.login.otp'].search([])
        docargs = {
            'docs': otp_log_details,
        }
        return self.env['report'].render('otp_login_ft.user_password_print', docargs)
