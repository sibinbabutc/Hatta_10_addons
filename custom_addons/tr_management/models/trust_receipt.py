from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class TrDetails(models.Model):
    _name = 'tr.details'
    _description = 'A model for trust receipts'

    name = fields.Char('TR Number', required="1",
                       readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Float('Amount', required="1", digits=dp.get_precision('Account'),
                          readonly=True, states={'draft': [('readonly', False)]})
    interest_rate = fields.Float('Interest Rate', required="1", digits=(3,2),
                                 readonly=True, states={'draft': [('readonly', False)]})
    duration = fields.Float('Duration (Days)', required="1", digits=(2,2),
                            readonly=True, states={'draft': [('readonly', False)]})
    start_date = fields.Date('Start Date', required="1",
                             readonly=True, states={'draft': [('readonly', False)]})
    closing_date = fields.Date('Closing Date', compute='_get_closing_date', store=True)
    notify_before = fields.Integer('Notify Before(days)', required="1", default=7,
                                   readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('settle', 'Settled'),
                              ('cancel', 'Cancelled')], 'State', default='draft')
    note = fields.Text('Purpose')
    final_interest = fields.Float(compute='_get_final_interest', string="Interest as on Closing Date")
    interest_today = fields.Float(compute='_get_final_interest', string="Interest as on Today")
    settle_ids = fields.One2many('account.payment', 'tr_details_id', 'Settlement Lines')
    tr_account_id = fields.Many2one('tr.account', 'TR Account', readonly=True, required=True,
                                    states={'draft': [('readonly', False)]})
    # amt_cleared = fields.Float('Amount Cleared', digits=dp.get_precision('Account'))
    voucher_id = fields.Many2one('account.payment', 'Related Voucher',
                                 readonly=True, states={'draft': [('readonly', False)]})
    is_supplier = fields.Boolean('Supplier')
    partner_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    account_id = fields.Many2one('account.account', 'Account')
    settled_amount = fields.Float('Settled Amount', compute='get_settled_amount')
    account_move_line = fields.One2many('account.move.line', compute='get_account_move_lines')
    # 'settle_voucher_id': fields.many2one('account.move', 'Settlement Voucher'),
    # 'settle_date': fields.date('Settlement Date'),
    # 'settle_note': fields.text('Settlement Note'),

    # 'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
    #     multi='sums', help="The total amount."),
    # 'due_amount': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
    #     multi='sums', help="The total amount."),

    @api.depends('duration', 'start_date')
    def _get_closing_date(self):
        for record in self:
            if record.start_date:
                record.closing_date = (datetime.strptime(record.start_date, '%Y-%m-%d') +
                                       relativedelta(days=+record.duration)).strftime(DATE_FORMAT)

    @api.depends('voucher_id', 'settle_ids')
    def get_account_move_lines(self):
        move_line = []
        if self.voucher_id:
            move_line.extend(self.voucher_id.move_line_ids.ids)
        if self.settle_ids:
            for x in self.settle_ids:
                if x.move_line_ids.ids:
                    move_line.extend(x.move_line_ids.ids)
        self.account_move_line = move_line

    @api.multi
    def _get_final_interest(self):
        for tr in self:
            if tr.state == 'settle':
                tr.final_interest = 0.0
                tr.interest_today = 0.0
            else:
                start_date = datetime.strptime(tr.start_date, "%Y-%m-%d")
                today = datetime.today()
                end_date = datetime.strptime(tr.closing_date, "%Y-%m-%d")
                final_days = (end_date - start_date).days
                days_today = (today - start_date).days
                int_rate = tr.interest_rate/ 100.00
                principle = tr.amount or 0.00
                tr.final_interest = (principle * (1.00 + (int_rate * (final_days / 365.00)))) - principle
                tr.interest_today = (principle * (1.00 + (int_rate * (days_today / 365.00)))) - principle

    @api.depends('settle_ids', 'settle_ids.amount', 'settle_ids.state')
    def get_settled_amount(self):
        settled_amount = 0
        for settlement in self.settle_ids:
            if settlement.state == 'posted':
                settled_amount += settlement.amount
        self.settled_amount = settled_amount

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            self.account_id = self.partner_id.property_account_payable_id.id

    @api.multi
    def action_confirm(self):
        payment_methods = self.tr_account_id.bank_account.outbound_payment_method_ids
        payment_method_id = payment_methods and payment_methods[0] or False
        vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'is_a_tr': True,
            'partner_id': self.partner_id.id,
            'journal_id': self.tr_account_id.bank_account.id,
            'amount': self.amount,
            'payment_method_id': payment_method_id.id,
        }
        acc_pay_obj = self.env['account.payment'].create(vals)
        self.voucher_id = acc_pay_obj.id
        self.state = 'open'

    @api.multi
    def action_view_voucher(self):
        return {
            'name': "Voucher",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.voucher_id.id,
            'view_type': 'form',
            'res_model': 'account.payment',
        }

    @api.multi
    def action_view_journal_entries(self):
        move_line_obj = self.env['account.move.line'].search([('payment_id', '=', self.voucher_id.id)])
        voucher_ids = [x.move_id.id for x in move_line_obj]
        domain = [('id', 'in', voucher_ids)]
        return {
            'name': "Journal Entries",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.move',
            'flags': {'action_buttons': False},
            'domain': domain
        }

    @api.multi
    def action_view_settlements(self):
        context = {
            'default_payment_type': 'transfer',
            'default_destination_journal_id': self.tr_account_id.bank_account.id,
            'default_amount': self.amount - self.settled_amount,
            'default_tr_details_id': self.id
        }
        return {
            'name': "Settlements",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.settle_ids.ids)],
            'view_type': 'form',
            'res_model': 'account.payment',
            'context': context
        }

    @api.multi
    def action_settlement(self):
        context = {
            'default_payment_type': 'transfer',
            'default_destination_journal_id': self.tr_account_id.bank_account.id,
            'default_amount': self.amount - self.settled_amount,
            'default_tr_details_id': self.id
        }
        return {
            'name': 'Register Settlement',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.payment',
            'target': 'new',
            'context': context
        }

    # @api.multi
    # def get_amount(self, domain):
    #     tr_obj = self.env['tr.details'].search(domain)
    #     amount = 0.00
    #     for tr in tr_obj:
    #         amount += tr.amount
    #     return amount

    @api.multi
    def get_total_tr_amount(self):
        tr_obj = self.env['tr.details'].search([('state', '!=', 'draft')])
        amount_total = 0.00
        for tr in tr_obj:
            amount_total += tr.amount
        return amount_total

    @api.multi
    def get_open_tr_amount(self):
        tr_obj = self.env['tr.details'].search([('state', '=', 'open')])
        open_tr = 0.00
        for tr in tr_obj:
            open_tr += tr.amount
        return open_tr

    @api.multi
    def get_settle_tr_amount(self):
        tr_obj = self.env['tr.details'].search([('state', '=', 'settle')])
        settle_tr = 0.00
        for tr in tr_obj:
            settle_tr += tr.amount
        return settle_tr


