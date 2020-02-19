from odoo import api,fields,models


class ShippingInvoice(models.Model):
    _name = 'shipping.invoice'
    _rec_name = 'name'

    name = fields.Char('Name')
    carrier_id = fields.Many2one('res.partner', string='Carrier')
    account_number = fields.Char(string='Acc No')
    date = fields.Date(string='Date')
    date_accounting = fields.Date(string='Accounting Date')
    journal_id = fields.Many2one('account.journal', string='Journal')
    quotation_ids = fields.One2many('shipping.quotation', 'shipping_invoice_id', string='')
    total = fields.Float(string='Total', compute='get_total')
    rounding_off = fields.Float(string='Rounding Off')
    net_total = fields.Float(string='Net Total', compute='get_total')
    payment_ids = fields.Many2many('account.move')
    purchase_others = fields.Many2one('account.move', string='Purchase Others')

    @api.depends('quotation_ids', 'quotation_ids.total')
    def get_total(self):
        for rec in self:
            total = 0.0
            for item in rec.quotation_ids:
                total += item.total
            rec.total = total
            rec.net_total = total - rec.rounding_off


class AccountMoveInherited(models.Model):

    _inherit = 'account.move'

    company_id = fields.Many2one('res.company',string='Company')
