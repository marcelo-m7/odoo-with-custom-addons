from odoo import models, fields, api


class RemarkCategory(models.Model):
    _name = 'construction.remark.category'
    _description = 'Remark Category'

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color')


class RemarkStage(models.Model):
    _name = 'construction.remark.stage'
    _description = 'Remark Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    project_ids = fields.Many2many('project.project', string='Projects')


class Remark(models.Model):
    _name = 'construction.remark'
    _description = 'Remark'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Name', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'Low Priority'),
        ('1', 'Medium Priority'),
        ('2', 'High Priority'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ], string='State', default='in_progress', tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    description = fields.Html('Description')
    date_deadline = fields.Date('Deadline')
    date = fields.Date('Date', default=fields.Date.context_today)
    reference = fields.Char('Reference')
    location = fields.Char('Location')
    remark_category_ids = fields.Many2many(
        'construction.remark.category', string='Categories',
    )
    event_id = fields.Many2one('calendar.event', string='Event')
    update_id = fields.Many2one('project.update', string='Project Update')
    partner_id = fields.Many2one('res.partner', string='Partner')
    stage_id = fields.Many2one(
        'construction.remark.stage', string='Stage',
        group_expand='_read_group_stage_ids', tracking=True,
    )

    def _read_group_stage_ids(self, stages, domain):
        """Show all stages relevant to the current project in kanban."""
        project_id = self.env.context.get('default_project_id')
        if project_id:
            return stages.search([('project_ids', 'in', project_id)])
        return stages.search([])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._generate_remark_reference(vals)
        res = super().create(vals_list)
        res._assign_default_stage()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'project_id' in vals:
            self._assign_default_stage()
        return res

    def _generate_remark_reference(self, vals):
        if vals.get('reference'):
            return
        
        project_id = vals.get('project_id')
        project = self.env['project.project'].browse(project_id) if project_id else None
        
        if project:
            last_ref = self.search([('project_id', '=', project.id), ('reference', '!=', False)], order='reference DESC', limit=1)
            if last_ref:
                pid, rid = last_ref.reference.split('-')
            elif hasattr(project, 'sale_order_id') and project.sale_order_id:
                pid, rid = project.sale_order_id.name[1:], 0
            elif project.name.split('-')[0].strip().startswith('S') and project.name.split('-')[0].strip()[1:].isnumeric():
                pid, rid = project.name.split('-')[0].strip()[1:], 0
            else:
                last_rem = self.search([('reference', 'like', '00000-')], order='reference DESC', limit=1)
                pid, rid = last_rem.reference.split('-') if last_rem else ("00000", 0)
        else:
            last_rem = self.search([('reference', 'like', '00000-')], order='reference DESC', limit=1)
            pid, rid = last_rem.reference.split('-') if last_rem else ("00000", 0)
            
        vals['reference'] = f"{pid}-{int(rid) + 1:05d}"
        
    def _assign_default_stage(self):
        for record in self:
            if not record.stage_id and record.project_id:
                # Provide a fallback default stage to project if it has none
                if not record.project_id.remark_stage_ids:
                    stage = self.env.ref('construction_developer.project_remark_stage_1', raise_if_not_found=False)
                    if stage:
                        stage.write({'project_ids': [(4, record.project_id.id)]})
                
                # Fetch first assigned stage for the project
                first_stage = self.env['construction.remark.stage'].search([('project_ids', 'in', record.project_id.id)], order='sequence', limit=1)
                if first_stage:
                    record.stage_id = first_stage.id
