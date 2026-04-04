# -*- coding: utf-8 -*-
from odoo import fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = 'timesheets.analysis.report'

    fleet_commission_amount = fields.Float(
        string='Commission',
        readonly=True,
        help='Commission amount from Fleet Sales service line.',
    )

    def _select(self):
        return super()._select() + """,
            (
                CASE
                    WHEN SO.commission_mode = 'per_product' THEN
                        COALESCE(SOL.service_commission_amount, 0.0)
                    WHEN SO.commission_mode IN ('nett_service', 'nett_all') THEN
                        COALESCE(SOL.price_subtotal, 0.0) * (COALESCE(SO.nett_commission_rate, 0.0) / 100.0)
                    WHEN SO.commission_mode IN ('gross_service', 'gross_all') THEN
                        COALESCE(SOL.price_total, 0.0) * (COALESCE(SO.revenue_commission_rate, 0.0) / 100.0)
                    ELSE 0.0
                END
            ) / COALESCE(NULLIF(COUNT(*) OVER (PARTITION BY A.fleet_so_line_id), 0), 1)
            AS fleet_commission_amount
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line SOL ON A.fleet_so_line_id = SOL.id
            LEFT JOIN sale_order SO ON SO.id = SOL.order_id
        """
