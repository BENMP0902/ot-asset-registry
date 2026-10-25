# 01 — Requerimientos (funcionales y no funcionales)

**Proyecto:** OT-Asset-Registry
**Materia:** Aplicaciones de Ingeniería de Software (Hybridge Education)
**Fase:** 2 — Análisis de requerimientos
**Autor:** Benjamín Martínez Pérez (`BENMP0902`)
**Fecha:** 2026-10-25

---

## Nota conceptual

- **Requerimiento funcional (RF):** una *acción* que el sistema ejecuta
  (verbos: registra, lista, consulta). Responde *qué hace*.
- **Requerimiento no funcional (RNF):** una *cualidad* del sistema (seguridad,
  rendimiento, portabilidad). Responde *qué tan bien lo hace*. Debe enunciarse
  con un criterio **verificable**, no como "debe ser seguro".

## Requerimientos funcionales (MVP)

| ID | Requerimiento | Rol |
|---|---|---|
| RF-01 | Gestionar catálogo de tipos de activo (`AssetType`): crear, editar, consultar | Admin |
| RF-02 | Gestionar zonas (`Zone`): CRUD | Admin |
| RF-03 | Dar de alta un activo (`Asset`) → genera movimiento `CHECK_IN` | Admin |
| RF-04 | Listar/consultar activos con filtros (tipo, zona, estado) | Admin + Operador |
| RF-05 | Editar datos descriptivos de un activo | Admin |
| RF-06 | Registrar reubicación de activo entre zonas → movimiento `RELOCATION` | Admin + Operador |
| RF-07 | Dar de baja un activo → movimiento `DECOMMISSION` | Solo Admin |
| RF-08 | Consultar el historial de movimientos de un activo (ledger) | Admin + Operador |
| RF-09 | Autenticarse (login / logout) | Todos |
| RF-10 | Aplicar permisos diferenciados por rol | Sistema |
| RF-11 | Reportar activos anómalos: sin zona, dados de baja o incompletos | Admin + Operador |
| RF-12 | Derivar estado y ubicación actual de cada activo desde su último movimiento | Sistema |

## Requerimientos no funcionales

| ID | Categoría | Criterio verificable |
|---|---|---|
| RNF-01 | Seguridad | Hash PBKDF2+salt en contraseñas; protección CSRF en formularios; consultas parametrizadas vía ORM (anti-SQLi) |
| RNF-02 | Integridad / Auditabilidad | El ledger `AssetMovement` es append-only: los movimientos no se editan ni se eliminan |
| RNF-03 | Trazabilidad | Cada movimiento registra quién (usuario), qué (tipo) y cuándo (timestamp) |
| RNF-04 | Control de acceso | Separación admin/operador; el operador no puede ejecutar `DECOMMISSION` (privilegio mínimo) |
| RNF-05 | Portabilidad | SQLite en desarrollo, PostgreSQL en target; conmutable por configuración |
| RNF-06 | Mantenibilidad | Catálogo de tipos extensible sin modificar código (Open/Closed Principle) |
| RNF-07 | Usabilidad | Interfaz en español, operable por un técnico sin capacitación extensa |

## Mapeo a estándares de seguridad

- **RNF-01** → OWASP A03 (Injection), A07 (Identification and Authentication Failures).
- **RNF-02 / RNF-03** → CIS Control 8 (Audit Log Management); familia AU de NIST SP 800-53.
- **RNF-04** → OWASP A01 (Broken Access Control); principio de privilegio mínimo.
