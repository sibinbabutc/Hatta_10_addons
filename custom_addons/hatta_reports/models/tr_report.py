from datetime import datetime
from odoo import api, fields, models
import datetime
from tr_report_xlxs import Tr_reportXlsx


class PurchaseOrderStatus(models.TransientModel):
    _name = 'tr.report'
    _description = 'TR Report'

    date_from = fields.Date(string='Closing Date From')
    date_to = fields.Date(string='Closing Date To')
    tr = fields.Many2one('tr.account',string='TR')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('settle', 'Settled'),
            ('cancel', 'Cancel'),
        ])
    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xls', 'EXCEL'),
        ])

    def print_report(self):
        datas = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'tr': self.tr.id,
            'tr_acc_name': self.tr.name,
            'tr_name': self.tr.name,
            'state': self.state,
            'report_format': self.report_format,
            }
        if datas['report_format'] == 'xls':
            return self.env['report'].with_context(datas).get_action(self, 'xls_format_tr_report.xlsx')
        else:
            return self.env['report'].get_action(self, 'hatta_reports.tr_report', data=datas)


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.tr_report'

    @api.multi
    def render_html(self, docids, data=None):
        tr_reciept_obj = self.env['tr.details']
        tr_account_obj = self.env['tr.account']
        domain = []
        if data['tr']:
            domain.append(('tr_account_id', '=', data['tr']))
        # if data['partner_id']:
        #     domain.append(('partner_id','=',data['partner_id']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('closing_date', '>=', d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('closing_date', '<=', d2))
        if data['state']:
            domain.append(('state', '=', data['state']))
        if not data['state']:
            domain.append(('state', '!=', 'draft'))
        docs = self.env['tr.details'].search(domain)
        open_tr = tr_reciept_obj.get_open_tr_amount()
        settled_tr = tr_reciept_obj.get_settle_tr_amount()
        total_tr = tr_reciept_obj.get_total_tr_amount()
        tr_limit = tr_account_obj.get_tr_limit()
        tr_balance = tr_account_obj.get_tr_balance()
        # lines = self.env['purchase.order.line'].search(domain)

        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'docs': docs,
            'tr_name': data['tr_name'],
            'total_tr': total_tr,
            'open_tr': open_tr,
            'settled_tr': settled_tr,
            'tr_limit': tr_limit,
            'tr_balance': tr_balance,
        }
        if data['report_format'] == 'pdf':
            return self.env['report'].render('hatta_reports.tr_report', docargs)
