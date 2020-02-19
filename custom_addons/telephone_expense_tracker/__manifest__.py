{
    'name': 'Telephone Expense Tracker',
    'version': '',
    'summary': 'Telephone Expense Tracker',
    'description': '',
    'category': '',
    'author': 'FourmalTech',
    'website': 'www.fourmaltech.com',
    'license': '',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/telephone_expense_data.xml',
        'views/telephone_directory_view.xml',
        'views/telephone_expense_view.xml',
        'reports/telephone_expense_report.xml',
    ],
    'installable': True,
    'auto_install': False,
}