# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def enable_cheque_on_journals(self):
        journals = self.search([('type', 'in', ['bank'])])
        cheque_out = self.env.ref('account_cheque_ft.account_payment_method_cheque')
        cheque_in = self.env.ref('account_cheque_ft.account_receipt_method_cheque')
        for journal in journals:
            journal.write({
                'inbound_payment_method_ids': [(4, cheque_in.id)],
                'outbound_payment_method_ids': [(4, cheque_out.id)]
            })
        return True

    @api.model
    def default_get(self, fields_list):
        res = super(AccountJournal, self).default_get(fields_list)
        if self.type == 'cheque':
            cheque_out = self.env.ref('account_cheque_ft.account_payment_method_cheque')
            cheque_in = self.env.ref('account_cheque_ft.account_receipt_method_cheque')
            if 'inbound_payment_method_ids' in res:
                res['inbound_payment_method_ids'][0][2].append(cheque_in.id)
            if 'outbound_payment_method_ids' in res:
                res['outbound_payment_method_ids'][0][2].append(cheque_out.id)
        return res

    @api.multi
    def name_get(self):
        res = []
        for journal in self:
            if journal.type == 'bank' and journal.bank_account_id:
                name = "%s(Acc:%s)" % (journal.bank_account_id.bank_name, journal.bank_account_id.acc_number)
            else:
                currency = journal.currency_id or journal.company_id.currency_id
                name = "%s (%s)" % (journal.name, currency.name)
            res += [(journal.id, name)]
        return res
