# -*- coding: utf-8 -*-
{
    'name': 'Kedoo Fleet Sales Bridge',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Bridge between Sales Orders and Fleet vehicles/services',
    'author': 'Kedoo',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'sale_stock',
        'fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'application': False,
}
