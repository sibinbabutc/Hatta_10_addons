#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, ValidationError


class EmployeeLeaveEncashment(models.Model):
    _name = 'employee.leave.encashment'
    _description = "Employee Leave Encashment"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'id desc'
    _rec_name = 'employee_id'

    @api.model
    def get_currency(self):
        return self.env.user.company_id.currency_id
    
    employee_id = fields.Many2one('hr.employee', required=True, readonly=True, string="Employee", states={'draft': [('readonly', False)]})
    request_date = fields.Date(string='Request Date', default=fields.Date.today(), readonly=True, states={'draft': [('readonly', False)]})
    confirm_date = fields.Date(string='Confirmed Date', \
                        readonly=True, copy=False)
    hr_validate_date = fields.Date(string='Approved Date(HR)', \
                        readonly=True, copy=False)
    account_validate_date = fields.Date(string='Paid Date', \
                        readonly=True, copy=False)
    confirm_by_id = fields.Many2one('res.users', string='Confirmed By', readonly=True, copy=False)

    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)

    department_id = fields.Many2one('hr.department', string='Department', readonly=True, states={'draft': [('readonly', False)]})
    job_id = fields.Many2one('hr.job', string='Job Title', readonly=True, states={'draft': [('readonly', False)]})
    manager_id = fields.Many2one('hr.employee', string='Department Manager', readonly=True, states={'draft': [('readonly', False)]})
    request_amount = fields.Monetary(string='Request Amount', required=True, readonly=True,
                                     currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=get_currency, required=True, readonly=True, states={'draft': [('readonly', False)]})
    comment = fields.Text(string='Comment')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='Request User', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, string='Company', readonly=True)

    state = fields.Selection(selection=[
                        ('draft', 'Draft'), \
                        ('approval', 'Approval'), \
                        ('approved_hr', 'Approved by HR'),\
                        ('confirm', 'Confirmed'), \
                        ('paid', 'Paid'),\
                        ('done', 'Done'),\
                        ('cancel', 'Cancelled'),\
                        ('reject', 'Rejected')],string='State', \
                        readonly=True, default='draft', \
                        track_visibility='onchange')
    
    partner_id = fields.Many2one('res.partner', string='Employee Partner', related='employee_id.address_home_id')
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    
    payslip = fields.Many2one('hr.payslip', string="Pay slip")
    encashable_leaves = fields.Float(string='Encashable Leave Days', readonly=True)
    encashable_leave_amount = fields.Float(string='Encashable Leave Amount/Day', readonly=True)
    to_encash = fields.Float(string="Days To Encash")
    to_encash_amount = fields.Float(string='To Encash Amount', readonly=True)
    pay_in_next_salary = fields.Boolean("Include In Next Salary")

    encashed_leave_allocations = fields.One2many('hr.holidays', 'encashment_id')

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        #a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    @api.onchange('employee_id')
    def get_enchased_leaves(self):
        if self.employee_id:
            remaining = 0.0
            # self.encashed_leave_allocations = False
            leaves = self.env['hr.holidays'].search([
                ('employee_id', '=', self.employee_id.id),
                ('type', '=', 'add'),
                ('state', '=', 'expired'),
                ('leave_encashed', '=', False)
            ])
            for leave in leaves:
                if leave.holiday_status_id.is_encashable:
                    remaining += leave.remaining_allocated_leaves
            self.encashable_leaves = remaining
            contract_ids = self.get_contract(self.employee_id, self.request_date, self.request_date)
            if contract_ids:
                contract = self.env['hr.contract'].browse(contract_ids[0])
                self.encashable_leave_amount = contract.encashable_leave_amount

    @api.onchange('to_encash')
    def get_to_encash_amount(self):
        if self.to_encash > self.encashable_leaves:
            raise Warning('To Encash value is greater than available encashable leaves')
        else:
            self.to_encash_amount = self.to_encash * self.encashable_leave_amount
            self.request_amount = self.to_encash * self.encashable_leave_amount

    @api.depends('payment_id', 'state')
    def _compute_payed_amount(self):
        for line in self:
            line.paid_amount = line.payment_id.amount
            
    paid_amount = fields.Float(compute=_compute_payed_amount, string='Paid Amount', store=True, readonly=True)

    # @api.model
    # def create(self, vals):
    #     if not vals['journal_id']:
    #         raise ValidationError('Please set a Journal for Advance Salary. '
    #                               'You can set it at Advance Salary > Configuration')
    #     return super(EmployeeLeaveEncashment, self).create(vals)

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
        self.state = 'approval'
        leaves = self.env['hr.holidays'].search([
                ('employee_id', '=', self.employee_id.id),
                ('type', '=', 'add'),
                ('state', '=', 'expired'),
                ('leave_encashed', '=', False)
            ])
        for leave in leaves:
            if leave.holiday_status_id.is_encashable:
                leave.write({
                    'encashment_id': self.id
                })

    @api.multi
    def get_confirm(self):
        confirm_date = time.strftime('%Y-%m-%d')

        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=confirm_date).compute_amount_fields(self.request_amount, self.currency_id, self.company_id.currency_id)
        name = self.journal_id.with_context(ir_sequence_date=self.confirm_date).sequence_id.next_by_id()
        mov_vals = {
            'name': name,
            'date': confirm_date,
            'ref': self.partner_id.name.title() + ' - Leave Encashment',
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
        # self.confirm_leave_allocation_encashment()
        for allocation in self.encashed_leave_allocations:
            allocation.action_leave_encashed()
        self.confirm_date = time.strftime('%Y-%m-%d')
        self.state = 'confirm'
        self.confirm_by_id = self.env.user.id

    @api.multi
    def confirm_leave_allocation_encashment(self):
        for allocation in self.encashed_leave_allocations:
            allocation.action_leave_encashed()

    # @api.multi
    # def action_reduce_leaves_encashed(self):
    #     leaves = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id)])
    #     encashed_days = self.to_encash
    #     for leave in leaves:
    #         if encashed_days > 0.0 and leave.holiday_status_id.is_encashable:
    #             create_vals = {
    #                 'employee_id': self.employee_id.id,
    #                 'name': 'Encashment',
    #                 'holiday_type': 'employee',
    #                 'holiday_status_id': leave.holiday_status_id.id,
    #                 'type': 'add',
    #                 }
    #             if leave.number_of_days > encashed_days:
    #                 create_vals['number_of_days_temp'] = -encashed_days
    #                 res = self.env['hr.holidays'].create(create_vals)
    #                 res.action_approve()
    #                 encashed_days = encashed_days - leave.number_of_days
    #             else:
    #                 create_vals['number_of_days_temp'] = -leave.number_of_days
    #                 res = self.env['hr.holidays'].create(create_vals)
    #                 res.action_approve()
    #                 encashed_days = encashed_days - leave.number_of_days

    @api.multi
    def get_apprv_hr(self):
        self.state = 'approved_hr'
        self.hr_validate_date = time.strftime('%Y-%m-%d')
        self.approved_by_id = self.env.user.id
        
    @api.multi
    def get_apprv_account(self):
        if not self.partner_id or not self.journal_id:
            raise Warning(_('Please make sure you have home address set for this employee and also check payment method is selected.'))
        self.state = 'paid'
        self.account_validate_date = time.strftime('%Y-%m-%d')
        self.account_by_id = self.env.user.id
        journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        payment_methods = journal.outbound_payment_method_ids
        payment_method_id = payment_methods and payment_methods[0] or False
        payment_obj = self.env['account.payment']
        vals = {
                'partner_type': 'employee',
                'partner_id' : self.partner_id.id,
                'journal_id' : journal.id,
                'amount' : self.request_amount,
                'currency_id' : self.currency_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_type': 'outbound',
                'communication': 'Leave Encashment of '+self.partner_id.name.title()
                }
        pay_id = payment_obj.create(vals)
        res = self.env.ref('account.action_account_payments')
        res = res.read()[0]
        res['domain'] = str([('id', 'in', [pay_id.id])])
        self.payment_id = pay_id.id
        return res

    @api.multi
    def action_paid(self):
        self.state = 'paid'

    @api.multi
    def get_done(self):
        self.state = 'done'
    
    @api.multi
    def get_reject(self):
        self.state = 'reject'

