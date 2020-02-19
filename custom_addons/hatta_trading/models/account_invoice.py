from odoo import api, fields, models, _
from odoo.tools import english_number
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools import english_number
from odoo.addons.hatta_trading.tools import amount_to_text_en


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


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    enquiry_id = fields.Many2one('enquiry.details')
    job_account = fields.Many2one('account.analytic.account', related='enquiry_id.job_account',
                                  string='Job Account', store=True)

    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center',
                                     domain=[('tag_type', '=', 'cost_center')])

    self_billing_number = fields.Boolean(string='Self Billing Number')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    credit_debit_amount = fields.Float('Amount')
    credit_debit_account = fields.Many2one('account.account', string='Account')
    credit_debit_type = fields.Selection(string="Type", selection=[('credit', 'Credit'),
                                                                   ('debit', 'Debit'), ])
    credit_debit_narration = fields.Char('Narration')
    credit_debit_tax_ids = fields.Many2many('account.tax', string='Taxes',
                                            domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                                    ('active', '=', True)], oldname='invoice_line_tax_id')
    is_shipping_invoice = fields.Boolean('Shipping Invoice')
    shipping_quotations = fields.Many2many('shipping.quotation', string='Shipping Quotations')
    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)
    exchange_rate = fields.Float(string='Exchange Rate (Local to CC)',
                                 digits=dp.get_precision('Exchange Rate Accuracy'),
                                 related='currency_id.rate', store=True)
    is_same_currency = fields.Boolean(compute='check_is_same_currency', store=True)

    @api.model
    def create(self, vals):
        if vals['origin']:
            vals['sale_order_id'] = self.env['sale.order'].search([('name', '=', vals['origin'])], limit=1).id
        return super(AccountInvoice, self).create(vals)


    @api.depends('company_id', 'currency_id')
    def check_is_same_currency(self):
        for inv in self:
            inv.is_same_currency = inv.company_id.currency_id.id == inv.currency_id.id

    @api.model
    def set_exchange_rate(self, currency_id, rate):
        rcr = self.env['res.currency.rate']
        date = fields.Date.today()
        company_id = self._context.get('company_id') or self.env['res.users']._get_company().id
        # the subquery selects the last rate before 'date' for the given currency/company
        domain = [
            ('currency_id', '=', currency_id),
            ('name', '=', date),
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
        ]
        rate_id = rcr.search(domain, order='company_id, name DESC', limit=1)
        if rate_id:
            rate_id.write({'rate': rate})
        else:
            rcr.create({'rate': rate, 'currency_id': currency_id})
        return True

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _(
                    'Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id,
                                                                                      delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = account_id
        self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}
        if type in ('out_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    def _prepare_invoice_line_from_po_line(self, line):
        res = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        if line.enquiry_id:
            res.update({'account_analytic_id': line.enquiry_id.job_account.id,
                        'serial_no': line.serial_no})
        return res

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        account_invoice_o = self.env['account.invoice']
        product_o = self.env['product.product']
        for line in res:
            invoice = account_invoice_o.browse(line['invoice_id'])
            if invoice.cost_center_id:
                line['analytic_tag_ids'].append((4, invoice.cost_center_id.id, None))
            product = product_o.browse(line['product_id'])
            if product.analytic_operation_type:
                for tag in product.analytic_tags:
                    line['analytic_tag_ids'].append((4, tag.id, None))
            # TODO: Clear below line after seting, tag many2many field in product.template
            else:
                line['analytic_tag_ids'].append((4, self.env.ref('hatta_trading.analytic_tag_nps').id, None))
        return res

    @api.onchange('shipping_quotations')
    def onchange_shipping_quotations(self):
        if self.is_shipping_invoice:
            lines = [(0, 0, {
                'name': '%s Courier charges for %s' % (x.carrier_id.name, x.purchase_order_id.name),
                'account_id': x.account_id.id,
                'quantity': 1,
                'price_unit': x.total,
                'account_analytic_id': x.job_id.id,
                'analytic_tag_ids': [(4, x.cost_center_id.id)] if x.cost_center_id else [],
                'shipping_quotation_id': x.id
            }) for x in self.shipping_quotations]
            return {
                'value': {
                    'invoice_line_ids': lines
                }
            }

    @api.onchange('credit_debit_amount', 'credit_debit_account', 'credit_debit_narration', 'credit_debit_tax_ids')
    def onchange_amount_account(self):
        if self.credit_debit_account and self.credit_debit_amount and self.credit_debit_narration:
            invoice_line_ids = [(0, 0, {
                'name': self.credit_debit_narration,
                'account_id': self.credit_debit_account.id,
                'price_unit': self.credit_debit_amount,
                'quantity': 1,
                'invoice_line_tax_ids': self.credit_debit_tax_ids,
            })]
            return {
                'value': {
                    'invoice_line_ids': invoice_line_ids
                }
            }

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        if self.credit_debit_type:
            for line in move_lines:
                line[2]['credit'], line[2]['debit'] = line[2]['debit'], line[2]['credit']
        for items in move_lines:
            account_obj = self.env['account.account'].browse(items[2]['account_id'])
            if account_obj.user_type_id.type in ['receivable', 'payable']:
                inv_obj = self.env['account.invoice'].browse(items[2]['invoice_id'])
                if inv_obj.cost_center_id.id:
                    if items[2]['analytic_tag_ids']:
                        items[2]['analytic_tag_ids'].append((4, inv_obj.cost_center_id.id))
                    else:
                        items[2]['analytic_tag_ids'] = [(4, inv_obj.cost_center_id.id)]

        return move_lines

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        if self:
            for rec in self:
                if rec.is_shipping_invoice:
                    quotations = [x.id for x in rec.shipping_quotations]
                    quotation_obj = self.env['shipping.quotation'].search([('id', 'in', quotations)])
                    if quotation_obj:
                        for x in quotation_obj:
                            x.action_done()
        return res


    @api.depends('amount_total_signed')
    def get_amount_in_words(self):
        for inv in self:
            if inv.currency_id.name == 'AED':
                inv.amount_in_words = amount_to_text_ae(inv.amount_total_signed)
            elif inv.currency_id.name == 'EUR':
                inv.amount_in_words = amount_to_text_en.amount_to_text(inv.amount_total_signed, lang='en',
                                                                       currency='euro',
                                                                       sub='cent')
            else:
                inv.amount_in_words = amount_to_text_en.amount_to_text(inv.amount_total_signed, lang='en',
                                                                       currency=inv.currency_id.unit_name or 'euro',
                                                                       sub=inv.currency_id.sub_unit_name or 'cent'
                                                                       )


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    enquiry_id = fields.Many2one('enquiry.details', related='invoice_id.enquiry_id', store=True)
    serial_no = fields.Char(string='Sl.No')
    line_tax_amount = fields.Float(compute='_compute_tax_line_price', string='VAT Amount')
    total_excluded_amount = fields.Float(compute='_compute_tax_line_price', string="Total excluded", store=True)
    total_included_amount = fields.Float(compute='_compute_tax_line_price', string="Total Included", store=True)
    shipping_quotation_id = fields.Many2one('shipping.quotation')
    name = fields.Html(
        'Description', translate=True, required=True,
        help="A precise description of the Product, used only for internal information purposes.")


    @api.model
    def create(self, vals):
        if self.env.context.get('active_model') == 'sale.order':
            order = self.env['sale.order'].browse(self.env.context.get('active_id'))
            if order.enquiry_id:
                vals.update({
                    'account_analytic_id': order.enquiry_id.job_account.id,
                    'analytic_tag_ids': [(4, order.cost_center_id.id)] if order.cost_center_id else []
                })
        return super(AccountInvoiceLine, self).create(vals)

    @api.depends('invoice_line_tax_ids', 'price_unit')
    def _compute_tax_line_price(self):
        for record in self:
            currency = record.invoice_id and record.invoice_id.currency_id or None
            price = record.price_unit * (1 - (record.discount or 0.0) / 100.0)
            taxes = False
            tax_amount = 0.0
            if record.invoice_line_tax_ids:
                taxes = record.invoice_line_tax_ids.compute_all(price, currency, record.quantity,
                                                                product=record.product_id,
                                                                partner=record.invoice_id.partner_id)
                record.tax_id_for_report = record.invoice_line_tax_ids.ids[0]
            if taxes:
                for item in taxes['taxes']:
                    tax_amount += item['amount']
                record.total_excluded_amount = taxes['total_excluded']
                record.total_included_amount = taxes['total_included']
            record.line_tax_amount = tax_amount


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    manager_id = fields.Many2one('res.users', string='Account Manager')
    default = fields.Boolean(string='Default')
    send_quote_mail = fields.Boolean(string='Send Quote By Email')
    register_payment_invoice = fields.Boolean(string='Register Payment from Invoice')
    consider_quotation_status_report = fields.Boolean(string='Consider In Quotation Status Report')
    type = fields.Selection(selection=[('view', 'Analytic View'), ('normal', 'Analytic Account'),
                                       ('contract', 'Contract/Project'), ('template', 'Template of Contract')],
                            default='normal', string="Account Type")
    parent_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    liquid_damage_note = fields.Text(string='Liquidated Damages Note')
