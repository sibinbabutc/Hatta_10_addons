# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta


class HrPaySlip(models.Model):
    _inherit = 'hr.payslip'

    other_allow_ids = fields.One2many('employee.other.allowances', 'payslip_id',
                                      'Other Allowances')

    @api.depends('date_from', 'date_to')
    def _get_total_days(self):
        for record in self:
            if record.date_from and record.date_to:
                from_date = datetime.strptime(record.date_from, '%Y-%m-%d')
                to_date = datetime.strptime(record.date_to, '%Y-%m-%d')
                days = (to_date - from_date).days + 1
                record.total_days = days

    total_days = fields.Float(string="Total Days", compute='_get_total_days')
    days_payable = fields.Float(string="Days Payable")
    leave_days = fields.Float(string="Total Days Leave", compute='compute_leave_days')
    sick_leave = fields.Float(string="Sick Leave")
    paid_leaves = fields.Float(string='Paid Leaves', compute='get_paid_leaves')
    unpaid_leaves = fields.Float(string='Unpaid Leaves', compute='get_paid_leaves')

    sal_advance = fields.Float('Salary Advance', digits=dp.get_precision('Account'),
                               compute='get_advance_salary_amount')
    overtime_normal = fields.Float('Normal Overtime(Hours)')
    holiday_overtime = fields.Float('Holiday Overtime(Hours)')
    holiday_worked = fields.Float('Holiday Worked')
    advance_balance = fields.Float(digits=dp.get_precision('Account'),
                                   string="Balance Advance", compute='get_remaining_advance_amount')
    advance_ded = fields.Float('Advance Deduction',
                               digits=dp.get_precision('Account'))
    tel_deduction = fields.Float('Telephone Deduction',
                                 digits=dp.get_precision('Account'))
    other_deductions = fields.One2many('other.deductions', 'payslip_id')
    leave_sal_ids = fields.Many2many('employee.salary.structure', domain="[('contract_id', '=', contract_id)]",
                                     string='Leave Salary Details')
    leave_base_amount = fields.Float('Leave Salary Base Amount')

    @api.depends('employee_id')
    def get_advance_salary_amount(self):
        for rec in self:
            rec.sal_advance = rec.employee_id.get_advance_salary_amount()

    @api.depends('employee_id')
    def get_remaining_advance_amount(self):
        for rec in self:
            rec.advance_balance = rec.employee_id.get_remaining_advance_amount()

    @api.onchange('employee_id')
    def employee_id_change(self):
        if self.employee_id:
            self.advance_ded = self.employee_id.get_advance_salary_deduction_amount()
            self.leave_base_amount = self.contract_id.wage

    @api.onchange('leave_sal_ids')
    def onchange_leave_sal_ids(self):
        if self.leave_sal_ids:
            base_amount = self.contract_id.wage
            for item in self.leave_sal_ids:
                base_amount += item.amount
            self.leave_base_amount = base_amount

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_paid_leaves(self):
        for rec in self:
            if rec.employee_id and rec.date_from and rec.date_to:
                cr = self.env.cr
                query = "SELECT id " \
                        "FROM hr_holidays " \
                        "WHERE (date_from, date_to) OVERLAPS ('%s', '%s')" % (rec.date_from, rec.date_to)
                cr.execute(query)
                qres = cr.dictfetchall()
                leave_ids = []
                for item in qres:
                    leave_ids.append(item['id'])
                paid_leaves = 0.0
                unpaid_leaves = 0.0
                leave_obj = self.env['hr.holidays'].search([('type', '=', 'remove'),
                                                            ('id', 'in', leave_ids),
                                                            ('employee_id', '=', rec.employee_id.id),
                                                            ('state', '=', 'validate')])
                for leave in leave_obj:
                    start = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S')
                    end = datetime.strptime(leave.date_to, '%Y-%m-%d %H:%M:%S')
                    date_generated = [start + timedelta(days=x) for x in range(0, (end-start).days+1)]
                    for date in date_generated:
                        if datetime.strptime(rec.date_from, "%Y-%m-%d") <= date <= datetime.strptime(rec.date_to, "%Y-%m-%d"):
                            if leave.holiday_status_id.paid_leave:
                                paid_leaves += 1
                            else:
                                unpaid_leaves += 1
                rec.paid_leaves = paid_leaves
                rec.unpaid_leaves = unpaid_leaves

    @api.depends('paid_leaves', 'unpaid_leaves')
    def compute_leave_days(self):
        for rec in self:
            rec.leave_days = rec.paid_leaves + rec.unpaid_leaves
            rec.days_payable = rec.total_days - rec.leave_days

    @api.model
    def create(self, vals):
        payslip = super(HrPaySlip, self).create(vals)
        if payslip.payslip_run_id:
            deduction_amount = payslip.employee_id.get_advance_salary_deduction_amount()
            payslip.payslip_run_id.write({
                'sal_detail_ids':  [(0, 0, {
                    'payslip_id': payslip.id,
                    'advance_ded': deduction_amount
                 })]
            })
        return payslip

    @api.multi
    def write(self, vals):
        payslip_batch_id = self.payslip_run_id
        payslip = super(HrPaySlip, self).write(vals)
        if 'payslip_run_id' in vals:
            if vals['payslip_run_id']:
                deduction_amount = self.employee_id.get_advance_salary_deduction_amount()
                self.payslip_run_id.write({
                    'sal_detail_ids':  [(0, 0, {
                        'payslip_id': self.id,
                        'advance_ded': deduction_amount
                     })]
                })
            else:
                sal_details_obj = payslip_batch_id.sal_detail_ids.search([('payslip_id', '=', self.id)])
                sal_details_obj.unlink()
        return payslip

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.payslip_run_id:
                obj = self.env['payroll.emp.line'].search([('payslip_id', '=', rec.id),
                                                           ('payroll_id', '=', rec.payslip_run_id.id)])
                if obj:
                    for item in obj:
                        item.unlink()
        return super(HrPaySlip, self).unlink()

    @api.multi
    def get_encashable_leave_days(self):
        return self.employee_id.get_encashable_leave_days(self.date_from, self.date_to)

    @api.multi
    def action_payslip_done(self):
        for line in self.line_ids:
            if line.code == 'ADVDED':
                advance_obj = self.env['employee.advance.salary'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'paid')])
                vals = {
                    'payslip_id': self.id,
                    'deduction_amount': abs(line.amount),
                    'advance_id': advance_obj.id,
                }
                advance_line_obj = self.env['advance.salary.deduction'].create(vals)
                advance_line_obj.advance_done()
        res = super(HrPaySlip, self).action_payslip_done()
        if res:
            advance_sal_obj = self.env['employee.advance.salary'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'confirm'), ('pay_in_next_salary', '=', True)], limit=1)
            if advance_sal_obj:
                advance_sal_obj.write({'state': 'paid'})
            encashment_obj = self.env['employee.leave.encashment'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'confirm'), ('pay_in_next_salary', '=', True)], limit=1)
            if encashment_obj:
                for encashment in encashment_obj:
                    encashment.action_paid()
        return res


class OtherDeductions(models.Model):
    _name = 'other.deductions'
    _rec_name = 'name'

    name = fields.Char('Narration')
    code = fields.Char('Code')
    amount = fields.Float('Amount')
    payslip_id = fields.Many2one('hr.payslip')