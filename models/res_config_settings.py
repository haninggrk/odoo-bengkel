# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_mode = fields.Selection(
        selection=[
            ('per_product', 'Per Product Commission'),
            ('nett_service', 'NETT Service Commission'),
            ('nett_all', 'NETT All Commission'),
            ('gross_service', 'GROSS Service Commission'),
            ('gross_all', 'GROSS All Commission'),
        ],
        string='Sales Commission Mode',
        config_parameter='fleet_sales.commission_mode',
        default='per_product',
        help='Determines how Sales Order commission amount is calculated.',
    )
