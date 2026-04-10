# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    fold = fields.Boolean(default=False)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    sales_assignment_group_id = fields.Many2one(
        'res.groups',
        string='Sales Assignment Group',
        help='Only employees with users in this group can be assigned for tasks in this project.',
    )
