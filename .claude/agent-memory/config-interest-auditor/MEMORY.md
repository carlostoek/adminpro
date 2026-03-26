# Agent Memory - Config/Interest/Content Auditor

## Audit Findings
- [audit-findings.md](./audit-findings.md) - Reporte completo de auditoría de seguridad

## Codebase Patterns Identified

### SQLAlchemy Patterns
- **Async Session Management:** Services reciben AsyncSession via constructor, no manejan commits (patrón delegado a handlers)
- **Soft Delete:** Implementado con flag `is_active` + índice, métodos explícitos deactivate/activate
- **Timestamps:** Modelos usan `datetime.now(timezone.utc).replace(tzinfo=None)` (correcto)
- **Numeric for Currency:** ContentPackage usa Numeric(10, 2) para precios

### Index Patterns
- UserInterest: índice único compuesto (user_id, package_id) para deduplicación
- ContentPackage: índices compuestos (category, is_active) y (type, is_active)

### Service Patterns
- **No-Commit Pattern:** ContentService documenta explícitamente que no hace commit
- **Validation:** Validaciones de input en métodos setters y create
- **Error Handling:** Try-except con logging en métodos de query

### Issues Identified
1. datetime.utcnow() deprecado en interest.py y content.py
2. Race condition TOCTOU en register_interest()
3. Falta commit en mark_as_attended()
4. Query ineficiente en get_interest_stats()
5. Uso de getattr() con defaults en lugar de columnas con defaults en modelo
