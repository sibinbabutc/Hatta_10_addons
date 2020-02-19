# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    advance_ids = fields.One2many('employee.advance.salary', 'employee_id', string='Advance Salary Requests')
    
    # def get_advance_salary(self, emp_id, date_from, date_to=None):
    #     if date_to is None:
    #         date_to = datetime.now().strftime('%Y-%m-%d')
    #     self._cr.execute("SELECT sum(o.request_amount) from employee_advance_salary as o where \
    #                         o.employee_id=%s \
    #                         and o.state='done' AND to_char(o.account_validate_date, 'YYYY-MM-DD') >= %s AND to_char(o.account_validate_date, 'YYYY-MM-DD') <= %s ",
    #                         (emp_id, date_from, date_to))
    #     res = self._cr.fetchone()
    #     return res and res[0] or 0.0

    @api.multi
    def get_advance_salary_deduction_amount(self):
        deduction_amount = 0.0
        for advances in self.advance_ids:
            if advances.state == 'paid':
                deduction_amount += advances.get_deduction_amount()
        return deduction_amount

    @api.multi
    def get_remaining_advance_amount(self):
        remaining_amount = 0.0
        for advances in self.advance_ids:
            if advances.state == 'paid':
                remaining_amount += advances.get_remaining_amount()
        return remaining_amount

    @api.multi
    def get_advance_salary_amount(self):
        advance_amount = 0.0
        for advances in self.advance_ids:
            if advances.state == 'confirm':
                advance_amount += advances.request_amount
        return advance_amount