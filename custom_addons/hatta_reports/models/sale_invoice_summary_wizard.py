from odoo import api, fields, models
import datetime
from odoo.exceptions import UserError


class PurchaseOrderSummary(models.TransientModel):
    _name = 'sale.invoice.summary'

    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center')
    inv_id = fields.Many2one('account.invoice', string='Invoice')
    partner_id = fields.Many2one('res.partner', 'Customer')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    def print_report(self):
        datas = {
            'cost_center_id': self.cost_center_id.id,
            'inv_id': self.inv_id.id,
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to
        }

        return self.env['report'].get_action(self, 'hatta_reports.sale_invoice_summary_report', data=datas)


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = 'report.hatta_reports.sale_invoice_summary_report'

    @api.multi
    def render_html(self, docids, data=None):
        domain = [('state', 'not in', ['draft', 'cancel']), ('type', '=', 'out_invoice'),
                  ('credit_debit_type', 'not in', ['credit', 'debit'])]
        if data['inv_id']:
            domain.append(('id', '=', data['inv_id']))
        if data['cost_center_id']:
            domain.append(('cost_center_id', '=', data['cost_center_id']))
        if data['partner_id']:
            domain.append(('partner_id', '=', data['partner_id']))
        if data['date_from']:
            date1 = datetime.datetime.strptime(data['date_from'], '%Y-%m-%d')
            d1 = datetime.datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('date_invoice', '>=', d1))
        if data['date_to']:
            date2 = datetime.datetime.strptime(data['date_to'], '%Y-%m-%d')
            d2 = datetime.datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('date_invoice', '<=', d2))

        inv_obj = self.env['account.invoice'].search(domain).sorted(key=lambda r: r.cost_center_id.id)
        if not inv_obj:
            raise UserError('No records found !')
        list_3 = []
        cost_centers = []
        for x in inv_obj:
            if x.cost_center_id not in cost_centers:
                cost_centers.append(x.cost_center_id)

        grand_total_net = 0.0
        grand_total_balance = 0.0
        for cost_center in cost_centers:
            invoices = inv_obj.filtered(lambda s: s.cost_center_id.id == cost_center.id)
            list_1 = []
            list_2 = []
            total_net = 0.0
            total_balance = 0.0
            list_2.append(cost_center.name)
            for inv in invoices:
                partner_obj = inv.partner_id
                partner_code = inv.partner_id.sub_ledger_code or ''
                partner_name = partner_obj.name or ''
                partner = partner_code and "[%s] %s" %(partner_code, partner_name) or partner_name
                lpo = inv.name
                # if inv.self_billing_num:
                #     lpo = "%s[%s]"%(lpo, inv.self_billing_num)
                fc_amount = 0.0
                if inv.currency_id != inv.company_id.currency_id:
                    fc_amount = inv.amount_total
                    residual = 0.0
                    net = 0.0
                    debit = 0.0
                    credit = 0.0
                    if inv.move_id:
                        for move_line in inv.move_id.line_ids:
                            if move_line.account_id.user_type_id in \
                                    [self.env.ref('account.data_account_type_receivable'),
                                     self.env.ref('account.data_account_type_payable')]:
                                debit += move_line.debit
                                credit += move_line.credit
                    net = abs(debit - credit)
                    exchange_rate = net/fc_amount
                    residual = exchange_rate * inv.residual
                else:
                    net = inv.amount_total
                    residual = inv.residual
                vals = {
                        'name': inv.number or inv.internal_number or '',
                        'date': inv.date_invoice,
                        # 'cost_center': inv.cost_center_id and inv.cost_center_id.code or '',
                        'cost_center': (inv.cost_center_id.code or inv.cost_center_id.name) if inv.cost_center_id else '' ,
                        'customer': partner,
                        'job': inv.job_account and inv.job_account.name or '',
                        'lpo': lpo or '',
                        'curr': inv.currency_id and inv.currency_id.name or '',
                        'net': net or "0.00",
                        'fc_amount': fc_amount or "0.00",
                        'balance': residual or "0.00"
                        }
                total_net += net
                total_balance += residual
                grand_total_net += total_net
                grand_total_balance += total_balance
                list_1.append(vals)
            list_2.append(list_1)
            list_2.append(total_net)
            list_2.append(total_balance)
            list_3.append(list_2)
        docargs = {

            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'docs': list_3,
            'grand_total_net': grand_total_net,
            'grand_total_balance': grand_total_balance

        }
        return self.env['report'].render('hatta_reports.sale_invoice_summary_report', docargs)


