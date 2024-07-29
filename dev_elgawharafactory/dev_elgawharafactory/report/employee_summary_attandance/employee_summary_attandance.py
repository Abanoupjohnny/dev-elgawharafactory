import frappe
from dev_elgawharafactory.dev_elgawharafactory.report.employee_daily_attendance.employee_daily_attendance import \
    get_overtime_rate


def execute(filters=None):
    try:
        columns = get_columns()
        filters = frappe._dict(filters)
        conditions = get_conditions(filters)
        data = get_data(filters, conditions)
        return columns, data
    except ImportError as e:
        frappe.throw(f"Import Error: {str(e)}")
    except Exception as e:
        frappe.throw(f"An error occurred: {str(e)}")


def get_data(filters, conditions):
    try:
        query = f"""
        SELECT
            emp.name AS `Employee ID`,
            emp.designation AS `Designation`,
            emp.branch AS `Branch`,
            CONCAT(
                YEAR(att.attendance_date),
                '-W',
                LPAD(WEEK(att.attendance_date, 1), 2, '0')
            ) AS `Week`,
            DATE_SUB(DATE(att.attendance_date), INTERVAL (DAYOFWEEK(att.attendance_date) - 1) DAY) AS `Week Start Date`,
            DATE_ADD(DATE(att.attendance_date), INTERVAL (7 - DAYOFWEEK(att.attendance_date)) DAY) AS `Week End Date`,
            COUNT(CASE WHEN att.status = 'Present' THEN 1 END) AS `Days Present`,
            COUNT(CASE WHEN att.status = 'Absent' AND DAYOFWEEK(att.attendance_date) != 1 THEN 1 END) AS `Days Absent`,
            att.shift AS `Shift Type`,
            SUM(
                TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) / 60
            ) AS `Total Hours`,
            SUM(
                IF(
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) > 720,
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) - 720,
                    0
                )
            ) / 60 AS `Overtime Hours`,
            SUM(
                IF(
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) > 720,
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) - 720,
                    0
                )
            ) AS `Overtime Minutes`,
            ROUND(SUM(
                IF(
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) > 720,
                    TIMESTAMPDIFF(MINUTE, att.in_time, att.out_time) - 720,
                    0
                )
            ) / 60 * (ROUND(emp.ctc / 6, 2) / 12), 2) AS `Daily Salary (EGP)`,
            (SELECT
                SUM(CASE WHEN sal.salary_component = 'Deduction' THEN sal.amount ELSE 0 END)
            FROM
                `tabAdditional Salary` sal
            WHERE
                sal.employee = emp.name AND
                sal.from_date BETWEEN DATE_SUB(DATE(att.attendance_date), INTERVAL (DAYOFWEEK(att.attendance_date) - 1) DAY) AND DATE_ADD(DATE(att.attendance_date), INTERVAL (7 - DAYOFWEEK(att.attendance_date)) DAY)
            ) AS `Total Deductions (EGP)`,
            (SELECT
                SUM(CASE WHEN sal.salary_component = 'Earning' THEN sal.amount ELSE 0 END)
            FROM
                `tabAdditional Salary` sal
            WHERE
                sal.employee = emp.name AND
                sal.from_date BETWEEN DATE_SUB(DATE(att.attendance_date), INTERVAL (DAYOFWEEK(att.attendance_date) - 1) DAY) AND DATE_ADD(DATE(att.attendance_date), INTERVAL (7 - DAYOFWEEK(att.attendance_date)) DAY)
            ) AS `Total Earnings (EGP)`
        FROM
            `tabAttendance` att
        JOIN
            `tabEmployee` emp ON att.employee = emp.name
        {conditions}
        GROUP BY
            emp.name, CONCAT(YEAR(att.attendance_date), '-W', LPAD(WEEK(att.attendance_date, 1), 2, '0'))
        ORDER BY
            emp.name, `Week Start Date`
        """
        data = frappe.db.sql(query, filters, as_dict=1)

        for row in data:
            overtime_rate = get_overtime_rate(row['Employee ID'], row['Designation'], row['Branch'], row['Shift Type'])
            row['Overtime Pay (EGP)'] = round(
                (row['Overtime Minutes'] / 60 * (row['Daily Salary (EGP)'] / 12) * overtime_rate),
                2
            )
            row['Total Hours Pay (EGP)'] = row['Overtime Pay (EGP)'] + row['Daily Salary (EGP)']

        return data
    except Exception as e:
        frappe.throw(f"An error occurred while fetching data: {str(e)}")


def get_conditions(filters):
    conditions = []

    if filters.get('start_date') and filters.get('end_date'):
        conditions.append("att.attendance_date BETWEEN %(start_date)s AND %(end_date)s")
    if filters.get('employee'):
        conditions.append("att.employee = %(employee)s")
    if filters.get('branch'):
        conditions.append("emp.branch = %(branch)s")

    if filters.get('designation'):
        conditions.append("emp.designation = %(designation)s")

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
        {"label": "الأسبوع", "fieldname": "Week", "fieldtype": "Data", "width": 150},
        {"label": "التاريخ من", "fieldname": "Week Start Date", "fieldtype": "Date", "width": 120},
        {"label": "التاريخ الي", "fieldname": "Week End Date", "fieldtype": "Date", "width": 120},
        {"label": "عدد الحضور", "fieldname": "Days Present", "fieldtype": "Int", "width": 120},
        {"label": "عدد الغياب", "fieldname": "Days Absent", "fieldtype": "Int", "width": 120},
        {"label": "نوع الشيفت", "fieldname": "Shift Type", "fieldtype": "Link", "options": "Shift Type", "width": 150},
        {"label": "الخصومات(EGP)", "fieldname": "Total Deductions (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "المكافات(EGP)", "fieldname": "Total Earnings (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "ساعات العمل الكليه", "fieldname": "Total Hours", "fieldtype": "Float", "width": 120},
        {"label": "ساعات الاوفر تايم", "fieldname": "Overtime Hours", "fieldtype": "Float", "width": 120},
        {"label": "دقائق الاوفر تايم", "fieldname": "Overtime Minutes", "fieldtype": "Float", "width": 120},
        {"label": "ساعات العمل (EGP)", "fieldname": "Daily Salary (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": "ساعات الاوفر تايم (EGP)", "fieldname": "Overtime Pay (EGP)", "fieldtype": "Currency", "width": 120},
        {"label": " ساعات العمل الكليه(EGP)", "fieldname": "Total Hours Pay (EGP)", "fieldtype": "Currency",
         "width": 120}
    ]
