from odoo import fields,models

class LoanAcceptanceWizard(models.TransientModel):
    _name="loan.acceptance.wizard"
    
    loan_id=fields.Many2one("employee.loan.request")
    related_loan_amount = fields.Float(
        related="loan_id.loan_amount",
        string="Loan Amount",
        readonly=True)
    
    def loan_accept(self):
        for rec in self:
            rec.loan_id.write({"state":"approved"})
            rec.loan_id.intallment_lines_generation()