# -*- coding: utf-8 -*-
{
    'name': 'Fleet Sales',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Link Sales Orders to Fleet Vehicles with automatic vehicle creation',
    'description': """
Fleet Sales Integration
=======================
This module adds the following features:
- License Plate field on Sales Orders
- Automatic Fleet Vehicle creation when Sales Order is confirmed
- Link between Fleet Vehicle and Sales Order/Quotation
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
