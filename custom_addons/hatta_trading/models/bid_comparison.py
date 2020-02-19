from odoo import api, fields, models


class BidComparison(models.Model):
    _name = 'bid.comparison'

    supplier = fields.Many2one('res.partner', 'Supplier', readonly=True,
                               related='purchase_order_line_id.order_id.partner_id')
    product = fields.Many2one('product.product', 'Product', readonly=True,
                              related='purchase_order_line_id.product_id')
    qty = fields.Float('Quantity', related='purchase_order_line_id.product_qty')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  related='purchase_order_line_id.order_id.currency_id',
                                  required=True)
    price_unit = fields.Float(string="Unit Price",
                              related='purchase_order_line_id.price_unit')
    subtotal = fields.Monetary('Subtotal', currency_field='currency_id',
                               related='purchase_order_line_id.price_subtotal')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase')
    purchase_order_id = fields.Many2one('purchase.order', "Purchase Order",
                                        related='purchase_order_line_id.order_id')
    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry', related='purchase_order_id.enquiry_id')
    state = fields.Selection(string="State", selection=[('po_to_be_selected', 'PO To Be Selected'),
                                                        ('po_selected', 'PO Selected'), ], default='po_to_be_selected')
    is_selected_po = fields.Boolean('Selected', default=False, readonly=True)

    @api.multi
    def select_purchase_order(self):
        # self.state = 'po_selected'
        selected_lines = self.search([('purchase_order_id', '=', self.purchase_order_id.id)])
        all_lines = self.search([('enquiry_id', '=', self.enquiry_id.id)])
        for x in selected_lines:
            x.is_selected_po = True
        for y in all_lines:
            y.state = 'po_selected'
        so_obj = self.env['sale.order']
        orderline = [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'price_unit': line.price_unit,
                'product_uom_qty': line.product_qty,
                'product_uom_id': line.product_uom.id,
                'price_subtotal': line.price_subtotal}) for line in self.purchase_order_id.order_line]
        so = so_obj.create({
            'enquiry_id': self.enquiry_id.id,
            'partner_id': self.enquiry_id.partner_id.id,
            # 'price_list_id': self.purchase_order_id.price_list_id.id,
            'order_line': orderline,

        })
        enquiry_obj = self.env['enquiry.details'].browse(self.enquiry_id.id)
        enquiry_obj.write({
            'state': 'sale_quotation',
            'sale_id': so.id
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
