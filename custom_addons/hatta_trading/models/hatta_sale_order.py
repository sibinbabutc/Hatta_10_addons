# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import english_number, amount_to_text_en


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


class HattaSaleOrder(models.Model):
    _inherit = 'sale.order'

    _sql_constraints = [
        ('unique_sale_order_from_enquiry', 'unique(enquiry_id)',
         'You have already created a Sale Order for this Enquiry. Either Use it or Revise it.')
    ]
    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry No')
    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center')
    job_account = fields.Many2one('account.analytic.account', 'Job Account', related='enquiry_id.job_account')
    client_order_reference = fields.Char(string='Customer PO', related='enquiry_id.customer_rfq')

    # confirm_date = fields.Datetime(string='Confirm Date')
    delivery_date = fields.Date(string='Delivery Date')
    quotation_validity = fields.Char(string='Quotation Validity(Days)')
    sale_history_id = fields.Many2one('product.wizard')

    shop_location = fields.Selection(string="Location", selection=[('1', 'Hatta AUH')], default='1')
    delivery_term = fields.Char(string='Delivery Terms')

    revision_reason = fields.Many2one('revision.reason', string='Revision Reason')
    current_revision_id = fields.Many2one('sale.order', string='Current revision', readonly=True)
    old_revision_ids = fields.One2many(comodel_name='sale.order', inverse_name='current_revision_id',
                                       string='Old revisions',
                                       readonly=True, context={'active_test': False}, )
    revision_number = fields.Integer(string='Revision', copy=False, default=0)
    unrevisioned_name = fields.Char(string='Order Reference', copy=False, readonly=True)
    is_revision = fields.Boolean(string='Revision')
    is_sale_done = fields.Boolean(compute='_compute_sale_done')

    def _compute_sale_done(self):
        for record in self:
            if record.invoice_status == 'invoiced':
                if record.order_line.filtered(lambda s: s.qty_delivered == s.product_uom_qty):
                    record.enquiry_id.purchase_order_ids.button_done()
                    record.enquiry_id.write({'state': 'done'})
                    record.is_sale_done = True
            else:
                record.is_sale_done = False

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('on_revision', 'On Revision'),
        ('revision_sent', 'Revision Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    amount_total = fields.Monetary(string='Total(VAT Included)', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    active = fields.Boolean(string='Active', default=True)

    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})
        self.filtered(lambda s: s.state == 'on_revision').write({'state': 'revision_sent'})
        return self.env['report'].get_action(self, 'hatta_trading.hatta_sale_order_report')

    @api.multi
    def action_on_revision(self):
        self.state = 'on_revision'

    @api.multi
    def action_sale_revision(self):
        return {
            'name': 'Revision Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.revision',
            'view_id': self.env.ref('hatta_trading.sale_order_revision_view_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_reference': self.id,
            },
        }

    @api.model
    def create(self, values):
        if values['enquiry_id']:
            enquiry_obj = self.env['enquiry.details'].browse(values['enquiry_id'])
            enquiry_obj.create_job_account()
        po = super(HattaSaleOrder, self).create(values)
        if not po.is_revision:
            po.write({
                'unrevisioned_name': po.name
            })
        return po

    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)

    @api.depends('amount_total')
    def get_amount_in_words(self):
        for payment in self:
            if payment.currency_id.name == 'AED':
                payment.amount_in_words = amount_to_text_ae(payment.amount_total)
            elif payment.currency_id.name == 'EUR':
                payment.amount_in_words = amount_to_text_en.amount_to_text(payment.amount_total, lang='en', currency='euro')
            else:
                payment.amount_in_words = amount_to_text_en.amount_to_text(payment.amount_total, lang='en', currency='')

    @api.multi
    def new_revision(self, vals):
        self.ensure_one()
        self.is_revision = True
        revno = self.revision_number
        today = fields.Date.from_string(fields.Date.today())
        defaults = {
            'name': '%s-Rev/%s/%s/%s/%s' % (self.unrevisioned_name, today.day, today.month, today.year, str(revno + 1)),
            'revision_number': revno + 1,
            'state': 'draft',
            # 'old_revision_ids': (self.old_revision_ids | self).ids,
            'unrevisioned_name': self.unrevisioned_name,
        }
        revised = super(HattaSaleOrder, self).copy(default=defaults)
        self.write({
            # 'name': self.name,
            'active': False,
            'state': 'cancel',
            'revision_reason': vals['revision_reason'],
            'current_revision_id': revised.id
        })
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_id': self.env.ref('sale.view_order_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': revised.id
        }

    @api.multi
    def action_confirm(self):
        if not self.enquiry_id:
            return super(HattaSaleOrder, self).action_confirm()
        for p_order in self.enquiry_id.purchase_orders:
            selected_lines = [x.selected_for_sale for x in p_order.order_line]
            if all(selected_lines):
                p_order.button_confirm()
            elif any(selected_lines):
                revised = p_order.new_revision(by_code=True)
                revised.order_line.filtered(lambda s: (not s.selected_for_sale)).unlink()
                revised.button_confirm()
            else:
                p_order.button_cancel()
            self.enquiry_id.state = 'sale_quotation'
        for line in self.order_line:
            if line.variant_ids and not line.selected_variant:
                if len(line.variant_ids) == 1:
                    line.selected_variant = line.variant_ids
                else:
                    raise ValidationError('Please select a variant for %s' % line.product_id.name)
        return super(HattaSaleOrder, self).action_confirm()

    @api.multi
    def _prepare_invoice(self):
        res = super(HattaSaleOrder, self)._prepare_invoice()
        if self.enquiry_id:
            res.update({'enquiry_id': self.enquiry_id.id})
        return res


class HattaSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _order = 'serial_no asc'

    serial_no = fields.Char(string="Serial No")
    name = fields.Html(string='Description', required=True)
    line_tax_amount = fields.Float(compute='_compute_tax_line_price', string='VAT Amount')
    variant_ids = fields.One2many('variants.line', 'sol_id')
    selected_variant = fields.Many2one('variants.line', string='Selected Variant')

    qualification = fields.Text('Qualification')
    justification = fields.Text('Justification')

    @api.multi
    def view_sale_order(self):
        return {
            'res_id': self.order_id.id,
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_id': self.env.ref('sale.view_order_form').id
        }

    @api.depends('tax_id', 'price_unit')
    def _compute_tax_line_price(self):
        for record in self:
            currency = record.order_id and record.order_id.currency_id or None
            price = record.price_unit * (1 - (record.discount or 0.0) / 100.0)
            taxes = False
            tax_amount = 0.0
            if record.tax_id:
                taxes = record.tax_id.compute_all(price, currency, record.product_uom_qty, product=record.product_id,
                                                  partner=record.order_id.partner_id)
            if taxes:
                for item in taxes['taxes']:
                    tax_amount += item['amount']
            record.line_tax_amount = tax_amount

    @api.multi
    def open_product_variants(self):
        return {
            'name': _("Product Variants"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'view_id': self.env.ref('hatta_trading.sale_order_line_variants_form_view').id,
            'res_model': 'sale.order.line',
            'target': 'new',
        }

    @api.onchange('selected_variant')
    def onchange_selected_variant(self):
        if self.selected_variant:
            pol_obj = self.env['purchase.order.line'].browse(self.selected_variant.pol_id.id)
            pol_obj.write({
                'selected_variant': self.selected_variant.id
            })

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(HattaSaleOrderLine, self)._prepare_invoice_line(qty)
        res.update({'serial_no': self.serial_no, })
        return res


class HattaMailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get(
                'default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state == 'draft':
                # order.enquiry_id.selected_purchase_order.sale_order_state = 'sent'
                order.state = 'sent'
            elif order.state == 'on_revision':
                order.state = 'revision_sent'
            # order.enquiry_id.selected_purchase_order.write({
            #     'state': 'sent_to_customer'
            # })
            self = self.with_context(mail_post_autofollow=True)
        return super(HattaMailComposeMessage, self).send_mail(auto_commit=auto_commit)


class VariantsLine(models.Model):
    _name = 'variants.line'
    _rec_name = 'name'

    name = fields.Char('Variant Name')
    description = fields.Char('Variant Description')
    sol_id = fields.Many2one('sale.order.line')
    pol_id = fields.Many2one('purchase.order.line')
    selected_variant = fields.Boolean('Select')

    @api.constrains('selected_variant')
    def check_selected_variant(self):
        variants = self.env['variants.line'].search(['|', ('pol_id', '=', self.pol_id.id),
                                                     ('sol_id', '=', self.sol_id.id)])
        for variant in variants:
            if variant.id != self.id and variant.selected_variant:
                raise UserError('You can select only one variant for a product')
