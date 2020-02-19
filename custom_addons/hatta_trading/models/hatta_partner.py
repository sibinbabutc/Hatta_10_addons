# -*- coding: utf-8 -*-
from email.utils import formataddr

from odoo import models, fields, api
from odoo.exceptions import UserError


class HattaPartner(models.Model):
    _inherit = 'res.partner'

    sub_ledger_code = fields.Char(string='Subledger Code')
    is_manufacturer = fields.Boolean("Manufacturer")
    is_principal_supplier = fields.Boolean("Principal Supplier")
    is_employee = fields.Boolean("Employee")
    is_carrier = fields.Boolean("Carrier")    
    partner_code = fields.Char(string='Partner Code')
    reviewed = fields.Boolean(string='Reviewed')
    # trn_code = fields.Char(string='TRN')
    upload_invoice_to_customer = fields.Boolean(string='Upload Invoice to Customer Site')
    partner_abbreviation = fields.Char(string='Partner Abbr.')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center')
    sequence_id = fields.Many2one('ir.sequence', string='Sequence')
    # bank_account_id = fields.Many2one('res.bank')
    pay_bank_ids = fields.Many2many('res.partner.bank', string='Paying Bank Account')
    parent_id = fields.Many2one('res.partner')
    final_destination_id = fields.One2many('res.partner.final.destinations', 'partner_id', string='Final Destination')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = u"[%s] %s" % (record.sub_ledger_code, record.name )if record.sub_ledger_code else record.name
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            name = name.split(' / ')[-1]
            args = ['|', ('sub_ledger_code', operator, name), ('name', operator, name)] + args
        return self.search(args, limit=limit).name_get()


# class PartnerBankLine(models.Model):
#     _name = "partner.bank.line"
#
#     @api.onchange('pay_bank')
#     def _get_bank_name(self):
#         for record in self:
#             search_obj = self.env['res.partner.bank'].search([('id','=',record.pay_bank.id)])
#             if search_obj:
#                 record.bank_name = search_obj.bank_id.bic
#
#     partner_id = fields.Many2one('res.partner')
#     pay_bank = fields.Many2one('res.partner.bank',string='Acc #',required=True)
#     bank_name = fields.Char('Bank')


class ResPartnerFinalDestination(models.Model):
    _name = "res.partner.final.destinations"

    def _default_company(self):
        return self.env['res.company']._company_default_get('res.partner')

    name = fields.Char(index=True, required=True)
    fax = fields.Char()
    title = fields.Many2one('res.partner.title')
    function = fields.Char(string='Job Position', required=True)
    color = fields.Integer(string='Color Index', default=0)

    street = fields.Char(required=True)
    street2 = fields.Char(required=True)
    zip = fields.Char(change_default=True, required=True)
    city = fields.Char(required=True)
    state_id = fields.Many2one("res.country.state", string='State', required=True, ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    mobile = fields.Char(required=True)
    company_id = fields.Many2one('res.company', 'Company', index=True, default=_default_company, required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    color = fields.Integer(string='Color Index', default=0)
    comment = fields.Text(string='Notes')
    image = fields.Binary("Image", attachment=True,
                          help="This field holds the image used as avatar for this contact, limited to 1024x1024px", )

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        for partner_id in self:
            partner_id.email_formatted = formataddr((partner_id.name, partner_id.email))
            
    # @api.model
    # def create(self, vals):
    #     return super(ResPartnerFinalDestination, self).create(vals)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            name = name.split(' / ')[-1]
            args = ['|', ('sub_ledger_code', operator, name), ('name', operator, name)] + args
        return self.search(args, limit=limit).name_get()