from odoo import api, fields, models


class CreateRFQ(models.TransientModel):
    _name = 'create.rfq'

    @api.model
    def default_get(self, fields_list):
        res = super(CreateRFQ, self).default_get(fields_list)
        enquiry = self.env['enquiry.details'].browse(self.env.context.get('active_id'))
        html = self.env['ir.qweb'].render('hatta_trading.product_supplier_details', {
            'lines': enquiry.supplier_product_lines.sorted('product_id')
        })
        res.update({
            'supplier_product_details': html,
            'supplier_product_lines': [(4, x.id) for x in enquiry.supplier_product_lines.filtered(
                lambda s: not s.purchase_order_line_id)]
        })
        return res

    reference = fields.Char(string='Reference')
    enquiry_date = fields.Date(string='Enquiry Date')
    closing_date = fields.Date(string='Closing Date')
    customer_id = fields.Many2one('res.partner', string='Customer')
    supplier_closing_date = fields.Date(string='Supplier Closing Date')
    enquiry_detail_id = fields.Many2one('enquiry.details')
    enquiry_id = fields.Many2one('enquiry.details')
    customer_rfq = fields.Char(string='Customer RFQ')
    detail_wise = fields.Selection([('product', 'Product Wise'), ('supplier', 'Supplier Wise')],
                                   string='Show Detail', default='product')
    supplier_product_details = fields.Html(readonly=True)

    add_more = fields.Boolean()

    supplier_product_lines = fields.One2many('supplier.product.line', 'enquiry_create_rfq_temp')

    @api.onchange('detail_wise', 'supplier_product_lines')
    def onchange_filter(self):
        html = ''
        qweb = self.env['ir.qweb']
        id_sorted = (self.enquiry_id.supplier_product_lines | self.supplier_product_lines).sorted('id')
        if self.detail_wise == 'product':
            html = qweb.render('hatta_trading.product_supplier_details',
                               {'lines': id_sorted.sorted(lambda s: s.product_id.id)})
        if self.detail_wise == 'supplier':
            html = qweb.render('hatta_trading.supplier_product_details',
                               {'lines': id_sorted.sorted(lambda s: s.supplier_id.id)})
        self.supplier_product_details = html

    @api.multi
    def create_multiple_rfqs(self):
        return self.enquiry_id.create_rfqs()