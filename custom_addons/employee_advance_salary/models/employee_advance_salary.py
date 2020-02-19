#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, ValidationError


class EmployeeAdvanceSalary(models.Model):
    _name = 'employee.advance.salary'
    _description = "Employee Advance Salary"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'id desc'
    _rec_name = 'employee_id'

    @api.model
    def get_currency(self):
        return self.env.user.company_id.currency_id

    employee_id = fields.Many2one('hr.employee', required=True, readonly=True, string="Employee",
                                  states={'draft': [('readonly', False)]})
    request_date = fields.Date(string='Request Date', default=fields.Date.today(), readonly=True,
                               states={'draft': [('readonly', False)]})
    confirm_date = fields.Date(string='Confirmed Date', \
                               readonly=True, copy=False)
    dept_approved_date = fields.Date(string='Approved Date(Department)', \
                                     readonly=True, copy=False)
    hr_validate_date = fields.Date(string='Approved Date(HR)', \
                                   readonly=True, copy=False)
    director_validate_date = fields.Date(string='Approved Date(Director)', \
                                         readonly=True, copy=False)
    account_validate_date = fields.Date(string='Paid Date', \
                                        readonly=True, copy=False)
    confirm_by_id = fields.Many2one('res.users', string='Confirm By', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    dept_manager_by_id = fields.Many2one('res.users', string='Department Manager', readonly=True, copy=False)
    hr_manager_by_id = fields.Many2one('res.users', string='HR Manager', readonly=True, copy=False)
    director_by_id = fields.Many2one('res.users', string='Director', readonly=True, copy=False)
    account_by_id = fields.Many2one('res.users', string='Paid By', readonly=True, copy=False)

    department_id = fields.Many2one('hr.department', string='Department', readonly=True,
                                    states={'draft': [('readonly', False)]})
    job_id = fields.Many2one('hr.job', string='Job Title', readonly=True, related='employee_id.job_id',
                             states={'draft': [('readonly', False)]})
    manager_id = fields.Many2one('hr.employee', string='Department Manager', readonly=True,
                                 states={'draft': [('readonly', False)]})
    request_amount = fields.Monetary(string='Request Amount', required=True, readonly=True,
                                     currency_field='currency_id', states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', default=get_currency, required=True, readonly=True,
                                  states={'draft': [('readonly', False)]})
    comment = fields.Text(string='Comment')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='Request User', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, string='Company',
                                 readonly=True)
    reason_for_advance = fields.Text(string='Reason For Advance', readonly=True,
                                     states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('approval', 'Approval'), ('approved_hr', 'Approved by HR'), ('confirm', 'Confirmed'),
        ('paid', 'Paid'), ('done', 'Done'), ('cancel', 'Cancelled'), ('reject', 'Rejected')], string='State',
        readonly=True, default='draft',
        track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Employee Partner', related='employee_id.address_home_id')
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=1)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    pay_in_next_salary = fields.Boolean("Include In Next Salary")
    # deduction_type = fields.Selection(string="Deduction Type", selection=[('one_time', 'One Time'),
    #                                                                       ('monthly', 'Monthly'), ], default='one_time')
    number_of_months = fields.Integer('No. Of Deductions (Months)', default=1)
    deduction_details = fields.One2many('advance.salary.deduction', 'advance_id')

    @api.depends('payment_id', 'state')
    def _compute_payed_amount(self):
        for line in self:
            line.paid_amount = line.payment_id.amount

    paid_amount = fields.Float(compute=_compute_payed_amount, string='Paid Amount', store=True, readonly=True)

    @api.model
    def create(self, vals):
        if not vals['journal_id']:
            raise ValidationError('Please set a Journal for Advance Salary. '
                                  'You can set it at Advance Salary > Configuration')
        return super(EmployeeAdvanceSalary, self).create(vals)

    @api.onchange('employee_id', 'employee_id.address_home_id')
    def get_department(self):
        for line in self:
            line.department_id = line.employee_id.department_id.id
            line.job_id = line.employee_id.job_id.id
            line.manager_id = line.employee_id.parent_id.id
            line.partner_id = line.employee_id.address_home_id and line.employee_id.address_home_id.id or False

    @api.multi
    def request_set(self):
        self.state = 'draft'

    @api.multi
    def exit_cancel(self):
        self.state = 'cancel'

    @api.multi
    def request_approval(self):
        exists = self.search([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['draft', 'done'])])
        if exists:
            raise UserError('Another uncomplete advance salary record exists for this employee.')
        self.state = 'approval'

    @api.multi
    def get_confirm(self):
        if self.job_id.salary_limit_amount < self.request_amount:
            raise Warning(_('You can not request advance salary more than limit amount, please contact your manager.'))

        confirm_date = time.strftime('%Y-%m-%d')

        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=confirm_date).compute_amount_fields(
            self.request_amount, self.currency_id, self.company_id.currency_id)
        name = self.journal_id.with_context(ir_sequence_date=self.confirm_date).sequence_id.next_by_id()
        mov_vals = {
            'name': name,
            'date': confirm_date,
            'ref': self.partner_id.name.title() + ' - Advance Salary Payment',
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
        }

        move = self.env['account.move'].create(mov_vals)

        advance_move_line_vals = {
            'name': name,
            'partner_id': self.partner_id.id,
            'move_id': move.id,
            'debit': debit,
            'credit': credit,
            'amount_currency': amount_currency or False,
            'account_id': self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }
        aml_obj.create(advance_move_line_vals)

        debit, credit = credit, debit

        payable_move_line_vals = {
            'name': name,
            'partner_id': self.partner_id.id,
            'move_id': move.id,
            'debit': debit,
            'credit': credit,
            'amount_currency': -(amount_currency) or False,
            'account_id': self.partner_id.property_account_payable_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        aml_obj.create(payable_move_line_vals)
        move.post()

        self.confirm_date = time.strftime('%Y-%m-%d')
        self.state = 'confirm'
        self.confirm_by_id = self.env.user.id

    @api.multi
    def get_apprv_hr(self):
        self.state = 'approved_hr'
        self.hr_validate_date = time.strftime('%Y-%m-%d')
        self.approved_by_id = self.env.user.id

    @api.multi
    def get_apprv_account(self):
        if not self.partner_id or not self.journal_id:
            raise Warning(_(
                'Please make sure you have home address set for this employee and also check payment method is selected.'))
        self.state = 'paid'
        self.account_validate_date = time.strftime('%Y-%m-%d')
        self.account_by_id = self.env.user.id
        journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        payment_methods = journal.outbound_payment_method_ids
        payment_method_id = payment_methods and payment_methods[0] or False
        payment_obj = self.env['account.payment']
        vals = {
            'partner_type': 'employee',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'amount': self.request_amount,
            'currency_id': self.currency_id.id,
            'payment_method_id': payment_method_id.id,
            'payment_type': 'outbound',
            'communication': 'Salary Advance of ' + self.partner_id.name.title()
        }
        pay_id = payment_obj.create(vals)
        res = self.env.ref('account.action_account_payments')
        res = res.read()[0]
        res['domain'] = str([('id', 'in', [pay_id.id])])
        self.payment_id = pay_id.id
        return res

    @api.multi
    def get_done(self):
        self.state = 'done'

    @api.multi
    def get_reject(self):
        self.state = 'reject'

    @api.multi
    def get_deduction_amount(self):
        deduction_amount = 0.0
        if self.deduction_details:
            if self.deduction_details[-1].remaining_months:
                deduction_amount = self.deduction_details[-1].remaining_amount \
                                   / self.deduction_details[-1].remaining_months
            else:
                deduction_amount = self.deduction_details[-1].remaining_amount
        else:
            deduction_amount = (self.request_amount / self.number_of_months)
        return deduction_amount

    @api.multi
    def get_remaining_amount(self):
        amount = 0.0
        if self.deduction_details:
            amount = self.deduction_details[-1].remaining_amount
        else:
            amount = self.request_amount
        return amount

    @api.model
    def create(self, vals):
        if 'employee_id' in vals:
            exists = self.search([('employee_id', '=', vals['employee_id']), ('state', 'not in', ['draft', 'done'])])
            if exists:
                raise UserError('Another uncomplete advance salary record exists for this employee.')
        return super(EmployeeAdvanceSalary, self).create(vals)


class AdvanceSalaryDeduction(models.Model):
    _name = 'advance.salary.deduction'

    advance_id = fields.Many2one('employee.advance.salary')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    deduction_amount = fields.Monetary('Deduction Amount', currency_field='currency_id')
    remaining_months = fields.Integer('Remaining Months')
    remaining_amount = fields.Monetary('Remaining Amount', currency_field='currency_id')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    payslip_reference = fields.Char('Reference', related='payslip_id.number')

    @api.depends('remaining_amount')
    def advance_done(self):
        if self.remaining_amount == 0.0 and self.advance_id.state == 'paid':
            self.advance_id.get_done()

    @api.model
    def create(self, vals):
        if vals and vals['advance_id']:
            advance_obj = self.env['employee.advance.salary'].search([('id', '=', vals['advance_id'])])
            if not advance_obj.deduction_details:
                vals['remaining_months'] = advance_obj.number_of_months - 1
                vals['remaining_amount'] = advance_obj.request_amount - vals['deduction_amount']
            else:
                vals['remaining_months'] = advance_obj.deduction_details[-1].remaining_months - 1
                vals['remaining_amount'] = advance_obj.deduction_details[-1].remaining_amount - vals['deduction_amount']
        return super(AdvanceSalaryDeduction, self).create(vals)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def post(self):
        for rec in self:
            if rec.partner_type == 'employee':
                if rec.state != 'draft':
                    raise UserError(
                        _("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

                if any(inv.state != 'open' for inv in rec.invoice_ids):
                    raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                    if rec.partner_type == 'employee':
                        # if rec.payment_type == 'inbound':
                        #     sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.employee.advance'
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                    sequence_code)

                # Create the journal entry
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = rec._create_payment_entry(amount)

                # In case of a transfer, the first journal entry created debited the source liquidity account and credited
                # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
                if rec.payment_type == 'transfer':
                    transfer_credit_aml = move.line_ids.filtered(
                        lambda r: r.account_id == rec.company_id.transfer_account_id)
                    transfer_debit_aml = rec._create_transfer_entry(amount)
                    (transfer_credit_aml + transfer_debit_aml).reconcile()

                rec.write({'state': 'posted', 'move_name': move.name})
            else:
                return super(AccountPayment, self).post()
