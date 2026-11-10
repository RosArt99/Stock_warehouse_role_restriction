from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestWarehouseRestriction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env = env
        Warehouse = env["stock.warehouse"]
        cls.wh1 = Warehouse.create({"name": "Test WH 1", "code": "TW1"})
        cls.wh2 = Warehouse.create({"name": "Test WH 2", "code": "TW2"})

        Product = env["product.product"]
        vals = {"type": "consu", "is_storable": True}
        cls.comp1 = Product.create({"name": "Test Component 1", **vals})
        cls.comp2 = Product.create({"name": "Test Component 2", **vals})
        cls.finished = Product.create({"name": "Test Finished", **vals})

        Quant = env["stock.quant"]
        Quant._update_available_quantity(cls.comp1, cls.wh1.lot_stock_id, 10)
        Quant._update_available_quantity(cls.comp2, cls.wh2.lot_stock_id, 20)

        cls.role = env["res.users.role"].create(
            {
                "name": "Test Workshop Manager",
                "implied_ids": [(6, 0, [env.ref("mrp.group_mrp_user").id])],
                "warehouse_ids": [(6, 0, [cls.wh1.id])],
            }
        )
        cls.restricted_user = env["res.users"].create(
            {
                "name": "Restricted",
                "login": "test_restricted",
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )
        # Same stock rights, but no role => must not be restricted.
        cls.plain_user = env["res.users"].create(
            {
                "name": "Plain",
                "login": "test_plain",
                "group_ids": [(6, 0, [env.ref("mrp.group_mrp_user").id])],
            }
        )
        cls.admin = env.ref("base.user_admin")
        cls.products = cls.comp1 | cls.comp2

    def _visible_locations(self, user):
        quants = (
            self.env["stock.quant"]
            .with_user(user)
            .search([("product_id", "in", self.products.ids)])
        )
        return quants.location_id

    def test_restricted_user_sees_only_allowed_warehouse(self):
        self.assertEqual(
            self._visible_locations(self.restricted_user), self.wh1.lot_stock_id
        )

    def test_admin_sees_everything(self):
        self.assertEqual(
            self._visible_locations(self.admin),
            self.wh1.lot_stock_id | self.wh2.lot_stock_id,
        )

    def test_user_without_restricted_role_sees_everything(self):
        self.assertEqual(
            self._visible_locations(self.plain_user),
            self.wh1.lot_stock_id | self.wh2.lot_stock_id,
        )

    def test_on_hand_quantity_follows_restriction(self):
        comp2_as_user = self.comp2.with_user(self.restricted_user)
        comp1_as_user = self.comp1.with_user(self.restricted_user)
        self.assertEqual(comp1_as_user.qty_available, 10)
        self.assertEqual(comp2_as_user.qty_available, 0)
        # ``qty_available`` is cached without the user in its cache key, so
        # within a single test transaction the value computed above would leak
        # to the admin check. (Real requests always start with a fresh cache.)
        self.env.invalidate_all()
        self.assertEqual(self.comp2.with_user(self.admin).qty_available, 20)

    def test_restricted_user_cannot_touch_other_warehouse_quant(self):
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.comp2.id),
                ("location_id", "=", self.wh2.lot_stock_id.id),
            ]
        )
        with self.assertRaises(AccessError):
            quant.with_user(self.restricted_user).read(["quantity"])

    def test_changing_role_warehouses_takes_effect_immediately(self):
        # Prime the (cached) rule domain first.
        self.assertEqual(
            self._visible_locations(self.restricted_user), self.wh1.lot_stock_id
        )
        self.role.warehouse_ids = [(6, 0, [self.wh2.id])]
        self.assertEqual(
            self._visible_locations(self.restricted_user), self.wh2.lot_stock_id
        )
        self.role.warehouse_ids = [(6, 0, [self.wh1.id, self.wh2.id])]
        self.assertEqual(
            self._visible_locations(self.restricted_user),
            self.wh1.lot_stock_id | self.wh2.lot_stock_id,
        )

    def test_role_without_warehouses_is_not_restricted(self):
        self.assertEqual(
            self._visible_locations(self.restricted_user), self.wh1.lot_stock_id
        )
        self.role.warehouse_ids = [(5, 0, 0)]
        self.assertEqual(
            self._visible_locations(self.restricted_user),
            self.wh1.lot_stock_id | self.wh2.lot_stock_id,
        )

    def test_restricted_user_can_complete_manufacturing_order(self):
        """The restriction must not break manufacturing in the allowed warehouse."""
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.finished.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [(0, 0, {"product_id": self.comp1.id, "product_qty": 1})],
            }
        )
        mo = (
            self.env["mrp.production"]
            .with_user(self.restricted_user)
            .create(
                {
                    "product_id": self.finished.id,
                    "bom_id": bom.id,
                    "product_qty": 2,
                    "picking_type_id": self.wh1.manu_type_id.id,
                }
            )
        )
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        mo.qty_producing = 2
        mo._set_qty_producing(False)
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")

        self.assertEqual(self.comp1.with_user(self.restricted_user).qty_available, 8)
        self.assertEqual(
            self.finished.with_user(self.restricted_user).qty_available, 2
        )
