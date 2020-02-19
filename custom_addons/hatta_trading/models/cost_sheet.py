from odoo import api, fields, models, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class HattaCostSheet(models.Model):
    _name = 'hatta.cost.sheet'

    _sql_constraints = [
        ('purchase_order_cost_sheet_unique', 'unique(purchase_order_id)',
         'You have already created a Cost Sheet for this Purchase Order. Please Use it.')
    ]

    @api.depends('cost_sheet_currency_id', 'currency_id')
    def check_is_same_currency(self):
        for sheet in self:
            sheet.is_same_currency = sheet.cost_sheet_currency_id.id == sheet.currency_id.id
            sheet.exchange_rate_label = '(%s to %s)' % (sheet.currency_id.name, sheet.cost_sheet_currency_id.name)
            sheet.exchange_rate_view_label = '%s to %s' % (sheet.cost_sheet_currency_id.name, sheet.currency_id.name)

    @api.depends('purchase_order_id.name')
    def compute_name(self):
        for sheet in self:
            sheet.name = 'CS-%s' % sheet.purchase_order_id.name

    @api.depends('cost_line_equipment_ids.amount_lc')
    def _get_total_equipment_costs(self, total=0.0):
        for sheet in self:
            for line in sheet.cost_line_equipment_ids:
                total += line.amount_lc
            sheet.total_equipment_cost = total

    @api.depends('cost_line_expense_ids.amount_lc')
    def _get_total_expenses(self, total=0.0):
        for sheet in self:
            for line in sheet.cost_line_expense_ids:
                total += line.amount_lc
            sheet.total_expenses = total

    @api.depends('cost_line_equipment_ids', 'cost_line_expense_ids', 'cost_line_expense_ids.amount_lc',
                 'cost_line_equipment_ids.charge_type', 'exchange_rate')
    def get_cost_all(self):
        qweb = self.env['ir.qweb']
        for order in self:
            costs = order.compute_all_costs()
            order.amount_total = costs.get('total_cost_lc', 0.0)
            order.equipment_cost_html = qweb.render('hatta_trading.cost_sheet_equipment_cost_details', costs)

    # Adding 30 Days to Delivery Weeks
    @api.depends('delivery_weeks')
    def _get_delivery_days(self):
        for order in self:
            order.delivery_days = (order.delivery_weeks * 7) + 45 if order.delivery_weeks else 45

    @api.depends('cost_lines.split_method')
    def compute_landed_cost_lines(self):
        for sheet in self:
            if sheet.state not in ['approve', 'submitted']:
                continue
            sheet_landed_cost_lines = [(5,)]
            for order_line in sheet.purchase_order_id.order_line:
                for cost_line in sheet.cost_lines:
                    additional_landed_cost = cost_line.amount_lc
                    sheet_landed_cost_lines.append((0, 0, {
                        'purchase_order_line': order_line.id,
                        'cost_sheet_id': sheet.id,
                        'cost_sheet_line_id': cost_line.id,
                        'additional_landed_cost': additional_landed_cost
                    }))
            sheet.sheet_landed_cost_lines = sheet_landed_cost_lines

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True, ondelete='restrict')

    name = fields.Char(string='Reference', compute='compute_name', store=True)
    cost_sheet_currency_id = fields.Many2one(related='purchase_order_id.currency_id', string='Cost Sheet Currency',
                                             required=True, store=True)
    currency_id = fields.Many2one('res.currency', string='Local Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    is_same_currency = fields.Boolean(compute='check_is_same_currency', store=True)
    exchange_rate = fields.Float(string='Exchange Rate (Local to CS)',
                                 digits=dp.get_precision('Exchange Rate Accuracy'),
                                 related='cost_sheet_currency_id.rate', store=True)
    exchange_rate_label = fields.Char('', compute='check_is_same_currency', store=True)
    exchange_rate_view = fields.Float(string='Exchange Rate (CS to Local)',
                                      digits=dp.get_precision('Exchange Rate Accuracy'),
                                      compute='get_inverse_exchange_rate', store=True)
    exchange_rate_view_label = fields.Char('', compute='check_is_same_currency', store=True)
    shipping_method_id = fields.Many2one('hatta.shipment.method', string='Shipping Method')
    is_duty_required = fields.Boolean('Duty Exemption ?')
    collect_delivery_type = fields.Selection([('collected_by_hatta', 'Collected by Hatta'),
                                              ('delivered_by_vendor', 'Delivered by Vendor')], string='Delivery Method')
    revision_date = fields.Date(string='Date of Revision')

    total_equipment_cost = fields.Monetary('Equipment Cost', compute='_get_total_equipment_costs', readonly=True,
                                           store=True, digits=dp.get_precision('Cost Sheet'))
    total_expenses = fields.Monetary('Expenses', compute='_get_total_expenses', readonly=True, store=True,
                                     digits=dp.get_precision('Cost Sheet'))

    margin = fields.Float(string='Margin')

    total_cost = fields.Float('Total Cost', readonly=True)
    total_cost_lc = fields.Float('Total Cost LC', compute='compute_total_cost_lc')

    amount_total = fields.Monetary(string='Total Amount')

    state = fields.Selection([('draft', 'Draft'), ('margin_update', 'Margin Updated'),
                              ('approve', 'Approved'), ('submitted', 'Submitted')], string='State',
                             copy=False, default='draft', readonly=True)

    cost_lines = fields.One2many('cost.sheet.line', 'cost_sheet_id')
    cost_line_equipment_ids = fields.One2many('cost.sheet.line', 'cost_sheet_id',
                                              domain=[('cost_type', '=', 'equipment_cost')])
    cost_line_expense_ids = fields.One2many('cost.sheet.line', 'cost_sheet_id', domain=[('cost_type', '=', 'expense')])

    sheet_landed_cost_lines = fields.One2many('pol.landed.cost.line', 'cost_sheet_id', string='Landed Cost Adjustments',
                                              compute='compute_landed_cost_lines')

    equipment_cost_html = fields.Html(readonly=True, compute='get_cost_all')

    interest_rate = fields.Float(string='Interest', related='shipping_method_id.bank_interest')
    bank_interest = fields.Monetary(string='Bank Interest', currency_field='cost_sheet_currency_id',
                                    compute='_get_interest')
    bank_interest_calculated = fields.Boolean(string='Bank Interest Calculated')
    # field only for triggering compute
    bank_interest_computed = fields.Float(compute='compute_bank_interest', store=True)
    customs_interest_computed = fields.Float(compute='compute_customs_duty', store=True)

    custom_duty_rate = fields.Float(string='Custom Duty Rate', related='shipping_method_id.customs_duty')
    customs_duty = fields.Monetary(string='Customs Duty', currency_field='cost_sheet_currency_id')
    customs_duty_calculated = fields.Boolean(string='Customs Duty Calculated')
    real_customs_duty = fields.Float('Customs Duty')

    # Shipment Charge Details
    weight = fields.Char(string='Weight')
    volume = fields.Char(string='Volume')
    dimension = fields.Char(string='Dimension')
    zone = fields.Char(string='Zone')
    cost_sheet_notes = fields.Text(string='Notes')
    factor = fields.Float(string='Factor')

    shipping_ids = fields.One2many('shipping.quotation', 'cost_sheet_id')
    bank_interest_line = fields.One2many('bank.interest.line', 'cost_sheet_id')
    delivery_weeks = fields.Integer(string='Delivery Weeks', related='purchase_order_id.delivery_weeks')
    delivery_days = fields.Integer(string='Delivery Days', compute='_get_delivery_days')
    prepared_by = fields.Many2one('res.users', string='Prepared By', default=lambda s: s.env.user.id)
    checked_by = fields.Many2one('res.users', string='Checked By')


    @api.onchange('shipping_method_id')
    def onchange_shipping_method(self):
        self.bank_interest_calculated = False
        self.customs_duty_calculated = False
        bank_interest_line = self.bank_interest_line
        if self.shipping_method_id:
            expense_line = [(0, False, {
                'cost_type': 'expense',
                'line_charge_id': x.name.id,
                'split_method': x.name.split_method_default,
                'amount_lc': x.amount,
            }) for x in self.shipping_method_id.shipment_method_line]
            if self.shipping_method_id.bank_interest_charge:
                expense_line.append((0, False, {
                    'cost_type': 'expense',
                    'line_charge_id': self.shipping_method_id.bank_interest_charge.id,
                    'split_method': self.shipping_method_id.bank_interest_charge.split_method_default,
                    'amount_lc': self.bank_interest_computed,
                }))
            if self.shipping_method_id.customs_duty_charge and not self.is_duty_required:
                expense_line.append((0, False, {
                    'cost_type': 'expense',
                    'line_charge_id': self.shipping_method_id.customs_duty_charge.id,
                    'split_method': self.shipping_method_id.customs_duty_charge.split_method_default,
                    'amount_lc': self.customs_interest_computed,
                }))
            if self.bank_interest_line:
                bank_interest_line = [(0, 0, {
                    'amount': line.amount,
                    'delivery_days': line.delivery_days,
                }) for line in bank_interest_line]
            else:
                bank_interest_line = [(0, 0, {
                    'amount': self.cost_sheet_currency_id.compute(self.purchase_order_id.amount_total,
                                                                  self.currency_id) +
                              self.cost_sheet_currency_id.compute(self.total_equipment_cost, self.currency_id),
                    'delivery_days': float(self.delivery_days),
                })]
        else:
            expense_line = [(5,)]
            bank_interest_line = [(5,)]
        return {
            'value': {
                'cost_line_expense_ids': expense_line,
                'bank_interest_line': bank_interest_line
            }
        }

    @api.onchange('total_cost', 'total_cost_lc')
    def onchange_total_cost(self):
        if self.total_cost or self.total_cost_lc:
            self.bank_interest_line = [(0, 0, {
                'amount': self.cost_sheet_currency_id.compute(self.purchase_order_id.amount_total,
                                                              self.currency_id) +
                          self.cost_sheet_currency_id.compute(self.total_equipment_cost, self.currency_id),
                'delivery_days': float(self.delivery_days),
            })]

    @api.depends('exchange_rate')
    def get_inverse_exchange_rate(self):
        for record in self:
            record.exchange_rate_view = record.cost_sheet_currency_id._get_conversion_rate(
                record.cost_sheet_currency_id, record.currency_id)

    @api.onchange('is_duty_required')
    def onchange_duty_required(self):
        if self.shipping_method_id:
            duty_line = self.cost_line_expense_ids.filtered(
                lambda s: s.line_charge_id.id == self.shipping_method_id.customs_duty_charge.id)
            existing_lines = []
            for line in self.cost_line_expense_ids:
                existing_lines.append(line.id)
            if not self.is_duty_required:
                if not duty_line:
                    existing_lines.append((0, 0, {
                        'cost_type': 'expense',
                        'line_charge_id': self.shipping_method_id.customs_duty_charge.id,
                        'split_method': self.shipping_method_id.customs_duty_charge.split_method_default,
                        'amount_lc': self.customs_interest_computed,
                    }))
                    return {
                        'value': {
                            'cost_line_expense_ids': existing_lines
                        }
                    }
            else:
                if duty_line:
                    existing_lines.remove(duty_line.id)
                    self.cost_line_expense_ids = existing_lines

    @api.depends('cost_line_equipment_ids', 'cost_line_equipment_ids.amount_lc')
    def compute_total_cost_lc(self):
        for record in self:
            record.total_cost_lc = record.cost_sheet_currency_id.compute(record.purchase_order_id.amount_total,
                                                                         record.currency_id) + \
                                   sum(line.amount_lc for line in record.cost_line_equipment_ids)

    def compute_all_costs(self):
        round_fc = self.cost_sheet_currency_id.round
        round_lc = self.currency_id.round
        result = {
            'foreign_currency': self.cost_sheet_currency_id,
            'local_currency': self.currency_id,
        }
        other_charges_fc = other_charges_lc = 0.0
        certificate_charges_fc = certificate_charges_lc = 0.0
        freight_charge_fc = freight_charge_lc = 0.0
        fob_charges_fc = fob_charges_lc = 0.0
        agency_commission_fc = agency_commission_lc = 0.0
        for line in self.cost_line_equipment_ids:
            if line.line_charge_id.charge_type == 'other':
                # if line.line_charge_id.related_certificate_id:
                #     certificate_charges_fc += line.amount_fc
                #     certificate_charges_lc += line.amount_lc
                # else:
                #     other_charges_fc += line.amount_fc
                #     other_charges_lc += line.amount_lc
                if line.line_charge_id.related_certificate_id:
                    certificate_charges_fc += line.amount_fc
                    certificate_charges_lc += line.amount_lc
                else:
                    other_charges_fc = line.amount_fc
                    other_charges_lc = line.amount_lc
            elif line.line_charge_id.charge_type == 'fob':
                fob_charges_fc += line.amount_fc
                fob_charges_lc += line.amount_lc
            elif line.line_charge_id.charge_type == 'freight':
                freight_charge_fc += line.amount_fc
                freight_charge_lc += line.amount_lc
            else:
                agency_commission_fc += line.amount_fc
                agency_commission_lc += line.amount_lc

        result.update({
            'certificate_charges_fc': round_fc(certificate_charges_fc),
            'certificate_charges_lc': round_lc(certificate_charges_lc),
            'other_charges_fc': round_fc(other_charges_fc),
            'other_charges_lc': round_lc(other_charges_lc),
            'freight_charge_fc': round_fc(freight_charge_fc),
            'freight_charge_lc': round_lc(freight_charge_lc),
            'fob_charges_fc': round_fc(fob_charges_fc),
            'fob_charges_lc': round_lc(fob_charges_lc),
            'agency_commission_fc': round_fc(agency_commission_fc),
            'agency_commission_lc': round_lc(agency_commission_lc),
        })

        total_eq_fc = other_charges_fc + freight_charge_fc + fob_charges_fc + certificate_charges_fc
        total_eq_lc = other_charges_lc + freight_charge_lc + fob_charges_lc + certificate_charges_lc

        result.update({
            'total_equipment_cost_fc': round_fc(total_eq_fc),
            'total_equipment_cost_lc': round_lc(total_eq_lc),
        })

        product_cost_fc = self.purchase_order_id.amount_total
        product_cost_lc = self.cost_sheet_currency_id.compute(self.purchase_order_id.amount_total, self.currency_id)

        result.update({
            'product_cost_fc': round_fc(product_cost_fc),
            'product_cost_lc': round_lc(product_cost_lc),
        })

        total_cost_fc = product_cost_fc + total_eq_fc
        total_cost_lc = product_cost_lc + total_eq_lc
        result.update({
            'total_cost_fc': round_fc(total_cost_fc),
            'total_cost_lc': round_lc(total_cost_lc),
        })

        net_payable_supplier_fc = total_cost_fc - agency_commission_fc
        net_payable_supplier_lc = total_cost_lc - agency_commission_lc

        total_expense_line_fc = sum(x.amount_fc for x in self.cost_line_expense_ids)
        total_expense_line_lc = sum(x.amount_lc for x in self.cost_line_expense_ids)

        result.update({
            'net_payable_supplier_fc': round_fc(net_payable_supplier_fc),
            'net_payable_supplier_lc': round_lc(net_payable_supplier_lc),
            'expense_line_ids': self.cost_line_expense_ids,
            'total_expense_line_fc': total_expense_line_fc,
            'total_expense_line_lc': total_expense_line_lc,
            'final_total_fc': total_cost_fc + total_expense_line_fc,
            'final_total_lc': total_cost_lc + total_expense_line_lc,
        })
        return result

    @api.multi
    def action_approve(self):
        self.total_cost = self.total_equipment_cost + self.total_expenses
        self.state = 'approve'

    @api.multi
    def action_margin_update(self):
        self.state = 'margin_update'

    @api.multi
    def action_submit(self):
        return {
            'name': _("Cost Sheet Margin Confirmation"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('hatta_trading.wizard_cost_sheet_margin_confirm').id,
            'view_type': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def action_submit_(self):
        self.state = 'submitted'
        self.purchase_order_id.action_cost_received()

    @api.multi
    def action_print_cost(self):
        return self.env['report'].get_action(self, 'hatta_trading.hatta_cost_sheet_report')

    @api.depends('bank_interest_line.interest_amount')
    def _get_interest(self):
        for order in self:
            interest = 0
            for line in order.bank_interest_line:
                interest += line.interest_amount
            order.update({
                'bank_interest': round(interest, 0),
            })

    @api.depends('total_cost_lc', 'shipping_method_id.customs_duty')
    def compute_customs_duty(self):
        for record in self:
            customs_duty_percent = record.shipping_method_id.customs_duty / 100
            net_customs_duty = record.total_cost_lc * customs_duty_percent
            record.customs_duty_calculated = True
            record.customs_interest_computed = max(record.shipping_method_id.minimum_customs_duty,
                                                   round(net_customs_duty))

    @api.onchange('customs_interest_computed')
    @api.depends('customs_interest_computed')
    def onchange_customs_interest_computed(self):
        for record in self:
            for item in record.cost_line_expense_ids:
                if item.line_charge_id.id == record.shipping_method_id.customs_duty_charge.id:
                    item.amount_lc = record.customs_interest_computed

    @api.depends('bank_interest_line', 'bank_interest_line.interest_amount')
    def compute_bank_interest(self):
        for record in self:
            if record.bank_interest_line:
                record.bank_interest_computed = max(record.shipping_method_id.minimum_bank_interest,
                                                    sum(line.interest_amount for line in record.bank_interest_line))
                for item in record.cost_line_expense_ids:
                    if item.line_charge_id.id == record.shipping_method_id.bank_interest_charge.id:
                        item.amount_lc = record.bank_interest_computed

    # @api.onchange('bank_interest_computed')
    # @api.depends('bank_interest_computed')
    # def onchange_bank_interest_computed(self):
    #     for record in self:
    #         for item in record.cost_line_expense_ids:
    #             if item.line_charge_id.id == record.shipping_method_id.bank_interest_charge.id:
    #                 item.amount_lc = record.bank_interest_computed

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
            rate_id.write({'inverse_rate': rate})
        else:
            rcr.create({'inverse_rate': rate, 'currency_id': currency_id})
        return True


class HattaShipmentMethod(models.Model):
    _name = 'hatta.shipment.method'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    bank_interest = fields.Float('Bank Interest Rate',digits=(16, 4),)
    minimum_bank_interest = fields.Float('Minimum Bank Interest')
    customs_duty = fields.Float('Customs Duty Percent')
    minimum_customs_duty = fields.Float('Minimum Customs Duty')
    shipment_method_line = fields.One2many('shipment.method.line', 'shipment_method_id')
    bank_interest_charge = fields.Many2one('costsheet.line.charge', string='Bank Interest Charge')
    customs_duty_charge = fields.Many2one('costsheet.line.charge', string='Customs Duty Charge')


class ShipmentMethodLine(models.Model):
    _name = 'shipment.method.line'

    name = fields.Many2one('costsheet.line.charge', 'Name', domain="[('cost_type','=','expense')]")
    amount = fields.Float('Amount')
    shipment_method_id = fields.Many2one('hatta.shipment.method')


class CostSheetLine(models.Model):
    _name = 'cost.sheet.line'
    _rec_name = 'line_charge_id'

    cost_type = fields.Selection(string="Cost Type", selection=[('equipment_cost', 'Equipment Cost'),
                                                                ('expense', 'Expense')])
    cost_sheet_id = fields.Many2one('hatta.cost.sheet', 'Cost Sheet')

    line_charge_id = fields.Many2one('costsheet.line.charge', string='Charge', required=True, ondelete='cascade')
    charge_type = fields.Selection([('freight', 'Freight Charge'), ('fob', 'Fob Charge'), ('other', 'Other Charges'),
                                    ('agency_comm', 'Agency Commission')], string="Sum Applicable To", default='other')
    info = fields.Text(string="Description/Info")
    account_id = fields.Many2one('account.account', string='Account')
    split_method = fields.Selection([('equal', 'Equally'), ('quantity', 'By Quantity'),
                                     ('price', 'By Current Price'), ('percentage', 'By Percentage')],
                                    string='Split Method')
    exchange_rate = fields.Float(string='Exchange Rate', digits=dp.get_precision('Exchange Rate Accuracy'),
                                 related='cost_sheet_id.exchange_rate')
    amount_fc = fields.Float('Amount FC', required=True, compute='compute_foreign_amount', inverse='set_amount_lc',
                             store=True)
    amount_lc = fields.Float('Amount LC', required=True, store=True)

    @api.onchange('line_charge_id')
    def onchange_charge(self):
        if self.line_charge_id:
            self.account_id = self.line_charge_id.account_id
            self.charge_type = self.line_charge_id.charge_type
            self.split_method = self.line_charge_id.split_method_default

    @api.depends('amount_lc', 'cost_sheet_id.exchange_rate')
    def compute_foreign_amount(self):
        for line in self:
            if line.amount_lc:
                line.amount_fc = line.cost_sheet_id.currency_id.compute(line.amount_lc,
                                                                        line.cost_sheet_id.cost_sheet_currency_id)

    @api.onchange('amount_fc', 'exchange_rate')
    def set_amount_lc(self):
        for line in self:
            if line.amount_fc:
                line.amount_lc = line.cost_sheet_id.cost_sheet_currency_id.compute(line.amount_fc,
                                                                                   line.cost_sheet_id.currency_id)

    
class ChargeType(models.Model):
    _name = 'costsheet.line.charge'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    account_id = fields.Many2one('account.account', string='Account')
    related_certificate_id = fields.Many2one("product.certificate", string="Product Certificate")
    charge_type = fields.Selection(string="Sum Applicable To",
                                   selection=[('freight', 'Freight Charge'),
                                              ('fob', 'Fob Charge'),
                                              ('other', 'Other Charges'),
                                              ('agency_comm', 'Agency Commission')],
                                   default='other')
    cost_type = fields.Selection(string="Cost Type", selection=[('equipment_cost', 'Equipment Cost'),
                                                                ('expense', 'Expense')])
    description = fields.Text('Description')
    split_method_default = fields.Selection([('equal', 'Equally'), ('quantity', 'By Quantity'),
                                             ('price', 'By Current Price'), ('percentage', 'By Percentage')],
                                            string='Default Split Method', default='equal')


class ShippingQuotation(models.Model):
    _name = 'shipping.quotation'
    _rec_name = 'carrier_id'

    name = fields.Char('Name')
    cost_sheet_id = fields.Many2one('hatta.cost.sheet', string='Cost Sheet')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('order', 'Order'),
                                                        ('done', 'Done'),
                                                        ('cancelled', 'Cancelled')], default='draft')
    carrier_id = fields.Many2one('res.partner', 'Carrier')
    cost_center_id = fields.Many2one('account.analytic.tag', string='Cost Center')
    awb_date = fields.Date(string='AWB Date')
    awb = fields.Char('AWB')
    invoice_number = fields.Char('Invoice Number')
    duty_invoice_number = fields.Char('Duty Invoice Number')
    carrier_freight = fields.Float('Carrier Freight Quote')
    carrier_duty = fields.Float('Carrier Duty Quote')
    invoice_freight = fields.Float('Carrier Invoice Freight')
    invoice_duty = fields.Float('Carrier Invoice Duty')
    total = fields.Float(compute='get_total', string='Total', store=True)
    movement_state = fields.Selection(string="Movement Status", selection=[
        ('with_supp', 'With Supplier'),
        ('in_transit', 'In Transit'),
        ('received', 'Received')])
    shipping_invoice_id = fields.Many2one('account.invoice', 'Shipping Invoice', compute='get_shipping_invoice_id')
    job_id = fields.Many2one('account.analytic.account', string='Job No')
    account_id = fields.Many2one('account.account', string='Account')
    account_analytic_id = fields.Many2one('account.analytic.tag')
    move_id = fields.Many2one('account.payment', string='Related Voucher')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id,
                 "%s (%s)" % (record.name, record.carrier_id.name)
                 ))
        return result

    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('hatta_shipping_quotation')
        })
        return super(ShippingQuotation, self).create(vals)

    @api.depends('invoice_freight', 'invoice_duty')
    def get_total(self):
        for rec in self:
            rec.total = rec.invoice_freight + rec.invoice_duty

    @api.multi
    def get_shipping_invoice_id(self):
        for rec in self:
            si_id = self.env['account.invoice.line'].search([('shipping_quotation_id', '=', rec.id)],
                                                            limit=1, order='id')
            if si_id:
                rec.shipping_invoice_id = si_id.invoice_id.id
            else:
                rec.shipping_invoice_id = False

    @api.multi
    def action_cancel(self):
        self.state = 'cancelled'

    @api.multi
    def action_confirm(self):
        confirmed_order = self.env['shipping.quotation'].search([
            ('purchase_order_id', '=', self.purchase_order_id.id), ('state', '=', 'order')], limit=1)
        if confirmed_order:
            raise UserError("Cannot confirm more than one quotation for same Purchase Order! \n"
                            "Quotation '%s' has been already confirmed for Purchase Order '%s'"
                            % (confirmed_order.name, confirmed_order.purchase_order_id.name))
        self.state = 'order'

    @api.multi
    def action_reset_draft(self):
        self.state = 'draft'

    @api.multi
    def action_done(self):
        for rec in self:
            rec.state = 'done'

    @api.multi
    def action_create_shipping_invoice(self):
        line = [(0, 0, {
            'name': '%s Courier charges for %s' % (self.carrier_id.name, self.purchase_order_id.name),
            'account_id': self.account_id.id,
            'quantity': 1,
            'price_unit': self.total,
            'account_analytic_id': self.job_id.id,
            'analytic_tag_ids': [(4, self.cost_center_id.id)] if self.cost_center_id else [],
            'shipping_quotation_id': self.id
        })]
        acc_inv_obj = self.env['account.invoice'].create({
            'partner_id': self.carrier_id.id,
            'type': 'in_invoice',
            'journal_type': 'purchase',
            'invoice_line_ids': line,
            'is_shipping_invoice': True,
            'shipping_quotations': [(4, self.id)]
        })
        return {
            'name': 'Shipping Invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('hatta_trading.shipping_invoice_supplier_form').id,
            'res_id': acc_inv_obj.id
        }

    @api.multi
    def action_view_shipping_invoice(self):
        return {
            'name': 'Shipping Invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('hatta_trading.shipping_invoice_supplier_form').id,
            'res_id': self.shipping_invoice_id.id
        }


class ShippingCarrier(models.Model):
    _name = 'shipping.carrier'

    name = fields.Char(string='Name')
    partner_id = fields.Many2one('res.partner', string='Related Subledger')
    account_number = fields.Char(string='Account Number')
    note = fields.Text('Note')


class BankInterestLine(models.Model):
    _name = 'bank.interest.line'

    cost_sheet_id = fields.Many2one('hatta.cost.sheet')
    amount = fields.Float(string='Amount', required=True)
    delivery_days = fields.Float(string='Days', required=True)
    # interest_rate = fields.Float(string='Interest Rate')
    interest_amount = fields.Float(string='Interest Amount', compute='_get_amount', store=True)

    @api.depends('amount', 'delivery_days')
    def _get_amount(self):
        for record in self:
            net_interest = 0
            interest = record.cost_sheet_id.interest_rate / 100
            if record.amount and record.delivery_days:
                net_interest = (record.amount * interest * record.delivery_days) / 365
            record.interest_amount = net_interest
