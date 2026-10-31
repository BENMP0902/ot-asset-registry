# 02 — Plan de proyecto

**Proyecto:** OT-Asset-Registry
**Materia:** Aplicaciones de Ingeniería de Software (Hybridge Education)
**Fase:** 1 — Planeación
**Autor:** Benjamín Martínez Pérez (`BENMP0902`)
**Fecha:** 2026-10-25
**Modalidad:** Individual
**Fecha de entrega:** ~23 de noviembre de 2026

---

## 1. Participantes

Proyecto individual: una sola persona cubre todos los roles del ciclo de vida.
Se declaran explícitamente para dejar constancia de que el ciclo completo fue
gestionado, no omitido.

| Rol | Responsable | Responsabilidad |
|---|---|---|
| Analista / Product Owner | Ben | Requerimientos y alcance |
| Arquitecto de software | Ben | Diseño, modelo de datos, patrones |
| Desarrollador | Ben | Implementación |
| QA / Tester | Ben | Pruebas unitarias y funcionales |
| Documentador | Ben | Manuales y documentación técnica |
| Evaluador | Asesor/profesor Hybridge | Validación del entregable |

### Stakeholders simulados (usuarios del sistema → actores del diagrama de casos de uso)

- **Administrador OT / Ingeniero de seguridad** — gestiona catálogo, da de
  alta/baja activos, administra usuarios.
- **Operador / Técnico de mantenimiento** — consulta y registra reubicaciones;
  **no** puede dar de baja activos.

## 2. Alcance

### DENTRO del alcance (MVP)

- CRUD de activos (`Asset`) con tipo (`AssetType`) y zona (`Zone`).
- Registro de movimientos (`AssetMovement`) *append-only*: alta (`CHECK_IN`),
  reubicación (`RELOCATION`), baja (`DECOMMISSION`).
- Estado y ubicación actual **derivados** del ledger de movimientos.
- Autenticación + 2 roles (admin / operador) con permisos diferenciados.
- Regla de negocio: reporte de activos sin zona asignada o dados de baja.
- Listado/consulta de activos y su historial.

### FUERA del alcance (future work — diferido, no omitido)

- Escaneo/descubrimiento real de red (Nmap, SNMP) → puente al curso de
  Cybersecurity.
- Integración con un CMDB real o sistemas externos.
- Multi-planta / multi-tenant.
- API REST pública.
- Dashboards analíticos → puente al taller de Power BI.
- Notificaciones por correo.

## 3. Cronograma

| Semana | Fechas | Fases | Entregable |
|---|---|---|---|
| 1 | 24–31 oct | Cierre F1 + F2 Requerimientos + F3 Diseño | Docs de requerimientos y diseño |
| 2 | 1–9 nov | F4 Desarrollo (1): entorno, modelos, migraciones, admin, auth+roles | Esqueleto funcional con CRUD seguro |
| 3 | 10–16 nov | F4 Desarrollo (2): vistas, lógica del ledger, regla de negocio + F5 Pruebas | Sistema funcional + pruebas |
| 4 | 17–23 nov | F5 cierre + F6 Entrega: manuales, doc consolidado, repo + buffer | Paquete de entrega completo |

Esfuerzo total estimado: ~35–50 h. La segunda mitad del calendario actúa como
**buffer** (en un proyecto individual, el autor es el único punto de falla).

## 4. Recursos necesarios

- **Lenguaje/framework:** Python 3.x + Django + PostgreSQL (target) / SQLite (desarrollo).
- **Entorno:** WSL2 Kali, VSCode, Git + GitHub (repo `BENMP0902/ot-asset-registry`).
- **Modelado UML/ERD:** Mermaid o draw.io / PlantUML.
- **Documentación oficial:** Django docs.
- **Tiempo:** según cronograma.
