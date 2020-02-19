# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Leave Encashment',
    'version': '1.0',
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Employee Leave Encashment',
    'description': """
            """,
    'author': 'Fourmaltech',
    'website': 'www.fourmaltech.com',
    'depends': ['hr', 'account', 'hr_payroll', 'hr_contract', 'hr_holidays', 'web_readonly_bypass'],
    'data': [
            'security/ir.model.access.csv',
            'views/employee_leave_encashment.xml',
            'views/hr_holiday_view.xml',
            'views/hr_views.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
