{
    'name': "TR Management",

    'summary': """
        Managing Trust Receipts""",

    'description': """
        For managing Trust Receipts and TR Bank Accounts
    """,
    'author': "FourmalTech",
    'website': "http://www.fourmaltech.com",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/trust_receipt_view.xml'],
    'installable': True,
    'auto_install': False,
}