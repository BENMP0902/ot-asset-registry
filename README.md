# OT-Asset-Registry

Registro de activos industriales / OT: un sistema web para inventariar y
controlar los activos eléctricos, de red y de control de una instalación
(escenario simulado), con su historial auditable de movimientos.

Proyecto integrador de la materia **Aplicaciones de Ingeniería de Software**
(Hybridge Education). Desarrollado de forma individual, siguiendo el ciclo de
vida completo: planeación, requerimientos, diseño, desarrollo, pruebas y entrega.

## Enfoque

El inventario de activos es la función **Identify (ID.AM)** del NIST
Cybersecurity Framework y el **CIS Control 1** — la capa fundacional de todo
programa de seguridad: no se puede proteger lo que no se sabe que se tiene.
El sistema se diseña con ese lente: control de acceso por rol, registro de
movimientos *append-only* como pista de auditoría, y secretos fuera del
control de versiones.

## Stack

- **Lenguaje:** Python 3
- **Framework:** Django
- **Base de datos:** PostgreSQL (producción) · SQLite (desarrollo)
- **Control de versiones:** Git / GitHub
- **Entorno de desarrollo:** WSL2 (Kali Linux), VSCode

## Estructura del repositorio

```
docs/            Documentación por fase del ciclo de vida (01–06)
src/             Proyecto Django (código fuente)
.env.example     Plantilla de variables de entorno (sin secretos)
.gitignore       Exclusiones de versionado (secretos, BD local, venv)
```

## Instalación (desarrollo)

```bash
git clone https://github.com/BENMP0902/ot-asset-registry.git
cd ot-asset-registry
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/requirements.txt
cp .env.example .env          # luego edita .env con tus valores locales
python src/manage.py migrate
python src/manage.py runserver
```

## Estado

En desarrollo — proyecto académico. Ver `docs/` para el detalle de cada fase.

## Autor

Benjamín Martínez Pérez — [`BENMP0902`](https://github.com/BENMP0902)
Hybridge Education · Ingeniería en Software
