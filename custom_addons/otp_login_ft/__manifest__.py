{
    'name': 'Login Customization',
    'version': '1.01',
    'category': '',
    'description': """
    This module is to add additional features in Login.

    """,
    'author': 'FourmalTech',
    'website': 'http://www.fourmaltech.com',
    'depends': ['base', 'mail'],
    'data': [
        # 'security/hatta_security.xml',
        'security/ir.model.access.csv',
        'views/user_view.xml',
        'wizard/generate_otp_view.xml',
        'report/login_log_report.xml',
        'report/user_data.xml',
        'report/user_login_details.xml',
        'views/login_log_view.xml',
        'wizard/login_log_view.xml',
        'report/hatta_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# -*- coding: utf-8 -*-
