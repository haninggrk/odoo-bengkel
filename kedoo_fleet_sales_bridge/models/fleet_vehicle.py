# -*- coding: utf-8 -*-
from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        readonly=True,
        help='Sales order/quotation from which this vehicle was created.',
    )
    sale_order_name = fields.Char(
        string='Sales Order Reference',
        related='sale_order_id.name',
        readonly=True,
        store=True,
    )
    service_date = fields.Date(
        string='Service Date',
        related='sale_order_id.service_date',
        readonly=True,
        store=True,
    )

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return

        action = self.env['ir.actions.act_window']._for_xml_id('sale.action_quotations_with_onboarding')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        action['context'] = {'create': False}
        return action
