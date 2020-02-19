# -*- coding: utf-8 -*-
{
    'name': "Custom Widget for List Boolean",

    'summary': """
        Enables boolean field in List View as like Button""",

    'description': """
        By this Module, can have boolean field in X2many fields list view as like as Button.
        Working: Add toggle_boolean_always_enabled as widget for field.
    """,
    'author': "FourmalTech KM",
    'website': "http://www.fourmaltech.com",
    'category': 'Widget',
    'version': '0.1',
    'depends': ['base', 'web','account'],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': False,
}
