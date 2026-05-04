from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    remark_stage_ids = fields.Many2many('construction.remark.stage', string='Remark Stages')
