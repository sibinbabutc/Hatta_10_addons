# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    is_job_code = fields.Boolean('Job Code')
    is_subledger_account = fields.Boolean("Sub Ledger Code")
    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry')
    sale_order_ids = fields.One2many(related='enquiry_id.sale_ids')
    purchase_order_ids = fields.One2many(related='enquiry_id.purchase_orders')
    move_line_ids = fields.One2many('account.move.line', 'analytic_account_id')
    analytic_entries = fields.One2many('account.analytic.line', 'account_id')
    # account_invoice_ids = fields.One2many()


class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    tag_type = fields.Selection(string="Type", selection=[('cost_center', 'Cost Center'),
                                                          ('operation_mode', 'Operation Mode'), ])
    code = fields.Char(string='Reference')
    sequence = fields.Many2one('ir.sequence', string='Sequence', domain=[('is_cost_center', '=', True)])


class Sequence(models.Model):
    _inherit = 'ir.sequence'

    is_cost_center = fields.Boolean(string='Cost Center')
