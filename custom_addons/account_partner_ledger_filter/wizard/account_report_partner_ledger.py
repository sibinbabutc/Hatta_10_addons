# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    partner_ids = fields.Many2many('res.partner', 'partner_ledger_partner_rel', 'id', 'partner_id', string='Partners')
    analytic_tag_ids = fields.Many2one('account.analytic.account',
                                       string='Analytic Account')
    analytic_account_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency,
                             'partner_ids': self.partner_ids.ids,})
        return self.env['report'].get_action(self, 'account.report_partnerledger', data=data)
