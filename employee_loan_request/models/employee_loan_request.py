from odoo import models,fields,api
from odoo.exceptions import ValidationError 
from dateutil.relativedelta import relativedelta


class EmployeeLoanRequest(models.Model):
    _name="employee.loan.request"
    _description="Employee Loan Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    
    name=fields.Char(readonly=True,default="new")
    employee_id=fields.Many2one("hr.employee",required=True,tracking=True)
    loan_amount=fields.Float(required=True,tracking=True,)
    number_of_installments=fields.Integer(required=True,tracking=True,default=1)
    installment_amount_per_month=fields.Float(readonly=True,
                                       compute="_compute_installment_amount",
                                       store=True,tracking=True,)
    request_date=fields.Date(default=fields.Date.context_today,readonly=True)
    start_date=fields.Date(required=True,tracking=True)
    loan_justification=fields.Text(tracking=True)
    state=fields.Selection([('draft','Draft'),
                            ('submitted','Submitted'),
                            ('approved','Approved'),
                            ('rejected','Rejected'),
                            ('ongoing','Ongoing'),
                            ('completed','Completed'),],tracking=True)
    installment_line_ids = fields.One2many("monthly.installment.lines","related_loan_id",string="The Monthly Installment")
    loan_move_line_id = fields.Many2one("account.move.line", string="Loan Move Line")

    
    def set_state_draft(self):
        for rec in self:
            rec.write({"state":"draft"})
    def set_state_submitted(self):
        for rec in self:
            rec.write({"state":"submitted"})
    def set_state_approved(self):
        return self.open_acceptance_wizard()
    def set_state_rejected(self):
        return self.open_rejection_wizard()
    def set_state_completed(self):
        for rec in self:
            rec.write({"state":"completed"})
            
    def get_loan_journal(self):
        return self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

    def get_loan_account(self):
        return self.env['account.account'].search([('code', '=', '230000')], limit=1)

    def get_bank_account(self):
        return self.env['account.account'].search([('code', '=', '101401')], limit=1)       
    
    @api.depends("loan_amount", "number_of_installments")
    def _compute_installment_amount(self):
        for rec in self:
            if rec.number_of_installments==0:
                return
            rec.installment_amount_per_month=rec.loan_amount/rec.number_of_installments
    
    @api.model_create_multi
    def create(self, vals_list):
        for rec in vals_list:
            if not rec.get("name") or rec.get("name")=="new":
                rec["name"]=self.env["ir.sequence"].next_by_code("emp_loan_req_seq_code")
        
        return super().create(vals_list)
    
    def loan_owner(self):
        action=self.env['ir.actions.actions']._for_xml_id('hr.open_view_employee_list_my')
        view_id=self.env.ref('hr.view_employee_form').id
        action['views']=[[view_id,'form']]
        action['res_id']=self.employee_id.id
        return action
    
    @api.constrains("loan_amount","number_of_installments")
    def _check_loanAmount_and_numberOfInstallments(self):
         for rec in self:
             if rec.loan_amount<1 or rec.number_of_installments<1:
                 raise ValidationError("Loan Amount or Number Of Installments Must be above zero")
    def open_rejection_wizard(self):
        action=self.env['ir.actions.actions']._for_xml_id('employee_loan_request.rejection_action')
        action['context']={'default_loan_id':self.id}
        return action
    def open_acceptance_wizard(self):
        action=self.env["ir.actions.actions"]._for_xml_id("employee_loan_request.loan_accpetance_wizard_action")
        action['context']={"default_loan_id":self.id}
        return action

    def intallment_lines_generation(self):
        for rec in self:
            for i in range(rec.number_of_installments):
                due_date = rec.start_date + relativedelta(months=i)
                self.env['monthly.installment.lines'].create({
                "related_loan_id":rec.id,
                "sequence":i+1,
                "amount":rec.installment_amount_per_month,
                "state":"pending",
                "due_date":due_date,
                })
            move=self.env['account.move'].create({
                "journal_id":rec.get_loan_journal().id,
                "date":rec.request_date,
                "ref":rec.name,
                "line_ids":[(0,0,{
                    'account_id': rec.get_loan_account().id,
                    'name': f'Loan to {rec.employee_id.name}',
                    'debit': rec.loan_amount,
                    'credit': 0.0,
                }),
                (0,0,{
                    'account_id': rec.get_bank_account().id,
                    'name': f'Loan to {rec.employee_id.name}',
                    'debit': 0.0,
                    'credit': rec.loan_amount,})
                ]
                
            })
            move.action_post()
            rec.loan_move_line_id = move.line_ids.filtered(
                lambda l: l.account_id.id == rec.get_loan_account().id and l.debit > 0
            )   
    def update_loan_payment(self):

        today = fields.Date.today()
        loans = self.search([('state', '=', 'approved'),('start_date', '<=', today),])
        for loan in loans:
            loan.write({"state": "ongoing"})
        
        records=self.env["monthly.installment.lines"].search([("state","=","pending"),("due_date", "<=", today)])
        for rec in records:
            rec.write({
                "state":"paid"
            })
            move=self.env["account.move"].create({
                "journal_id":self.get_loan_journal().id,
                "date":rec.due_date,
                "ref":f"Installment for {rec.related_loan_id.name}",
                "line_ids":[(0,0,{
                    "account_id":self.get_bank_account().id,
                    'name': f'Loan to {rec.related_loan_id.employee_id.name}',
                    "debit":rec.amount,
                    "credit":0.0
                    }),
                    (0,0,{
                        "account_id":self.get_loan_account().id,
                        'name': f'Loan to {rec.related_loan_id.employee_id.name}',
                        "debit":0.0,
                        'credit':rec.amount
                    })        
                    ]
            })
            move.action_post()
            installment_line = move.line_ids.filtered(
            lambda l: l.account_id.id == self.get_loan_account().id and l.credit > 0
            )
            loan_line = rec.related_loan_id.loan_move_line_id
            if loan_line and installment_line:
                (loan_line | installment_line).reconcile()

    

class MonthlyInstallmentLines(models.Model):
    _name="monthly.installment.lines"
    
    related_loan_id=fields.Many2one("employee.loan.request")
    sequence = fields.Integer(string="Installment#")
    amount = fields.Float()
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid')])
    due_date=fields.Date()
