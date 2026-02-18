---
phase: 24-admin-configuration
plan: "02"
status: complete
completed_at: "2026-02-17"
---

# Plan 24-02: Shop Management Handlers

## Summary

Implementa handlers para gestión de productos de tienda desde el panel de administración.
Permite crear, listar, ver detalles y activar/desactivar productos con FSM wizard.

## Deliverables

### Files Created

1. **bot/handlers/admin/shop_management.py** (785 líneas)
   - `callback_admin_shop` - Menú principal de tienda
   - `callback_shop_list` - Listado paginado de productos
   - `callback_shop_list_page` - Navegación de paginación
   - `callback_shop_details` - Detalles de producto
   - `callback_shop_toggle` - Activar/desactivar productos
   - `callback_shop_create_start` - Iniciar creación (FSM)
   - `process_product_name` - Paso 1: Nombre
   - `process_product_description` - Paso 2: Descripción
   - `process_product_price` - Paso 3: Precio
   - `process_product_tier` - Paso 4: Tier (FREE/VIP/PREMIUM)
   - `process_product_content_set` - Paso 5: ContentSet
   - `process_product_creation` - Paso 6: Confirmación

### Files Modified

2. **bot/states/admin.py**
   - Added `ShopCreateState` StatesGroup con 6 estados FSM

3. **bot/handlers/admin/__init__.py**
   - Import and register `shop_router`

4. **bot/services/message/admin_main.py**
   - Added "🛍️ Tienda" button to admin menu

## Features

### Product Management
- ✅ Listado paginado (5 productos por página)
- ✅ Ver detalles completos de producto
- ✅ Activar/desactivar productos
- ✅ Crear productos con wizard FSM de 6 pasos

### Product Creation Flow
1. **Nombre** - Validación: requerido, máx 200 chars
2. **Descripción** - Opcional, máx 1000 chars
3. **Precio** - Entero positivo en besitos
4. **Tier** - Selección via botones (FREE/VIP/PREMIUM)
5. **ContentSet** - Lista de conjuntos activos
6. **Confirmación** - Resumen y confirmación final

### Auto-Calculated Fields
- `vip_price` = `price * 0.8` (20% descuento VIP por defecto)
- `purchase_count` = 0 al crear
- `is_active` = True al crear

## Key Decisions

1. **Router Pattern**: Usa router separado `shop_router` para handlers de tienda
2. **Pagination**: 5 productos por página con navegación ⬅️ ➡️
3. **Voice**: Todos los mensajes usan voz de Lucien (🎩)
4. **ContentSet Validation**: Verifica que existan ContentSets antes de iniciar creación

## Verification

```bash
# Verify handlers exist
grep -q "admin:shop" bot/handlers/admin/shop_management.py
grep -q "ShopCreateState" bot/states/admin.py
grep -q "shop_router" bot/handlers/admin/__init__.py

# Verify menu button
grep -q "admin:shop" bot/services/message/admin_main.py
```

## Next Steps

- Plan 24-03: Reward Management Handlers
