from odoo import models, fields

class LoanRejectionWizard(models.Model):
    _name="loan.rejection.wizard"
    
    loan_id=fields.Many2one("employee.loan.request")
    rejetion_reason=fields.Char(required=True)
    
    def accept_the_reason(self):
        for rec in self:
            rec.loan_id.write({
            'state':"rejected"
        })
