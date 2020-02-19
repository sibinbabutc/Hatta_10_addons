# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    type = fields.Selection(selection_add=[('pettycash', 'PettyCash')])


class AccountMove(models.Model):
    _inherit = 'account.move'

    pettycash_id = fields.Many2one('pettycash.fund')
    pc_credit = fields.Monetary('Credit', compute='compute_pc_balance', store=True)
    pc_debit = fields.Monetary('Debit', compute='compute_pc_balance', store=True)
    pc_balance = fields.Monetary('Balance', compute='compute_pc_balance', store=True)

    @api.depends('line_ids.credit', 'line_ids.debit')
    def compute_pc_balance(self):
        for move in self:
            if move.pettycash_id:
                for line in move.line_ids:
                    if line.account_id == move.pettycash_id.custodian_account:
                        move.pc_credit = line.credit if line.credit > 0 else 0.0
                        move.pc_debit = line.debit if line.debit > 0 else 0.0
                        move.pc_balance = line.debit - line.credit


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pettycash_id = fields.Many2one(related='move_id.pettycash_id')