# -*- coding: utf-8 -*-
{
    'name': 'Kedoo Sales Commission',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Flexible commission calculation for sales orders and lines',
    'author': 'Kedoo',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'product',
    ],
    'data': [
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
