# -*- coding: utf-8 -*-
from odoo import fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = 'timesheets.analysis.report'

    sales_commission_amount = fields.Float(
        string='Commission',
        readonly=True,
        help='Commission amount from linked sales service line.',
    )

    def _select(self):
        return super()._select() + """,
            (
                CASE
                    WHEN FSO.commission_mode = 'per_product' THEN
                        COALESCE(FSL.service_commission_amount, 0.0)
                    WHEN FSO.commission_mode IN ('nett_service', 'nett_all') THEN
                        COALESCE(FSL.price_subtotal, 0.0) * (COALESCE(FSO.nett_commission_rate, 0.0) / 100.0)
                    WHEN FSO.commission_mode IN ('gross_service', 'gross_all') THEN
                        COALESCE(FSL.price_total, 0.0) * (COALESCE(FSO.revenue_commission_rate, 0.0) / 100.0)
                    ELSE 0.0
                END
            ) / COALESCE(NULLIF(COUNT(*) OVER (PARTITION BY A.sales_service_line_id), 0), 1)
            AS sales_commission_amount
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line FSL ON A.sales_service_line_id = FSL.id
            LEFT JOIN sale_order FSO ON FSO.id = FSL.order_id
        """
