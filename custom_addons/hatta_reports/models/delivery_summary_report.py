from datetime import datetime
from operator import itemgetter

from odoo import api, fields, models


class DeliveryOrderSummary(models.TransientModel):
    _name = 'delivery.order.summary'
    _description = 'Delivery Order Summary'

    from_date = fields.Date('From')
    to_date = fields.Date('To')
    partner_id = fields.Many2one('res.partner', 'Customer',
                                 domain="[('customer', '=', True), ('is_company', '=', True)]")
    sort_based_on = fields.Selection([('seq', 'DN Number'),
                                      ('date', 'Date'), ('cust', 'Customer'),
                                      ('job', 'Job No')],
                                     string='Sort Based On', default='seq')

    def print_report(self):
        return self.env['report'].get_action(self, 'hatta_reports.delivery_summary',
                                             data={'from_date': self.from_date,
                                                   'to_date': self.to_date,
                                                   'partner_id': self.partner_id.id,
                                                   'sort_based_on': self.sort_based_on,
                                                   })


class DeliveryOrderSummaryReport(models.AbstractModel):
    _name = 'report.hatta_reports.delivery_summary'

    @api.multi
    def render_html(self, docids, data=None):
        result = []
        picking_obj = self.env['stock.picking']
        domain = [('state', '=', 'done'),
                  ('picking_type_id.code', '=', 'outgoing')]

        if data.get('from_date', False):
            domain.append(('date', '>=', data['from_date']))
        if data.get('to_date', False):
            domain.append(('date', '>=', data['to_date']))
        if data.get('partner_id', False):
            domain.append(('partner_id', '=', data['partner_id'][0]))
        sort_based_on = data['sort_based_on']
        picking_ids = picking_obj.search(domain)
        for picking in picking_ids:
            vals = {
                'doc_no': picking.name,
                'date': picking.date and datetime.strptime(picking.date, '%Y-%m-%d %H:%M:%S').date() or '',
                'partner_name': picking.partner_id.name or '',
                'job_id': 'Job Id'
            }
            result.append(vals)
        if sort_based_on == 'date':
            result = sorted(result, key=itemgetter('date'))
        elif sort_based_on == 'cust':
            result = sorted(result, key=itemgetter('partner_name'))
        elif sort_based_on == 'job':
            result = sorted(result, key=itemgetter('job_id'))
        elif sort_based_on == 'seq':
            result = sorted(result, key=itemgetter('doc_no'))

        docargs = {
            'docs': result,
        }
        return self.env['report'].render('hatta_reports.delivery_summary', docargs)