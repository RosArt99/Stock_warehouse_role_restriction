from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    restricted_warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        compute="_compute_restricted_warehouse_ids",
        compute_sudo=True,
        string="Restricted to warehouses",
        help="Warehouses this user is limited to through their roles. "
        "Empty means the user is not restricted. Used by the stock.quant record rule.",
    )

    @api.depends_context("uid")
    def _compute_restricted_warehouse_ids(self):
        Role = self.env["res.users.role"].sudo()
        for user in self:
            # base_user_role keeps each role's group in sync with the user's
            # *currently enabled* roles (including its date-based activation),
            # so group membership is the single source of truth here.
            roles = Role.search(
                [
                    ("group_id", "in", user.all_group_ids.ids),
                    ("warehouse_ids", "!=", False),
                ]
            )
            user.restricted_warehouse_ids = roles.warehouse_ids
