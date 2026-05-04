from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    so_contract_type = fields.Selection([
        ('unspecified', 'Unspecified'),
        ('fixed_price', 'Fixed Price'),
        ('open_book', 'Open Book'),
        ('per_line', 'Per Line'),
    ], string='Contract Type')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._initialize_sol_sequences()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'order_line' in vals:
            self._initialize_sol_sequences()
        return res

    def _initialize_sol_sequences(self):
        for record in self:
            sequences = record.order_line.mapped('sequence')
            if not sequences:
                continue
            if len(sequences) != len(set(sequences)):
                new_sols = []
                for sol_i, sol in enumerate(record.order_line):
                    previous_same_sequences = sum(seq == sequences[sol_i] for seq in sequences[:sol_i + 1])
                    new_sols.append((sol.id, sol.sequence + (previous_same_sequences / sequences.count(sol.sequence))))
                new_sols.sort(key=lambda soltup: soltup[1])
                seqs = {sid: i for i, (sid, _) in enumerate(new_sols)}
            else:
                seqs = {sol.id: i for i, sol in enumerate(record.order_line.sorted('sequence'))}
            
            for sol in record.order_line:
                if sol.sequence != seqs[sol.id] + 1:
                    sol.sequence = seqs[sol.id] + 1


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    reference = fields.Char(string='Reference')
    delivered_progress = fields.Float(string='Delivered Progress')
    quantity_increment = fields.Float(string='Quantity Increment')
    progress_increment = fields.Float(string='Progress Increment')
    current_progress = fields.Float(string='Current Progress')
    service_policy = fields.Selection(
        related='product_id.service_policy', string='Service Policy',
    )
    is_undeliverable = fields.Boolean(string='Is Undeliverable')
    is_deliverable = fields.Boolean(string='Is Deliverable')
    display_button = fields.Boolean(string='Display Button')
    sol_contract_type = fields.Selection([
        ('fixed_price', 'Fixed Price'),
        ('open_book', 'Open Book'),
    ], string='Line Contract Type', default='fixed_price')
    cost_nature = fields.Selection(
        related='product_id.product_tmpl_id.categ_id.cost_nature',
        string='Cost Nature',
    )
    category_id = fields.Many2one(
        'product.category',
        related='product_id.product_tmpl_id.categ_id',
        string='Category',
    )
    line_bom_id = fields.Many2one('mrp.bom', string='Linked BoM')

    @api.onchange('quantity_increment')
    def _onchange_quantity_increment(self):
        for record in self:
            record.progress_increment = (record.quantity_increment / record.product_uom_qty) if record.product_uom_qty > 0 else 0.0

    @api.onchange('progress_increment')
    def _onchange_progress_increment(self):
        for record in self:
            record.quantity_increment = record.progress_increment * record.product_uom_qty

    def action_update_section_progress(self):
        self.ensure_one()
        lines = self.order_id.order_line.sorted(key=lambda sol: sol.sequence)
        i = lines.ids.index(self.id) + 1
        while (i < len(lines) and
              ((self.display_type == 'line_section' and lines[i].display_type != 'line_section')
              or (self.display_type == 'line_note' and lines[i].display_type not in ['line_note', 'line_section']))):
            if hasattr(lines[i], 'is_deliverable') and lines[i].is_deliverable:
                increment = min(lines[i].product_uom_qty - lines[i].qty_delivered, lines[i].product_uom_qty * self.progress_increment)
                percentage = increment / lines[i].product_uom_qty if lines[i].product_uom_qty else 0.0
                lines[i].write({
                    'quantity_increment': increment,
                    'progress_increment': percentage
                })
            i += 1
        self.progress_increment = 0
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def action_update_qty_delivered(self):
        for sol in self:
            sol.write({
                'qty_delivered': sol.qty_delivered + sol.quantity_increment,
                'quantity_increment': 0,
                'progress_increment': 0
            })
        return {
            'type': 'ir.actions.client', 
            'tag': 'display_notification', 
            'params': {
                'message': "Delivered quantities updated.", 
                'type': 'success', 
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_associated_work_item()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._create_associated_work_item()
        return res

    def _create_associated_work_item(self):
        for sol in self:
            if not sol.line_bom_id and sol.product_id.bom_template_id:
                bom = sol.product_id.bom_template_id.copy({
                    'sale_order_line_id': sol.id,
                    'is_template': False,
                })
                sol.line_bom_id = bom.id


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reference = fields.Char(string='Construction Reference')
