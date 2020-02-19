from odoo import api, fields, models


class ChequeReportWizard(models.TransientModel):
    _name = "cheque.report.wizard"

    payment_id = fields.Many2one("account.payment", string="Payment Id")
    report_type = fields.Many2one('cheque.format')

    @api.multi
    def print_report(self):
        return self.env['report'].get_action(self, 'account_cheque_ft.report_cheque_print_for_all_one',
                                             data={'rpt_type': self.report_type.id,
                                                   'order_id': self.payment_id.id,})
