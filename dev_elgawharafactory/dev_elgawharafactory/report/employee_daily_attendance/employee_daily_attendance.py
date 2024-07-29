import frappe


def execute(filters=None):
    try:
        columns = get_columns()
        filters = frappe._dict(filters)
        conditions = get_conditions(filters)
        data = get_data(filters)
        return columns, data
    except ImportError as e:
        frappe.throw(f"Import Error: {str(e)}")
    except Exception as e:
        frappe.throw(f"An error occurred: {str(e)}")


def get_data(filters):
    try:
        conditions = get_conditions(filters)
        query = f"""
        SELECT
            emp.name AS `Employee ID`,
            emp.designation AS `Designation`,
            emp.branch AS `Branch`,
            DATE(chk.time) AS `Attendance Date`,
            chk.shift AS `Shift Type`,
            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END) AS `Checkin Time`,
            MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END) AS `Checkout Time`,
            TIMEDIFF(
                MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), 
                MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)
            ) AS `Total Working Hours`,
            IF(
                TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                TIMEDIFF(
                    TIMEDIFF(
                        MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END),
                        MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)
                    ),
                    '12:00:00'
                ),
                '00:00:00'
            ) AS `Overtime Hours`,
            TIME_TO_SEC(
                IF(
                    TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                    TIMEDIFF(
                        TIMEDIFF(
                            MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END),
                            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)
                        ),
                        '12:00:00'
                    ),
                    '00:00:00'
                )
            ) / 60 AS `Overtime Minutes`,
            TIMESTAMPDIFF(
                MINUTE,
                MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END),
                MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END)
            ) / 60 - IF(
                TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                TIME_TO_SEC(
                    TIMEDIFF(
                        TIMEDIFF(
                            MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END),
                            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)
                        ),
                        '12:00:00'
                    )
                ) / 3600,
                0
            ) AS `Working Hours Without Overtime`,
            (TIMESTAMPDIFF(
                MINUTE,
                MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END),
                MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END)
            ) - IF(
                TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                TIME_TO_SEC(
                    TIMEDIFF(
                        TIMEDIFF(
                            MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END),
                            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)
                        ),
                        '12:00:00'
                    )
                ) / 60,
                0
            )) AS `Working Minutes Without Overtime`,
            ROUND(emp.ctc / 6, 2) AS `Daily Salary (EGP)`,
            emp.name AS `Employee ID`,
        IF(
            TIMESTAMPDIFF(MINUTE, chk.shift_start, MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > 60 OR
            TIMESTAMPDIFF(MINUTE, MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), chk.shift_end) > 60,
            1,
            0
        ) AS `Shift Missed Time`

        FROM
            `tabEmployee Checkin` chk
        JOIN
            `tabEmployee` emp ON chk.employee = emp.name
        LEFT JOIN
            `tabAdditional Salary` add_sal ON emp.name = add_sal.employee AND DATE(chk.time) BETWEEN add_sal.from_date AND add_sal.to_date
        {conditions}
        GROUP BY
            emp.name, DATE(chk.time)
        HAVING
            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END) IS NOT NULL
            AND MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END) IS NOT NULL
        ORDER BY
            emp.name, DATE(chk.time)
        """
        data = frappe.db.sql(query, filters, as_dict=1)

        for row in data:
            overtime_rate = get_overtime_rate(row['Employee ID'], row['Designation'],
                                              row['Branch'], row['Shift Type'])

            row['Overtime Pay (EGP)'] = round(
                (row['Overtime Minutes'] * (row['Daily Salary (EGP)'] / (12 * 60)) * overtime_rate),
                2
            )
            row['Total Hours (EGP)'] = row['Overtime Pay (EGP)'] + row['Daily Salary (EGP)']

            additional_salary = get_additional_salary(row['Employee ID'], row['Attendance Date'])
            row['Deductions'] = additional_salary.get('Deductions', 0)
            row['Earnings'] = additional_salary.get('Earnings', 0)

        return data
    except Exception as e:
        frappe.throw(f"An error occurred while fetching data: {str(e)}")


