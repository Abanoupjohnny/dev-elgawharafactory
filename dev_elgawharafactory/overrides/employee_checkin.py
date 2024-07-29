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
        apply_penalty(self)


def apply_penalty(doc):
    if doc.is_new():
        if doc.log_type.lower() == "in":
            apply_late_entry_penalty(doc)
        else:
            apply_overtime_policy(doc)


def apply_late_entry_penalty(doc):
    employee = frappe.get_doc('Employee', doc.employee)
    designation = employee.designation
    branch = employee.branch

    deduction_min = get_employee_deduction_min(doc, designation, branch)

    if deduction_min > 0:
        ctc = employee.ctc  # Weekly CTC
        deduction_amount = get_employee_deduction_amount(ctc, deduction_min)
        apply_additional_salary(employee=employee, amount=deduction_amount,
                                payroll_date=getdate(),
                                salary_component='Late Entry Penalty')


def apply_overtime_policy(doc):
    extra_minutes = calculate_overtime_minutes(doc)
    if extra_minutes:
        employee_doc = frappe.get_doc("Employee", doc.employee)
        ctc = employee_doc.ctc

        overtime_policy = get_employee_overtime_policy(doc, employee_doc)
        if overtime_policy:
            overtime_multiplier = overtime_policy.extra_time_per
            extra_pay = calculate_extra_pay(ctc, extra_minutes, overtime_multiplier)
            apply_additional_salary(employee=doc.employee, amount=extra_pay,
                                    payroll_date=getdate(),
                                    salary_component='Over Time')


def get_employee_deduction_min(doc, designation, branch):
    check_in_time_str = doc.get("time")
    check_in_time = datetime.strptime(check_in_time_str, '%Y-%m-%d %H:%M:%S')

    late_entry_penalty = frappe.get_single('Employee Penalty')
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


def calculate_overtime_minutes(doc):
    # Convert shift and actual times to datetime objects
    actual_start = datetime.strptime(doc.get("shift_actual_start"), '%Y-%m-%d %H:%M:%S')
    actual_end = datetime.strptime(doc.get("shift_actual_end"), '%Y-%m-%d %H:%M:%S')
    shift_start = datetime.strptime(doc.get("shift_start"), '%Y-%m-%d %H:%M:%S')
    shift_end = datetime.strptime(doc.get("shift_end"), '%Y-%m-%d %H:%M:%S')

    # Calculate total working time
    total_working_time = actual_end - actual_start

    # Calculate shift duration
    shift_duration = shift_end - shift_start

    # Calculate overtime
    if total_working_time > shift_duration:
        overtime = total_working_time - shift_duration
    else:
        overtime = timedelta(0)

    # Convert overtime to minutes
    overtime_minutes = overtime.total_seconds() / 60

    return overtime_minutes


def calculate_extra_pay(weekly_salary, extra_minutes, overtime_multiplier):
    # Calculate daily salary
    daily_hours = 12
    working_days_per_week = 6

    daily_salary = weekly_salary / working_days_per_week

    # Calculate hourly rate
    hourly_rate = daily_salary / daily_hours

    # Calculate rate per minute
    rate_per_minute = hourly_rate / 60

    # Calculate overtime rate per minute
    overtime_rate_per_minute = rate_per_minute * overtime_multiplier

    # Calculate total extra pay
    total_extra_pay = overtime_rate_per_minute * extra_minutes

    return round(total_extra_pay, 2)


def get_employee_overtime_policy(doc, employee_doc):
    employee_penalty_doc = frappe.get_single("Employee Penalty")

    # Check if there's an active overtime policy that matches the employee's criteria
    overtime_policy = None
    for policy in employee_penalty_doc.overtime_policy:
        if (policy.active and
                policy.designation == employee_doc.designation and
                policy.branch == employee_doc.branch and
                policy.shift_type == doc.shift_type):
            overtime_policy = policy
            break

    return overtime_policy


def apply_additional_salary(employee, amount, payroll_date, salary_component):
    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee
    additional_salary_doc.salary_component = salary_component
    additional_salary_doc.amount = amount
    additional_salary_doc.payroll_date = payroll_date
    additional_salary_doc.save()
    additional_salary_doc.submit()
