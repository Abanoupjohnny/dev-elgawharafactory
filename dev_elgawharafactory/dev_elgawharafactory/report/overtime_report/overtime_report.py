# employee_checkin_report.py

import frappe
from frappe.utils import flt, getdate

def execute(filters=None):
    columns = [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Check-in Time", "fieldname": "check_in_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Check-out Time", "fieldname": "check_out_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Total Working Hours", "fieldname": "total_working_hours", "fieldtype": "Float", "width": 150},
        {"label": "Overtime Hours", "fieldname": "overtime_hours", "fieldtype": "Float", "width": 150},
        {"label": "Overtime Pay (EGP)", "fieldname": "overtime_pay", "fieldtype": "Currency", "width": 150},
        {"label": "Daily Salary (EGP)", "fieldname": "daily_salary", "fieldtype": "Currency", "width": 150},
        {"label": "Total Pay (EGP)", "fieldname": "total_pay", "fieldtype": "Currency", "width": 150},
    ]

    data = []
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    conditions = "WHERE 1=1"
    if start_date:
        conditions += f" AND time(chk.time) >= '{start_date}'"
    if end_date:
        conditions += f" AND time(chk.time) <= '{end_date}'"
    
    query = f"""
        SELECT
            emp.employee_name,
            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END) AS check_in_time,
            MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END) AS check_out_time,
            TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) AS total_working_hours,
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
            ) AS overtime_hours,
            ROUND(
                (TIME_TO_SEC(
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
                ) / 3600) * emp.custom_overtime_rate,
                2
            ) AS overtime_pay,
            ROUND(
                (TIME_TO_SEC(
                    IF(
                        TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                        '12:00:00',
                        TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END))
                    )
                ) / 60) * (emp.ctc / (6 * 12 * 60)),
                2
            ) AS daily_salary,
            ROUND(
                (TIME_TO_SEC(
                    IF(
                        TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END)) > '12:00:00',
                        '12:00:00',
                        TIMEDIFF(MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END), MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END))
                    )
                ) / 60) * (emp.ctc / (6 * 12 * 60)) +  (TIME_TO_SEC(
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
                ) / 3600) * emp.custom_overtime_rate,
                2
            ) AS total_pay
        FROM
            `tabEmployee Checkin` chk
        JOIN
            `tabEmployee` emp ON chk.employee = emp.name
        {conditions}
        GROUP BY
            emp.employee_name,
            DATE(chk.time)
        HAVING
            MIN(CASE WHEN chk.log_type = 'IN' THEN chk.time END) IS NOT NULL
            AND MAX(CASE WHEN chk.log_type = 'OUT' THEN chk.time END) IS NOT NULL
    """

    results = frappe.db.sql(query, as_dict=True)

    for row in results:
        data.append(row)

    return columns, data
