# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountPaymentAbstractHr(models.AbstractModel):
    _inherit = "account.abstract.payment"

    partner_type = fields.Selection(selection_add=[('employee', 'Employee')])
