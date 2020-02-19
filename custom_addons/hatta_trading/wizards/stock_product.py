from odoo import api, fields, models


class StockProduct(models.Model):
    _name = 'stock.product.wizard'

    product_id = fields.Many2one('product.template', string='Product')
    manufacturer_id = fields.Many2one('res.partner', string='Manufacturer', readonly=True)
    vendor_ids = fields.Many2many('product.supplierinfo', string='Vendors')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.manufacturer_id = self.product_id.manufacturer_id
        supplier = []
        res = {'value': {}}
        for x in self.product_id.seller_ids:
            supplier.append(x.id)
        res['value']['vendor_ids'] = [(6, 0, supplier)]
        return res
