{
    'name': 'Account Tax Report',
    'summary': 'Account Tax',
    'description': 'VAT Report With commercial Invoice in dual language(Arabic and English)',
    'author': 'FourmalTech',
    'website': 'www.fourmaltech.com',
    'depends': ['sale', 'purchase', 'account','hatta_trading'],
    'data': [
        'wizard/account_tax_report_view.xml',
        'reports/tax_in_out_report.xml',
        'security/ir.model.access.csv',
        'views/res_partner_inherit_view.xml'
            ],
    'installable': True,
    'auto_install': False,
}