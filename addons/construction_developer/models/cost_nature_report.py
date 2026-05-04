from odoo import fields, models, tools


class CostNatureAnalysisReport(models.Model):
    _name = 'construction.cost.nature.analysis.report'
    _description = 'Cost Nature Analysis Report'
    _auto = False
    _order = 'margin desc, total_cost desc'

    category_id = fields.Many2one('product.category', string='Category', readonly=True)
    cost_nature = fields.Selection([
        ('labour', 'Labour'),
        ('material', 'Material'),
        ('equipment', 'Equipment'),
    ], string='Cost Nature', readonly=True)
    total_cost = fields.Float('Total Cost', readonly=True)
    total_price = fields.Float('Total Price', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    so_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    bom_id = fields.Many2one('mrp.bom', string='BoM', readonly=True)
    margin = fields.Float('Margin', readonly=True)
    margin_percent = fields.Float('Margin Percent', readonly=True)
    quantity = fields.Float('Quantity', readonly=True)
    margin_share = fields.Float('Margin Share', readonly=True)
    cost_share = fields.Float('Cost Share', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW construction_cost_nature_analysis_report AS (
                SELECT
                    bl.id AS id,
                    bl.product_id,
                    bl.bom_id,
                    pt.categ_id AS category_id,
                    pc.cost_nature,
                    bl.sale_order_id AS so_id,
                    bl.product_qty AS quantity,
                    bl.unit_cost * bl.product_qty AS total_cost,
                    bl.unit_price * bl.product_qty AS total_price,
                    (bl.unit_price - bl.unit_cost) * bl.product_qty AS margin,
                    CASE
                        WHEN bl.unit_price > 0
                        THEN (bl.unit_price - bl.unit_cost) / bl.unit_price
                        ELSE 0.0
                    END AS margin_percent,
                    0.0 AS margin_share,
                    0.0 AS cost_share
                FROM mrp_bom_line bl
                JOIN product_product pp ON pp.id = bl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN product_category pc ON pc.id = pt.categ_id
            )
        """)
