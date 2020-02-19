from odoo import api, fields, models
import datetime


class PurchaseOrderSummary(models.TransientModel):
    _name = 'purchase.order.summary'

    po_id = fields.Many2one('purchase.order', 'Purchase Order')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    cost_center_id = fields.Many2one('account.analytic.account', 'Cost Center')
    job_id = fields.Many2one('account.analytic.account', 'A/C #')

    def print_report(self):
        datas = {
            'po_id': self.po_id.id,
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'cost_center_id': self.cost_center_id.id,
            'job_id': self.job_id.id,
        }

        return self.env['report'].get_action(self, 'hatta_reports.report_po_summary', data=datas)


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.report_po_summary'

    @api.multi
    def render_html(self, docids, data=None):
        domain = []

        if data['po_id']:
            domain.append(('id','=',data['po_id']))
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

        docs = self.env['purchase.order'].search(domain)

        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'docs': docs

        }
        return self.env['report'].render('hatta_reports.report_po_summary', docargs)


