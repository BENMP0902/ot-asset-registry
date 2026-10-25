# 01 — Definición del problema

**Proyecto:** OT-Asset-Registry — Registro de activos industriales / OT
**Materia:** Aplicaciones de Ingeniería de Software (Hybridge Education)
**Fase:** 1 — Planeación
**Autor:** Benjamín Martínez Pérez (`BENMP0902`)
**Fecha:** 2026-10-25

---

## Contexto

Una instalación industrial o comercial (escenario **simulado**, representativo
del clúster manufacturero del Bajío) administra un parque de activos
**eléctricos, de red y de control**: tableros y centros de carga, interruptores
termomagnéticos, UPS, transformadores, variadores de frecuencia (VFD), switches
de red, cámaras/DVR, sensores, PLCs y HMIs, distribuidos físicamente en **zonas**.

## Problema

Hoy ese parque se controla con registros dispersos —hojas de cálculo y
conocimiento tácito de los técnicos—, **sin una fuente única de verdad**
(*single source of truth*) verificable sobre la existencia, tipo, ubicación e
historial de cada activo.

En ausencia de ese registro, la organización no puede:

1. Localizar un activo ni auditar qué equipo hay en cada zona.
2. Detectar equipo no autorizado o faltante.
3. Ejecutar ninguna línea base de seguridad o mantenimiento, porque **toda
   protección depende de un inventario de activos completo y confiable**
   (NIST SP 800-82 Rev. 3; CIS Control 1 — *Inventory and Control of Enterprise
   Assets*).

## Solución propuesta

Un sistema web que centraliza el **registro y control del inventario de activos
y su historial de movimientos**, con autenticación, control de acceso por rol y
un historial auditable (*audit trail*) de cada alta, reubicación y baja.

## Límites (lo que el sistema NO hace)

- No monitorea el estado operativo en tiempo real de los activos.
- No se conecta a los activos ni los descubre por red.
- Se limita a **registrar y controlar el inventario y su historial de
  movimientos.**

> Esta sección de límites es deliberada: elimina la ambigüedad sobre el alcance.
> Un lector no puede interpretar que el sistema "monitorea equipo en vivo".

## Justificación como control de seguridad

El inventario de activos no es una función administrativa, es la **función
*Identify* (categoría ID.AM, Asset Management) del NIST Cybersecurity Framework
2.0** — la capa base de la que dependen Protect, Detect, Respond y Recover.
Construir este sistema es implementar ese primer control.
