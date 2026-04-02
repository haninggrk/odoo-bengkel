# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    license_plate = fields.Char(
        string='License Plate',
        copy=False,
        help='Vehicle license plate number. When the order is confirmed, '
             'a fleet vehicle will be created automatically with this license plate.'
    )
    
    fleet_vehicle_model_id = fields.Many2one(
        'fleet.vehicle.model',
        string='Vehicle Model',
        copy=True,
        help='Select the vehicle brand/model for the fleet vehicle to be created.'
    )
    
    fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Fleet Vehicle',
        copy=False,
        readonly=True,
        help='The fleet vehicle created from this sales order.'
    )
    
    fleet_vehicle_count = fields.Integer(
        string='Fleet Vehicle Count',
        compute='_compute_fleet_vehicle_count',
    )

    @api.depends('fleet_vehicle_id')
    def _compute_fleet_vehicle_count(self):
        for order in self:
            order.fleet_vehicle_count = 1 if order.fleet_vehicle_id else 0

    def action_confirm(self):
        """Override to create fleet vehicle when order is confirmed."""
        result = super().action_confirm()
        
        for order in self:
            if order.license_plate and not order.fleet_vehicle_id:
                order._create_fleet_vehicle()
        
        return result

    def _create_fleet_vehicle(self):
        """Create a fleet vehicle from the sales order."""
        self.ensure_one()
        
        vehicle_vals = {
            'license_plate': self.license_plate,
            'sale_order_id': self.id,
            'driver_id': self.partner_id.id,
            'company_id': self.company_id.id,
        }
        
        # Use selected vehicle model, or fall back to first available
        if self.fleet_vehicle_model_id:
            vehicle_vals['model_id'] = self.fleet_vehicle_model_id.id
        else:
            default_model = self.env['fleet.vehicle.model'].search([], limit=1)
            if default_model:
                vehicle_vals['model_id'] = default_model.id
        
        vehicle = self.env['fleet.vehicle'].create(vehicle_vals)
        self.fleet_vehicle_id = vehicle.id
        
        # Post message on sales order
        self.message_post(
            body=_('Fleet vehicle %s has been created from this sales order.') % vehicle.name
        )
        
        return vehicle

    def action_view_fleet_vehicle(self):
        """Open the fleet vehicle form view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fleet Vehicle'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'form',
            'res_id': self.fleet_vehicle_id.id,
            'context': {'create': False},
        }
