from datetime import datetime
from odoo import api, fields, models
import datetime


class TrStatusWizard(models.TransientModel):
    _name = 'tr.status.report.wizard'
    _description = 'TR Status Report'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    tr = fields.Many2one('tr.account', string='TR')
    report_format = fields.Selection([('pdf', 'PDF'), ('excel', 'Excel')], string='Format')

    def print_report(self):
        datas = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'tr': self.tr.id,
            'report_format': self.report_format,

        }
        return self.env['report'].get_action(self, 'hatta_reports.tr_status_report', data=datas)


class TrStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.tr_status_report'

    def get_opening_balance(self, from_date, tr_model_id):
        tr_pool = self.env['tr.details'].search(['|', ('start_date', '<', from_date), ('tr_account_id', '=', tr_model_id),
                                                 ('state', 'not in', ['draft', 'cancel'])])
        used = 0.00
        cleared = 0.00
        for tr in tr_pool:
            if tr.start_date < from_date:
                used += tr.amount
            if tr.state == 'settle':
                cleared += tr.amount
        if used > 0.00 or cleared > 0.00:
            return {
                'tt_date': from_date,
                'amount_cleared': cleared or 0.00,
                'amount_used': used or 0.00,
                'cr_days': 0.00,
                'due_date': '',
                'note': "OPENING BALANCE",
                'disb_id': ''
            }
        else:
            return {}

    @api.multi
    def render_html(self, docids, data=None):
        result = []
        from_date = data['date_from']
        to_date = data['date_to']
        tr_model_id = data['tr']
        tr_obj = self.env['tr.account'].search([('id', '=', tr_model_id)])
        domain = []
        if data['tr']:
            domain.append(('tr_account_id', '=', data['tr']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('start_date', '>=', d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('closing_date', '<=', d2))
        tr_details_obj = self.env['tr.details'].search(domain)
        opening_data = self.get_opening_balance(from_date, tr_model_id)
        if opening_data:
            result.append(opening_data)
        for tr_detail in tr_details_obj:
            if from_date <= tr_detail.start_date <= to_date:
                data = {
                    'tt_date': from_date,
                    'amount_cleared': 0.00,
                    'amount_used': tr_detail.amount or "0.00",
                    'cr_days': tr_detail.duration or "0.00",
                    'due_date': tr_detail.closing_date,
                    'note': '',
                    'disb_id': tr_detail.voucher_id.name if tr_detail.voucher_id else '',
                }
                result.append(data)
            if tr_detail.state == 'settle':
                for settle_obj in tr_detail.settle_ids:
                    if from_date <= settle_obj.payment_date <= to_date:
                        settle_data = {
                                       'tt_date': settle_obj.payment_date,
                                       'amount_cleared': settle_obj.amount or "0.00",
                                       'amount_used': 0.00,
                                       'cr_days': 0.00,
                                       'due_date': '',
                                       'note': '',
                                       'disb_id': '',
                                       }
                        result.append(settle_data)
        docargs = {
            'tr_account': tr_obj,
            'docs': result,
        }
        return self.env['report'].render('hatta_reports.tr_status_report', docargs)

