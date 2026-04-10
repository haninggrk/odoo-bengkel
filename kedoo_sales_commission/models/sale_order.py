# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    revenue_commission_rate = fields.Float(
        string='Revenue Commission (%)',
        default=0.0,
        help='Used by GROSS commission modes.',
    )
    nett_commission_rate = fields.Float(
        string='NETT Commission (%)',
        default=0.0,
        help='Used by NETT commission modes.',
    )
    commission_mode = fields.Selection(
        selection=[
            ('per_product', 'Per Product Commission'),
            ('nett_service', 'NETT Service Commission'),
            ('nett_all', 'NETT All Commission'),
            ('gross_service', 'GROSS Service Commission'),
            ('gross_all', 'GROSS All Commission'),
        ],
        string='Commission Mode',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'kedoo_sales_commission.default_mode', 'per_product'
        ),
    )
    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_commission_amount',
        store=True,
    )

    @api.onchange('commission_mode')
    def _onchange_commission_mode(self):
        for order in self:
            if order.commission_mode in ('nett_service', 'nett_all', 'per_product'):
                order.revenue_commission_rate = 0.0
            if order.commission_mode in ('gross_service', 'gross_all', 'per_product'):
                order.nett_commission_rate = 0.0
            if order.commission_mode != 'per_product':
                order.order_line.write({'service_commission_rate': 0.0})

    @api.depends(
        'commission_mode',
        'revenue_commission_rate',
        'nett_commission_rate',
        'amount_total',
        'amount_untaxed',
        'order_line.price_total',
        'order_line.price_subtotal',
        'order_line.service_commission_amount',
        'order_line.product_id.type',
    )
    def _compute_commission_amount(self):
        for order in self:
            mode = order.commission_mode or 'per_product'
            service_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type == 'service'
            )
            gross_service_base = sum(service_lines.mapped('price_total'))
            nett_service_base = sum(service_lines.mapped('price_subtotal'))

            if mode == 'per_product':
                order.commission_amount = sum(
                    order.order_line.filtered(lambda l: not l.display_type).mapped('service_commission_amount')
                )
            elif mode == 'nett_service':
                order.commission_amount = nett_service_base * (order.nett_commission_rate / 100.0)
            elif mode == 'nett_all':
                order.commission_amount = order.amount_untaxed * (order.nett_commission_rate / 100.0)
            elif mode == 'gross_service':
                order.commission_amount = gross_service_base * (order.revenue_commission_rate / 100.0)
            else:
                order.commission_amount = order.amount_total * (order.revenue_commission_rate / 100.0)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    service_commission_rate = fields.Float(
        string='Commission (%)',
        default=0.0,
        help='Default comes from the product and can be overridden per line.',
    )
    service_commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_service_commission_amount',
        store=True,
    )

    @api.depends('price_subtotal', 'service_commission_rate', 'product_id.type')
    def _compute_service_commission_amount(self):
        for line in self:
            if line.product_id and not line.display_type:
                line.service_commission_amount = line.price_subtotal * (line.service_commission_rate / 100.0)
            else:
                line.service_commission_amount = 0.0

    @api.onchange('product_id')
    def _onchange_product_id_service_commission_rate(self):
        for line in self:
            if line.product_id:
                line.service_commission_rate = line.product_id.product_tmpl_id.service_commission_rate
            else:
                line.service_commission_rate = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env['product.product']
        for vals in vals_list:
            if 'service_commission_rate' in vals:
                continue
            product_id = vals.get('product_id')
            if not product_id:
                continue
            product = Product.browse(product_id)
            vals['service_commission_rate'] = product.product_tmpl_id.service_commission_rate if product else 0.0
        return super().create(vals_list)
