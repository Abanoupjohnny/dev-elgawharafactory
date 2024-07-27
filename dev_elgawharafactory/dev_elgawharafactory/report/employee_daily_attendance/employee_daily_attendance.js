// Copyright (c) 2024, Abanoub Johnny and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Daily Attendance"] = {
	"filters": [
		{
			label: 'Employee',
			fieldname: 'employee',
			fieldtype: 'Link',
			options: 'Employee'
		},
		{
			label: 'From Date',
			fieldname: 'from_date',
			fieldtype: 'Date',
			reqd:0
		},
		{
			label: 'To Date',
			fieldname: 'to_date',
			fieldtype: 'Date',
			reqd:0
		},
	]
};
