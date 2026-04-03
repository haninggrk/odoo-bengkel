# -*- coding: utf-8 -*-
# This is the top-level __init__.py for the module.
# It imports the 'models' package, which in turn imports all model files.
# Odoo uses these imports to discover and register your models with the ORM.
from odoo import SUPERUSER_ID, api

from . import models


def post_init_hook(cr, registry):
	env = api.Environment(cr, SUPERUSER_ID, {})
	env['project.task.type'].search([]).write({'fold': False})
