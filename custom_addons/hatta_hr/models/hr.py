# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from datetime import datetime
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    blood_group = fields.Char(string="Blood Group")
    employee_number = fields.Char(string="Employee Number")
    join_date = fields.Date('Joining Date')
    last_working_date = fields.Date('Last Working Date')

    home_contact_no = fields.Char('Home Contact No')
    home_address = fields.Char('Home Address')
    local_address = fields.Char('Local Address')
    local_contact_no = fields.Char('Local Contact No')

    passport_issue_date = fields.Date('Passport Issue Date')
    passport_expiry_date = fields.Date('Passport Expiry Date')
    place_issue = fields.Char('Place of Issue')

    visa_no = fields.Char('Visa No')
    visa_issue_date = fields.Date('Visa Issue Date')
    visa_expiry_date = fields.Date('Visa Expiry Date')

    labour_card_no = fields.Char('Labour Card No')
    labour_card_issue_date = fields.Date('Labour Card Issue Date')
    labour_card_expiry_date = fields.Date('Labour Card Expiry Date')

    insurance_no = fields.Char('Insurance No')
    insurance_issue_date = fields.Date('Insurance Issue Date')
    insurance_expiry_date = fields.Date('Insurance Expiry Date')

    emirates_id_no = fields.Char('Emirates Id No')
    emirates_id_issue_date = fields.Date('Emirates Id Issue Date')
    emirates_id_expiry_date = fields.Date('Emirates Id Expiry Date')

    license_no = fields.Char('UAE Driving License')
    license_issue_date = fields.Date('DL Issue Date')
    license_expiry_date = fields.Date('DL Expiry Date')

    sal_transfer_mode = fields.Selection([('WPS', 'WPS'), ('CHQ', 'Cheque')],
                                         'Salary Payment Mode')

    sub_ledger_account = fields.Many2one('account.analytic.account', string='Subledger Account', ondelete='restrict')

    @api.onchange('user_id')
    def _onchange_user(self):
        self.work_email = self.user_id.email
        self.name = self.user_id.name
        self.image = self.user_id.image
        self.address_home_id = self.user_id.partner_id.id
        self.home_contact_no = self.user_id.partner_id.phone
        self.home_address = self.user_id.partner_id.street
        self.local_address = self.user_id.partner_id.street2
        self.local_contact_no = self.user_id.partner_id.mobile

    @api.model
    def create(self, vals):
        if not vals.get('user_id'):
            partner = self.env['res.partner'].create({'name': vals.get('name'),
                                                      'phone': vals.get('home_contact_no'),
                                                      'street': vals.get('home_address'),
                                                      'street2': vals.get('local_address'),
                                                      'mobile': vals.get('local_contact_no')})
            vals['address_home_id'] = partner.id
        else:
            partner = self.env['res.partner'].search([('id', '=', vals.get('address_home_id'))])
        if partner:
            partner.sub_ledger_code = vals['employee_number']
        sub_ledger_account = self.env['account.analytic.account'].create({
            'is_subledger_account': True,
            'name': vals['name'],
        })
        vals.update({
            'sub_ledger_account': sub_ledger_account.id
        })
        return super(HrEmployee, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'address_home_id' in vals:
            partner = self.env['res.partner'].browse(vals['address_home_id'])
            if partner:
                partner.sub_ledger_code = self.employee_number
        return super(HrEmployee, self).write(vals)

    @api.multi
    def get_encashable_leave_days(self, date_from=False, date_to=False):
        holiday_obj = self.env['hr.holidays'].search([('employee_id', '=', self.id),
                                                      ('state', '=', 'expired'),
                                                      ('is_encashed', '=', False),
                                                      ('expiry_date', '>=', date_from),
                                                      ('expiry_date', '<=', date_to)])
        total_days = 0.0
        for holiday in holiday_obj:
            total_days += holiday.remaining_allocated_leaves
        return total_days


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # Used in Reporting
    display_bold = fields.Boolean('Display in Bold')


class HRContract(models.Model):
    _inherit = 'hr.contract'

    sal_ids = fields.One2many('employee.salary.structure', 'contract_id', 'Salary Details')
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], string='Contract Type',
                                     default='unlimited')


class EmployeeSalaryStructure(models.Model):
    _name = 'employee.salary.structure'
    _description = 'Model to define employee salary amounts'
    _rec_name = 'categ_id'

    categ_id = fields.Many2one('hr.salary.rule.category', 'Category')
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    contract_id = fields.Many2one('hr.contract', 'Contract',
                                  ondelete="cascade")


