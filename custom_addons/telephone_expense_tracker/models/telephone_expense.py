# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


def get_years():
        year_list = []
        for i in range(2017, 2036):
            year_list.append((i, str(i)))
        return year_list


class TelephoneExpense(models.Model):
    _name = "telephone.expense"
    _description = "Telephone Expense"

    _month_selection = [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
                        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12','December')
                        ]

    @api.model
    def _get_month(self):
        return str(datetime.now().month)

    @api.model
    def _get_default_year(self):
        return datetime.now().year

    @api.model
    def _get_account_id_domain(self):
        return [('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)]

    @api.depends('expense_line_ids', 'expense_line_ids.total_amount','expense_line_ids.prev_month_balance')
    def _amount_all(self):
        total_amount = 0.0
        total_prev_month_balance = 0.0
        total_prev_month_increase = 0.0
        total_prev_month_decrease = 0.0
        for expense_line_obj in self.expense_line_ids:
            total_amount += expense_line_obj.total_amount
            total_prev_month_balance += expense_line_obj.prev_month_balance
            total_prev_month_increase += expense_line_obj.prev_month_increase
            total_prev_month_decrease += expense_line_obj.prev_month_decrease
        net_prev_month_increase = total_prev_month_increase - total_prev_month_decrease
        self.total_amount = total_amount
        self.total_prev_month_balance = total_prev_month_balance
        self.total_prev_month_increase = total_prev_month_increase
        self.total_prev_month_decrease = total_prev_month_decrease
        self.net_prev_month_increase = net_prev_month_increase

    @api.depends('account_allocation_ids', 'group_allocation_ids',
                 'account_allocation_ids.value', 'group_allocation_ids.value')
    def _total_value(self):
        account_total_value = 0.0
        group_total_value = 0.0
        for account_line_obj in self.account_allocation_ids:
            account_total_value += account_line_obj.value
        for group_line_obj in self.group_allocation_ids:
            group_total_value += group_line_obj.value
        self.account_total_value = account_total_value
        self.group_total_value = group_total_value

    name = fields.Char(string='Name', compute='get_expense_name')
    sequence = fields.Char('Sequence')
    year = fields.Selection(get_years(), 'Year', default=_get_default_year)
    month = fields.Selection(selection=_month_selection,  string='Month', default=_get_month)
    prev_year = fields.Selection(get_years(), 'Previous Year')
    prev_month = fields.Selection(selection=_month_selection,  string='Previous Month')
    service_provider_id = fields.Many2one('tel.service.provider', 'Service Provider')
    partner_id = fields.Many2one('res.partner', 'Party')
    expense_line_ids = fields.One2many('telephone.expense.line', 'expense_id', 'Expense Lines')
    account_allocation_ids = fields.One2many('tel.account.allocation', 'expense_id', 'Account Allocation', copy=False)
    group_allocation_ids = fields.One2many('tel.group.allocation', 'expense_id', 'Group Allocation', copy=False)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'),
                                                         ('confirm', 'Confirmed'),
                                                         ('paid', 'Paid')],
                             copy=False, default='draft')
    total_amount = fields.Float(compute=_amount_all, digits=dp.get_precision('Account'), string='Total Amount',
                                multi='sums', help="The total amount.")
    total_prev_month_balance = fields.Float(compute=_amount_all, digits=dp.get_precision('Account'), string='Total Previous Month Balance',
                                    multi='sums')
    total_prev_month_increase = fields.Float(compute=_amount_all, digits=dp.get_precision('Account'), string='Total Increase Over Previous Month',
                                    multi='sums')
    total_prev_month_decrease = fields.Float(compute=_amount_all, digits=dp.get_precision('Account'), string='Total Decrease Over Previous Month',
                                    multi='sums')
    net_prev_month_increase = fields.Float(compute=_amount_all, digits=dp.get_precision('Account'), string='Net Increase Over Previous Month',
                                    multi='sums')
    account_total_value = fields.Float(compute=_total_value, digits=dp.get_precision('Account'), string='Total Account Value',
                                    multi='value')
    group_total_value = fields.Float(compute=_total_value, digits=dp.get_precision('Account'), string='Total Group Value',
                                    multi='value')
    journal_id = fields.Many2one('account.journal', 'Posting Journal')
    account_id = fields.Many2one('account.account', 'Credit Account',
                                 domain=_get_account_id_domain)
    posted_move_id = fields.Many2one('account.move', 'Posted Voucher', copy=False)
    payment_move_id = fields.Many2one('account.move', related='vendor_bill.move_id', string='Payment Voucher', copy=False)
    notes = fields.Text('Notes')
    check_no = fields.Char(related='payment_move_id.ref', size=64, store=True, string='Check No', copy=False)
    bank_journal_id = fields.Many2one(related='payment_move_id.journal_id', string='Bank', copy=False)
    remarks = fields.Char('Remarks')
    loaded_accounts_groups = fields.Boolean('Loaded Accounts and Group Info', copy=False)
    compared_prev_month = fields.Boolean('Compared With Previous Month', copy=False)
    vendor_bill = fields.Many2one('account.invoice', ondelete='restrict')

    @api.depends('service_provider_id', 'month', 'year', 'sequence')
    def get_expense_name(self):
        for record in self:
            name_prefix = 'Telephone Expense for '
            if record.service_provider_id:
                name_prefix += '('+record.service_provider_id.name + ') '
            if record.month:
                name_prefix += '('+dict(self._fields['month'].selection).get(record.month) + ') '
            if record.year:
                name_prefix += '('+str(record.year) + ') '
            if record.sequence:
                name = name_prefix + record.sequence
            else:
                name = name_prefix
            record.name = name

    @api.onchange('service_provider_id')
    def onchange_service_provider_id(self):
        if self.service_provider_id:
            self.partner_id = self.service_provider_id.partner_id
            self.account_id = self.partner_id.property_account_payable_id.id
            directory_ids = self.env['telephone.directory'].search([(
                'service_provider_id', '=', self.service_provider_id.id)])
            if directory_ids:
                expense_lines = []
                sl_no =1
                for item in directory_ids:
                    expense_lines.append((0, 0, {
                        'directory_id': item.id,
                        'sl_no':  sl_no,
                        'mobile': item.mobile,
                        'allowed_amount': item.allowed_amount,
                    }))
                    sl_no += 1
                return {'value': {
                    'expense_line_ids': expense_lines,
                }}

    @api.constrains('service_provider_id', 'year', 'month')
    def _check_exp_year_month(self):
        expense_ids = self.env['telephone.expense'].search([
            ('service_provider_id', '=', self.service_provider_id.id),
            ('id', '!=', self.id),
            ('year', '=', self.year),
            ('month', '=', self.month)])
        if expense_ids:
            raise ValidationError('Expense should be Unique for a month, year and service provider!')

    @api.model
    def create(self, vals):
        vals.update({
            'sequence': self.env['ir.sequence'].next_by_code('tel_expense_code'),
        })
        return super(TelephoneExpense, self).create(vals)

    @api.multi
    def button_compare_prev_month(self):
        if not self.prev_month and self.prev_year:
            raise ValidationError("'Previous Year/Previous Year' cannot be blank ! ")
        expense_line_obj = self.env['telephone.expense.line']
        prev_expense_ids = self.env['telephone.expense'].search([
            ('service_provider_id', '=', self.service_provider_id.id),
            ('month', '=', self.prev_month),
            ('year', '=', self.prev_year)])
        for prev_obj in prev_expense_ids:
            for prev_line in prev_obj.expense_line_ids:
                expense_line_ids = expense_line_obj.search([
                    ('expense_id', '=', self.id),
                    ('directory_id', '=', prev_line.directory_id.id)], limit=1)
                if expense_line_ids:
                    expense_line_ids.write({
                        'prev_month_balance': prev_line.balance
                    })
                else:
                    if prev_line.remarks:
                            remarks = 'Remarks: ' + prev_line.remarks
                    else:
                        remarks = ''
                    line_dict = {
                        'expense_id': self.id,
                        'directory_id': prev_line.directory_id.id,
                        'sl_no':  prev_line.sl_no,
                        'mobile': prev_line.mobile,
                        'total_amount': prev_line.total_amount,
                        'allowed_amount': prev_line.allowed_amount,
                        'deduction': prev_line.deduction,
                        'prev_month_balance': prev_line.balance,
                        'remarks': "From Previous Expense. " + remarks
                        }
                    expense_line_obj.create(line_dict)
        return expense_line_obj

    @api.multi
    def _unlink_accounts_groups(self):
        if self.account_allocation_ids:
            for account_line in self.account_allocation_ids:
                account_line.unlink()
        if self.group_allocation_ids:
            for group_line in self.group_allocation_ids:
                group_line.unlink()

    @api.multi
    def _get_percentages(self, account_total, group_total):
        if self.account_allocation_ids:
            for account_line in self.account_allocation_ids:
                if account_total!=0:
                    percentage = (account_line.value/account_total) * 100
                    account_line.write({'percentage': percentage})
        if self.group_allocation_ids:
            for group_line in self.group_allocation_ids:
                if group_total!=0:
                    percentage = (group_line.value/group_total) * 100
                    group_line.write({'percentage': percentage})

    @api.multi
    def button_load_account_group_info(self):
        account_info_obj = self.env['tel.account.allocation']
        group_info_obj = self.env['tel.group.allocation']
        account_total = 0.0
        group_total = 0.0
        if self.account_allocation_ids or self.group_allocation_ids:
            self._unlink_accounts_groups()

        for line in self.expense_line_ids:
            for account_line in line.directory_id.account_allocation_ids:
                value = 0.0
                analytic_account_id = account_line.analytic_account_id.id
                account_info_id = account_info_obj.search([('expense_id', '=', self.id),
                                                           ('account_id', '=', account_line.account_id.id),
                                                           ('analytic_account_id', '=', analytic_account_id)], limit=1)
                if account_info_id:
                    new_value = line.balance * (account_line.percentage/100)
                    value = account_info_id.value + new_value
                    account_info_id.write({'value': value})
                    account_total += new_value
                else:
                    value = line.balance * (account_line.percentage/100)
                    account_info_dict = {
                        'account_id': account_line.account_id and account_line.account_id.id or False,
                        'analytic_account_id': analytic_account_id,
                        'value': value,
                        'expense_id': self.id
                    }
                    account_info_obj.create(account_info_dict)
                    account_total += value
            for group_line in line.directory_id.group_allocation_ids:
                group_info_id = group_info_obj.search([('expense_id', '=', self.id),
                                                        ('group_id', '=', group_line.group_id.id)], limit=1)
                value = 0.0
                if group_info_id:
                    new_value = line.balance * (group_line.percentage/100)
                    value = group_info_id.value + new_value
                    group_info_id.write({'value': value})
                    group_total += new_value
                else:
                    value = line.balance * (group_line.percentage/100)
                    group_info_dict = {
                        'group_id': group_line.group_id and group_line.group_id.id or False,
                        'value': value,
                        'expense_id': self.id
                    }
                    group_info_obj.create(group_info_dict)
                    group_total += value
        self._get_percentages(account_total, group_total)

    @api.multi
    def button_action_confirm(self):
        self.state = 'confirm'
        self.create_bills()

    @api.multi
    def create_bills(self):
        if self.account_allocation_ids:
            acc_inv_obj = self.env['account.invoice']
            invoice_line_ids = []
            for account_line in self.account_allocation_ids:
                invoice_line_ids.append((0, 0, {
                    'account_id': account_line.account_id.id,
                    'account_analytic_id': account_line.analytic_account_id.id,
                    'name': self.name,
                    'quantity': 1,
                    'price_unit': account_line.value
                }))
            bill = acc_inv_obj.create({
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'type': 'in_invoice',
                'account_id': self.account_id.id,
                'invoice_line_ids': invoice_line_ids,
            })
            self.vendor_bill = bill.id

    @api.multi
    def action_view_bill(self):
        return {
            'name': 'Vendor Bill',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.vendor_bill.id
        }

    @api.multi
    def action_paid(self):
        for record in self:
            if record.state == 'confirm':
                record.state = 'paid'

    # @api.multi
    # def button_create_account_move(self):
    #     if self.account_allocation_ids:
    #         line_ids = []
    #         account_move_obj = self.env['account.move']
    #         line_ids.append((0, 0, {
    #             'account_id': self.account_id.id,
    #             'partner_id': self.partner_id.id,
    #             'name': self.name,
    #             'credit': self.account_total_value
    #         }))
    #         for account_line in self.account_allocation_ids:
    #             line_ids.append((0, 0, {
    #                 'account_id': account_line.account_id.id,
    #                 'analytic_account_id': account_line.analytic_account_id.id,
    #                 'name': self.name,
    #                 'debit': account_line.value
    #             }))
    #         move = account_move_obj.create({
    #             'journal_id': self.journal_id.id,
    #             'ref': self.name,
    #             'line_ids': line_ids
    #         })
    #         move.post()
    #
    # @api.multi
    # def action_payment(self):
    #     journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
    #     payment_methods = journal.outbound_payment_method_ids
    #     payment_method_id = payment_methods and payment_methods[0] or False
    #     payment_obj = self.env['account.payment']
    #     vals = {
    #             'partner_type': 'customer',
    #             'partner_id': self.partner_id.id,
    #             'journal_id': journal.id,
    #             'amount': self.account_total_value,
    #             'payment_method_id': payment_method_id.id,
    #             'payment_type': 'outbound',
    #             'communication': self.name
    #             }
    #     pay_id = payment_obj.create(vals)
    #     res = self.env.ref('account.action_account_payments')
    #     res = res.read()[0]
    #     res['domain'] = str([('id', 'in', [pay_id.id])])
    #     return res


