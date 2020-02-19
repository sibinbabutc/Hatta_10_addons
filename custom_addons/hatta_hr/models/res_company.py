# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    mol_no = fields.Char('MOL ID', size=64, help="Ministry Of Labour ID")
    comp_bank_number = fields.Char('Company ID Number as per bank', size=128)
    labour_number = fields.Char('Company Labour Number', size=128)
