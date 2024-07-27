import frappe


def execute(filters=None):
    columns = get_columns()
    filters = frappe._dict(filters)
    conditions = get_conditions(filters)
    data = get_data(filters, conditions)
    return columns, data


def get_data(filters, conditions):
    query = f"""
    SELECT 
        checkin.employee AS `Employee ID`,
        checkin.employee_name AS `Employee Name`,
        DATE(checkin.time) AS `Log Day`,
        checkin.shift AS `Shift Type`,
        TIME(checkin.time) AS `Checkin Time`,
        TIME(checkout.time) AS `Checkout Time`,

        -- Total work hours in HH:MM:SS
        SEC_TO_TIME(
            TIMESTAMPDIFF(SECOND, checkin.time, checkout.time) + 
            IF(checkout.time < checkin.time, 86400, 0)
        ) AS `Total Work Hours`,

        -- Calculate overtime in HH:MM:SS
        SEC_TO_TIME(
            GREATEST(
                TIMESTAMPDIFF(SECOND, checkin.time, checkout.time) + 
                IF(checkout.time < checkin.time, 86400, 0) - 
                TIMESTAMPDIFF(SECOND, 
                    GREATEST(DATE_ADD(DATE(checkin.time), INTERVAL '08:00:00' HOUR_SECOND), checkin.time), 
                    LEAST(DATE_ADD(DATE(checkin.time), INTERVAL '17:00:00' HOUR_SECOND), checkout.time)
                ),
                0
            )
        ) AS `Overtime Hours`,

        -- Calculate overtime in minutes
        GREATEST(
            TIMESTAMPDIFF(SECOND, checkin.time, checkout.time) + 
            IF(checkout.time < checkin.time, 86400, 0) - 
            TIMESTAMPDIFF(SECOND, 
                GREATEST(DATE_ADD(DATE(checkin.time), INTERVAL '08:00:00' HOUR_SECOND), checkin.time), 
                LEAST(DATE_ADD(DATE(checkin.time), INTERVAL '17:00:00' HOUR_SECOND), checkout.time)
            ),
            0
        ) / 60 AS `Overtime Hours In Minutes`,

        -- Calculate working hours without overtime
        SEC_TO_TIME(
            GREATEST(
                LEAST(
                    TIMESTAMPDIFF(SECOND, checkin.time, checkout.time) + 
                    IF(checkout.time < checkin.time, 86400, 0),
                    TIMESTAMPDIFF(SECOND, 
                        GREATEST(DATE_ADD(DATE(checkin.time), INTERVAL '08:00:00' HOUR_SECOND), checkin.time), 
                        LEAST(DATE_ADD(DATE(checkin.time), INTERVAL '17:00:00' HOUR_SECOND), checkout.time)
                    )
                ),
                0
            )
        ) AS `Working Hours Without Overtime`

    FROM 
        `tabEmployee Checkin` checkin
    JOIN 
        `tabEmployee Checkin` checkout
    ON 
        checkin.employee = checkout.employee
        AND checkin.log_type = 'IN'
        AND checkout.log_type = 'OUT'
        AND checkin.time < checkout.time
    {f'WHERE {conditions}' if conditions else ''}
    ORDER BY 
        checkin.employee,
        checkin.time;
    """
    data = frappe.db.sql(query, filters, as_dict=1)
    return data


def get_conditions(filters):
    conditions = []
    employee = filters.get('employee')
    from_date = filters.get('from_date')
    to_date = filters.get('to_date')

    if from_date and to_date:
        conditions.append('DATE(checkin.time) BETWEEN %(from_date)s AND %(to_date)s')

    if employee:
        conditions.append('checkin.employee = %(employee)s')

    return ' AND '.join(conditions)


def get_columns():
    cols = [
        {
            'label': 'رقم الموظف',
            'fieldname': 'Employee ID',
            'fieldtype': 'Link',
            'options': 'Employee',
            'width': 150
        },
        {
            'label': 'اسم الموظف',
            'fieldname': 'Employee Name',
            'fieldtype': 'Data',
            'width': 150
        },
        {
            'label': 'حضور / انصراف',
            'fieldname': 'Log Day',
            'fieldtype': 'Date',
            'width': 100
        },
        {
            'label': 'نوع الشيفت',
            'fieldname': 'Shift Type',
            'fieldtype': 'Link',
            'options': 'Shift Type',
            'width': 100
        },
        {
            'label': 'وقت الحضور',
            'fieldname': 'Checkin Time',
            'fieldtype': 'Time',
            'width': 100
        },
        {
            'label': 'وقت الانصراف',
            'fieldname': 'Checkout Time',
            'fieldtype': 'Time',
            'width': 100
        },
        {
            'label': 'ساعات عمل اليوم',
            'fieldname': 'Total Work Hours',
            'fieldtype': 'Data',
            'width': 150
        },
        {
            'label': 'ساعات الاوفر تايم',
            'fieldname': 'Overtime Hours',
            'fieldtype': 'Data',
            'width': 150
        },
        {
            'label': 'الاوفر تايم بالدقائق',
            'fieldname': 'Overtime Hours In Minutes',
            'fieldtype': 'Float',
            'width': 150
        },
        {
            'label': 'ساعات عمل اليوم بدون الاوفر تايم',
            'fieldname': 'Working Hours Without Overtime',
            'fieldtype': 'Data',
            'width': 150
        },
    ]
    return cols