class TelephoneExpenseLine(models.Model):
    _name = "telephone.expense.line"
    _description = "Telephone Expense Line"
    _rec_name = 'directory_id'

    expense_id = fields.Many2one('telephone.expense', 'Telephone Expense')
    directory_id = fields.Many2one('telephone.directory', 'Name')
    sl_no = fields.Integer('Sl No')
    mobile = fields.Char('Mobile No')
    total_amount = fields.Float('Total Amount')
    allowed_amount = fields.Float('Allowed Amount')
    deduction = fields.Float('Deduction')
    balance = fields.Float(compute='compute_balance', string='Balance', digits=dp.get_precision('Account'), multi='subtotal')
    remarks = fields.Char('Remarks')
    prev_month_balance = fields.Float('Previous Month Balance')
    prev_month_increase = fields.Float(compute='compute_balance', string='Increase Over Previous Month', digits=dp.get_precision('Account'), multi='subtotal')
    prev_month_decrease = fields.Float(compute='compute_balance', string='Decrease Over Previous Month', digits=dp.get_precision('Account'), multi='subtotal')

    @api.onchange('directory_id')
    def onchange_directory_id(self):
        if self.directory_id:
            self.mobile = self.directory_id.mobile
            self.allowed_amount = self.directory_id.allowed_amount

    @api.depends('total_amount', 'deduction', 'prev_month_balance')
    def compute_balance(self):
        for record in self:
            record.balance = record.total_amount - record.deduction
            balance_difference = record.balance - record.prev_month_balance
            if balance_difference > 0.0:
                record.prev_month_increase = balance_difference
            else:
                record.prev_month_decrease = abs(balance_difference)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        if self:
            expense_obj = self.env['telephone.expense'].search([('vendor_bill', '=', self.id)])
            if expense_obj:
                if expense_obj.state == 'confirm':
                    expense_obj.action_paid()
        return res