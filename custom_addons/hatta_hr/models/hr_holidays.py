# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    expiry_date = fields.Date('Expiry Date', compute='get_expiry_date', store=True)
    leave_validity = fields.Integer('Validity in Month(s)')
    renew_allocation = fields.Boolean('Renew Automatically')
    auto_approve_on_renewal = fields.Boolean('Auto Approve On Renewal')
    state = fields.Selection(selection_add=[('expired', 'Expired')])
    used_leaves = fields.Float('Used Leaves')
    remaining_allocated_leaves = fields.Float(compute='get_remaining_allocated_leaves')
    is_encashed = fields.Boolean()
    joining_date = fields.Date('Joining Date')
    is_renew = fields.Boolean(default=False)

    @api.depends('number_of_days')
    def get_remaining_allocated_leaves(self):
        for record in self:
            record.remaining_allocated_leaves = record.number_of_days - record.used_leaves

    @api.model
    def create(self, vals):
        return super(HrHolidays, self).create(vals)
    
    @api.depends('leave_validity', 'joining_date')
    def get_expiry_date(self):
        for leave in self:
            if leave.leave_validity:
                start_date = date.today()
                if self.joining_date and not self.is_renew:
                    start_date = datetime.strptime(self.joining_date, '%Y-%m-%d').date()
                leave.expiry_date = start_date + relativedelta(months=+leave.leave_validity)

    @api.multi
    def leave_expiry_cron(self):
        leave_obj = self.search([('type', '=', 'add'), ('state', '=', 'validate')])
        for record in leave_obj:
            if record.expiry_date <= fields.Date.today():
                record.state = 'expired'
                if record.renew_allocation:
                    default = {'is_renew': True}
                    leave_obj = record.copy(default)
                    leave_obj.number_of_days_temp = record.number_of_days_temp
                    if record.auto_approve_on_renewal:
                        leave_obj.action_approve()

    @api.multi
    def action_approve(self):
        res = super(HrHolidays, self).action_approve()
        if self.type == 'remove':
            allocations = self.env['hr.holidays'].search([('type', '=', 'add'),
                                                          ('holiday_status_id', '=', self.holiday_status_id.id),
                                                          ('employee_id', '=', self.employee_id.id),
                                                          ('state', '=', 'validate')])
            requested_leaves = self.number_of_days_temp
            for allocation in allocations:
                if requested_leaves > 0.0:
                    if allocation.used_leaves < allocation.number_of_days:
                        if requested_leaves <= allocation.remaining_allocated_leaves:
                            allocation.used_leaves += requested_leaves
                            requested_leaves = 0.0
                        else:
                            allocation.used_leaves += allocation.remaining_allocated_leaves
                            requested_leaves = requested_leaves - allocation.remaining_allocated_leaves
        return res


class HrHolidayStatus(models.Model):
    _inherit = 'hr.holidays.status'

    paid_leave = fields.Boolean('Paid Leave')
