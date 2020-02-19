# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class Manufacturer(models.Model):
    _name = 'product.manufacturer'
    _description = 'Manufacturer'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'name'

    image = fields.Binary()
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    street = fields.Char("Street")
    street2 = fields.Char("Street2")
    zip = fields.Char('Zip')
    city = fields.Char("City")
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    fax = fields.Char(string='Fax')
    website = fields.Char(string='Website')

    supplier = fields.Many2one('res.partner')

    @api.multi
    def create_supplier(self):
        supplier = self.env['res.partner'].create({
            'image': self.image,
            'name': self.name,
            'sub_ledger_code': self.code,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email,
            'fax': self.fax,
            'website': self.website,
            'supplier': True,
            'is_manufacturer': True
        })
        self.supplier = supplier.id
        return {
            'name': 'Supplier',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'res.partner',
            'res_id': supplier.id
        }
