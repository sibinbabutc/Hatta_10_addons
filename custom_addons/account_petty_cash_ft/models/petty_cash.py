from odoo import api, exceptions, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare, english_number
from odoo.exceptions import ValidationError, UserError


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

PETTYCASH_STATE = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('reconcile', 'On Reconcile Approval'),
    ('topup', 'On Topup Approval'),
    ('closed', 'Closed'),
]
PAYMENT_METHODS = [
    ('cash', 'Cash or Bank'),
    ('payable', 'Payable')
]
PAYMENT_MODES = [
    ('manual', 'Cash on Hand'),
    ('cheque', 'Cheque')
]
DRAFT_EDITONLY = {'draft': [('readonly', False)]}


class PettyCash(models.Model):
    _name = 'pettycash.fund'
    _description = 'Petty Cash Fund'

    @api.model
    def default_get(self, fields_list):
        res = super(PettyCash, self).default_get(fields_list)
        admin = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        if not res.get('custodian') and admin:
            res.update({'custodian': admin.id})
        return res

    @api.multi
    def get_journal_domain(self):
        return [('journal_id', '=', self.journal_id.id)]

    code = fields.Char('Fund Code', readonly=True)
    name = fields.Char(required=True, readonly=True, states=DRAFT_EDITONLY)
    custodian = fields.Many2one('hr.employee', required=True, readonly=True,
                                states=DRAFT_EDITONLY)
    custodian_partner = fields.Many2one('res.partner', related='custodian.address_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)

    balance = fields.Float(string='Balance', compute='_valid_balance', readonly=True, store=True,
                           digits=dp.get_precision('Product Price'))
    state = fields.Selection(selection=PETTYCASH_STATE, default='draft')
    effective_date = fields.Date('Allocation Date', readonly=True, default=fields.Date.today(),
                                 states=DRAFT_EDITONLY, required=True)

    custodian_account = fields.Many2one('account.account', states=DRAFT_EDITONLY, required=True)
    payment_account = fields.Many2one('account.account', states=DRAFT_EDITONLY)

    payment_mode = fields.Selection(PAYMENT_MODES, default='manual', states=DRAFT_EDITONLY)
    cheque_number = fields.Many2one('cheque.register', 'Cheque Number', states=DRAFT_EDITONLY,
                                    domain=[('state', '=', 'blank')])
    active = fields.Boolean(default=True)
    company = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)
    vouchers = fields.One2many('pettycash.voucher', 'pettycash_id', states={'open': [('readonly', False)]})
    payments = fields.One2many('account.payment', 'pettycash_id', string='Cash Transfers',
                               domain=[('state', '!=', 'draft')], readonly=True)
    draft_payments = fields.One2many('account.payment', 'pettycash_id', string='Draft Cash Transfers',
                                     domain=[('state', '=', 'draft')])
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.user.company_id.currency_id)
    journal_entries = fields.One2many('account.move', 'pettycash_id', domain=get_journal_domain)

    # cus_related_user = fields.One2many("hr.employee", 'petty_cash_fund', string="Related Users")
    fund_related_users = fields.Many2many("res.users", string="Users")

    @api.constrains('balance')
    def negative_balance(self):
        if self.balance < 0:
            raise UserError('Sorry, You cannot make Balance Negative. Please Transfer Cash for continue.')

    @api.onchange('custodian')
    def on_change_values(self):
        res = {}
        if self.custodian:
            res.update(name='Petty Cash - ' + self.custodian.name)
        return {'value': res}

    @api.depends('payments.state', 'vouchers.amount')
    def _valid_balance(self):
        for fund in self:
            amount = 0.0
            for payment in self.payments:
                if payment.journal_id == fund.journal_id:
                    amount -= payment.amount
                if payment.destination_journal_id == fund.journal_id:
                    amount += payment.amount
            for voucher in fund.vouchers:
                if voucher.state == 'cancel':
                    continue
                else:
                    amount -= voucher.amount
            fund.balance = amount

    @api.multi
    def open_petty_cash_voucher_in(self):
        if self.balance <= 0.0:
            raise UserError('No Balance.'
                            'Please Add/Transfer some Cash to this Pettycash Fund.')
        context = {
            'default_pettycash_id': self.id,
            'default_currency_id': self.currency_id.id,
            'default_journal_id': self.journal_id.id,
            'form_view_ref': 'account_petty_cash_ft.view_pettycash_voucher_form_in'
        }
        return {
            'name': "%s-Pettycash Voucher" % self.code,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('account_petty_cash_ft.view_pettycash_voucher_form_in').id,
            'view_type': 'form',
            'res_model': 'pettycash.voucher',
            'target': 'current',
            'context': context
        }

    @api.multi
    def validate_fund(self):
        seq_o = self.env['ir.sequence']
        fund_code = seq_o.next_by_code('petty.cash.fund')
        journal_seq = self.create_journal_sequence(fund_code)
        journal_o = self.create_journal(fund_code, journal_seq.id)
        self.write({
            'code': fund_code,
            'name': self.name + ' (%s)' % fund_code,
            'journal_id': journal_o.id,
            'state': 'open',
        })
        return True

    @api.multi
    def add_pettycash_voucher(self):
        if self.balance <= 0.0:
            raise UserError('No Balance.'
                            'Please Add/Transfer some Cash to this Pettycash Fund.')
        else:
            return {
                'name': _("Add Pettycash Voucher"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'pettycash.voucher',
                'target': 'current',

            }

    @api.multi
    def transfer_amount(self):
        return {
            'name': _("Transfer Cash to Pettycash"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('account_petty_cash_ft.view_account_payment_form').id,
            'view_type': 'form',
            'res_model': 'account.payment',
            'target': 'new',
            'context': {
                'default_pettycash_id': self.id,
                'default_payment_type': 'transfer',
                'default_destination_journal_id': self.journal_id.id,
                'default_hide_payment_method': True,
            }
        }

    @api.multi
    def validate_and_open(self):
        self.validate_fund()
        desc = _("Petty Cash Allocation(%s)" % self.code)
        voucher = self.create_pettycash_voucher(desc, allocation=True)
        voucher.action_move_line_create()
        self.update({
            'journal_entries': voucher.move_id,
            'state': 'open'
        })
        return True

    @api.multi
    def get_statement(self):
        return {
            'name': _("Petty Cash Statement"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'pettycash.statement',
            'target': 'new',
            'context': {'default_pettycash_id': self.id}
        }

    @api.multi
    def create_pettycash_voucher(self, desc, allocation=False):
        voucher_o = self.env['account.voucher']
        line = [(0, False, {
            'name': desc,
            'account_id': self.custodian_account.id,
            'price_unit': self.amount,
        })]
        voucher = voucher_o.create({
            'voucher_type': 'pettycash',
            'pc_voucher_type': 'allocation',
            'number': self.env['ir.sequence'].next_by_code('voucher.pettycash.allocation'),
            'name': desc if allocation else self.name,
            'date': self.effective_date,
            'journal_id': self.journal_id.id,
            'account_id': self.payment_account.id,
            'partner_id': self.custodian_partner.id,
            'line_ids': line,
            'petty_cash_fund': self.id,
            'amount': self.amount
        })
        return voucher

    @api.model
    def create_journal_sequence(self, fund_code):
        seq_o = self.env['ir.sequence']
        seq = seq_o.sudo().create({
            'name': self.name,
            'code': 'petty.cash.fund.' + fund_code,
            'prefix': fund_code + "%(y)s",
            'padding': 4,
        })
        return seq

    @api.model
    def create_journal(self, fund_code, journal_seq):
        journal_o = self.env['account.journal']
        journal = journal_o.create({
            'name': '%s (%s)' % (self.name, fund_code),
            'code': fund_code,
            'type': 'pettycash',
            'default_credit_account_id': self.custodian_account.id,
            'default_debit_account_id': self.custodian_account.id,
            'sequence_id': journal_seq,
            'update_posted': True,
            'show_on_dashboard': False
        })
        return journal

    @api.multi
    def request_reconcile(self):
        self.state = 'reconcile'

    @api.multi
    def request_topup(self):
        self.state = 'topup'

    @api.multi
    def post_all_vouchers(self):
        moves = []
        for voucher in self.vouchers:
            if voucher.state == 'draft':
                voucher.validate()
                voucher.post()
            if voucher.state == 'valid':
                voucher.post()
            moves.append((4, voucher.account_move_id.id))
        self.journal_entries = moves
        self.state = 'open'

    @api.multi
    def reconcile_and_refill(self):
        self.reconcile_fund()
        self.topup_fund()

    @api.multi
    def close_fund(self):
        if self.vouchers:
            for voucher in self.vouchers:
                if voucher.state == 'draft':
                    voucher.unlink()
                    continue
                if voucher.state == 'valid':
                    voucher.account_move_id.unlink()
                    voucher.unlink()
        self.state = 'closed'

    @api.multi
    def unlink(self):
        for fund in self:
            if fund.state != 'closed':
                raise UserError('Please Close the Fund first and then try Delete.')
            if fund.balance > 0:
                raise UserError('Please Reverse transfer the Balance amount before Deleting.')
            for move in self.env['account.move'].search([('pettycash_id', '=', fund.id)]):
                move.button_cancel()
                for mline in move.line_ids:
                    mline.remove_move_reconcile()
                move.unlink()
            for voucher in fund.vouchers:
                voucher.unlink()
            for payment in fund.payments | fund.draft_payments:
                payment.move_name = False
                payment.move_line_ids = False
                payment.unlink()
            fund.journal_id.unlink()
            super(PettyCash, self).unlink()
        return True

    @api.multi
    def reverse_transfer(self):
        if self.balance > 0:
            return {
                'name': _("Reverse Transfer Cash from Pettycash"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_id': self.env.ref('account_petty_cash_ft.view_account_payment_form_for_reverse').id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'target': 'new',
                'context': {
                    'default_pettycash_id': self.id,
                    'default_payment_type': 'transfer',
                    'default_journal_id': self.journal_id.id,
                    'default_amount': self.balance,
                    'default_hide_payment_method': True,
                }
            }
        else:
            raise UserError('You have Zero Balance to Tranfer')

    @api.multi
    def reopen_fund(self):
        self.state = 'open'

    @api.model
    def check_is_in_group(self, name, name_desc, action_desc):

        grp = self.env.ref(name)
        user_grp_ids = self.env.user.groups_id.ids
        if grp.id not in user_grp_ids:
            raise exceptions.AccessError(
                _("Only users in group %s may %s." % (name_desc, action_desc))
            )

    @api.multi
    def change_fund_amount(self, new_amount):

        # Only the Finance manager should be allowed to change the
        # amount of the fund.
        self.check_is_in_group('account.group_account_manager',
                               'Finance Manager',
                               _("change the amount of a petty cash fund"))

        for fund in self:
            # If this is a decrease in funds and there are unreconciled
            # vouchers do not allow the user to proceed.
            diff = float_compare(new_amount, fund.amount, precision_digits=2)
            if diff == -1 and fund.vouchers and len(fund.vouchers) > 0:
                raise exceptions.ValidationError(
                    _("Petty Cash fund (%s) has unreconciled vouchers" %
                      (fund.name))
                )
            fund.amount = new_amount


DRAFT_READONLY = {'valid': [('readonly', True)], 'posted': [('readonly', True)]}


class PettyCashVoucher(models.Model):
    _name = 'pettycash.voucher'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'number'
    _order = "date desc,number desc"

    pettycash_id = fields.Many2one('pettycash.fund', string='Petty Cash Fund', required=True, states=DRAFT_READONLY)
    number = fields.Char('PCV No.', default='Draft Voucher')
    date = fields.Date('Voucher Date', required=True, default=fields.Date.today(), states=DRAFT_READONLY)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda s: s.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount', compute='get_total_voucher_amount', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Confirm'),
        ('posted', 'Posted')
    ], default='draft',track_visibility='onchange',)

    paid_to_type = fields.Selection([('internal', 'Internal (Employee)'),
                                     ('external', 'External (Supplier)')], states=DRAFT_READONLY, string='Paid')
    paid_to_char = fields.Char('Paid To', states=DRAFT_READONLY)
    paid_to_in = fields.Many2one('hr.employee', string='Paid To', states=DRAFT_READONLY)
    paid_to_out = fields.Many2one('res.partner', string='Paid To', states=DRAFT_READONLY)

    partner_id = fields.Many2one('res.partner', compute='get_partner', store=True)

    journal_id = fields.Many2one('account.journal', 'Journal', required=True)

    narration = fields.Text('Narration', states=DRAFT_READONLY)

    voucher_lines = fields.One2many('pettycash.voucher.line', 'pettycash_voucher_id', states=DRAFT_READONLY)

    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)

    prepared_by = fields.Char('Prepared By', default=lambda s: s.env.user.name, states=DRAFT_READONLY)
    checked_by = fields.Char('Checked By', states=DRAFT_READONLY)
    passed_by = fields.Char('Passed By', states=DRAFT_READONLY)
    receivers_name = fields.Char('Receivers Name', states=DRAFT_READONLY)

    account_move_id = fields.Many2one('account.move', 'Journal Entry')

    attachments = fields.Many2many('ir.attachment', states=DRAFT_READONLY)

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft':
            return 'account_petty_cash_ft.ft_petty_cash_voucher_draft'
        elif 'state' in init_values and self.state == 'valid':
            return 'account_petty_cash_ft.ft_petty_cash_voucher_valid'
        elif 'state' in init_values and self.state == 'posted':
            return 'account_petty_cash_ft.ft_petty_cash_voucher_posted'
        return super(PettyCashVoucher, self)._track_subtype(init_values)

    @api.onchange('pettycash_id')
    def onchange_pettycash(self):
        if self.pettycash_id:
            return {'value': {'journal_id': self.pettycash_id.journal_id.id}}

    @api.onchange('paid_to_in', 'paid_to_out')
    def get_partner(self):
        value = {}
        if self.paid_to_type:
            if self.paid_to_type == 'internal':
                value.update({
                    'paid_to_char': self.paid_to_in.name,
                    'partner_id': self.paid_to_in.address_id.id
                })
            if self.paid_to_type == 'external':
                value.update({
                    'paid_to_char': self.paid_to_out.name,
                    'partner_id': self.paid_to_out.id
                })
        return {'value': value}

    @api.depends('amount')
    def get_amount_in_words(self):
        for voucher in self:
            voucher.amount_in_words = amount_to_text_ae(voucher.amount)

    @api.model
    def create(self, vals):
        if vals.get('pettycash_id') and not vals.get('journal_id'):
            vals.update({'journal_id': self.pettycash_id.browse(vals.get('pettycash_id')).journal_id.id})
        if 'paid_to_char' not in vals:
            if 'paid_to_type' == 'internal':
                vals.update({'paid_to_char': vals.get('paid_to_in')})
            if 'paid_to_type' == 'external':
                vals.update({'paid_to_char': vals.get('paid_to_out')})
        return super(PettyCashVoucher, self).create(vals)

    @api.depends('voucher_lines.amount')
    def get_total_voucher_amount(self):
        for voucher in self:
            amount = 0.0
            for line in voucher.voucher_lines:
                amount += line.amount
            voucher.amount = amount

    @api.multi
    def validate(self):
        if not self.pettycash_id:
            if not self.number or self.number == 'Draft Voucher':
                self.number = self.env['ir.sequence'].with_context(ir_sequence_date=self.date). \
                    next_by_code('voucher.pettycash')
        if self.pettycash_id:
            if not self.number or self.number == 'Draft Voucher':
                seq_code = "petty.cash.fund." + str(self.pettycash_id.code)
                self.number = self.env['ir.sequence'].with_context(ir_sequence_date=self.date). \
                    next_by_code(seq_code)
        self.action_move_line_create()
        self.checked_by = self.env.user.name
        self.state = 'valid'

    @api.multi
    def post(self):
        if self.state == 'valid':
            self.account_move_id.post()
            self.passed_by = self.env.user.name
            self.state = 'posted'

    @api.multi
    def set_to_draft(self):
        if self.state == 'valid':
            if self.account_move_id:
                self.account_move_id.unlink()
            self.state = 'draft'

    @api.multi
    def account_move_get(self):
        move = {
            'name': self.number,
            'journal_id': self.journal_id.id,
            'narration': self.narration,
            'date': self.date,
            'ref': self.pettycash_id.code,
            'pettycash_id': self.pettycash_id.id
        }
        return move

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        debit = 0.0
        credit = self.currency_id.compute(self.amount, self.journal_id.company_id.currency_id)
        if debit < 0.0:
            debit = 0.0
        if credit < 0.0:
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        # set the first line of the voucher
        move_line = {
            'name': self.number or '/',
            'debit': debit,
            'credit': credit,
            'account_id': self.pettycash_id.custodian_account.id,
            'move_id': move_id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': (sign * abs(self.amount)  # amount < 0 for refunds
                                if company_currency != current_currency else 0.0),
            'date': self.date,
            'date_maturity': self.date
        }
        return move_line

    @api.multi
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        for line in self.voucher_lines:
            # create one move line per voucher line where amount is not 0.0
            if not line.amount:
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context,
            # so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self.currency_id.compute(line.amount, self.journal_id.company_id.currency_id)
            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.description or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': line.partner_id.id,
                'analytic_account_id': line.analytic_account_id and line.analytic_account_id.id or False,
                'credit': 0.0,
                'debit': abs(amount),
                'date': self.date,
                'amount_currency': line.amount if current_currency != company_currency else 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
            }

            self.env['account.move.line'].with_context(apply_taxes=True).create(move_line)
        return line_total

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
            if voucher.account_move_id:
                continue
            amount = self.amount
            for line in self.voucher_lines:
                amount -= line.amount
            if round(amount) != 0:
                raise UserError('Please Validate the Payment Lines. Total Amount and'
                                'Sum of lines doesnt match')
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = voucher.date
            ctx['check_move_validity'] = False
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())
            # Get the name of the account_move just created
            # Create the first line of the voucher with main Asset/Payable Account (Cash, Bank, etc)
            move_line = self.env['account.move.line'].with_context(ctx).create(
                voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency,
                                                                            current_currency)
            voucher.account_move_id = move.id
        return True

    @api.multi
    def print_voucher(self):
        return self.env['report'].get_action(self, 'account_petty_cash_ft.report_voucher')


class PettyCashVoucherLine(models.Model):
    _name = 'pettycash.voucher.line'

    pettycash_voucher_id = fields.Many2one('pettycash.voucher')
    account_id = fields.Many2one('account.account', 'Account', required=True)
    description = fields.Char('Description')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    asset_id = fields.Many2one('account.asset.asset', string='Asset')

    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary('Amount', required=True)

    account_move_line = fields.Many2one('account.move.line')

