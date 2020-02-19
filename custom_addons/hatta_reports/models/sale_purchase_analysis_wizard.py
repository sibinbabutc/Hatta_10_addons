from odoo import api, fields, models
import datetime


class PurchaseOrderSummary(models.TransientModel):
    _name = 'sale.purchase.analysis'

    job_id = fields.Char('Job Id')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    def print_report(self):
        datas = {
            'job_id': self.job_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

        return self.env['report'].get_action(self, 'hatta_reports.sale_purchase_analysis', data=datas)


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.sale_purchase_analysis'

    @api.multi
    def render_html(self, docids, data=None):
        domain = []

        # if data['so_id']:
        #     domain.append(('id','=',data['so_id']))
        # if data['partner_id']:
        #     domain.append(('partner_id','=',data['partner_id']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('date_order','>=',d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('date_order','<=',d2))

        docs = self.env['sale.order'].search(domain)

        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'docs': docs

        }
        return self.env['report'].render('hatta_reports.sale_purchase_analysis', docargs)


