# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    timesheet_project_id = fields.Many2one(
        'project.project',
        string='Default Timesheet Project',
        config_parameter='kedoo_sales_timesheet_assignment.default_project_id',
        help='Project used when creating auto task and timesheet entries from assigned service lines.',
    )
