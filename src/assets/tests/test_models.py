"""
Pruebas de MODELO e INTEGRACIÓN con la base de datos.
Verifican el estado derivado, el ledger append-only, on_delete=PROTECT y la restricción CHECK.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from assets.models import Asset, AssetMovement, AssetStatus, MovementType

from .helpers import make_catalog, make_user


class LedgerModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Se crea UNA vez para toda la clase; cada prueba ve una copia limpia
        cls.user = make_user("tecnico")
        cls.asset_type, cls.z1, cls.z2 = make_catalog()

    def setUp(self):
        self.asset = Asset.objects.create(tag="VFD-001", name="ABB ACS580 7.5 kW", asset_type=self.asset_type)

    def move(self, movement_type, from_zone=None, to_zone=None):
        return AssetMovement.objects.create(
            asset=self.asset, movement_type=movement_type,
            from_zone=from_zone, to_zone=to_zone, performed_by=self.user,
        )

    # --- Estado derivado ---

    def test_asset_without_movements_has_no_state(self):
        self.assertIsNone(self.asset.current_status())
        self.assertIsNone(self.asset.current_zone())

    def test_state_is_derived_from_last_movement(self):
        self.move(MovementType.CHECK_IN, to_zone=self.z1)
        self.assertEqual(self.asset.current_zone(), self.z1)
        self.assertEqual(self.asset.current_status(), AssetStatus.ACTIVE)

        # En pruebas rápidas dos movimientos pueden compartir timestamp: el desempate por "-id" lo resuelve
        self.move(MovementType.RELOCATION, from_zone=self.z1, to_zone=self.z2)
        self.assertEqual(self.asset.current_zone(), self.z2)

    def test_decommission_sets_status_and_clears_zone(self):
        self.move(MovementType.CHECK_IN, to_zone=self.z1)
        self.move(MovementType.DECOMMISSION, from_zone=self.z1)
        self.assertEqual(self.asset.current_status(), AssetStatus.DECOMMISSIONED)
        self.assertIsNone(self.asset.current_zone())

    # --- Append-only ---

    def test_movement_cannot_be_edited(self):
        movement = self.move(MovementType.CHECK_IN, to_zone=self.z1)
        movement.note = "alterado"
        with self.assertRaises(PermissionDenied):
            movement.save()

    def test_movement_cannot_be_deleted(self):
        movement = self.move(MovementType.CHECK_IN, to_zone=self.z1)
        with self.assertRaises(PermissionDenied):
            movement.delete()

    def test_bulk_update_and_delete_are_blocked(self):
        self.move(MovementType.CHECK_IN, to_zone=self.z1)
        with self.assertRaises(PermissionDenied):
            AssetMovement.objects.update(note="x")
        with self.assertRaises(PermissionDenied):
            AssetMovement.objects.all().delete()

    # --- on_delete=PROTECT ---

    def test_asset_and_zone_with_history_are_protected(self):
        self.move(MovementType.CHECK_IN, to_zone=self.z1)
        with self.assertRaises(ProtectedError):
            self.asset.delete()
        with self.assertRaises(ProtectedError):
            self.z1.delete()

    # --- Restricción CHECK (la aplica la BD, no Python) ---

    def test_db_rejects_zone_combinations_invalid_for_type(self):
        invalid = {
            "CHECK_IN con origen": dict(movement_type=MovementType.CHECK_IN, from_zone=self.z1, to_zone=self.z2),
            "CHECK_IN sin destino": dict(movement_type=MovementType.CHECK_IN),
            "RELOCATION sin origen": dict(movement_type=MovementType.RELOCATION, to_zone=self.z2),
            "RELOCATION a la misma zona": dict(movement_type=MovementType.RELOCATION, from_zone=self.z1, to_zone=self.z1),
            "DECOMMISSION con destino": dict(movement_type=MovementType.DECOMMISSION, from_zone=self.z1, to_zone=self.z2),
        }
        for label, kwargs in invalid.items():
            # subTest: si un caso falla, los demás se siguen evaluando y se reportan por separado.
            # atomic(): savepoint, para que el IntegrityError no deje inutilizable la transacción de la prueba.
            with self.subTest(label), self.assertRaises(IntegrityError), transaction.atomic():
                AssetMovement.objects.create(asset=self.asset, performed_by=self.user, **kwargs)
