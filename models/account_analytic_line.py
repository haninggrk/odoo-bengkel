# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    fleet_so_line_id = fields.Many2one(
        'sale.order.line',
        string='Fleet SO Line',
        copy=False,
        ondelete='set null',
        help='Sale order line that generated this timesheet entry (set by Fleet Sales).',
    )
    fleet_commission_amount = fields.Float(
        string='Commission',
        compute='_compute_fleet_commission_amount',
        store=True,
        digits='Account',
        help='Commission amount from the linked Fleet Sales order line.',
    )

    @api.depends('fleet_so_line_id', 'fleet_so_line_id.service_commission_amount',
                 'fleet_so_line_id.order_id.commission_mode',
                 'fleet_so_line_id.order_id.commission_amount')
    def _compute_fleet_commission_amount(self):
        for line in self:
            so_line = line.fleet_so_line_id
            if not so_line:
                line.fleet_commission_amount = 0.0
                continue
            order = so_line.order_id
            mode = order.commission_mode or 'per_product'
            if mode == 'per_product':
                line.fleet_commission_amount = so_line.service_commission_amount
            else:
                # For order-level commission modes, distribute evenly
                # across all auto-generated timesheet lines on that order.
                auto_lines = self.search([('fleet_so_line_id.order_id', '=', order.id)])
                count = len(auto_lines) or 1
                line.fleet_commission_amount = order.commission_amount / count
