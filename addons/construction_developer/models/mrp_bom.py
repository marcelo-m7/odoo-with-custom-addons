from odoo import api, models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_template = fields.Boolean(string='Is Template')
    unit_cost = fields.Monetary(
        string='Unit Cost', compute='_compute_totals',
        store=True, currency_field='currency_id',
    )
    unit_price = fields.Monetary(
        string='Unit Price', compute='_compute_totals',
        store=True, currency_field='currency_id',
    )
    unit_margin = fields.Float(
        string='Margin (%)', compute='_compute_totals', store=True,
    )
    is_margin_fixed = fields.Boolean(string='Is Margin Fixed')
    reference = fields.Char(string='Construction Reference')
    unit_custom_id = fields.Many2one('uom.uom', string='Custom Unit')
    targeted_so_id = fields.Many2one('sale.order', string='Target Sale Order')
    product_bom_template_id = fields.Many2one(
        'mrp.bom', related='product_id.bom_template_id', string='Product BoM Template',
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )

    @api.depends(
        'bom_line_ids.unit_cost',
        'bom_line_ids.unit_price',
        'bom_line_ids.product_qty',
    )
    def _compute_totals(self):
        for bom in self:
            total_cost = sum(
                line.unit_cost * line.product_qty
                for line in bom.bom_line_ids
            )
            total_price = sum(
                line.unit_price * line.product_qty
                for line in bom.bom_line_ids
            )
            bom.unit_cost = total_cost
            bom.unit_price = total_price
            bom.unit_margin = (
                (total_price - total_cost) / total_price
                if total_price else 0.0
            )


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    line_reference = fields.Char(string='Line Reference')
    unit_id = fields.Many2one(
        'uom.uom', related='product_id.uom_id', string='Product Unit',
    )
    demand = fields.Float(string='Demand')
    consumed = fields.Float(string='Consumed')
    unit_cost = fields.Monetary(
        string='Unit Cost', compute='_compute_unit_cost_price',
        store=True, currency_field='currency_id',
    )
    unit_price = fields.Monetary(
        string='Unit Price', compute='_compute_unit_cost_price',
        store=True, currency_field='currency_id',
    )
    margin = fields.Float(
        string='Margin (%)', compute='_compute_margin', store=True,
    )
    category_id = fields.Many2one(
        'product.category', related='product_id.categ_id',
        string='Category', store=True,
    )
    cost_nature = fields.Selection(
        related='product_id.categ_id.cost_nature',
        string='Cost Nature', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='bom_id.company_id.currency_id',
    )

    @api.depends('product_id', 'product_id.standard_price', 'product_id.list_price')
    def _compute_unit_cost_price(self):
        for line in self:
            line.unit_cost = line.product_id.standard_price if line.product_id else 0.0
            line.unit_price = line.product_id.list_price if line.product_id else 0.0

    @api.depends('unit_cost', 'unit_price')
    def _compute_margin(self):
        for line in self:
            line.margin = (
                (line.unit_price - line.unit_cost) / line.unit_price
                if line.unit_price else 0.0
            )
