from odoo import api, fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        relation="res_users_role_stock_warehouse_rel",
        column1="role_id",
        column2="warehouse_id",
        string="Allowed warehouses",
        help="Users with this role only see the stock levels of these warehouses. "
        "Leave empty for no restriction.",
    )

    def _clear_rule_cache(self):
        # ir.rule domains are cached per user (registry cache), and
        # ``res.users.restricted_warehouse_ids`` lives in the ORM field cache.
        # The quant rule depends on this field, so drop both when it changes.
        self.env.registry.clear_cache()
        self.env.invalidate_all()

    @api.model_create_multi
    def create(self, vals_list):
        roles = super().create(vals_list)
        if any("warehouse_ids" in vals for vals in vals_list):
            roles._clear_rule_cache()
        return roles

    def write(self, vals):
        res = super().write(vals)
        if "warehouse_ids" in vals:
            self._clear_rule_cache()
        return res
