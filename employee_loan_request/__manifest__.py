{
    "name":"Employee Loan Request",
    "category":"Task Test",
    "author":"Mo-Ragab",
    "description":"Module for submitting requests for company loans",
    'icon': 'employee_loan_request/static/description/give-money.png',
    #######################################################################
    "installable": True,
    "application": True,
    "license":"LGPL-3",
    "version":"17.0.1.0.0",
    #######################################################################
    "depends":["base","mail","hr","account"],
    "data":[
            "security/ir.model.access.csv",
            "data/emp_loan_req_seq.xml",
            "views/hr_employee_related_loan.xml",
            "views/employee_loan_request_view.xml",
            "views/menu_views.xml",
            "wizard/loan_rejection_wizard_views.xml",
            "wizard/loan_acceptance_wizard_views.xml",

            ],
}