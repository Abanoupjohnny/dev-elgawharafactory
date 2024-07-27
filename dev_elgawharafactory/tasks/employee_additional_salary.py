import frappe
from datetime import datetime, timedelta


def calculate_weekly_attendance_and_add_salary():
    today = datetime.now()

    # Calculate the previous Sunday and the current Sunday
    # The current Sunday is the end of the previous week
    previous_sunday = today - timedelta(days=today.weekday() + 1 + 7)
    current_sunday = previous_sunday + timedelta(days=7)

    # Get all employees
    employees = frappe.get_all('Employee', fields=['name', 'employee_name', 'ctc'])

    for employee in employees:
        # Get all check-ins for the employee from the previous Sunday to the current Sunday
        checkins = frappe.get_all('Employee Checkin', filters={
            'employee': employee.name,
            'time': ['between', [previous_sunday, current_sunday]]
        }, fields=['time'])

        print(checkins)

        attended_days = set()

        for checkin in checkins:
            checkin_date = checkin.time.date()  # Get the date part of the datetime
            attended_days.add(checkin_date)

        # Check if the employee attended all 7 days
        if len(attended_days) >= 1:
            amount = employee.ctc / 6
            add_additional_salary_for_full_attendance(employee.name, amount)

    frappe.db.commit()


def add_additional_salary_for_full_attendance(employee_name, amount):
    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee_name
    additional_salary_doc.salary_component = 'Extra Day Allowance'
    additional_salary_doc.amount = amount
    additional_salary_doc.payroll_date = datetime.now().date()
    additional_salary_doc.save()
    additional_salary_doc.submit()