def get_conditions(filters):
    conditions = []

    if filters.get('from_date') and filters.get('to_date'):
        conditions.append("DATE(chk.time) BETWEEN %(from_date)s AND %(to_date)s")
    if filters.get('employee'):
        conditions.append("chk.employee = %(employee)s")
    if filters.get('designation'):
        conditions.append("emp.designation = %(designation)s")
    if filters.get('branch'):
        conditions.append("emp.branch = %(branch)s")

    if conditions:
        return "WHERE " + " AND ".join(conditions)
    else:
        return ""


def get_columns():
    return [
        {"label": "اسم الموظف", "fieldname": "Employee ID", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "المسمى الوظيفي", "fieldname": "Designation", "fieldtype": "Link", "options": "Designation",
         "width": 120},
        {"label": "الفرع", "fieldname": "Branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": "تاريخ الحضور", "fieldname": "Attendance Date", "fieldtype": "Date", "width": 120},
        {"label": "نوع الشيفت", "fieldname": "Shift Type", "fieldtype": "Link", "options": "Shift Type", "width": 100},
        {"label": "وقت الحضور", "fieldname": "Checkin Time", "fieldtype": "Data", "width": 100},
        {"label": "وقت الانصراف", "fieldname": "Checkout Time", "fieldtype": "Data", "width": 100},
        {"label": "الخصومات (EGP)", "fieldname": "Deductions", "fieldtype": "Currency", "width": 120},
        {"label": "الأرباح (EGP)", "fieldname": "Earnings", "fieldtype": "Currency", "width": 120},
        {"label": "ساعات الدوام", "fieldname": "Total Working Hours", "fieldtype": "Data", "width": 120},
        {"label": "ساعات العمل الإضافي", "fieldname": "Overtime Hours", "fieldtype": "Data", "width": 120},
        {"label": "دقائق العمل الإضافي", "fieldname": "Overtime Minutes", "fieldtype": "Float", "width": 120},
        {"label": "ساعات العمل بدون العمل الإضافي", "fieldname": "Working Hours Without Overtime", "fieldtype": "Data",
         "width": 150},
        {"label": "دقائق العمل بدون العمل الإضافي", "fieldname": "Working Minutes Without Overtime",
         "fieldtype": "Float", "width": 150},
        {"label": "الراتب اليومي (EGP)", "fieldname": "Daily Salary (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "أجر العمل الإضافي (EGP)", "fieldname": "Overtime Pay (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "اجمالي الساعات (EGP)", "fieldname": "Total Hours (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "تخلف عن مواعيد الشيفت", "fieldname": "Shift Missed Time", "fieldtype": "Check", "width": 120},
    ]


def get_overtime_rate(employee_id, designation, branch, shift_type):
    overtime_policy = get_employee_overtime_policy(designation, branch, shift_type)
    overtime_multiplier = 1.0
    if overtime_policy:
        overtime_multiplier = overtime_policy.extra_time_per

    return overtime_multiplier


def get_employee_overtime_policy(designation, branch, shift_type):
    employee_penalty_doc = frappe.get_single("Employee Penalty")

    # Check if there's an active overtime policy that matches the employee's criteria
    overtime_policy = None
    for policy in employee_penalty_doc.overtime_policy:
        if (policy.active and
                policy.designation == designation and
                policy.branch == branch and
                policy.shift_type == shift_type):
            overtime_policy = policy
            break

    return overtime_policy


def get_additional_salary(employee, date):
    try:
        query = """
        SELECT
            type,
            amount
        FROM
            `tabAdditional Salary`
        WHERE
            employee = %s AND %s BETWEEN from_date AND to_date
        """
        additional_salaries = frappe.db.sql(query, (employee, date), as_dict=True)

        earnings = 0
        deductions = 0

        for salary in additional_salaries:
            if salary.get('type') == 'Earning':
                earnings += salary.get('amount', 0)
            elif salary.get('type') == 'Deduction':
                deductions += salary.get('amount', 0)

        return {'Earnings': earnings, 'Deductions': deductions}
    except Exception as e:
        frappe.throw(f"Error fetching additional salary for {employee} on {date}: {str(e)}")
