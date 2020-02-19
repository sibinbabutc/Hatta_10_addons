from odoo import api, fields, models


class ShippingResConfig(models.TransientModel):
    _name = 'shipping.config.settings'
    _inherit = 'res.config.settings'

    default_shipping_account = fields.Many2one('account.account', string='Default Shipping Account')

    @api.multi
    def set_default_shipping_account(self):
        ir_values_obj = self.env['ir.values']
        if self.default_shipping_account:
            ir_values_obj.sudo().set_default('shipping.quotation', "account_id",
                                             self.default_shipping_account.id)

    @api.model
    def get_default_shipping_account(self, fields_list):
        res = {}
        ir_values_obj = self.env['ir.values']
        if 'default_shipping_account' in fields_list:
            value = ir_values_obj.sudo().get_default('shipping.quotation', "account_id")
            if value:
                res.update(default_shipping_account=value)
        return res