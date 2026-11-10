{
    "name": "Stock: Restrict Stock Levels by Role Warehouse",
    "summary": "Limit the stock levels a user role can see to selected warehouses",
    "description": """
Adds an "Allowed warehouses" field to the OCA *User roles* (base_user_role).
Users holding a role with allowed warehouses only see on-hand stock
(stock.quant) located in those warehouses. Users without such a role
(e.g. the administrator) keep seeing everything.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "license": "LGPL-3",
    "author": "Test task",
    "depends": ["stock", "mrp", "base_user_role"],
    "data": [
        "security/stock_quant_security.xml",
        "views/res_users_role_views.xml",
    ],
    "installable": True,
    "application": False,
}
