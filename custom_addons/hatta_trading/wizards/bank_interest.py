
from odoo import fields,models


class BankInterest(models.Model):
    _name = 'bank.interest'

    cost_sheet_id = fields.Many2one('hatta.cost.sheet', string='Cost Sheet')
    total_amount = fields.Monetary(string='Total Amount', realted='cost_sheet_id.amount_total')
    bank_interest = fields.Float(string='Bank Interest')
    interest_line = fields.One2many('bank.interest.line', 'cost_sheet_id')
    currency_id = fields.Many2one('res.currency', string='Currency', realted='cost_sheet_id.cost_sheet_currency_id')
    total_interest = fields.Monetary(string='Total Interest')


class BankInterestLine(models.Model):
    _name = 'bank.interest.line'

    currency_id = fields.Many2one('res.currency', string='Currency', related='cost_sheet_id.currency_id')
    cost_sheet_id = fields.Many2one('bank.interest')
    amount = fields.Float(string='Amount')
    delivery_days = fields.Float(string='Days')
    interest_rate = fields.Float(string='Interest Rate')
    interest_amount = fields.Float(string='Interest Amount')