import frappe
from datetime import datetime, timedelta


def calculate_weekly_attendance_and_add_salary():
    today = datetime.now()

    # Calculate the previous Sunday
    # today.weekday() returns 0 for Monday, 6 for Sunday
    days_since_sunday = today.weekday() + 1
    previous_sunday = today - timedelta(days=days_since_sunday + 7)
    last_saturday = previous_sunday + timedelta(days=6)

    # Get all employees
    employees = frappe.get_all('Employee', fields=['name', 'employee_name', 'ctc'])

    for employee in employees:
        # Get all check-ins for the employee from the previous Sunday to the last Saturday
        checkins = frappe.get_all('Employee Checkin', filters={
            'employee': employee.name,
            'time': ['between', [previous_sunday, last_saturday]]
        }, fields=['time'])

        print(checkins)

        attended_days = set()

        for checkin in checkins:
            checkin_date = checkin.time.date()  # Get the date part of the datetime
            attended_days.add(checkin_date)

        # Check if the employee attended all 7 days
        if len(attended_days) >= 7:
            amount = employee.ctc / 6
            add_additional_salary_for_full_attendance(employee.name, amount, previous_sunday)

    frappe.db.commit()


def add_additional_salary_for_full_attendance(employee_name, amount, payroll_date):
    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee_name
    additional_salary_doc.salary_component = 'Extra Day Allowance'
    additional_salary_doc.amount = amount
    additional_salary_doc.payroll_date = payroll_date
    additional_salary_doc.save()
    additional_salary_doc.submit()
