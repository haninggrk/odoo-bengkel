# -*- coding: utf-8 -*-
# This encoding declaration ensures Python handles special characters (UTF-8) correctly.

# Odoo ORM imports:
#   api    - decorators for model methods (e.g., @api.depends, @api.onchange)
#   fields - field types to define database columns (Char, Many2one, Integer, etc.)
#   models - base classes for Odoo models (Model, TransientModel, AbstractModel)
#   _      - translation function, wraps strings so they can be translated to other languages
from odoo import api, fields, models, _


class FleetVehicle(models.Model):
    # _inherit = 'fleet.vehicle' means we are EXTENDING the existing 'fleet.vehicle' model
    # (defined in the 'fleet' module). We don't define _name, so no new table is created.
    # Instead, our new fields are added to the existing fleet_vehicle table.
    _inherit = 'fleet.vehicle'

    # Many2one field creates a foreign key to the 'sale.order' table.
    # This links each vehicle to the sales order that generated it.
    #   copy=False   -> when duplicating a vehicle record, this field won't be copied
    #   readonly=True -> users can't manually edit this field in the UI (it's set by code)
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        readonly=True,
        help='The sales order/quotation from which this vehicle was created.'
    )

    # A "related" field acts like a shortcut to a field on a linked record.
    # Here it reads sale_order_id.name (the SO reference like "S00001") directly.
    #   store=True -> the value is stored in the database (not just computed on-the-fly),
    #                 which allows searching/grouping by this field efficiently.
    sale_order_name = fields.Char(
        string='Sales Order Reference',
        related='sale_order_id.name',
        readonly=True,
        store=True,
    )

    def action_view_sale_order(self):
        """Open the related sales order form view.
        
        This method is called when the user clicks the 'Sales Order' smart button
        on the fleet vehicle form. Uses _for_xml_id() to fetch the standard sale
        order action, then overrides it to show only this specific SO in form view.
        """
        self.ensure_one()

        if not self.sale_order_id:
            return

        # Fetch the standard sale order action and override for specific record
        action = self.env['ir.actions.act_window']._for_xml_id('sale.action_quotations_with_onboarding')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        action['context'] = {'create': False}
        return action
