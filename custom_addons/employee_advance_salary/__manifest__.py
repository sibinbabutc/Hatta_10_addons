# -*- coding: utf-8 -*-

{
    'name': 'Employee Advance Salary Requests',
    'version': '1.0',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Employee Advance Salary Requests and Workflow - Integrated with Accounting',
    'description': """
        Employee Advance Salary Requests:

Tags:
Employee advance salary
advance salary
salary request
advance request
payroll salary
accounting salary
employee advance salary process
director salary approval
            """,
    'author': 'Fourmaltech',
    'website': 'www.fourmaltech.com',
    'depends': ['hr', 'account', 'hr_payroll', 'l10n_ae'],
    'data': [
            'data/data.xml',
            'data/salary_rule_data.xml',
            'security/employee_advance_salary_security.xml',
            'security/ir.model.access.csv',
            'data/salary_rule_data.xml',
            'views/employee_advance_salary.xml',
            'views/hr_job.xml',
            'report/employee_advance_salary_report.xml'
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
