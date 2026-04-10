# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_commission_rate = fields.Float(
        string='Commission (%)',
        default=0.0,
        help='Default commission percentage for products. '
             'Used as the default value on Sales Order lines.',
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    service_commission_rate = fields.Float(
        string='Commission (%)',
        related='product_tmpl_id.service_commission_rate',
        readonly=False,
    )