class EmployeeOtherAllowances(models.Model):
    _name = 'employee.other.allowances'

    name = fields.Char('Narration', size=256)
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    gen_allowance_ids = fields.One2many('gen.employee.allowances', 'payroll_id',
                                        'General Allowances')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self:self.env.user.company_id.id)
    sal_detail_ids = fields.One2many('payroll.emp.line', 'payroll_id')
    is_confirmed = fields.Boolean()

    @api.onchange('date_start', 'company_id')
    def get_payroll_name(self):
        date_from_obj = datetime.strptime(self.date_start, "%Y-%m-%d")
        month = date_from_obj.strftime("%B")
        year = str(date_from_obj.strftime("%Y"))
        if self.company_id:
            company_name = '(%s)' % self.company_id.name
        else:
            company_name = ''
        self.name = "SALARY FOR THE MONTH OF %s - %s %s" % (month.upper(), year, company_name)

    @api.multi
    def write(self, vals):
        res = super(HrPayslipRun, self).write(vals)
        if 'gen_allowance_ids' in vals:
            for x in self.slip_ids:
                x.compute_sheet()
        return res

    @api.multi
    def compute_all_payslip(self):
        for slip in self.slip_ids:
            slip.compute_sheet()

    @api.multi
    def confirm_all_payslip(self):
        for slip in self.slip_ids:
            slip.action_payslip_done()
        self.is_confirmed = True

    @api.multi
    def export_data_sif(self):
        rows = []
        fs = fields.Date.from_string
        icp = self.env['ir.config_parameter']
        count=0
        total=0.0
        salary_earned_code = icp.get_param('hatta_hr.salary_earned_code', False)
        deduction_code = icp.get_param('hatta_hr.total_deduction_code', False)
        sal_advance_code = icp.get_param('hatta_hr.salary_advance_code', False)
        allowance_code = icp.get_param('hatta_hr.allowance_code', False)
        overtime_code = icp.get_param('hatta_hr.overtime_code', False)

        if not salary_earned_code or not deduction_code or not sal_advance_code or \
                     not allowance_code or not overtime_code:
            raise ValidationError("Please configure all codes in HR settings !!!!")

        for rec in self.slip_ids:
            emp = rec.employee_id
            salary_earned = 0.00
            deduction = 0.00
            sal_advance = 0.00
            allowance = 0.00
            overtime = 0.00
            if rec.employee_id.sal_transfer_mode != 'WPS':
                continue
            count+=1
            for line in rec.line_ids:
                if line.code == salary_earned_code:
                    salary_earned += line.total or 0.00
                if line.code == deduction_code:
                    deduction += line.total or 0.00
                if line.code == sal_advance_code:
                    sal_advance += line.total or 0.00
                if line.code == allowance_code:
                    allowance += line.total
                if line.code == overtime_code:
                    overtime += line.total
            allowance += sal_advance + allowance + overtime
            total += ((salary_earned - deduction) + allowance)
            if not emp.bank_account_id:
                raise ValidationError('No Account Number Detected For Employee : %s ' % emp.name)
            row_edr = [
                'EDR',
                emp.labour_card_no,
                emp.bank_account_id.bank_id.bic,
                emp.bank_account_id.acc_number,
                rec.date_from,
                rec.date_to,
                int(rec.days_payable),
                int(salary_earned - deduction),
                int(allowance),
                int(rec.total_days - rec.days_payable)
            ]
            rows.append(row_edr)

        row_scr = [
            'SCR',
            self.company_id.labour_number or '',
            self.company_id.comp_bank_number or '',
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%H%M'),
            self.date_start[5:7] +
            self.date_start[:4],
            count,
            int(total),
            'AED',
            self.company_id.name
        ]
        rows.append(row_scr)
        return rows

    @api.multi
    def get_sif_file_name(self):
        return (self.company_id.mol_no or '') + datetime.now().strftime('%d%m%y%H%M%S') + '.SIF'


class GeneralEmployeeAllowances(models.Model):
    _name = 'gen.employee.allowances'
    _description = 'General Employee Allowances'

    name = fields.Char('Narration', size=256)
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    payroll_id = fields.Many2one('hr.payslip.run', 'Payroll')


class PayrollEmpLine(models.Model):
    _name = 'payroll.emp.line'

    employee_id = fields.Many2one('hr.employee', 'Employee', related='payslip_id.employee_id')
    total_days = fields.Float(string="Total Days", related='payslip_id.total_days', readonly=True)
    days_payable = fields.Float('Days Payable', related='payslip_id.days_payable')
    leave_days = fields.Float('Days Leave', related='payslip_id.leave_days')
    sick_leave = fields.Float('Sick Leave', related='payslip_id.sick_leave')
    sal_advance = fields.Float('Salary Advance', digits=dp.get_precision('Account'), related='payslip_id.sal_advance')
    overtime_normal = fields.Float('Normal Overtime(Hours)', related='payslip_id.overtime_normal')
    holiday_overtime = fields.Float('Holiday Overtime(Hours)', related='payslip_id.holiday_overtime')
    holiday_worked = fields.Float('Holiday Worked', related='payslip_id.holiday_worked')
    advance_balance = fields.Float(digits=dp.get_precision('Account'),
                                   string="Balance Advance", compute='get_remaining_advance_amount', related='payslip_id.advance_balance')
    advance_ded = fields.Float('Advance Deduction',
                               digits=dp.get_precision('Account'), related='payslip_id.advance_ded')
    tel_deduction = fields.Float('Telephone Deduction',
                                 digits=dp.get_precision('Account'), related='payslip_id.tel_deduction')
    payroll_id = fields.Many2one('hr.payslip.run', 'Payroll Ref', on_delete="cascade")
    payslip_id = fields.Many2one('hr.payslip', 'Related Payslip', on_delete="cascade")

class HrSalaryRuleCategory(models.Model):
    _inherit = "hr.salary.rule.category"

    alw_deduction = fields.Boolean("Allowance/Deduction")

