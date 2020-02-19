from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import english_number, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons import decimal_precision as dp
from datetime import datetime
from lxml import etree


def amount_to_text_ae(number):
    number = '%.2f' % number
    units_name = 'Dirhams'
    list = str(number).split('.')
    start_word = english_number(int(list[0]))
    end_word = english_number(int(list[1]))
    fils_name = 'Fils'

    return ' '.join(filter(None,
                           [start_word, units_name, (start_word or units_name) and (end_word or fils_name) and 'and',
                            end_word, fils_name]))


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry', readonly=True)
    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center')
    job_account = fields.Many2one('account.analytic.account', 'Job Account', related='enquiry_id.job_account')
    cost_sheet_id = fields.One2many('hatta.cost.sheet', 'purchase_order_id', string='Cost Sheet')
    customer_id = fields.Many2one('res.partner', string='Customer', related='enquiry_id.partner_id', store=True, readonly=True)
    enquiry_date = fields.Date(string='Enquiry Date', related='enquiry_id.creation_date', store=True, readonly=True)
    enquiry_closing_date = fields.Date(string='Enquiry Closing', related='enquiry_id.date_deadline', store=True, readonly=True)
    customer_rfq = fields.Char(string='Customer RFQ', related='enquiry_id.customer_rfq', store=True, readonly=True)
    base_currency = fields.Many2one('res.currency', default=lambda s: s.env.user.company_id.currency_id)
    exchange_rate = fields.Float(related='base_currency.rate')

    warehouse_id = fields.Many2one('stock.warehouse', string='Dest.Warehouse')

    invoiced = fields.Boolean(string='Invoiced')
    validated_by = fields.Many2one('res.users', string='Validated By')
    approval_date = fields.Date(string='Approval Date')
    is_selected_po = fields.Boolean("Selected", default=False)
    related_sale_order = fields.Many2one('sale.order')
    state = fields.Selection([('draft', 'RFQ'), ('sent', 'RFQ Sent'), ('cost_received', 'Quote Received'),
                              ('sale_ready', 'Ready for Sale'), ('to approve', 'To Approve'),
                              ('purchase', 'Purchase Order'), ('done', 'Locked'), ('cancel', 'Cancelled')],
                             string='Status', readonly=True, index=True, copy=False, default='draft',
                             track_visibility='onchange')
    active = fields.Boolean(string='Active', default=True)
    total_amount_lc = fields.Float('Total Amount LC', compute='get_total_amount_lc')

    # TODO: Move below field to wizards, its using for wizard_zero_rfq
    order_line_for_wizard = fields.One2many('purchase.order.line', 'order_id', domain=[('price_unit', '=', 0.0)])

    cost_sheet_status = fields.Selection(string='Cost Sheet Status', related='cost_sheet_id.state', readonly=True)
    cost_sheet_submitted = fields.Boolean(default=False)

    landed_cost_id = fields.One2many('purchase.landed.cost', 'purchase_order_id')

    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)
    sale_price_calculated = fields.Boolean(string='Sale Price')

    revision_reason = fields.Many2one('revision.reason', string='Revision Reason', store=True)
    is_revision = fields.Boolean(string='Revision')
    revision_number = fields.Integer(string='Revision', copy=False, default=0)
    unrevisioned_name = fields.Char(string='Order Reference', copy=False, readonly=True)
    current_revision_id = fields.Many2one('purchase.order', string='Active Revision', readonly=True)
    old_revision_ids = fields.Many2many('purchase.order', 'purchase_order_revision_ids_rel', 'purchase_order_id',
                                        'older_revision_id',
                                        domain=['|', ('active', '=', False), ('active', '=', False)],
                                        string='Old revisions', readonly=True)

    quotation_send_by = fields.Char(string='Quote Send By')
    quotation_date = fields.Date(string='Quote Date')
    supplier_invoice_date = fields.Date(string='Supplier Invoice Date')

    # company_id = fields.Many2one('res.company', string='Company')

    delivery_term = fields.Char(string='Delivery Period')
    delivery_term_place = fields.Char(string='Delivery Term place')
    delivery_date = fields.Date(string='Delivery Date')
    display_end_user_name = fields.Boolean(string='Display End-User', default=True)
    display_inquiry_name = fields.Boolean(string='Display Inquiry Name')
    override_sale_qty_check = fields.Boolean(string='Override Sale Qty Check')
    direct_delivery = fields.Boolean(string='Direct Delivery')
    direct_delivery_address = fields.Text(string='Delivery Address')
    final_destination = fields.Boolean(string='Display Final Destination')
    final_destination_id = fields.Many2one('res.partner', string='Final Destination')
    items = fields.Char(string='Items')

    # NOTES
    notes = fields.Text(string='Notes')
    special_notes = fields.Html(string='Special Notes')
    sp_note_duty_exemption = fields.Html(string='Special Notes for Duty Exemption')
    liquid_damage_notes = fields.Html(string='Liquidated Damage Notes')
    remarks = fields.Html(string='Remarks')
    data_sheet_remarks = fields.Html(string='Data Sheet Remarks')
    cancel_notes = fields.Html(string='Cancellation Notes')
    special_notes_bool = fields.Boolean(string='Special Notes', default=False)
    duty_exemption_bool = fields.Boolean(string='Duty Exemption Note', default=False)
    liquidated_damages_bool = fields.Boolean(string='Liquidated Damages Notes', default=False)
    remarks_bool = fields.Boolean(string='Remarks', default=False)
    po_data_remarks_bool = fields.Boolean(string='PO Datasheet Remark', default=False)
    cancellation_bool = fields.Boolean(string='Cancellation Notes', default=False)

    # INCOMING SHIPPING
    destination_address_id = fields.Many2one('res.partner', string='Customer Address')
    vendor_closing_date = fields.Date(string='Vendor Closing Date')
    vendor_origin_id = fields.Many2one('res.country', string='Vendor Origin')
    quotation_validity = fields.Integer(string='Quotation Validity')
    quotation_validity_type = fields.Selection(string="Type", selection=[
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('days', 'Days'),
    ], default='days')
    delivery_weeks = fields.Integer(string='Delivery(Weeks)')
    manufactures_id = fields.Many2one('res.partner', string='Manufacturer')
    product_type = fields.Char(string='Product Type')
    product_weight = fields.Float(string='Weight')
    product_volume = fields.Float(string='Volume(m3)')
    certificate_needed = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], string='Certificate Needed', default='yes')
    location_id = fields.Many2one('stock.location', string='Destination')
    is_shipped = fields.Boolean(string='Shipped')

    ship_quot_count = fields.Integer(compute='get_ship_quot_count')
    #VendorAddress
    street = fields.Char(string="Street")
    street2 = fields.Char(strinstreet2g="Street2")
    city = fields.Char(string="City")
    country_id = fields.Many2one('res.country', string="Country")
    state_id = fields.Many2one('res.country.state', string="State")
    zip = fields.Char(string="Zip")
    contact_person = fields.Char(string='Contact Person')
    contact_number = fields.Char(string='Contact Number')
    delivery_schedule = fields.Char(string='Delivery Schedule')
    complete_name = fields.Char('Complete Name', compute='get_complete_name')
    cost_sheet_required = fields.Boolean(string='Cost Sheet Required')

    @api.onchange('cost_sheet_required')
    def onchange_cost_sheet_required(self):
        if self.enquiry_id and self.cost_sheet_required:
            for line in self.order_line:
                line.dist_margin = 0.0

    @api.multi
    def get_complete_name(self):
        for record in self:
            if not len(record.order_line):
                record.complete_name = ''
            else:
                seq = [x.serial_no for x in record.order_line if x.serial_no]
                if seq:
                    if len(seq) == 1:
                        record.complete_name = '(Item %s)' % seq[0]
                    elif len(seq) == 2:
                        record.complete_name = '(Item %s , %s)' % (min(seq), max(seq))
                    else:
                        record.complete_name = '(Item %s - %s)' % (min(seq), max(seq))
                else:
                    record.complete_name = ''

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.fiscal_position_id = False
            self.payment_term_id = False
            self.currency_id = False
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].with_context(
                company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
            self.street = self.partner_id.street
            self.street2 = self.partner_id.street2
            self.city = self.partner_id.city
            self.country_id = self.partner_id.country_id
            self.state_id = self.partner_id.state_id
            self.zip = self.partner_id.zip
        return {}

    @api.depends('amount_total')
    def get_amount_in_words(self):
        for payment in self:
            payment.amount_in_words = amount_to_text_ae(payment.amount_total)

    @api.depends('order_line')
    def get_total_amount_lc(self):
        self.total_amount_lc = sum(line.price_total_lc for line in self.order_line) or 0.0

    @api.multi
    def get_ship_quot_count(self):
        for rec in self:
            sq_obj = self.env['shipping.quotation'].search([('purchase_order_id', '=', rec.id)])
            rec.ship_quot_count = len(sq_obj.ids)

    @api.multi
    def action_view_shipping_quotations(self):
        if not self.ship_quot_count:
            return {
                'name': "Shipping Quotations",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'shipping.quotation',
                'domain': [('purchase_order_id', '=', self.id)],
                'context': {
                    'default_purchase_order_id': self.id,
                    'default_cost_center_id': self.cost_center_id.id,
                    'default_job_id': self.job_account.id
                }
            }
        else:
            action = self.env.ref('hatta_trading.shipping_quotation_action')
            result = action.read()[0]
            result['domain'] = [('purchase_order_id', '=', self.id)]
            result['context'] = {'default_purchase_order_id': self.id}
            return result

    @api.multi
    def action_go_to_cost_sheet(self):
        if not self.order_line:
            raise ValidationError('Required Product Lines to be Added in Purchase Order.')
        res = self.cost_sheet_id
        if not self.cost_sheet_id:
            res = self.env['hatta.cost.sheet'].create({
                'purchase_order_id': self.id,
                'cost_sheet_currency_id': self.currency_id.id
            })
            res.onchange_total_cost()
        return {
            'name': 'Cost Sheet',
            'type': 'ir.actions.act_window',
            'res_model': 'hatta.cost.sheet',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': res.id
        }

    @api.multi
    def action_go_to_landed_cost(self):
        if not self.landed_cost_id:
            raise UserError('No Landed Cost Record Created')
        return {
            'name': 'Product Landed Cost',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.landed.cost',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.landed_cost_id.id if self.landed_cost_id else False
        }

    @api.multi
    def action_rfq_revision(self):
        return {
            'name': _('Order Revision'),
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.order.revision',
            'view_id': self.env.ref('hatta_trading.hatta_rfq_revision_order_wizard_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_reference': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    @api.model
    def create(self, values):
        po = super(PurchaseOrder, self).create(values)
        if not po.unrevisioned_name:
            po.unrevisioned_name = po.name
        return po

    @api.multi
    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference('hatta_trading', 'hatta_email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('hatta_trading',
                                                                 'hatta_email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def new_revision(self, by_code=False):
        self.ensure_one()
        today = fields.Date.from_string(fields.Date.today())
        older_revisions = self.old_revision_ids | self
        defaults = {
            'name': '%s-Rev/%s/%s/%s/%s' % (self.unrevisioned_name, today.day, today.month, today.year, str(self.revision_number + 1)),
            'revision_number': self.revision_number + 1,
            'state': 'draft',
            'old_revision_ids': [(4, older_revisions.ids, False)],
            'unrevisioned_name': self.unrevisioned_name,
        }
        revised = super(PurchaseOrder, self).copy(default=defaults)
        self.write({
            'is_revision': True,
            'active': False,
            'state': 'cancel'
        })
        self.old_revision_ids.write({
            'current_revision_id': revised.id
        })
        if by_code:
            return revised
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': self.env.ref('hatta_trading.purchase_order_for_enquiry_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': revised.id
        }

    @api.multi
    def action_cost_received(self):
        for line in self.order_line:
            if not line.price_unit:
                return {
                    'name': _("RFQ Line Price not Updated"),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_id': self.env.ref('hatta_trading.wizard_zero_unit_price_rfq_line').id,
                    'view_type': 'form',
                    'res_model': self._name,
                    'res_id': self.id,
                    'target': 'new',
                }
        self.state = 'cost_received'
        # if all([x.state in ('cost_received', 'sale_ready', 'cancel') for x in self.enquiry_id.purchase_order_lines]):
        #     self.enquiry_id.state = 'bid_completed'

    @api.multi
    def action_calculate_sale_price(self):
        if not self.cost_sheet_id:
            raise UserError("For Calculating Sale Price, it requires a Cost Sheet.\n"
                            "Please Create and Submit a Cost Sheet.")
        if not self.cost_sheet_status == 'submitted':
            raise UserError('Cost Sheet not Submitted.Please Submit Cost Sheet First')
        self.landed_cost_id.unlink()
        return {
            'name': _("Calculate Sale Price"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('hatta_trading.wizard_po_cost_sheet_required').id,
            'view_type': 'form',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def action_submit(self):
        if not self.cost_sheet_required:
            self.state = 'sale_ready'
            pass
        else:
            return {
                'name': _("Product Landed Cost"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_id': self.env.ref('hatta_trading.purchase_landed_cost_view_form').id,
                'view_type': 'form',
                'res_model': 'purchase.landed.cost',
                'context': {
                    'default_purchase_order_id': self.id,
                    'default_cost_sheet_id': self.cost_sheet_id.ids[0]
                }
            }


    @api.multi
    def select_purchase_order(self):
        if not self.sale_price_calculated:
            raise UserError("Sale Price not Calculated for Selected RFQ")
        elif self.enquiry_id.selected_purchase_order:
            raise UserError("You have already selected Purchase Order '%s' for this enquiry"
                            % self.enquiry_id.selected_purchase_order.name)
        else:
            self.is_selected_po = True
            so_obj = self.env['sale.order']
            self.enquiry_id.write(
                {'selected_purchase_order': self.id, })
            orderline = [(0, 0, {
                'serial_no': line.serial_no,
                'product_id': line.product_id.id,
                'name': line.name,
                'price_unit': line.sale_price_lc,
                'product_uom_qty': line.product_qty,
                'product_uom_id': line.product_uom.id,
                'tax_id': [(6, 0, line.product_id.taxes_id.ids)],
                'price_subtotal': line.price_subtotal}) for line in self.order_line]
            so = so_obj.create({
                'related_po_id': self.id,
                'enquiry_id': self.enquiry_id.id,
                'partner_id': self.enquiry_id.partner_id.id,
                # 'price_list_id': self.price_list_id.id,
                'order_line': orderline,
            })
            self.related_sale_order = so.id
            enquiry_obj = self.env['enquiry.details'].browse(self.enquiry_id.id)
            enquiry_obj.write({
                'state': 'sale_quotation',
                'sale_id': so.id,
            })
            return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.multi
    def button_approve(self, force=False):
        self.write({
            'state': 'purchase',
            'date_approve': fields.Date.context_today(self),
            'name': self.cost_center_id.sequence.next_by_id() if self.cost_center_id.sequence else self.name,
        })
        self._create_picking()
        self.filtered(
            lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'cost_received', 'sale_ready']:
                continue
            for line in order.order_line:
                if line.variant_ids and not line.selected_variant:
                    if len(line.variant_ids) == 1:
                        line.selected_variant = line.variant_ids
                    else:
                        raise ValidationError("Please select a variant for the product '%s'." % line.product_id.name)
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step' \
                    or (order.company_id.po_double_validation == 'two_step' \
                        and order.amount_total < self.env.user.company_id.currency_id.compute(
                        order.company_id.po_double_validation_amount, order.currency_id)) \
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
                for record in order.order_line:
                    record.update_product_suppliers()
                    if record.manufacturer_id:
                        record.update_product_manufacturer_supplier()
            else:
                order.write({'state': 'to approve'})
        return True

    @api.multi
    def action_view_invoice(self):
        # for rec in self:
        res = super(PurchaseOrder, self).action_view_invoice()
        if self.enquiry_id:
            res['context'].update({
                'default_enquiry_id': self.enquiry_id.id
            })
        if self.cost_center_id:
            res['context'].update({
                'default_cost_center_id': self.cost_center_id.id
            })
        if self.related_sale_order:
            res['context'].update({
                'default_sale_order_id': self.related_sale_order.id
            })
        return res

    def check_boolean_html(self, text):
        try:
            return bool(etree.fromstring(text, etree.XMLParser(remove_blank_text=True)).text)
        except:
            return False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    _description = 'Purchase Order Line'

    # _sql_constraints = [
    #     ('non_repeat_products_in_line', 'unique(order_id, product_id, enquiry_line_id)',
    #      'Product Lines are repeating. Please Check it')
    # ]

    def _compute_amount(self):
        super(PurchaseOrderLine, self)._compute_amount()
        for line in self:
            if line.enquiry_id:
                line.price_unit_lc = line.currency_id.compute(line.price_unit, line.base_currency, round=False)
                line.price_subtotal_lc = line.currency_id.compute(line.price_subtotal, line.base_currency, round=False)
                line.price_total_lc = line.currency_id.compute(line.price_total, line.base_currency, round=False)

    @api.depends('taxes_id', 'price_unit')
    def _compute_tax_line_price(self, total_tax=0.0):
        for record in self:
            currency = record.order_id and record.order_id.currency_id or None
            taxes = record.taxes_id.compute_all(record.price_unit, currency, record.product_qty, product=record.product_id,
                                                partner=record.order_id.partner_id)
            for item in taxes['taxes']:
                total_tax += item['amount']
            record.line_tax_amount = total_tax

    @api.depends('landed_cost_lines.cost_sheet_line_id.amount_lc', 'dist_margin')
    def compute_sale_price(self):
        for line in self:
            if line.order_id.cost_sheet_required:
                line.total_landed_cost = sum([cost.additional_landed_cost for cost in line.landed_cost_lines])
                line.net_cost_lc = line.total_landed_cost + line.price_total_lc
                line.sale_price_lc = round(line.net_cost_lc + line.dist_margin, 0)
                line.sale_price_unit = line.sale_price_lc / line.product_qty if line.product_qty else 0.0
            else:
                line.sale_price_lc = round(line.price_unit_lc + line.dist_margin, 0)
                line.sale_price_unit = line.sale_price_lc / line.product_qty if line.product_qty else 0.0

    name = fields.Html(string='Description', required=True)
    enquiry_line_id = fields.Many2one("enquiry.products.line", string="Enquiry Line ID")
    enquiry_id = fields.Many2one(related='enquiry_line_id.enquiry_id', store=True, string='Enquiry')
    enquiry_supplier_product_line_id = fields.Many2one('supplier.product.line', ondelete='cascade')
    purchase_method = fields.Selection(related='product_id.purchase_method')

    serial_no = fields.Char(string="Serial No", store=True)
    manufacturer_id = fields.Many2one('product.manufacturer', string='Manufacturer')
    line_tax_amount = fields.Float(compute='_compute_tax_line_price', string='VAT Amount')
    certificate_ids = fields.Many2many('product.certificate', string='Certificate(s) Required')
    base_currency = fields.Many2one(related='order_id.base_currency', store=True, string='Local Currency', readonly=True)

    price_unit_lc = fields.Float(string='Unit Price LC', compute='_compute_amount',  currency_field='base_currency', store=True)
    price_subtotal_lc = fields.Monetary(string='Subtotal', compute='_compute_amount', currency_field='base_currency', store=True)
    price_total_lc = fields.Monetary(string='Total', compute='_compute_amount', currency_field='base_currency', store=True)

    landed_cost_lines = fields.One2many('pol.landed.cost.line', 'purchase_order_line')

    total_landed_cost = fields.Monetary('Total Landed Cost', compute='compute_sale_price',
                                     store=True, currency_field='base_currency',)
    net_cost_lc = fields.Monetary(string='NetCost', readonly=True, currency_field='base_currency',
                                  compute='compute_sale_price', store=True)

    margin_percentage = fields.Float('Margin Allocation Percentage')
    dist_margin = fields.Monetary('Margin', readonly=True, currency_field='base_currency',)

    sale_price_lc = fields.Monetary(string='Sale Price', readonly=True, currency_field='base_currency',
                                 compute='compute_sale_price', store=True)
    sale_price_unit = fields.Monetary('Unit Sale Price', readonly=True,
                                      compute='compute_sale_price', store=True,
                                      currency_field='base_currency',)

    selected_for_sale = fields.Boolean(string='Select')

    variant_ids = fields.One2many('variants.line', 'pol_id')
    selected_variant = fields.Many2one('variants.line', string='Selected Variant')

    qualification = fields.Text('Qualification')
    justification = fields.Text('Justification')
    is_revision = fields.Boolean(string='Revision', related='order_id.is_revision')

    vendor_closing_date = fields.Date(string='Vendor Closing Date')
    # margin = fields.Float(string='Margin')

    @api.model
    def create(self, vals):
        res = super(PurchaseOrderLine, self).create(vals)
        if res.order_id.enquiry_id and not res.enquiry_supplier_product_line_id:
            enquiry_line = res.order_id.enquiry_id.product_lines.filtered(lambda s: s.product_id.id == res.product_id.id)
            if not enquiry_line:
                raise ValidationError('Only products in Enquiry are allowed to add in an Enquiry based RFQ')
            supplier_product_line = self.env['supplier.product.line'].create({
                'purchase_order_line_id': res.id,
                'enquiry_id': res.order_id.enquiry_id.id,
                'enquiry_line_id': enquiry_line.ids[0],
                'supplier_id': res.partner_id.id,
                'product_id': enquiry_line.product_id.id,
                'product_qty': enquiry_line.product_uom_qty,
                'product_uom_id': enquiry_line.product_uom_id.id
            })
            res.update({
                'enquiry_line_id': enquiry_line.id,
                'enquiry_supplier_product_line_id': supplier_product_line.id,
                'product_qty': enquiry_line.product_uom_qty,
            })
        return res

    @api.multi
    def select_po_line(self):
        eng_product_line = self.env['enquiry.products.line']
        uom_obj = self.env['product.uom']
        # for pol_obj in self:
        purchase_obj = self.order_id or False
        if self.price_unit == 0.00:
            raise UserError(_("Unit price cannot be 0.00"))
        if purchase_obj:
            product_uom_id = self.product_id.uom_id.id or False
            enq_id = purchase_obj.enquiry_id and purchase_obj.enquiry_id.id or False
            enq_product_qty = 0.00
            same_pol_qty = 0.00
            if enq_id:
                enq_product_ids = eng_product_line.search(
                    [('product_id', '=', self.product_id.id), ('enquiry_id', '=', enq_id)])
                for enq_product in enq_product_ids:
                    enq_qty = enq_product.product_uom_qty or 0.00
                    if enq_product.product_uom_id.id != product_uom_id:
                        enq_qty = uom_obj._compute_quantity(enq_product.product_uom_id.id, enq_qty, product_uom_id)
                    enq_product_qty += enq_qty
                same_pol_ids = self.search(
                    [('order_id.enquiry_id', '=', enq_id), ('product_id', '=', self.product_id.id),
                     ('state', '!=', 'cancel')])
                for same_pol_obj in same_pol_ids:
                    same_qty = same_pol_obj.product_qty or 0.00
                    pol_uom = same_pol_obj.product_uom and same_pol_obj.product_uom.id or same_pol_obj.product_id.uom.id or False
                    if pol_uom != product_uom_id:
                        same_qty = uom_obj._compute_quantity(pol_uom, same_qty, product_uom_id)
                    same_pol_qty += same_qty
            pol_qty = self.product_qty or 0.00
            pol_uom = self.product_uom and self.product_uom.id or self.product_id.uom_id.id or False
            if pol_uom != product_uom_id:
                pol_qty = uom_obj._compute_quantity(pol_uom, pol_qty, product_uom_id)
            same_pol_qty += pol_qty
            if enq_product_qty < same_pol_qty and not self.env.context.get('overide', False):
                return {
                    'name': _('Change Select Qty'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pol.select.qty.adjust',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                self.write({'select_for_sale': True})

    @api.multi
    def view_purchase_order(self):
        return {
            'res_id': self.order_id.id,
            'name': 'Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_id': self.env.ref('purchase.purchase_order_form').id
        }

    @api.onchange('selected_variant')
    def onchange_selected_variant(self):
        if self.selected_variant:
            sol_obj = self.env['sale.order.line'].browse(self.selected_variant.sol_id.id)
            sol_obj.write({
                'selected_variant': self.selected_variant.id
            })

    def apply_margin_percentage(self, margin):
        for line in self:
            line.dist_margin = margin * (line.margin_percentage / 100)

    def update_product_manufacturer_supplier(self):
        if self.product_id.manufacturer_ids:
            manufacture_line = self.product_id.manufacturer_ids.filtered(lambda s: s.manufacturer_id.id == self.manufacturer_id.id)
            if not manufacture_line:
                self.product_id.manufacturer_ids = [(0, 0, {
                    'manufacturer_id': self.manufacturer_id.id,
                    'vendor_ids': [(4, self.partner_id.id,)]
                })]
            if manufacture_line and self.partner_id not in manufacture_line.vendor_ids:
                manufacture_line.vendor_ids = [(4, self.partner_id.id,)]

    def update_product_suppliers(self):
        if self.product_id.manufacturer_ids:
            vendor_line = self.product_id.seller_ids.filtered(lambda s: s.name.id == self.partner_id.id)
            if not vendor_line:
                self.product_id.seller_ids = [(0, 0, {
                    'name': self.partner_id.id,
                    'delay': 1,
                    'min_qty': 0.00,
                    'price': 0.00
                })]
            if vendor_line:
                vendor_line.seller_ids = [(4, self.partner_id.id,)]

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(
                self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result


class RevisionReason(models.Model):
    # TODO: If not using remove below. if using, make it same field from revising model and remove this model
    _name = 'revision.reason'
    _rec_name = 'reason'

    reason = fields.Char(string='Reason')


class PolSelectQtyAdjust(models.Model):
    _name = 'pol.select.qty.adjust'
    _description = 'POL Select Qty Adjust'

    @api.model
    def default_get(self, fields_list):
        res = super(PolSelectQtyAdjust, self).default_get(fields_list)
        purchase_order_line = self.env['purchase.order.line']
        claim_product_pool = self.env['enquiry.products.line']
        active_id = self.env.context.get('active_id', False)
        if active_id:
            pol_obj = purchase_order_line.browse(active_id)
            enq_obj = pol_obj.order_id and pol_obj.order_id.enquiry_id or False
            res[
                'name'] = "<h3><b>Selection for the product %s in customer enquiry number %s is already made. Do you want to continue ?</b></h3>" % (
            pol_obj.product_id.name, enq_obj.reference)
            res['pol_id'] = pol_obj.id
            if enq_obj:
                same_pol_ids = purchase_order_line.search([('order_id.enquiry_id', '=', enq_obj.id),
                                                           ('product_id', '=', pol_obj.product_id.id),
                                                           ('state', '!=', 'cancel')])
                enq_product_qty = 0.00
                enq_product_ids = claim_product_pool.search([('product_id', '=', pol_obj.product_id.id),
                                                             ('enquiry_id', '=', enq_obj.id)])
                for enq_product_obj in enq_product_ids:
                    enq_product_qty += enq_product_obj.product_uom_qty or 0.00
                res['enq_qty'] = enq_product_qty
                lines = []
                for same_pol_obj in same_pol_ids:
                    lines.append((0, 0, {
                        'order_ref': same_pol_obj.order_id.id,
                        'product_id': same_pol_obj.product_id.id,
                        'supplier_id': same_pol_obj.partner_id.id,
                        'customer_id': same_pol_obj.partner_id and
                                       same_pol_obj.partner_id.id,
                        'lead_id': enq_obj.id,
                        'product_qty': same_pol_obj.product_qty or 0.00,
                        'currency_id': same_pol_obj.currency_id.id,
                        'price_unit_fc': same_pol_obj.price_unit or 0.00,
                        'price_unit_lc': same_pol_obj.price_unit_lc or 0.00,
                        'pol_id': same_pol_obj.id,
                        'state': same_pol_obj.state
                    }))
                res['product_ids'] = lines
        return res

    name = fields.Text('Warning')
    pol_id = fields.Many2one('purchase.order.line', 'Purchase Order Line')
    enq_qty = fields.Float('Enquiry Quantity')
    product_ids = fields.One2many('pol.select.qty.adjust.line', 'wizard_id', 'Product Lines')

    def change_qty(self):
        pol_pool = self.env['purchase.order.line']
        pol_id = False
        for wizard_obj in self:
            for line in wizard_obj.product_ids:
                pol_obj = line.pol_id or False
                if pol_obj:
                    if pol_obj.product_qty != line.product_qty:
                        pol_obj.write({'product_qty': line.product_qty})
                        pol_pool.distribute_cost([pol_obj.id])
            pol_id = wizard_obj.pol_id or False
        ctx = self.env.context.copy()
        ctx['overide'] = True
        self.env.context = ctx
        if pol_id:
            pol_id.select_po_line()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class PolSelectQtyAdjustLine(models.Model):
    _name = 'pol.select.qty.adjust.line'
    _description = 'POL Select Qty Adjust Lines'

    order_ref = fields.Many2one('purchase.order', 'Order Reference')
    product_id = fields.Many2one('product.product', 'Product')
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    customer_id = fields.Many2one('res.partner', 'Customer')
    lead_id = fields.Many2one('enquiry.details', 'Customer Enq')
    product_qty = fields.Float('Quantity',
                               digits=dp.get_precision('Product Unit of Measure'))
    currency_id = fields.Many2one('res.currency', 'Currency')
    price_unit_fc = fields.Float('Price Unit FC',
                                 digits=dp.get_precision('Account'))
    price_unit_lc = fields.Float('Price Unit LC',
                                 digits=dp.get_precision('Account'))
    subtotal_lc = fields.Float('Subtotal LC',
                               digits=dp.get_precision('Account'))
    pol_id = fields.Many2one('purchase.order.line', 'Related POL')
    wizard_id = fields.Many2one('pol.select.qty.adjust', 'Wizard')
    state = fields.Selection([('draft', 'RFQ'), ('sent', 'RFQ Sent'),
                              ('cost_received', 'Cost Received'),
                              ('to approve', 'To Approve'),
                              ('purchase', 'Purchase Order'), ('done', 'Locked'),
                              ('cancel', 'Cancelled')], "State")
