from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import english_number


def amount_to_text_ae(number):
    number = '%.2f' % number
    units_name = 'Dirhams'
    start_word, end_word = str(number).split('.')
    start_word = english_number(int(start_word))
    end_word = english_number(int(end_word))
    fils_name = 'Fils'

    return ' '.join(filter(None,
                           [start_word, units_name, (start_word or units_name) and (end_word or fils_name) and 'and',
                            end_word, fils_name]))


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        res = super(MailMessage, self).create(vals)
        if res.message_type in ['email', 'comment'] and res.model == 'purchase.order':
            po = self.env['purchase.order'].browse(res.res_id)
            if po.enquiry_id:
                vals.update({
                    'model': 'enquiry.details',
                    'res_id': po.enquiry_id.id
                })
                super(MailMessage, self).create(vals)
        return res


class EnquiryDetails(models.Model):
    _name = 'enquiry.details'
    _description = 'Enquiry Details'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherits = {'crm.lead': 'crm_lead_id'}
    _rec_name = 'reference'

    @api.model
    def default_get(self, fields_list):
        res = super(EnquiryDetails, self).default_get(fields_list)
        if self.env.context.get('default_crm_lead_id'):
            crm_lead = self.env['crm.lead'].browse(self.env.context.get('default_crm_lead_id'))
            res.update({
                'partner_id': crm_lead.partner_id.id,
                'email_from': crm_lead.email_from,
                'phone': crm_lead.phone,
                'user_id': crm_lead.user_id.id,
                'name': crm_lead.name,
                'date_deadline': crm_lead.date_deadline,
                'description': crm_lead.description
            })
        return res

    reference = fields.Char(string='Reference', readonly=True)
    crm_lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade', auto_join=True, index=True)
    edit_ref = fields.Boolean(string='Edit')
    creation_date = fields.Date(string='Creation Date', default=fields.Date.today)
    customer_rfq = fields.Char(string='Customer RFQ')
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('customer', '=', True)], related='crm_lead_id.partner_id')
    partner_procure_id = fields.Many2one('res.partner', string='Procure.Address',
                                         domain="[('parent_id','=',partner_id)]")
    partner_delivery_id = fields.Many2one('res.partner', string='Delivery Address',
                                          domain="[('parent_id','=',partner_id)]")
    contact_id = fields.Many2one('res.partner', string='Contact')
    end_user_id = fields.Many2one('res.partner', string='End User', required=True)
    email_from = fields.Char('Email', related='crm_lead_id.email_from')
    phone = fields.Char(string='Phone', related='crm_lead_id.phone')
    user_id = fields.Many2one('res.users', string='Salesperson',
                              default=lambda self: self.env.user, related='crm_lead_id.user_id')
    product_type = fields.Char('Product Type')
    coll_buyer_ref_no = fields.Char('RFQ No. / Buyer Ref.')
    coll_no_type = fields.Selection(string="Coll.Type", selection=[('coll_rfq_no', 'Coll. RFQ No.'),
                                                                   ('buyer_ref', 'Buyer Ref.'), ], default='coll_rfq_no')
    name = fields.Char('Enquiry Subject', related='crm_lead_id.name')
    date_deadline = fields.Date('Expected Closing', related='crm_lead_id.date_deadline')
    priority = fields.Selection(string="Priority", selection=[
        ('1', 'Highest'),
        ('2', 'High'),
        ('3', 'Normal'),
        ('4', 'Low'),
        ('5', 'Lowest')], default='3')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Centre')
    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center', domain=[('tag_type', '=', 'cost_center')])
    partner_sequence = fields.Boolean(string='Partner Sequence')

    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')
    delivery_terms = fields.Char('Delivery Term')
    quote_validity = fields.Char('Our Quote Validity')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id,
                                  required=True)
    sale_id = fields.Many2one('sale.order', string='Related Sale Order', readonly=True)
    worksheet_date = fields.Datetime('Last Worksheet Date')
    description = fields.Text(string='Internal Notes', related='crm_lead_id.description')

    invoice_ids = fields.One2many('account.invoice', 'enquiry_id', string='Related Invoice(s)')
    customer_invoices = fields.One2many('account.invoice', 'enquiry_id', domain=[('type', '=', 'out_invoice')],
                                        string='Related Customer Invoice(s)')
    supplier_bills = fields.One2many('account.invoice', 'enquiry_id', domain=[('type', '=', 'in_invoice')],
                                     string='Related Supplier Bill(s)')

    sort_sl_no = fields.Boolean(string='Sort Remarks Report in String Format')
    customer_remark = fields.Html(string='')
    # qualification = fields.Html(string='')

    state = fields.Selection([
        ('pdf', 'PDF'),
        # ('draft', 'Draft'),
        ('enquiry', 'Enquiry'),
        ('sent', 'Enquiry Sent'),
        ('on_estimation', 'On Estimation'),
        ('sale_ready', 'Ready for Sale'),
        ('sale_quotation', 'Sale Ordered'),
        ('done', 'Done')], string='State',
        copy=False, default='pdf', readonly=True)

    product_lines = fields.One2many('enquiry.products.line', 'enquiry_id')
    enquiry_product_lines = fields.One2many('enquiry.products.line', 'enquiry_id')  # Dummy for Repeated View
    purchase_order_ids = fields.One2many('purchase.order', 'enquiry_id', domain=[('state', '!=', 'cancel')])  # TODO: Remove this field. Not usable

    rfq_count = fields.Integer(string='# of RFQs', compute='_compute_rfq_count', readonly=True)
    purchase_orders = fields.One2many('purchase.order', 'enquiry_id', string='Purchase Order', domain=[('state', '!=', 'cancel')])
    purchase_orders_dup = fields.One2many('purchase.order', 'enquiry_id', string='Purchase Order', domain=[('state', '!=', 'cancel')])
    purchase_order_lines = fields.One2many('purchase.order.line', 'enquiry_id', domain=[('state', '!=', 'cancel')])
    selected_purchase_order_lines = fields.One2many('purchase.order.line', 'enquiry_id', domain=[('selected_for_sale', '=', True)])

    selected_purchase_order = fields.Many2one('purchase.order', 'Selected Purchase Order')

    supplier_product_lines = fields.One2many('supplier.product.line', 'enquiry_id')
    supplier_closing_date = fields.Date('Supplier Closing Date')

    bid_comparison = fields.One2many('bid.comparison', 'enquiry_id', string='Bid Comparison')
    bid_html_group_supplier = fields.Boolean()
    bid_html = fields.Html(readonly=True, default='', compute='compute_bid_html')

    amount_untaxed = fields.Monetary(string='Total(VAT Excluded)', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='VAT', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total(VAT Included)', store=True, readonly=True, compute='_amount_all')
    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)

    sale_ids = fields.One2many('sale.order', 'enquiry_id', string='Related Sale Orders')
    sale_q_count = fields.Integer(compute='_compute_sale_count', store=True)

    pdf_file = fields.Binary('File')

    job_account = fields.Many2one('account.analytic.account', 'Job Account')

    enquiry_attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'enquiry.details')], string='Attachments')

    create_by = fields.Boolean()
    enquiry_line_id = fields.Many2one('enquiry.products.line', string='Product')
    supplier_id_list = fields.Many2many('res.partner', string='Supplier')

    enquiry_line_list = fields.Many2many('enquiry.products.line', string='Product')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    partner_final_destinations = fields.Many2many("res.partner.final.destinations", compute='get_partner_final_destinations')

    @api.depends('partner_id')
    def get_partner_final_destinations(self):
        if self.partner_id.final_destination_id.ids:
            self.partner_final_destinations = self.partner_id.final_destination_id.ids

    @api.depends('product_lines.price_subtotal', 'product_lines.currency_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.product_lines:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.vat.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                 product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('state', 'bid_html_group_supplier', 'purchase_order_lines')
    def compute_bid_html(self):
        for record in self:
            if record.state in ['on_estimation']:
                if record.bid_html_group_supplier:
                    bids = record.purchase_order_lines.sorted(lambda s: s.order_id.id)
                    template = 'hatta_trading.bid_details_supplier_wise'
                else:
                    bids = record.purchase_order_lines.sorted(lambda s: s.product_id.id)
                    template = 'hatta_trading.bid_details_product_wise'
                record.bid_html = self.env['ir.qweb'].render(template, {'bids': bids})

    @api.depends('product_lines.price_subtotal', 'product_lines.currency_id')
    def _amount_total(self):
        total = 0.0
        total += sum(sum.price_subtotal for sum in self.product_lines)
        self.amount_total = total

    @api.depends('purchase_order_ids')
    def _compute_rfq_count(self):
        for rec in self:
            rec.rfq_count = len(rec.purchase_order_ids)

    @api.depends('sale_ids')
    def _compute_sale_count(self):
        for rec in self:
            rec.sale_q_count = len(rec.sale_ids)

    @api.depends('amount_total')
    def get_amount_in_words(self):
        for payment in self:
            payment.amount_in_words = amount_to_text_ae(payment.amount_total)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_delivery_id': '',
                'partner_procure_id': '',
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'partner_delivery_id': addr['delivery'],
            'partner_procure_id': addr['invoice'],
        }
        self.update(values)
        self.end_user_id = self.partner_id
        self.contact_id = self.partner_id
        self.email_from = self.partner_id.email
        self.phone = self.partner_id.phone


    @api.multi
    def pdf_to_enquiry(self):
        if self.state == 'pdf':
            if self.enquiry_attachment_ids:
                self.state = 'enquiry'
            else:
                raise UserError("No PDF file Attached")

    @api.multi
    def skip_pdf(self):
        if self.state == 'pdf':
            self.state = 'enquiry'

    @api.model
    def create(self, vals):
        partner_obj = self.env['res.partner'].search([('id', '=', vals['partner_id'])])
        date = str(vals['date_deadline'])
        if partner_obj.partner_code:
            vals.update({
                'reference': self.env['ir.sequence'].next_by_code('hatta_enquiry_code')+"-"+date[2:7]+date[8:10]+partner_obj.partner_code,
            })
        else:
            vals.update({
                # 'reference': self.env['ir.sequence'].next_by_code('hatta_enquiry_code')+"-"+date[2:7]+date[8:10],
                'reference': self.env['ir.sequence'].next_by_code('hatta_enquiry_code')+"-"+date[2:5]+date[8:10]+date[5:7]
            })
        if not self.env.context.get('default_crm_lead_id') and not vals.get('crm_lead_id'):
            crm = self.env['crm.lead']
            partner = self.env['res.partner'].browse(vals['partner_id'])
            crm_vals = {
                'name': 'Enquiry %s by %s' % (vals.get('reference', 'Draft'), partner.name),
                'partner_id': partner.id,
                'user_id': vals.get('user_id'),
                'email_from': vals.get('email_from'),
                'phone': vals.get('phone'),
                'date_deadline': vals.get('date_deadline')
            }
            crm_lead_id = crm.create(crm_vals)
            vals.update({'crm_lead_id': crm_lead_id.id})

        return super(EnquiryDetails, self).create(vals)

    @api.multi
    def unlink(self):
        if all(x.state not in ['draft', 'sent', 'cost_received'] for x in self.purchase_orders):
            raise UserError('You cannot delete an enquiry having purchase orders!')
        else:
            for y in self.purchase_orders:
                y.unlink()
            return super(EnquiryDetails, self).unlink()


    # Create RFQ Wizard
    @api.multi
    def action_create_rfq(self):
        if not self.product_lines:
            raise UserError('Please Add Products First')
        else:
            return {
                'name': _('Create RFQ'),
                'type': 'ir.actions.act_window',
                'res_model': 'create.rfq',
                'view_id': self.env.ref('hatta_trading.hatta_create_rfq_view_form').id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_customer_id': self.partner_id.id,
                    'default_enquiry_date': self.creation_date,
                    'default_closing_date': self.date_deadline,
                    'default_reference': self.reference,
                    'default_enquiry_detail_id': self.id,
                    'default_enquiry_id': self.id,
                    'default_customer_rfq': self.customer_rfq,
                },
            }

    @api.onchange('create_by')
    def onchange_create_by(self):
        self.supplier_id = False
        self.enquiry_line_id = False

    @api.onchange('supplier_id', 'supplier_product_lines')
    def onchange_supplier_id(self):
        enquiry_line_list = [x.enquiry_line_id.id for x in self.supplier_product_lines
                             if x.supplier_id.id == self.supplier_id.id]
        return {
            'value': {
                'enquiry_line_list': enquiry_line_list
            }
        }

    @api.onchange('enquiry_line_id', 'supplier_product_lines')
    def onchange_enquiry_line_id(self):
        supplier_list = [x.supplier_id.id for x in self.supplier_product_lines if
                         x.enquiry_line_id.id == self.enquiry_line_id.id]
        return {
            'value': {
                'supplier_id_list': supplier_list
            }
        }

    @api.multi
    def add_by_supplier_product(self):
        res = {'type': 'ir.actions.ir_actions_act_window_no_close'}
        if self.create_by:
            self.add_batch_supplier_by_product()
        else:
            if self.enquiry_line_list and self.supplier_id:
                enquiry_line_list = []
                for line in self.enquiry_line_list:
                    if not self.supplier_product_lines.filtered(
                        lambda x: x.enquiry_line_id.id == line.id and
                                  x.supplier_id.id == self.supplier_id.id):
                        enquiry_line_list.append((0, 0, {
                            'enquiry_line_id': line.id,
                            'supplier_id': self.supplier_id.id,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom_id.id,
                            'product_qty': line.product_uom_qty,
                        }))
                if enquiry_line_list:
                    self.supplier_product_lines = enquiry_line_list
            supplier_product_lines_obj = self.supplier_product_lines.search(
                ['&', ('supplier_id', '=', self.supplier_id.id), ('enquiry_line_id', 'not in', self.enquiry_line_list.ids)])
            for x in supplier_product_lines_obj:
                x.unlink()
        return res

    @api.multi
    def add_batch_supplier_by_product(self):
        if self.enquiry_line_id and self.supplier_id_list:
            supplier_product_lines = []
            for supplier in self.supplier_id_list:
                if not self.supplier_product_lines.filtered(
                    lambda x: x.enquiry_line_id.id == self.enquiry_line_id.id and
                              x.supplier_id.id == supplier.id):
                    supplier_product_lines.append((0, 0, {
                        'enquiry_line_id': self.enquiry_line_id.id,
                        'supplier_id': supplier.id,
                        'product_id': self.enquiry_line_id.product_id.id,
                        'product_uom_id': self.enquiry_line_id.product_uom_id.id,
                        'product_qty': self.enquiry_line_id.product_uom_qty,
                    }))
            if supplier_product_lines:
                self.supplier_product_lines = supplier_product_lines
        supplier_product_lines_obj = self.supplier_product_lines.search(
            ['&', ('enquiry_line_id', '=', self.enquiry_line_id.id),
             ('supplier_id', 'not in', self.supplier_id_list.ids)])
        for x in supplier_product_lines_obj:
            x.unlink()

    def get_purchase_order_line_vals(self, line, order):
        return {
            'serial_no': line.enquiry_line_id.serial_no,
            'date_planned': fields.Datetime.now(),
            'vendor_closing_date': line.enquiry_line_id.supplier_closing_date,
            'order_id': order,
            'enquiry_supplier_product_line_id': line.id,
            'product_id': line.enquiry_line_id.product_id.id,
            'name': line.enquiry_line_id.name,
            'manufacturer_id': line.enquiry_line_id.manufacturer_id.manufacturer_id.id,
            'taxes_id': [(6, 0, line.enquiry_line_id.vat.ids)],
            'price_unit': 0.0,
            'product_qty': line.product_qty,
            'product_uom': line.enquiry_line_id.product_uom_id.id,
            'enquiry_line_id': line.enquiry_line_id.id,
            # 'certificate_ids': [(6, 0, line.enquiry_line_id.certificate_ids.ids)],
            'certificate_ids': [(0, 0, {
                'name': record.name,
                'code': record.code,
                'charge_id': record.charge_id.id,
                'note': record.note}) for record in line.enquiry_line_id.certificate_ids]
        }

    def get_purchase_order_vals(self, supplier):
        if supplier.property_purchase_currency_id:
            currency = supplier.property_purchase_currency_id.id
        elif supplier.parent_id.property_purchase_currency_id:
            currency = supplier.parent_id.property_purchase_currency_id.id
        else:
            currency = self.currency_id.id
        return {
            'date_planned': fields.Datetime.now(),
            'enquiry_id': self.id,
            'cost_center_id': self.cost_center_id.id,
            'message_follower_ids': [(4, 0, self.env.user.id)],
            'name': 'New',
            'vendor_closing_date': self.supplier_closing_date,
            'partner_id': supplier.id,
            'currency_id': currency
        }

    # Create RFQs for Product Suppliers
    def create_rfqs(self):
        purchase_order_o = self.env['purchase.order']
        purchase_order_line_o = self.env['purchase.order.line']
        rfqed_supplier_ids = self.purchase_order_ids.filtered(lambda s: s.state not in ('done')).mapped('partner_id.id')
        supplier_po_map = {}
        for supplier in self.supplier_product_lines.mapped('supplier_id'):
            if supplier.id in rfqed_supplier_ids:
                purchase_order = self.purchase_order_ids.filtered(lambda s: s.partner_id.id == supplier.id)
                if purchase_order.state in ['cost_received', 'sale_ready', 'to approve', 'purchase']:
                    purchase_order = purchase_order.new_revision(by_code=True)
            else:
                purchase_order = purchase_order_o.create(self.get_purchase_order_vals(supplier))
            supplier_po_map.update({supplier.id: purchase_order.id})
        for product_line in self.supplier_product_lines.filtered(lambda s: not s.purchase_order_line_id):
            po_line_vals = self.get_purchase_order_line_vals(product_line, supplier_po_map[product_line.supplier_id.id])
            product_line.purchase_order_line_id = purchase_order_line_o.create(po_line_vals)
        self.state = 'on_estimation'

    @api.multi
    def action_view_rfq(self):
        action = self.env.ref('hatta_trading.hatta_purchase_enquiry_rfq')
        result = action.read()[0]
        result['domain'] = [('enquiry_id', '=', self.id)]
        return result

    @api.multi
    def toggle_bid_html(self):
        self.bid_html_group_supplier ^= True

    @api.multi
    def action_wizard_rfq_selection(self):
        if not self.purchase_order_lines.filtered(lambda s: s.state == 'sale_ready'):
            raise UserError('No RFQ(s) has been reached "Ready for Sale" stage.\n'
                            'Only Ready for Sale RFQs can be included in Selection for preparing Sale Proposal.')
        return {
            'name': _("RFQ Line Selection for Sale"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('hatta_trading.wizard_rfq_selection_form_view').id,
            'view_type': 'form',
            'res_model': 'enquiry.details',
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def select_purchase_lines(self):
        pass

    @api.multi
    def action_send_enquiry(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('hatta_trading', 'email_template_edi_hatta_enquiry')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        self.state = 'sent'
        ctx = dict()
        ctx.update({
            'default_model': 'enquiry.details',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            # 'mark_so_as_sent': True,
            # 'custom_layout': "hatta_trading.mail_template_data_notification_email_enquiry"
        })
        return {
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
    def force_quotation_send(self):
        for order in self:
            email_act = order.action_quotation_send()
            if email_act and email_act.get('context'):
                email_ctx = email_act['context']
                email_ctx.update(default_email_from=order.company_id.email)
                order.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        self.state = 'sent'
        return True

    @api.multi
    def action_covering_letter(self):
        return {
            'name': _('Covering Letter'),
            'type': 'ir.actions.act_window',
            'res_model': 'covering.letter',
            'view_id': self.env.ref('hatta_trading.covering_letter_wizard_view_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_enquiry_id': self.id,
                'default_submission_date': self.date_deadline,
            },
        }

    @api.multi
    def confirm_and_sale_ready(self):
        # TODO: Do things to verify the Qty of Demand and Supplying
        self.state = 'sale_ready'
        for sale in self.sale_ids:
            order_lines = [(2, x.id,) for x in sale.order_line]
            order_lines += [(0, False, {
                'serial_no': x.serial_no,
                'product_id': x.product_id.id,
                'variant_ids': [(4, a.id) for a in x.variant_ids],
                'qualification': x.qualification,
                'justification': x.justification,
                'name': x.name,
                'product_uom': x.product_uom.id,
                'date_planned': fields.Datetime.now(),
                'product_qty': x.product_qty,
                'price_unit': x.sale_price_unit,
                'product_uom_qty': x.product_qty,
                'qty_invoiced': 0,
                'procurement_ids': [],
                'invoice_status': 'no',
                'qty_delivered_updateable': False,
            }) for x in self.selected_purchase_order_lines]
            sale.order_line = order_lines

    @api.multi
    def create_sale_order(self):
        vals = {}
        if self.state != 'sale_ready':
            raise UserError(_('Sale Price not Calculated.'))
        vals.update({
            'enquiry_id': self.id,
            'cost_center_id': self.cost_center_id.id,
            'partner_id': self.partner_id.id,
            'order_line': [(0, False, {
                'serial_no': x.serial_no,
                'product_id': x.product_id.id,
                'variant_ids': [(4, a.id) for a in x.variant_ids],
                'qualification': x.qualification,
                'justification': x.justification,
                'name': x.name,
                'product_uom': x.product_uom.id,
                'date_planned': fields.Datetime.now(),
                'product_qty': x.product_qty,
                'price_unit': x.sale_price_unit,
                'product_uom_qty': x.product_qty,
                'qty_invoiced': 0,
                'procurement_ids': [],
                'invoice_status': 'no',
                'qty_delivered_updateable': False,
            }) for x in self.selected_purchase_order_lines],
        })
        so_obj = self.env['sale.order'].create(vals)
        return {
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': so_obj.id
        }

    @api.multi
    def create_job_account(self):
        if not self.job_account:
            job_acc_obj = self.env['account.analytic.account'].create({
                # 'name': self.reference,
                'name': self.env['ir.sequence'].next_by_code('hatta_job_account'),
                'enquiry_id': self.id,
                'is_job_code': True
            })
            self.job_account = job_acc_obj.id

    @api.multi
    def action_view_sale_orders(self):
        return {
            'name': _("Sale Orders"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_ids.ids[0]
        }

    @api.multi
    def go_to_sale_order(self):
        return {
            'name': _("Sale Order"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_ids.ids[0],
            'target': 'current',
        }

    @api.multi
    def action_sale_quotation(self):
        self.state = 'sale_quotation'

    def _get_account(self, product, fpos, type):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type == 'sale':
            return accounts['income']
        return accounts['expense']

    @api.multi
    def create_sale_invoice_from_eq(self):
        if not self.partner_id:
            raise UserError(_("You must first select a partner!"))
        if self.partner_id.lang:
            self = self.with_context(lang=self.partner_id.lang)
        fpos = self.partner_id.property_account_position_id
        lines = []
        for line in self.product_lines:
            account = self._get_account(line.product_id, fpos, type='sale')
            line_vals = {
                         'sequence_no': line.serial_no or '',
                         'product_id': line.product_id and line.product_id.id,
                         'quantity': line.product_uom_qty or 1.00,
                         'uos_id': line.product_uom_id and line.product_uom_id.id or False,
                         'price_unit': line.price_unit or 0.00,
                         'name': line.name or '',
                         'account_id': account.id
                         }
            lines.append((0, 0, line_vals))
        return {
                'name': _("Sale Invoice"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_id': self.env.ref('account.invoice_form').id,
                'view_type': 'form',
                'res_model': 'account.invoice',
                'context': {
                    'default_payment_term': self.payment_term_id and self.payment_term_id.id or False,
                    'default_partner_id': self.partner_id and self.partner_id.id or False,
                    'default_parent_partner_id': self.partner_id and self.partner_id.id or False,
                    'default_cost_center_id': self.analytic_account_id and self.analytic_account_id.id or False,
                    'default_name': self.customer_rfq or '',
                    'default_invoice_line_ids': lines,
                    'default_type':'out_invoice',
                    'type':'out_invoice',
                    'journal_type': 'sale'
                }
            }


class EnquiryProductsLine(models.Model):
    _name = 'enquiry.products.line'
    _rec_name = 'name'
    _order = 'serial_no asc'

    @api.depends('pol_ids.selected_for_sale', 'pol_ids.product_qty')
    def get_supplying_qty(self):
        for line in self:
            qty = 0.0
            for pol in line.pol_ids.filtered(lambda s: s.selected_for_sale):
                qty += pol.product_qty
            line.supplying_qty = qty

    # @api.depends('enquiry_id.partner_id', 'product_id')
    # def get_partner_final_destinations(self):
    #     self.partner_final_destinations = self.enquiry_id.partner_id.final_destination_id.ids

    @api.onchange('enquiry_id.partner_id', 'product_id')
    def get_final_destination(self):
        if self.enquiry_id.partner_final_destinations:
            return {
                'value': {'final_destination': self.enquiry_id.partner_final_destinations.ids[0]},
                'domain': {'final_destination': [('id', 'in', self.enquiry_id.partner_final_destinations.ids)]},
            }
        else:
            return {
                'domain': {'final_destination': [('id', 'in', self.enquiry_id.partner_final_destinations.ids)]},
            }

        # if self.enquiry_id.partner_final_destinations:
        #     self.final_destination = self.enquiry_id.partner_final_destinations.ids[0]
        # else:
        #     self.final_destination = ''

    enquiry_id = fields.Many2one('enquiry.details', required=True, ondelete='cascade')
    # partner_final_destinations = fields.Many2many("res.partner.final.destinations", compute='get_partner_final_destinations')
    serial_no = fields.Char(string="Serial No")
    name = fields.Html(string='Description', required=1)
    default_code = fields.Char(string='Internal Reference')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    prod_temp_id = fields.Many2one(related='product_id.product_tmpl_id')
    product_uom_id = fields.Many2one('product.uom', string='UOM', required=True)
    product_uom_qty = fields.Float(string='Quantity', default=1.0, digits=dp.get_precision('Product Unit of Measure'),
                                   required=True)
    manufacturer_id = fields.Many2one('manufacturers.list', string='Manufacturer')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    cost_price = fields.Monetary('Unit Cost Price', readonly=True)
    price_unit = fields.Monetary('Unit Sale Price', compute='_get_price_unit', readonly=True)
    override_sale_price = fields.Float('Manual Sale Price')
    selected_pol_id = fields.Many2one('purchase.order.line', string='Selected Purchase Line',
                                      compute='_get_selected_pol_line')
    certificate_ids = fields.Many2many('product.certificate', string='Certificate(s) Required')
    vat = fields.Many2many("account.tax", string="VAT")
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    pol_ids = fields.One2many('purchase.order.line', 'enquiry_line_id', 'Purchase Line',
                              domain=[('is_revision', '!=', True)])
    principal_supplied = fields.Boolean(string='PS-able')
    supplier_product_lines = fields.One2many('supplier.product.line', 'enquiry_line_id', string='Suppliers')
    supplier_closing_date = fields.Date('Supplier Closing Date', required=True)

    supplying_qty = fields.Float(string='Supplying Quantity', digits=dp.get_precision('Product Unit of Measure'),
                                   compute='get_supplying_qty', store=True)
    final_destination = fields.Many2one("res.partner.final.destinations", string="Final Destination")

    @api.depends('product_uom_qty', 'cost_price', 'price_unit', 'vat', 'override_sale_price', 'selected_pol_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit
            taxes = line.vat.compute_all(price, line.enquiry_id.currency_id, line.product_uom_qty,
                                         product=line.product_id, partner=line.enquiry_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.price_unit * record.product_uom_qty

    @api.onchange('selected_pol_id')
    @api.depends('override_sale_price', 'selected_pol_id')
    def _get_price_unit(self):
        for line in self:
            price = 0.00
            if line.override_sale_price > 0.00:
                price = line.override_sale_price or 0.00
            else:
                if line.selected_pol_id:
                    price = line.selected_pol_id.sale_price_lc or 0.00
            line.update({'price_unit': price, })

    @api.onchange('product_uom_qty')
    def onchange_qty(self):
        if self.product_uom_qty and self.product_uom_qty > 0.0:
            for spl in self.supplier_product_lines:
                spl.product_qty = self.product_uom_qty

    @api.onchange('product_id', 'principal_supplied', 'manufacturer_id')
    def onchange_product_id(self):
        res_value = {}
        res_domain = {'supplier_ids': [('supplier', '=', True)]}
        if self.product_id:
            res_value.update({
                # 'manufacturer_id': self.product_id.manufacturer_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'vat': self.product_id.taxes_id.ids,
                'default_code': self.product_id.default_code,
                'principal_supplied': self.product_id.is_principal_suppliable,
                'supplier_product_lines': [(5, 0, 0)]
            })
            if self.product_id and self.principal_supplied:
                for supplier in self.product_id.principal_supplier_ids:
                    res_value['supplier_product_lines'].append((0, 0, {
                        'enquiry_line_id': self.id,
                        'supplier_id': supplier.partner_id.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_id.uom_id.id,
                        'product_qty': self.product_uom_qty
                    }))
            elif self.manufacturer_id:
                for seller in self.manufacturer_id.vendor_ids:
                    res_value['supplier_product_lines'].append((0, 0, {
                        'enquiry_line_id': self.id,
                        'supplier_id': seller.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_id.uom_id.id,
                        'product_qty': self.product_uom_qty
                    }))
            res_value.update({'name': self.product_id.name})
            if self.product_id.description:
                res_value['name'] += '\n' + self.product_id.description
            if self.product_id.is_principal_suppliable:
                res_domain['supplier_ids'].append(('is_principal_supplier', '=', True))
        return {'value': res_value, 'domain': res_domain}

    @api.multi
    def _get_selected_pol_line(self):
        res = {}
        for lead_line in self:
            result = False
            has = False
            overide = False
            for line in lead_line.pol_ids:
                if line.order_id.state != 'cancel':
                    result = line.id
                    # if has and not overide:
                    #     result = False
                    has = True
                lead_line.update({
                    'selected_pol_id': result,
                })

    @api.multi
    def view_history(self):
        ctx = {
                'default_product_id': self.product_id.id,
              }
        return {
            'name': _('Product History'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.wizard',
            'view_id': self.env.ref('hatta_trading.hatta_product_history_view_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }


class SupplierProductLines(models.Model):
    _name = 'supplier.product.line'

    # _sql_constraints = [
    #     ('supplier_product_line_unique', 'unique(enquiry_line_id, supplier_id)',
    #      'Supplier - Product Combination Duplicated. Please Check it.')
    # ]

    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Related RFQ Line')
    po_line_reference = fields.Char(compute='compute_po_line_ref', string='Related RFQ Line ')

    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry', compute='get_enquiry', store=True, ondelete='cascade')
    enquiry_line_id = fields.Many2one('enquiry.products.line', string='Enquiry Line', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    product_qty = fields.Float('Quantity', required=True)
    product_uom_id = fields.Many2one('product.uom', string='UOM', required=True)
    enquiry_create_rfq_temp = fields.Integer()  # For Linking this in Create RFQ Wizard More Section

    @api.depends('purchase_order_line_id')
    def compute_po_line_ref(self):
        for line in self:
            line.po_line_reference = '[%s] %s' % (line.purchase_order_line_id.order_id.name, line.purchase_order_line_id.product_id.name)

    @api.depends('enquiry_line_id')
    def get_enquiry(self):
        for line in self:
            line.enquiry_id = line.enquiry_line_id.enquiry_id

    @api.onchange('enquiry_line_id')
    def onchange_enquiry_id(self):
        if self.enquiry_id:
            return {'value': {
                'product_id': self.enquiry_line_id.product_id.id,
                'product_uom_id': self.enquiry_line_id.product_uom_id.id,
                'product_qty': self.enquiry_line_id.product_uom_qty
            }}
        return {}

    @api.onchange('product_id')
    def set_domain_supplier(self):
        domain = [('supplier', '=', True)]
        if self.product_id and self.product_id.is_principal_suppliable:
            domain = [('id', 'in', self.product_id.principal_supplier_ids.mapped('partner_id').ids)]
        return {'domain': {'supplier_id': domain}}


class ProductCertificates(models.Model):
    _name = 'product.certificate'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    charge_id = fields.Many2one('costsheet.line.charge', 'Charge')
    note = fields.Text(string='Note')
    # selected = fields.Boolean(string='Selected')


class QuotationStatus(models.Model):
    _name = 'quotation.status'
    _rec_name = 'submission_date'

    submission_date = fields.Date(string="Submission Date")
    user_id = fields.Many2one('res.users', string="Created User", default=lambda self : self.env.user)
    line_ids = fields.One2many('quotation.status.line', 'quotation_status', string="Quotation Satatus Line")
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed')], string='State',
        copy=False, default='open', readonly=True)
    tb_count = fields.Integer(string="T.B Quote Submission")
    email_count = fields.Integer(string="Email Quote Submission")
    late_count = fields.Integer(string="Late Quote Submission")
    regret_count = fields.Integer(string="Regret Quote Submission")
    revised_count = fields.Integer(string="Revised Quote Submission")
    online_count = fields.Integer(string="Online Quote Submission")
    other_count = fields.Integer(string="Other Quote Submission")

    @api.onchange('line_ids')
    def get_status_count(self):
        tb = email = late_quote = regret = revised = online = other = 0
        if self.line_ids:
            for line in self.line_ids:
                if line.sb_type == 'tb':
                    tb = tb + 1
                if line.sb_type == 'email':
                    email = email + 1
                if line.sb_type == 'late_quote':
                    late_quote = late_quote + 1
                if line.sb_type == 'regret':
                    regret = regret + 1
                if line.sb_type == 'revised':
                    revised = revised + 1
                if line.sb_type == 'online':
                    online = online + 1
                if line.sb_type == 'other':
                    other = other + 1
                else:
                    pass
        self.tb_count = tb
        self.email_count = email
        self.late_count = late_quote
        self.regret_count = regret
        self.revised_count = revised
        self.online_count = online
        self.other_count = other

    @api.multi
    def get_quote_status(self):
        if self.submission_date and self.state == 'open':
            enquiry_obj = self.env['enquiry.details'].search([('date_deadline', '=', self.submission_date)])
            self.line_ids.unlink()
            self.line_ids = [(0, 0, {
                'quotation_status': self.id,
                'received_date': enquiry.creation_date,
                'ref_no': enquiry.reference,
                'client_ref_no': enquiry.customer_rfq,
                'client_name': enquiry.partner_id.id,
                'closing_date': self.submission_date,
                'enquiry_id': enquiry.id,
                # 'sb_type': [(6, 0, line.vat.ids)],
                # 'remark': 0.0,
            }) for enquiry in enquiry_obj]

    @api.multi
    def unpost_quote_status(self):
        self.state = 'open'

    @api.multi
    def submit_quote_status(self):
        self.state = 'closed'


class QuotationStatusLine(models.Model):
    _name = 'quotation.status.line'

    quotation_status = fields.Many2one('quotation.status')
    received_date = fields.Date(string="Received Date")
    ref_no = fields.Char(string="Our Ref No.")
    client_ref_no = fields.Char(string="Client Ref No.")
    client_name = fields.Many2one('res.partner', string="Client Name")
    closing_date = fields.Date(string="Closing Date")
    sb_type = fields.Selection([('tb', 'T.B'), ('email', 'Email'), ('late_quote', 'Late Quote'), ('regret', 'Regret'),
                                ('revised', 'Revised Bid'), ('online', 'Online'), ('other', 'Other')], string="SB Type")
    remark = fields.Char(string="Remark")
    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry')
