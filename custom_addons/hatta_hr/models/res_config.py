from odoo import api, fields, models


class ResConfig(models.TransientModel):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    default_advance_salary_journal = fields.Many2one('account.journal', string='Advance Salary Journal')
    salary_earned_code = fields.Char('Salary Earned Code')
    total_deduction_code = fields.Char('Total Deduction Code')
    salary_advance_code = fields.Char('Salary Advance Code')
    allowance_code = fields.Char('Allowance Code')
    overtime_code = fields.Char('Overtime Code')
    net_salary_code = fields.Char('Net Salary Earned Code')
    basic_salary_code = fields.Char('Basic Code')

    @api.multi
    def set_default_advance_salary_journal(self):
        ir_values_obj = self.env['ir.values']
        if self.default_advance_salary_journal:
            ir_values_obj.sudo().set_default('employee.advance.salary', "journal_id",
                                             self.default_advance_salary_journal.id)

    @api.model
    def get_default_advance_salary_journal(self, fields_list):
        res = {}
        ir_values_obj = self.env['ir.values']
        if 'default_advance_salary_journal' in fields_list:
            value = ir_values_obj.sudo().get_default('employee.advance.salary', "journal_id")
            if value:
                res.update(default_advance_salary_journal=value)
        return res

    @api.multi
    def set_default_salary_earned_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.salary_earned_code:
            icp_obj.sudo().set_param('hatta_hr.salary_earned_code', self.salary_earned_code)

    @api.model
    def get_default_salary_earned_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'salary_earned_code': icp_obj.get_param('hatta_hr.salary_earned_code', False)}

    @api.multi
    def set_default_total_deduction_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.total_deduction_code:
            icp_obj.sudo().set_param('hatta_hr.total_deduction_code', self.total_deduction_code)

    @api.model
    def get_default_total_deduction_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'total_deduction_code': icp_obj.get_param('hatta_hr.total_deduction_code', False)}

    @api.multi
    def set_default_salary_advance_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.salary_advance_code:
            icp_obj.sudo().set_param('hatta_hr.salary_advance_code', self.salary_advance_code)

    @api.model
    def get_default_salary_advance_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'salary_advance_code': icp_obj.get_param('hatta_hr.salary_advance_code', False)}

    @api.multi
    def set_default_allowance_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.allowance_code:
            icp_obj.sudo().set_param('hatta_hr.allowance_code', self.allowance_code)

    @api.model
    def get_default_allowance_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'allowance_code': icp_obj.get_param('hatta_hr.allowance_code', False)}

    @api.multi
    def set_default_overtime_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.overtime_code:
            icp_obj.sudo().set_param('hatta_hr.overtime_code', self.overtime_code)

    @api.model
    def get_default_overtime_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'overtime_code': icp_obj.get_param('hatta_hr.overtime_code', False)}

    @api.multi
    def set_default_net_salary_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.net_salary_code:
            icp_obj.sudo().set_param('hatta_hr.net_salary_code', self.net_salary_code)

    @api.model
    def get_default_net_salary_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'net_salary_code': icp_obj.get_param('hatta_hr.net_salary_code', False)}

    @api.multi
    def set_default_basic_salary_code(self):
        icp_obj = self.env['ir.config_parameter']
        if self.basic_salary_code:
            icp_obj.sudo().set_param('hatta_hr.basic_salary_code', self.basic_salary_code)

    @api.model
    def get_default_basic_salary_code(self, fields_list):
        icp_obj = self.env['ir.config_parameter']
        return {'basic_salary_code': icp_obj.get_param('hatta_hr.basic_salary_code', False)}




