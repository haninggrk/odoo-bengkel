# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_commission_rate = fields.Float(
        string='Service Commission (%)',
        default=0.0,
        help='Default commission percentage for service products. '
             'Used as the default value on Sales Order lines.',
    )
