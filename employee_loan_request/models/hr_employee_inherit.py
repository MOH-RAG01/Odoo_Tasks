from odoo import models,fields

class HrEmployeeInherit(models.Model):
    _inherit="hr.employee"
    
    related_laons_ids=fields.One2many("employee.loan.request","employee_id",string="Loans Related")