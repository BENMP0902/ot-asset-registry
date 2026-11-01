"""
Pruebas FUNCIONALES: el sistema visto desde HTTP, como lo usaría un navegador (o un atacante).
"""

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from assets import services
from assets.models import Asset, AssetStatus

from .helpers import make_catalog, make_user


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = make_user("jefe", "Administrador")
        cls.operator = make_user("tecnico", "Operador")
        cls.asset_type, cls.z1, cls.z2 = make_catalog()

    def setUp(self):
        self.admin_client = Client()
        self.admin_client.force_login(self.admin_user)      # sesión iniciada sin pasar por el formulario
        self.operator_client = Client()
        self.operator_client.force_login(self.operator)
        self.register_url = reverse("assets:register")

    def form_data(self, tag, name="Tablero de distribución"):
        return {"tag": tag, "name": name, "asset_type": self.asset_type.pk,
                "zone": self.z1.pk, "description": "", "note": ""}

    def make_asset(self, tag="TAB-001"):
        return services.register_asset(user=self.admin_user, tag=tag, name="Tablero",
                                       asset_type=self.asset_type, zone=self.z1)

    # --- Autenticación ---

    def test_anonymous_is_redirected_to_login(self):
        list_url = reverse("assets:list")
        response = Client().get(list_url)
        self.assertRedirects(response, f"{reverse('login')}?next={list_url}")

    def test_logout_requires_post(self):
        self.assertEqual(self.operator_client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.operator_client.post(reverse("logout")), reverse("login"))

    # --- Alta ---

    def test_admin_registers_asset_through_form(self):
        response = self.admin_client.post(self.register_url, self.form_data("TAB-001"))
        asset = Asset.objects.get(tag="TAB-001")
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]))
        self.assertEqual(asset.current_zone(), self.z1)

    def test_operator_forced_browsing_gets_custom_403(self):
        for method in ("get", "post"):
            with self.subTest(method):
                response = getattr(self.operator_client, method)(self.register_url, self.form_data("TAB-X"))
                self.assertEqual(response.status_code, 403)          # la página amable conserva el 403
                self.assertTemplateUsed(response, "403.html")
                self.assertContains(response, "No tienes permiso", status_code=403)
        self.assertFalse(Asset.objects.filter(tag="TAB-X").exists())

    def test_403_page_does_not_leak_internal_permission_names(self):
        asset = self.make_asset()
        response = self.operator_client.post(reverse("assets:decommission", args=[asset.pk]), {"note": "x"})
        self.assertNotContains(response, "decommission_asset", status_code=403)   # CWE-209

    # --- Lo que ve cada rol (comodidad visual; la seguridad la prueban los 403) ---

    def test_detail_shows_actions_by_role(self):
        url = reverse("assets:detail", args=[self.make_asset().pk])
        operator_page = self.operator_client.get(url)
        admin_page = self.admin_client.get(url)
        self.assertContains(operator_page, "Reubicar")
        self.assertNotContains(operator_page, "Dar de baja")
        self.assertContains(admin_page, "Dar de baja")

    # --- Reubicación y baja ---

    def test_operator_relocates_and_sees_service_errors(self):
        asset = self.make_asset()
        url = reverse("assets:relocate", args=[asset.pk])
        response = self.operator_client.post(url, {"to_zone": self.z2.pk, "note": ""})
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]))
        self.assertEqual(asset.current_zone(), self.z2)

        response = self.operator_client.post(url, {"to_zone": self.z2.pk, "note": ""})
        self.assertContains(response, "ya está en esa zona")           # error del servicio en el formulario

    def test_decommission_requires_reason_then_succeeds(self):
        asset = self.make_asset()
        url = reverse("assets:decommission", args=[asset.pk])
        self.assertEqual(self.admin_client.post(url, {"note": "   "}).status_code, 200)
        self.assertEqual(asset.current_status(), AssetStatus.ACTIVE)

        self.admin_client.post(url, {"note": "Fin de vida útil"})
        self.assertEqual(asset.current_status(), AssetStatus.DECOMMISSIONED)

    # --- Seguridad web ---

    def test_stored_xss_is_escaped(self):
        self.admin_client.post(self.register_url, self.form_data("XSS-001", name="<script>alert(1)</script>"))
        response = self.admin_client.get(reverse("assets:list"))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_post_without_csrf_token_is_rejected(self):
        browser = Client(enforce_csrf_checks=True)       # exige token, como un navegador real
        browser.force_login(self.admin_user)
        response = browser.post(self.register_url, self.form_data("CSRF-001"))
        self.assertContains(response, "No se pudo verificar el formulario", status_code=403)
        self.assertFalse(Asset.objects.filter(tag="CSRF-001").exists())

    # --- Rendimiento ---

    def test_asset_list_query_count_is_constant(self):
        self.make_asset("TAB-000")
        url = reverse("assets:list")
        self.operator_client.get(url)                    # calentamiento: consume mensajes pendientes

        with CaptureQueriesContext(connection) as before:
            self.operator_client.get(url)
        for i in range(1, 6):
            self.make_asset(f"TAB-{i:03}")
        with CaptureQueriesContext(connection) as after:
            response = self.operator_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(before), len(after))         # 1 activo o 6 activos: mismas consultas

    def test_anomaly_report_is_available_to_operator(self):
        self.assertEqual(self.operator_client.get(reverse("assets:anomalies")).status_code, 200)
