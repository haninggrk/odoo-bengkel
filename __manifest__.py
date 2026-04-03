# -*- coding: utf-8 -*-
# __manifest__.py is the module descriptor file — every Odoo module MUST have one.
# It tells Odoo metadata about the module: name, version, dependencies, and which
# data files to load when the module is installed or upgraded.
{
    'name': 'Fleet Sales',
    # Version format: <odoo_version>.<module_major>.<module_minor>.<module_patch>
    'version': '19.0.2.1.5',
    # Category helps organize the module in Odoo's Apps store / settings.
    'category': 'Sales/Sales',
    'summary': 'Link Sales Orders to Fleet Services with automatic vehicle and service creation',
    'description': """
Fleet Sales Integration
=======================
This module adds the following features:
- License Plate and Vehicle Model fields on Sales Orders
- Automatic Fleet Service creation when Sales Order is confirmed
- Automatic Fleet Vehicle creation (or reuse) based on license plate
- Existing vehicle suggestion for returning customers
- Smart button navigation between SO, Vehicle, and Service
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    # LGPL-3 is the standard license for Odoo Community modules.
    'license': 'LGPL-3',
    # 'depends' lists modules that MUST be installed before this one.
    # Odoo will auto-install dependencies if they're not yet installed.
    #   'sale'  -> provides the sale.order model
    #   'fleet' -> provides fleet.vehicle and fleet.vehicle.model models
    'depends': [
        'sale',
        'fleet',
    ],
    # 'data' lists XML/CSV files loaded in order during install/upgrade.
    # Security files should come FIRST so that access rights exist before
    # views try to reference the models.
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    # installable=True means this module can be installed.
    'installable': True,
    # auto_install=False means users must explicitly install this module.
    # If True, it would auto-install when ALL dependencies are met.
    'auto_install': False,
    # application=False means this is a supporting module, not a full app.
    # Full apps (True) appear in the main Odoo Apps menu.
    'application': False,
}
