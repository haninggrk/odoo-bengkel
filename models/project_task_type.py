# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    fold = fields.Boolean(default=False)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    fleet_group_id = fields.Many2one(
        'res.groups',
        string='Fleet Group',
        help='Only employees whose user belongs to this group can be assigned to tasks in this project.',
    )
