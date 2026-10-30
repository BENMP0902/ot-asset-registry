"""
Migración de DATOS: crea los roles Administrador y Operador con sus permisos.

Por qué una migración y no clics en el admin: los roles quedan versionados,
revisables en un diff y se reproducen idénticos en cualquier base de datos.
"""

from django.contrib.auth.management import create_permissions  # crea filas de Permission para una app
from django.db import migrations

# Rol -> permisos (codenames). Diseño de mínimo privilegio, alineado con los casos de uso.
ROLES = {
    "Administrador": [
        # Catálogos: CRUD completo (on_delete=PROTECT impide borrar lo que está en uso)
        "add_assettype", "change_assettype", "delete_assettype", "view_assettype",
        "add_zone", "change_zone", "delete_zone", "view_zone",
        # Activos: editar datos descriptivos (UC-06). El alta va por el servicio, no por add_asset.
        "change_asset", "view_asset",
        # Ledger: ver + las tres operaciones de negocio
        "view_assetmovement", "register_checkin", "relocate_asset", "decommission_asset",
    ],
    "Operador": [
        # Consulta (UC-05, UC-09, UC-10) + reubicación (UC-07). Nada más.
        "view_assettype", "view_zone", "view_asset", "view_assetmovement",
        "relocate_asset",
    ],
}


def create_roles(apps, schema_editor):
    # Normalmente Django crea los permisos DESPUÉS de todas las migraciones (señal post_migrate).
    # En una BD nueva todavía no existen en este punto, así que los forzamos para esta app.
    app_config = apps.get_app_config("assets")
    app_config.models_module = True                 # create_permissions ignora apps sin módulo de modelos
    create_permissions(app_config, apps=apps, verbosity=0, using=schema_editor.connection.alias)
    app_config.models_module = None                 # restaura el estado del registro histórico

    Group = apps.get_model("auth", "Group")         # modelos HISTÓRICOS: nunca importar los reales aquí
    Permission = apps.get_model("auth", "Permission")

    for role, codenames in ROLES.items():
        group, _ = Group.objects.get_or_create(name=role)        # idempotente: no duplica si ya existe
        perms = Permission.objects.filter(
            content_type__app_label="assets", codename__in=codenames,
        )
        # Falla ruidosamente si un codename está mal escrito, en vez de crear un rol incompleto
        missing = set(codenames) - set(perms.values_list("codename", flat=True))
        if missing:
            raise RuntimeError(f"Permisos inexistentes para {role}: {sorted(missing)}")
        group.permissions.set(perms)                # reemplaza: el rol queda EXACTAMENTE con esta lista


def remove_roles(apps, schema_editor):
    """Reverso: permite deshacer la migración con 'migrate assets 0002'."""
    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0002_alter_assetmovement_options"),          # trae los permisos personalizados
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_roles, remove_roles),
    ]
