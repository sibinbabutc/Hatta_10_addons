from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pettycash_id = fields.Many2one('pettycash.fund', string='PettyCash Fund', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', 'in', ('bank', 'cash', 'pettycash'))])
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To',
                                             domain=[('type', 'in', ('bank', 'cash', 'pettycash'))])
    description = fields.Char('Description')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountPayment, self).default_get(fields_list)
        if res.get('pettycash_id'):
            if not res.get('journal_id'):
                res.update({
                    'journal_id': self.journal_id.search([('type', '=', 'cash')], limit=1).id
                })
            if not res.get('destination_journal_id'):
                res.update({
                    'destination_journal_id': self.destination_journal_id.search([('type', '=', 'cash')], limit=1).id
                })
        return res

    @api.multi
    def account_petty_cash_payment_voucher_report(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'account_petty_cash_ft.report_petty_cash_payment')