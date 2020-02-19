from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class HrGratuity(models.Model):
    _name = 'hr.gratuity'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    joining_date = fields.Date(string='Joining Date')
    last_working_date = fields.Date(string='Last Working Date')
    no_of_years = fields.Float(string='No.of Years', compute='get_no_of_years')
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], string='Contract Type')
    salary = fields.Float(string='Salary')
    total_gratuity = fields.Float(string='Total Gratuity')
    state = fields.Selection(selection=[('draft', 'Draft'), ('confirm', 'Confirmed'), ('paid', 'Paid')],
                             string="Status", required=False, default='draft')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            contract_obj = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)]).sorted(key=lambda k: k.date_start, reverse=True)
            self.joining_date = self.employee_id.join_date
            self.last_working_date = self.employee_id.last_working_date
            self.contract_id = contract_obj[0].id if contract_obj else False
            self.contract_type = contract_obj[0].contract_type if contract_obj else False
            self.salary = contract_obj[0].wage if contract_obj else False

    @api.depends('joining_date', 'last_working_date')
    def get_no_of_years(self):
        if self.joining_date and self.last_working_date:
            last_working_date = datetime.strptime(self.last_working_date, '%Y-%m-%d')
            joining_date = datetime.strptime(self.joining_date, '%Y-%m-%d')
            self.no_of_years = (last_working_date - joining_date).days/365.0

    @api.multi
    def action_confirm(self):
            self.state = 'confirm'

    @api.multi
    def action_paid(self):
            self.state = 'paid'

    @api.depends('salary', 'no_of_years')
    def action_calculate_gratuity(self):
        if self.salary and self.no_of_years:
            daily_wage = self.salary / 30.0
            if self.contract_type == 'limited':
                if self.no_of_years <= 1.0:
                    self.total_gratuity = 0.0
                elif self.no_of_years >= 5.0:
                    gratuity_per_year = daily_wage * 30.0
                else:
                    gratuity_per_year = daily_wage * 21.0
                self.total_gratuity = gratuity_per_year * self.no_of_years
            elif self.contract_type == 'unlimited':
                gratuity_per_year = daily_wage * 21.0
                if self.no_of_years <= 1.0:
                    self.total_gratuity = 0.0
                elif 1.0 < self.no_of_years < 3.0:
                    self.total_gratuity = gratuity_per_year * self.no_of_years * (1.0/3.0)
                else:
                    if 3.0 < self.no_of_years < 5.0:
                        self.total_gratuity = gratuity_per_year * self.no_of_years * (2.0/3.0)
            else:
                raise UserError('Please Select Contract Type For Employee')
        else:
            raise UserError('Please Fill Employee Contract Details')




