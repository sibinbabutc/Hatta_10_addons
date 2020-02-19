# -*- coding: utf-8 -*-
{
    'name': "Hatta HR Management",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "FourmalTech",
    'website': "http://www.fourmaltech.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'HR Management',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr',
                'hr_payroll',
                'hr_payroll_account',
                'hr_timesheet',
                'hr_holidays',
                'hr_expense',
                'employee_advance_salary',
                'hr_payroll_account',
                'employee_leave_encashment',
                # 'report_xlsx'
                ],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'data/salary_rule_data.xml',
        'views/hr_cron.xml',
        'views/hr_employee_view.xml',
        'views/hr_view.xml',
        'views/templates.xml',
        'views/hr_menus.xml',
        'views/res_company_view.xml',
        'views/res_config_view.xml',
        'views/hr_gratuity_view.xml',
        # 'reports/payslip_report.xml',
        # 'reports/payroll_batch_report.xml',
    ]
}