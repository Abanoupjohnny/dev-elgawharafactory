from datetime import datetime, timedelta

import frappe
from frappe.utils import getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin


class CustomEmployeeCheckin(EmployeeCheckin):
    def validate(self):
        # Call the parent class's validate method
        super().validate()
        # Add your custom validation logic here
        self.custom_validation()

    def custom_validation(self):
        apply_late_entry(self)


def apply_late_entry(doc):
    if doc.is_new() and doc.log_type.lower() == "in":
        apply_late_entry_penalty(doc)


def apply_late_entry_penalty(doc):
    employee = frappe.get_doc('Employee', doc.employee)
    designation = employee.designation
    branch = employee.branch

    deduction_min = get_employee_deduction_min(doc, designation, branch)

    if deduction_min > 0:
        ctc = employee.ctc  # Weekly CTC
        deduction_amount = get_employee_deduction_amount(ctc, deduction_min)
        apply_additional_salary(employee, deduction_amount)


def get_employee_deduction_min(doc, designation, branch):
    check_in_time_str = doc.get("time")
    check_in_time = datetime.strptime(check_in_time_str, '%Y-%m-%d %H:%M:%S')

    late_entry_penalty = frappe.get_single('Late Entry Penalty')
    deduction_min = 0

    for penalty in late_entry_penalty.employee_penalties:
        if penalty.designation == designation and penalty.branch == branch:
            from_time = parse_penalty_time(penalty.get("from"))
            to_time = parse_penalty_time(penalty.get("to"))

            if from_time <= check_in_time.time() <= to_time:
                deduction_min = penalty.deduction
                break

    return deduction_min


def parse_penalty_time(time_value):
    if isinstance(time_value, timedelta):
        # Convert timedelta to time
        total_seconds = int(time_value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return datetime.strptime(f"{hours:02}:{minutes:02}:{seconds:02}", '%H:%M:%S').time()
    elif isinstance(time_value, str):
        return datetime.strptime(time_value, '%H:%M:%S').time()
    else:
        raise ValueError("Invalid time value")


def get_employee_deduction_amount(ctc, deduction_min):
    # Total working minutes per week
    days_per_week = 6
    hours_per_day = 12
    minutes_per_hour = 60
    total_working_minutes_per_week = days_per_week * hours_per_day * minutes_per_hour

    # Calculate the per minute wage
    per_minute_wage = ctc / total_working_minutes_per_week

    # Calculate the deduction amount
    deduction_amount = per_minute_wage * deduction_min

    return deduction_amount


def apply_additional_salary(employee, deduction_amount):
    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee
    additional_salary_doc.salary_component = 'Late Entry Penalty'
    additional_salary_doc.amount = deduction_amount
    additional_salary_doc.payroll_date = getdate()
    additional_salary_doc.save()
    additional_salary_doc.submit()
