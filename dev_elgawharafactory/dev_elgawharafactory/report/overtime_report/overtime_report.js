// Copyright (c) 2024, Abanoub Johnny and contributors
// For license information, please see license.txt

frappe.query_reports["Overtime Report"] = {
	"filters": [
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end()
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee"
        }
    ]
};
