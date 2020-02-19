# -*- encoding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
import base64
fs = fields.Date.from_string
ts = fields.Date.to_string
from datetime import timedelta, date


def daterange(date1, date2):
    for n in range(int((date2 - date1).days)+1):
        yield date1 + timedelta(n)


class LoginLogWizard(models.TransientModel):
    _name = 'login.log.wizard'
    _description = 'Login Log Wizard'

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    user_id = fields.Many2one("res.users", string="User")

    def print_report(self):
        return self.env['report'].get_action(self, 'otp_login_ft.login_log_report',
                                             data={'from_date': self.from_date,
                                                   'to_date': self.to_date,
                                                   'user_id': self.user_id.id,})


class OtpLoginLogReport(models.AbstractModel):
    _name = 'report.otp_login_ft.login_log_report'

    @api.multi
    def render_html(self, docids, data=None):
        fd = data['from_date'] if data and data['from_date'] else fields.Date.today()
        td = data['to_date'] if data and data['to_date'] else fields.Date.today()
        domain = [('login_date', '>=', fd), ('login_date', '<=', td)]
        if data and data['user_id']:
            domain.append(('user_id', '=', data['user_id']))
        log_details = self.env['login.log.view'].search(domain)
        if not log_details:
            raise UserError('No Available Records In The Period')
        users = []
        if data:
            if not data['user_id']:
                for items in log_details:
                    if items.user_id not in users:
                        users.append(items.user_id)
            else:
                user = self.env['res.users'].browse(data['user_id'])
                users.append(user)
        else:
            for items in log_details:
                    if items.user_id not in users:
                        users.append(items.user_id)
        dates = []
        for dt in daterange(fs(fd), fs(td)):
            dates.append(dt)
        av_dates = []
        for date in dates:
            for item in log_details:
                if str(date) in item.login_date:
                    if date not in av_dates:
                        av_dates.append(date)
        docargs = {
            'docs': log_details,
            'users': users,
            'dates': av_dates,
            'form_date': fd,
            'to_date': td,
        }
        return self.env['report'].render('otp_login_ft.login_log_report', docargs)