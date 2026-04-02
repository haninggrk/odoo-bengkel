# -*- coding: utf-8 -*-
from odoo import fields, models


class FleetVehicleLogServices(models.Model):
    # Extend the fleet service model to add a back-link to the sales order
    # that triggered this service creation.
    _inherit = 'fleet.vehicle.log.services'

    # Many2one back-link: which sales order created this service record.
    # This allows navigating from the service back to the originating SO.
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        readonly=True,
        help='The sales order from which this service was created.',
    )
