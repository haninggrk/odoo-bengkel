# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_gross_commission = fields.Boolean(
        string='Enable Gross Commission',
        config_parameter='fleet_sales.enable_gross_commission',
        default=False,
        help='Allow using gross commission modes and revenue commission input on Sales Orders.',
    )

    commission_mode = fields.Selection(
        selection=[
            ('per_product', 'Per Product Commission'),
            ('nett_service', 'NETT Service Commission'),
            ('nett_all', 'NETT All Commission'),
            ('gross_service', 'GROSS Service Commission'),
            ('gross_all', 'GROSS All Commission'),
        ],
        string='Sales Commission Mode',
        config_parameter='fleet_sales.commission_mode',
        default='per_product',
        help='Determines how Sales Order commission amount is calculated.',
    )
    timesheet_project_id = fields.Many2one(
        'project.project',
        string='Default Timesheet Project',
        config_parameter='fleet_sales.default_timesheet_project_id',
        help='Project used when creating auto task and timesheet entries from service sale lines.',
    )

    def set_values(self):
        super().set_values()
        for setting in self:
            if not setting.enable_gross_commission and setting.commission_mode in {'gross_service', 'gross_all'}:
                self.env['ir.config_parameter'].sudo().set_param('fleet_sales.commission_mode', 'per_product')
