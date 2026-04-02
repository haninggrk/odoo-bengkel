# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        readonly=True,
        help='The sales order/quotation from which this vehicle was created.'
    )
    
    sale_order_name = fields.Char(
        string='Sales Order Reference',
        related='sale_order_id.name',
        readonly=True,
        store=True,
    )

    def action_view_sale_order(self):
        """Open the related sales order form view."""
        self.ensure_one()
        if not self.sale_order_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'context': {'create': False},
        }
