from odoo import api, models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    cost_nature = fields.Selection([
        ('labour', 'Labour'),
        ('material', 'Material'),
        ('equipment', 'Equipment'),
    ], string='Cost Nature')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cost_nature') and vals.get('parent_id'):
                parent_category = self.browse(vals['parent_id'])
                if parent_category.cost_nature:
                    vals['cost_nature'] = parent_category.cost_nature
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for category in self:
            if not category.cost_nature and category.parent_id.cost_nature:
                # Bypass 'write' to prevent recursion if not careful, though direct write is fine here
                super(ProductCategory, category).write({'cost_nature': category.parent_id.cost_nature})
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_matches_category = fields.Boolean(string='UoM Matches Category')
    bom_template_count = fields.Integer(
        string='BoM Count', compute='_compute_bom_template_count',
    )

    @api.depends('product_variant_ids')
    def _compute_bom_template_count(self):
        for tmpl in self:
            tmpl.bom_template_count = self.env['mrp.bom'].search_count([
                ('product_tmpl_id', '=', tmpl.id),
                ('is_template', '=', True),
            ])


class ProductProduct(models.Model):
    _inherit = 'product.product'

    bom_template_id = fields.Many2one('mrp.bom', string='BoM Template')
    bom_template_count = fields.Integer(
        string='BoM Count', compute='_compute_bom_template_count',
    )

    def _compute_bom_template_count(self):
        for product in self:
            product.bom_template_count = self.env['mrp.bom'].search_count([
                ('product_id', '=', product.id),
                ('is_template', '=', True),
            ])

    def write(self, vals):
        res = super().write(vals)
        if 'lst_price' in vals or 'standard_price' in vals:
            for product in self:
                boms = self.env['mrp.bom.line'].search([
                    ('product_id', '=', product.id),
                    ('bom_id.is_template', '=', True)
                ])
                if boms:
                    boms.write({
                        'unit_price': product.lst_price,
                        'unit_cost': product.standard_price,
                    })
        return res
