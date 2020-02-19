# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    _sql_constraints = [
        ('date_check', "CHECK ( 1 = 1 )", "The number of days must be greater than 0."),
    ]

    leave_encashed = fields.Boolean()
    encashment_id = fields.Many2one('employee.leave.encashment')

    @api.multi
    def action_leave_encashed(self):
        self.leave_encashed = True


class HrHolidayStatus(models.Model):
    _inherit = 'hr.holidays.status'
    
    is_encashable = fields.Boolean('Encashable')


class Hrcontract(models.Model):
    _inherit = 'hr.contract'
    
    encashable_leave_amount = fields.Float('Encashable Leave Amount', help="Encashable Leave Salary per Day")


class HrLeaveEncashmentPayslip(models.Model):

    _inherit = 'hr.payslip'

    @api.multi
    def get_leave_salary_amount(self):
        return self.employee_id.get_leave_salary_amount()


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    leave_encashment_ids = fields.One2many('employee.leave.encashment', 'employee_id')

    @api.multi
    def get_leave_salary_amount(self):
        amount = 0.0
        for encashment in self.leave_encashment_ids:
            if encashment.state == 'confirm':
                amount += encashment.request_amount
        return amount