class TrSettlementDetails(models.Model):
    _name = 'tr.settle.details'
    _description = 'TR Settlement Details'

    tr_details_id = fields.Many2one('tr.details', 'TR Details')
    amt_cleared = fields.Float('Amount Cleared', digits=dp.get_precision('Account'))
    settle_date = fields.Date('Settlement Date')
    settle_note = fields.Text('Settlement Note')
    settle_voucher_id = fields.Many2one('account.move', 'Settlement Voucher')
    state = fields.Selection(related='settle_voucher_id.state', string="Voucher Status")


class TrAccount(models.Model):
    _name = 'tr.account'
    _rec_name = 'name'

    name = fields.Char(string="TR No.", required="1")
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'),
                                                         ('active', 'Active'),
                                                         ('cancelled', 'Cancelled')], default='draft')
    limit = fields.Float('Limit', digits=dp.get_precision('Account'), required="1")
    balance = fields.Float('Balance', digits=dp.get_precision('Account'), compute='get_balance')
    bank_account = fields.Many2one('account.journal', string='Bank',required=True, domain="[('type', '=', 'bank')]")
    bank_acc_number = fields.Char('Bank Account Number', related='bank_account.bank_acc_number')
    account_id = fields.Many2one('account.account', 'Account')
    trust_receipts = fields.One2many('tr.details', 'tr_account_id')

    @api.depends('trust_receipts', 'trust_receipts.amount')
    def get_balance(self):
        for record in self:
            total_amount = 0.00
            for receipt in record.trust_receipts:
                total_amount += receipt.amount
                record.balance = record.limit - total_amount

    @api.multi
    def get_tr_limit(self):
        tr_account_obj = self.env['tr.account'].search([])
        total_amount = 0.00
        for record in tr_account_obj:
            total_amount += record.limit
        return total_amount

    @api.multi
    def get_tr_balance(self):
        tr_account_obj = self.env['tr.account'].search([])
        total_amount = 0.0
        for record in tr_account_obj:
            total_amount += record.balance
        return total_amount

    @api.multi
    def action_confirm(self):
        self.state = 'active'


class TrAccountPayment(models.Model):
    _inherit = 'account.payment'

    tr_details_id = fields.Many2one('tr.details')
    is_a_tr = fields.Boolean()

    @api.multi
    def post(self):
        post = super(TrAccountPayment, self).post()
        if self.tr_details_id:
            if self.tr_details_id.settled_amount == self.tr_details_id.amount:
                self.tr_details_id.state = 'settle'
        return post


class TrAccountMove(models.Model):
    _inherit = 'account.move'

    is_a_tr = fields.Boolean('Is a TR')


class TrAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_a_tr = fields.Boolean('Is a TR', related='move_id.is_a_tr')

    @api.model
    def create(self, vals):
        if 'payment_id' in vals:
            payment_id = self.env['account.payment'].browse(vals['payment_id'])
            if payment_id:
                vals.update({
                    'is_a_tr': payment_id.is_a_tr
                })
        return super(TrAccountMoveLine, self).create(vals)
