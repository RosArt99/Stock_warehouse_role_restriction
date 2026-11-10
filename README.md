# Stock: Restrict Stock Levels by Role Warehouse

Odoo 19 Community · depends on `stock`, `mrp` and OCA `base_user_role`
([OCA/server-backend](https://github.com/OCA/server-backend), branch `19.0`).

## What it does

Adds an **Allowed warehouses** field to the OCA *User roles* form.
A user who holds a role with allowed warehouses only sees on-hand stock
(`stock.quant`, and therefore product *On Hand* quantities, *Inventory →
Operations → Adjustments → Physical Inventory* and, for administrators,
*Inventory → Reporting*) of those warehouses.
(In Odoo 19 the *Reporting* menu itself needs *Inventory / Administrator*, so a
shop-floor manager with *Inventory / User* looks at stock levels in
*Physical Inventory* and *Products* instead.)

* Role **without** allowed warehouses → no restriction.
* Users **without** such a role (e.g. the administrator) → see everything.
* Several restricted roles on one user → the union of their warehouses.

## Setup for the test task

1. Install `base_user_role` (OCA) and this module.
2. *Settings → Users & Companies → User Roles* → open **Керівник цеху**
   (implied group: *Manufacturing / User*, which includes *Inventory / User*).
3. Set **Allowed warehouses** = `Склад К1` (K1) and save.
4. Assign the role to the shop-floor manager user.

Logged in as that user, only K1 stock is visible; as admin, K1 and K2.

## How it works

* `models/res_users_role.py` – the `warehouse_ids` field (+ cache invalidation
  when it changes, because `ir.rule` domains are cached per user).
* `models/res_users.py` – computed `restricted_warehouse_ids`: the warehouses of
  the roles whose group the user currently holds. Group membership is the
  source of truth because `base_user_role` already keeps it in sync with the
  enabled/expired role lines.
* `security/stock_quant_security.xml` – one global record rule on `stock.quant`.
  It is a no-op for unrestricted users. For restricted users it limits quants in
  *internal* locations to the allowed warehouses; non-internal locations
  (virtual production, customers, …) stay reachable so manufacturing orders keep
  working.
* `views/res_users_role_views.xml` – shows the field on the role form.

## Scope / known limits

* Only stock **levels** (`stock.quant`) are restricted. Moves, transfers and
  forecasts of other warehouses are out of scope for this task.
* The role itself is built from standard Odoo groups; *Inventory / User* allows
  inventory adjustments (write on `stock.quant`) inside the allowed warehouses.

## Tests

```bash
odoo-bin -d <new_db> -i stock_warehouse_role_restriction \
    --test-enable --test-tags /stock_warehouse_role_restriction --stop-after-init
```

Covers: restricted user sees only the allowed warehouse, admin and role-less
users see everything, product on-hand quantities, access denied on another
warehouse's quant, immediate effect of changing the role's warehouses, role
without warehouses is unrestricted, and a restricted user can complete a
manufacturing order.
