from odoo import models, fields

class ProjectUpdate(models.Model):
    _inherit = 'project.update'
    remark_ids = fields.One2many('construction.remark', 'update_id', string='Remarks')
