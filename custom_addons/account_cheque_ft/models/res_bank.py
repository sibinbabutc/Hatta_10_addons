# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CustomBank(models.Model):
    _inherit = 'res.bank'
    _description = 'Custom Bank'

    bank_code = fields.Char(string='Bank Code')
    iban_code = fields.Char(string='IBAN Code')
    mob_num = fields.Char(string='Mobile Number')
    website = fields.Char(string="Website")
    cont_person = fields.Many2one('res.partner', string='Contact person')

    cheque_print_id = fields.Many2one('ir.actions.report.xml', 'Cheque Print Format',
                                      domain=[('report_name', 'like', '%.cheque_format_%')])


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    iban_code = fields.Char(string='IBAN Code', related='bank_id.iban_code', readonly=True)
    bic = fields.Char(string="Bank Identifier Code", related='bank_id.bic', readonly=True)