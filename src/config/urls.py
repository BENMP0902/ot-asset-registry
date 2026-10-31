"""
Rutas raíz del proyecto.

Solo se exponen login y logout, NO todo django.contrib.auth.urls: ese módulo también
publica rutas para restablecer la contraseña por correo, y aquí no hay correo
configurado. Una ruta que no se usa es superficie de ataque gratuita.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "cuentas/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),   # si ya hay sesión, no muestra el login
        name="login",
    ),
    path("cuentas/logout/", auth_views.LogoutView.as_view(), name="logout"),  # Django 5: solo POST
    path("", include("assets.urls")),
]
