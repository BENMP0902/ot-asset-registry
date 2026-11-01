"""Pruebas de ROLES (migración de datos 0003) y del ADMIN de solo lectura."""

from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory, TestCase

from assets.models import Asset, AssetMovement

from .helpers import make_user


class RolePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = make_user("jefe", "Administrador")
        cls.operator = make_user("tecnico", "Operador")

    def test_roles_exist(self):
        self.assertEqual(Group.objects.filter(name__in=["Administrador", "Operador"]).count(), 2)

    def test_ledger_has_no_write_crud_permissions(self):
        # default_permissions = ("view",): estos permisos ni siquiera existen
        self.assertFalse(Permission.objects.filter(
            content_type__app_label="assets",
            codename__in=["add_assetmovement", "change_assetmovement", "delete_assetmovement"],
        ).exists())

    def test_operator_permissions(self):
        self.assertTrue(self.operator.has_perm("assets.relocate_asset"))
        for perm in ["assets.register_checkin", "assets.decommission_asset",
                     "assets.change_asset", "assets.change_zone"]:
            with self.subTest(perm):
                self.assertFalse(self.operator.has_perm(perm))

    def test_administrator_permissions(self):
        for perm in ["assets.register_checkin", "assets.relocate_asset", "assets.decommission_asset",
                     "assets.change_asset", "assets.add_zone"]:
            with self.subTest(perm):
                self.assertTrue(self.admin_user.has_perm(perm))

    def test_inactive_user_loses_all_permissions(self):
        # Ex empleado: se desactiva, no se borra (su firma en el ledger se conserva)
        former = make_user("exjefe", "Administrador", is_active=False)
        self.assertFalse(former.has_perm("assets.decommission_asset"))


class AdminReadOnlyTests(TestCase):
    def setUp(self):
        superuser = make_user("root", is_superuser=True, is_staff=True)
        self.request = RequestFactory().get("/admin/")
        self.request.user = superuser

    def test_ledger_is_read_only_even_for_superuser(self):
        model_admin = admin.site.get_model_admin(AssetMovement)
        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))
        self.assertNotIn("delete_selected", model_admin.get_actions(self.request))

    def test_assets_cannot_be_added_or_deleted_from_admin(self):
        model_admin = admin.site.get_model_admin(Asset)
        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))
