from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ChequeFormat(models.Model):
    _name = 'cheque.format'
    _rec_name = 'name'
    _description = 'To define Cheque dimension and other related properties '

    name = fields.Char()
    # basic dimension
    page_height = fields.Float(string="Height")
    page_width = fields.Float(string="Width")
    # pay
    payee_tm = fields.Float(string="Top Margin")
    payee_lm = fields.Float(string="Left Margin")
    payee_fs = fields.Float(string="Font Size")

    # cheque Date
    date_tm = fields.Float(string="Top Margin")
    date_lm = fields.Float(string="Left Margin")
    date_fs = fields.Float(string="Font-Size")
    date_cs = fields.Float(string="Character Spacing")

    # Amount in words
    amt_word_tm = fields.Float(string="Top Margin")
    amt_word_lm = fields.Float(string="Left Margin")
    amt_word_fs = fields.Float(string="Font-Size")
    amt_word_cs = fields.Float(string="Character Spacing")

    # Amount
    amt_tm = fields.Float(string="Top Margin")
    amt_lm = fields.Float(string="Left Margin")
    amt_fs = fields.Float(string="Font-Size")
    amt_cs = fields.Float(string="Character Spacing")


class ChequePrintForAll(models.AbstractModel):
    _name = 'report.account_cheque_ft.report_cheque_print_for_all_one'

    @api.multi
    def render_html(self, docids, data=None):
        # if data['rpt_type'] and data['order_id']:
        payment_id = self.env['account.payment'].browse(data['order_id'])
        report_type = self.env['cheque.format'].browse(data['rpt_type'])
        docargs = {
            'docs': payment_id,
            'payment': payment_id,
            'cheque_format': report_type,
        }
        return self.env['report'].render('account_cheque_ft.cheque_format_ib_and_eib_check', docargs)
