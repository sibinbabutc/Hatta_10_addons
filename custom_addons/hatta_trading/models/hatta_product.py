from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HattaProductTemplate(models.Model):
    _inherit = "product.template"

    part_number = fields.Char(string='Part Number')
    notes = fields.Html(string='Notes')
    is_principal_suppliable = fields.Boolean(string='Is Principal Suppliable')
    principal_supplier_ids = fields.One2many('principal.supplier', 'product_template_id')
    customer_ids = fields.One2many('product.customer.info', 'product_template_id')
    analytic_operation_type = fields.Many2one('account.analytic.tag', domain=[('tag_type', '=', 'operation_mode')],
                                               string='Operation Type', )
    analytic_tags = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    manufacturer_ids = fields.One2many('manufacturers.list', 'product_template_id', string='Manufacturer')

    description = fields.Html(
        'Description', translate=True,
        help="A precise description of the Product, used only for internal information purposes.")

    @api.onchange('is_principal_suppliable')
    def changing_operation_mode(self):
        tag_ids = self.analytic_tags.ids
        ps_tag = self.env.ref('hatta_trading.analytic_tag_ps').id
        nps_tag = self.env.ref('hatta_trading.analytic_tag_nps').id
        if self.is_principal_suppliable:
            self.analytic_operation_type = ps_tag
            tag_ids.append(ps_tag)
            if nps_tag in tag_ids:
                tag_ids.remove(nps_tag)

            # self.analytic_tags = [(6, 0, )]
        else:
            self.analytic_operation_type = nps_tag
            tag_ids.append(nps_tag)
            if ps_tag in tag_ids:
                tag_ids.remove(ps_tag)
            # self.analytic_tags = [(1, self.analytic_tags, self.env.ref('hatta_trading.analytic_tag_nps').id)]
        self.analytic_tags = [(6, 0, tag_ids)]

    @api.onchange('description')
    def onchange_description(self):
        if self.description:
            if not self.description_sale:
                self.description_sale = self.description
            if not self.description_purchase:
                self.description_sale = self.description
            if not self.description_picking:
                self.description_sale = self.description

    @api.onchange('type')
    def onchange_product_type(self):
        if self.type == 'product':
            tag_ids = self.analytic_tags.ids
            tag_ids.append(self.env.ref('hatta_trading.analytic_tag_stockable').id)
            self.analytic_tags = [(6, 0, tag_ids)]

    @api.model
    def default_get(self, fields_list):
        res = super(HattaProductTemplate, self).default_get(fields_list)
        res.update({
            'taxes_id': False,
            'supplier_taxes_id': False,
        })
        return res

    @api.constrains('is_principal_suppliable', 'principal_supplier_ids')
    def need_principal_supplier(self):
        if self.is_principal_suppliable and not self.principal_supplier_ids.ids:
            raise ValidationError('Please add atleast one Principal Supplier for this Principal Suppliable Product')
    
    @api.multi
    def write(self, vals):
        return super(HattaProductTemplate, self).write(vals)


class Product(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self.env.context.get('only_enquired_products'):
            enquiry = self.env.context.get('enquiry_id')
            if enquiry:
                args.append(['id', 'in', self.env['enquiry.details'].browse(enquiry).mapped('product_lines.product_id').ids])
        return super(Product, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []
        for product in self.sudo():
            # display only the attributes with multiple possible values on the template
            variable_attributes = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id')
            variant = product.attribute_value_ids._variant_name(variable_attributes)

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            customers = []
            if partner_ids:
                sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                customers = [x for x in product.customer_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                if not sellers:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
                if not customers:
                    customers = [x for x in product.customer_ids if (x.name.id in partner_ids) and not x.product_id]
            if sellers or customers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
                for c in customers:
                    customer_variant = c.product_name and (
                        variant and "%s (%s)" % (c.product_name, variant) or c.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': customer_variant or name,
                              'default_code': c.product_code or product.default_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          }
                result.append(_name_get(mydict))
        return result


class PrincipalSupplier(models.Model):
    _name = 'principal.supplier'
    _rec_name = 'partner_id'

    product_template_id = fields.Many2one('product.template')
    partner_id = fields.Many2one('res.partner', string='Name', domain=[('is_principal_supplier', '=', 'True')])
    partner_reference = fields.Char(string='Reference')


class HattaProductWizard(models.Model):
    _name = 'product.wizard'

    product_id = fields.Many2one('product.product', string='Product')
    partner_id = fields.Many2one('res.partner', string='Customer')
    purchase_history = fields.Many2many('purchase.order.line')
    sale_history = fields.Many2many('sale.order.line')

    @api.onchange('product_id')
    def onchange_product(self):
        purchase_obj = self.env['purchase.order.line'].search([('product_id', '=', self.product_id.id)])
        sale_obj = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id)])
        purchase_orders = []
        sale_orders = []
        res = {'value': {}}
        for x in purchase_obj:
            purchase_orders.append(x.id)
        res['value']['purchase_history'] = [(6, 0, purchase_orders)]
        for x in sale_obj:
            sale_orders.append(x.id)
        res['value']['sale_history'] = [(6, 0, sale_orders)]
        return res


class ProductCustomerInfo(models.Model):
    _name = 'product.customer.info'
    _rec_name = 'name'

    name = fields.Many2one('res.partner', 'Customer', domain="[('customer', '=', True)]")
    product_name = fields.Char('Customer Product Name')
    product_code = fields.Char('Customer Product Code')
    product_template_id = fields.Many2one('product.template')
    product_id = fields.Many2one('product.product', 'Product Variant')


class ManufacturersList(models.Model):
    _name = 'manufacturers.list'
    _rec_name = 'manufacturer_id'

    product_template_id = fields.Many2one('product.template')
    manufacturer_id = fields.Many2one('product.manufacturer', string='Manufacturer')
    vendor_ids = fields.Many2many('res.partner', string='Vendors', domain=[('supplier', '=', True)])





