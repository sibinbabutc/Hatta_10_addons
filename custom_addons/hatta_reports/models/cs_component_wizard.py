from datetime import datetime

from odoo import fields, models, api


class PurchaseReport(models.Model):
    _name = 'cost.sheet.component'

    from_date = fields.Date(string='From')
    to_date = fields.Date(string='To')
    component = fields.Many2one('costsheet.line.charge', string='Component')
    exclude_zero = fields.Boolean(string='Exclude Zero')

    @api.multi
    def print_purchase_report(self):
        return self.env['report'].get_action(self, 'hatta_reports.cost_sheet_component_report',
                                             data={'from_date': self.from_date,
                                                   'to_date': self.to_date,
                                                   'component': self.component.id,
                                                   'exclude_zero':self.exclude_zero,
                                                   })


class CostSheetComponentReport(models.AbstractModel):
    _name = 'report.hatta_reports.cost_sheet_component_report'

    @api.multi
    def render_html(self, docids, data=None):

        cr = self.env.cr
        query = "SELECT csl.id, cs.id, po.id, cslc.name as cslc, po.date_order as purchase_date, " \
                "rc.name as currency, po.name as " \
                "po_number, aaa.name as JOBCODE, rp.name as supplier, csl.amount_fc as amount_fc, csl.amount_lc as " \
                "amount_lc " \
                "FROM cost_sheet_line as csl  " \
                "LEFT JOIN hatta_cost_sheet as cs ON csl.cost_sheet_id = cs.id " \
                "LEFT JOIN costsheet_line_charge as cslc ON csl.line_charge_id = cslc.id " \
                "LEFT JOIN purchase_order as po ON cs.purchase_order_id = po.id " \
                "LEFT JOIN res_partner as rp ON po.partner_id = rp.id " \
                "LEFT JOIN enquiry_details as ed ON po.enquiry_id = ed.id " \
                "LEFT JOIN account_analytic_account as aaa ON ed.job_account = aaa.id " \
                "LEFT JOIN res_currency as rc ON po.currency_id = rc.id WHERE csl.line_charge_id=%s" % data['component']
        if data['from_date']:
                query += "AND '%s' <= po.date_order " % data['from_date']
        if data['from_date'] and data['to_date']:
                query += "AND  po.date_order <= '%s'" % data['to_date']
        if not data['from_date'] and data['to_date']:
            query += "AND '%s' >= po.date_order " % data['to_date']
        if data['exclude_zero']:
            query += "AND csl.amount_lc!=0"
        cr.execute(query)
        qres = cr.dictfetchall()
        docargs = {
            'items': qres,
            'component': self.env['costsheet.line.charge'].browse(data['component']),
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            # 'temp':temp,
        }
        return self.env['report'].render('hatta_reports.cost_sheet_component_report', docargs)
