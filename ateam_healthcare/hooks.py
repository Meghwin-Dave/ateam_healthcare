app_name = "ateam_healthcare"
app_title = "Ateam Healthcare"
app_publisher = "Meghwin Dave"
app_description = "Healthcare"
app_email = "meghwindave04@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ateam_healthcare",
# 		"logo": "/assets/ateam_healthcare/logo.png",
# 		"title": "Ateam Healthcare",
# 		"route": "/ateam_healthcare",
# 		"has_permission": "ateam_healthcare.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ateam_healthcare/css/ateam_healthcare.css"
# app_include_js = "/assets/ateam_healthcare/js/ateam_healthcare.js"

# include js, css files in header of web template
# web_include_css = "/assets/ateam_healthcare/css/ateam_healthcare.css"
# web_include_js = "/assets/ateam_healthcare/js/ateam_healthcare.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ateam_healthcare/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ateam_healthcare/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ateam_healthcare.utils.jinja_methods",
# 	"filters": "ateam_healthcare.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ateam_healthcare.install.before_install"
# after_install = "ateam_healthcare.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ateam_healthcare.uninstall.before_uninstall"
# after_uninstall = "ateam_healthcare.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ateam_healthcare.utils.before_app_install"
# after_app_install = "ateam_healthcare.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ateam_healthcare.utils.before_app_uninstall"
# after_app_uninstall = "ateam_healthcare.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ateam_healthcare.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "ateam_healthcare.ateam_healthcare.doctype.insurance_claim.insurance_claim.update_sales_invoice_eclaim_status_on_submit"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ateam_healthcare.tasks.all"
# 	],
# 	"daily": [
# 		"ateam_healthcare.tasks.daily"
# 	],
# 	"hourly": [
# 		"ateam_healthcare.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ateam_healthcare.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ateam_healthcare.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ateam_healthcare.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ateam_healthcare.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ateam_healthcare.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ateam_healthcare.utils.before_request"]
# after_request = ["ateam_healthcare.utils.after_request"]

# Job Events
# ----------
# before_job = ["ateam_healthcare.utils.before_job"]
# after_job = ["ateam_healthcare.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ateam_healthcare.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			["module", "in", ["Ateam Healthcare"]]
		]
	}
]