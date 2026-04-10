# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    sales_service_line_id = fields.Many2one(
        'sale.order.line',
        string='Sales Service Line',
        copy=False,
        ondelete='set null',
        help='Sales order line that generated this timesheet entry.',
    )
    sales_commission_amount = fields.Float(
        string='Commission',
        compute='_compute_sales_commission_amount',
        store=True,
        digits='Account',
        help='Commission amount derived from the linked sales service line.',
    )

    @api.depends(
        'sales_service_line_id',
        'sales_service_line_id.service_commission_amount',
        'sales_service_line_id.order_id.commission_mode',
        'sales_service_line_id.order_id.commission_amount',
    )
    def _compute_sales_commission_amount(self):
        for line in self:
            so_line = line.sales_service_line_id
            if not so_line:
                line.sales_commission_amount = 0.0
                continue
            order = so_line.order_id
            mode = order.commission_mode or 'per_product'
            if mode == 'per_product':
                line.sales_commission_amount = so_line.service_commission_amount
            else:
                auto_lines = self.search([('sales_service_line_id.order_id', '=', order.id)])
                count = len(auto_lines) or 1
                line.sales_commission_amount = order.commission_amount / count
