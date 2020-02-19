from datetime import datetime
from operator import itemgetter

from odoo import api, fields, models
import datetime


class PurchaseOrderStatus(models.TransientModel):
    _name = 'purchase.order.status'
    _description = 'Purchase Order Status Report'

    po_id = fields.Many2one('purchase.order', 'Purchase Order')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    sort_supp = fields.Boolean('Supplier Wise')
    pending_only = fields.Boolean('Pending Only')
    sort_del_date = fields.Boolean('Supplier Delivery Date')
    disp_cust_del_date = fields.Boolean('Display Customer Delivery Date')
    cost_center_id = fields.Many2one('account.analytic.account', 'Cost Center')
    job_id = fields.Many2one('account.analytic.account', 'A/C #')

    def print_report(self):
        datas = {
            'po_id': self.po_id.id,
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'sort_supp': self.sort_supp,
            'pending_only': self.pending_only,
            'sort_del_date': self.sort_del_date,
            'disp_cust_del_date': self.disp_cust_del_date,
            'cost_center_id': self.cost_center_id.id,
            'job_id': self.job_id.id,

        }

        return self.env['report'].get_action(self, 'hatta_reports.purchase_order_status_report', data=datas)


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.purchase_order_status_report'

    @api.multi
    def render_html(self, docids, data=None):
        domain = []
        if data['po_id']:
            domain.append(('order_id','=',data['po_id']))
        if data['partner_id']:
            domain.append(('partner_id','=',data['partner_id']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('date_order','>=',d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('date_order','<=',d2))
        lines = self.env['purchase.order.line'].search(domain)
        docs = self.env['purchase.order'].search(domain)

        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'lines':lines,
            'docs': docs,
        }
        return self.env['report'].render('hatta_reports.purchase_order_status_report', docargs)

