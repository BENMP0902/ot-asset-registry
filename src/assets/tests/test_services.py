"""Pruebas UNITARIAS de la capa de servicios: autorización, atomicidad y reglas de negocio."""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from assets import services
from assets.models import Asset, AssetStatus, MovementType, Zone

from .helpers import make_catalog, make_user


class ServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = make_user("jefe", "Administrador")
        cls.operator = make_user("tecnico", "Operador")
        cls.asset_type, cls.z1, cls.z2 = make_catalog()

    def register(self, tag="UPS-001", user=None, zone=None):
        return services.register_asset(
            user=user or self.admin_user, tag=tag, name="UPS 3 kVA",
            asset_type=self.asset_type, zone=zone or self.z1,
        )

    # --- Alta ---

    def test_register_requires_permission(self):
        for label, user in [("anónimo", AnonymousUser()), ("operador", self.operator)]:
            with self.subTest(label), self.assertRaises(PermissionDenied):
                self.register(user=user)
        self.assertFalse(Asset.objects.exists())

    def test_register_creates_asset_and_signed_checkin(self):
        asset = self.register(tag="  UPS-001  ")
        movements = list(asset.movements.all())
        self.assertEqual(asset.tag, "UPS-001")                      # etiqueta normalizada
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, MovementType.CHECK_IN)
        self.assertEqual(movements[0].performed_by, self.admin_user)
        self.assertEqual(asset.current_zone(), self.z1)

    def test_duplicate_tag_is_rejected_on_tag_field(self):
        self.register()
        with self.assertRaises(ValidationError) as ctx:
            self.register()
        self.assertIn("tag", ctx.exception.message_dict)             # el error apunta al campo correcto

    def test_register_is_atomic(self):
        # Zona no guardada: el CHECK_IN falla DESPUÉS de guardar el activo.
        # Si el servicio no fuera atómico, quedaría un activo huérfano.
        with self.assertRaises(ValueError):
            self.register(tag="ATOM-001", zone=Zone(code="NO-GUARDADA", name="x"))
        self.assertFalse(Asset.objects.filter(tag="ATOM-001").exists())

    # --- Reubicación ---

    def test_relocation_origin_is_derived_by_server(self):
        asset = self.register()
        movement = services.relocate_asset(user=self.operator, asset=asset, to_zone=self.z2)
        self.assertEqual(movement.from_zone, self.z1)
        self.assertEqual(asset.current_zone(), self.z2)

    def test_relocation_to_current_zone_is_rejected(self):
        asset = self.register()
        with self.assertRaises(ValidationError) as ctx:
            services.relocate_asset(user=self.operator, asset=asset, to_zone=self.z1)
        self.assertIn("to_zone", ctx.exception.message_dict)

    def test_asset_without_checkin_cannot_move(self):
        orphan = Asset.objects.create(tag="SIN-ALTA", name="x", asset_type=self.asset_type)
        with self.assertRaises(ValidationError):
            services.relocate_asset(user=self.operator, asset=orphan, to_zone=self.z2)

    # --- Baja ---

    def test_operator_cannot_decommission(self):
        asset = self.register()
        with self.assertRaises(PermissionDenied):
            services.decommission_asset(user=self.operator, asset=asset, note="x")

    def test_decommission_requires_reason(self):
        asset = self.register()
        with self.assertRaises(ValidationError) as ctx:
            services.decommission_asset(user=self.admin_user, asset=asset, note="   ")
        self.assertIn("note", ctx.exception.message_dict)

    def test_decommissioned_asset_cannot_move(self):
        asset = self.register()
        services.decommission_asset(user=self.admin_user, asset=asset, note="Daño por sobretensión")
        self.assertEqual(asset.current_status(), AssetStatus.DECOMMISSIONED)
        with self.assertRaises(ValidationError):
            services.relocate_asset(user=self.admin_user, asset=asset, to_zone=self.z1)

    # --- Consultas ---

    def test_assets_with_state_runs_a_single_query(self):
        for i in range(5):
            self.register(tag=f"UPS-{i:03}")
        with self.assertNumQueries(1):                               # falla si aparece el N+1
            rows = [(a.tag, a.asset_type.name, a.zone_code, a.last_movement_type)
                    for a in services.assets_with_state()]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r[2] == "Z-A1" for r in rows))

    def test_anomaly_report(self):
        active = self.register(tag="ACTIVO")
        retired = self.register(tag="BAJA")
        services.decommission_asset(user=self.admin_user, asset=retired, note="Fin de vida útil")
        Asset.objects.create(tag="SIN-ALTA", name="x", asset_type=self.asset_type)

        report = services.anomaly_report()
        self.assertEqual([a.tag for a in report["sin_alta"]], ["SIN-ALTA"])
        self.assertEqual([a.tag for a in report["dados_de_baja"]], ["BAJA"])
        self.assertNotIn(active.tag, [a.tag for a in report["sin_alta"]])
