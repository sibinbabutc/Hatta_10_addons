# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


class TelephoneDirectory(models.Model):
    _name = 'telephone.directory'
    _rec_name = 'name'

    name = fields.Char()
    mobile = fields.Char('Mobile', copy=False)
    service_provider_id = fields.Many2one('tel.service.provider', 'Service Provider')
    allowed_amount = fields.Float('Allowed Amount', digits=dp.get_precision('Account'))
    account_allocation_ids = fields.One2many('tel.account.allocation', 'directory_id', 'Account Allocation')
    group_allocation_ids = fields.One2many('tel.group.allocation', 'directory_id', 'Group Allocation')

    _sql_constraints = [
        ('number_uniq', 'unique(mobile)', 'Mobile Number must be unique!'),
    ]

    @api.model
    def create(self, vals):
        result = super(TelephoneDirectory, self).create(vals)
        account_perc_total = 0.0
        group_perc_total = 0.0
        for account_line_obj in result.account_allocation_ids:
            account_perc_total += account_line_obj.percentage
        for group_line_obj in result.group_allocation_ids:
            group_perc_total += group_line_obj.percentage
        if result.account_allocation_ids and account_perc_total != 100:
            raise ValidationError('Total Account allocation Percentage should be 100!')
        if result.group_allocation_ids and group_perc_total != 100:
            raise ValidationError('Total Group allocation Percentage should be 100!')
        return result

    @api.multi
    def write(self, vals):
        result = super(TelephoneDirectory, self).write(vals)
        account_perc_total = 0.0
        group_perc_total = 0.0
        for account_line_obj in self.account_allocation_ids:
            account_perc_total += account_line_obj.percentage
        for group_line_obj in self.group_allocation_ids:
            group_perc_total += group_line_obj.percentage
        if self.account_allocation_ids and account_perc_total != 100:
            raise ValidationError('Total Account allocation Percentage should be 100!')
        if self.group_allocation_ids and group_perc_total != 100:
            raise ValidationError('Total Group allocation Percentage should be 100!')
        return result


class TelAccountAllocation(models.Model):
    _name = "tel.account.allocation"
    _description = "Telephone Account Allocation"
    _rec_name = 'account_id'

    directory_id = fields.Many2one('telephone.directory', 'Telephone Directory')
    account_id = fields.Many2one('account.account', 'Account')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Cost Center')
    percentage = fields.Float('Percentage', digits=dp.get_precision('Account'),)
    expense_id = fields.Many2one('telephone.expense', 'Telephone Expense')
    value = fields.Float('Value', digits=dp.get_precision('Account'),)


class TelGroupAllocation(models.Model):
    _name = "tel.group.allocation"
    _description = "Telephone Group Allocation"
    _rec_name = 'group_id'

    directory_id = fields.Many2one('telephone.directory', 'Telephone Directory')
    group_id = fields.Many2one('telephone.group', 'Telephone Group')
    percentage = fields.Float('Percentage', digits=dp.get_precision('Account'),)
    expense_id = fields.Many2one('telephone.expense', 'Telephone Expense')
    value = fields.Float('Value', digits=dp.get_precision('Account'),)


class TelServiceProvider(models.Model):
    _name = "tel.service.provider"
    _description = "Service Provider"

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Party')


class TelephoneGroup(models.Model):
    _name = "telephone.group"
    _description = "Telephone Group"

    name = fields.Char('Name')
