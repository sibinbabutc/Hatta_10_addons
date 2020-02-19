from odoo import api, fields, models
import datetime


class SaleReturn(models.TransientModel):
    _name = 'sale.return.wizard'

    so_id = fields.Many2one('sale.order')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    partner_id = fields.Many2one('res.partner', 'Customer')

    def print_report(self):
        datas = {
            'so_id': self.so_id.id,
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

        return self.env['report'].get_action(self, 'hatta_reports.sales_return_report1', data=datas)


class SaleReturnReport(models.AbstractModel):
    _name = 'report.hatta_reports.sales_return_report1'

    @api.multi
    def render_html(self, docids, data=None):
        domain = []
        if data['partner_id']:
            domain.append(('partner_id', '=', data['partner_id']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('date_order', '>=', d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('date_order', '<=', d2))
        docs = self.env['sale.order'].search(domain)
        acc = self.env['account.invoice'].search(domain)

        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'docs': docs,
            'acc': acc
        }
        return self.env['report'].render('hatta_reports.sales_return_report1', docargs)



