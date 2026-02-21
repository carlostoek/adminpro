---
phase: 26-initial-data-migration
plan: 03
subsystem: database
tags: [seeder, shop, gamification, data-migration]
dependency_graph:
  requires: ["26-01", "26-02"]
  provides: ["shop-seeder"]
  affects: ["bot/database/seeders"]
tech_stack:
  added: []
  patterns: ["Idempotent seeding", "ContentSet-ShopProduct relationship"]
key_files:
  created:
    - bot/database/seeders/shop.py
  modified:
    - bot/database/seeders/__init__.py
decisions:
  - "Create ContentSet first, then ShopProduct with foreign key"
  - "Empty file_ids array for admin population after deployment"
  - "Idempotent by checking product name before creation"
metrics:
  duration: 2m
  completed_date: 2026-02-21
---

# Phase 26 Plan 03: Shop Products Seeder Summary

## Overview

Created shop products seeder that creates sample products with their associated content sets for the gamification shop system. Provides default shop products that demonstrate the shop functionality, with empty content that the admin can populate after deployment.

## Deliverables

### Files Created

1. **bot/database/seeders/shop.py** (115 lines)
   - `DEFAULT_PRODUCTS` - Configuration list with 2 default products
   - `seed_default_shop_products()` - Async idempotent seeder function
   - Creates ContentSet first, then ShopProduct with foreign key
   - Logs creation progress with IDs

### Files Modified

1. **bot/database/seeders/__init__.py**
   - Added export for `seed_default_shop_products`
   - Both reward and shop seeders now available from single import

## Default Products Seeded

### 1. Pack de Bienvenida (Welcome Pack)
- **Price:** 50 besitos
- **VIP Discount:** 20%
- **Tier:** FREE
- **Content Type:** Photo Set
- **Category:** welcome
- **Description:** Contenido especial para nuevos miembros del canal

### 2. Pack VIP Especial (VIP Special)
- **Price:** 200 besitos
- **VIP Discount:** 50%
- **Tier:** VIP
- **Content Type:** Mixed
- **Category:** premium
- **Description:** Contenido exclusivo para suscriptores VIP

## Key Implementation Details

### Idempotent Design
```python
# Check for existing product by name before creating
result = await session.execute(
    select(ShopProduct).where(ShopProduct.name == product_data["name"])
)
existing_product = result.scalar_one_or_none()
if existing_product:
    skipped_count += 1
    continue
```

### ContentSet-ShopProduct Relationship
```python
# 1. Create ContentSet first
content_set = ContentSet(...)
session.add(content_set)
await session.flush()  # Get content_set.id

# 2. Create ShopProduct with foreign key
product = ShopProduct(
    content_set_id=content_set.id,
    ...
)
```

### Empty Content for Admin Population
- Content sets created with `file_ids: []`
- Admin must upload actual content after deployment
- Docstring notes this requirement

## Verification

- [x] File `bot/database/seeders/shop.py` exists
- [x] Contains DEFAULT_PRODUCTS list with 2 products
- [x] Contains `async def seed_default_shop_products(session)` function
- [x] Uses proper imports from bot.database.models and bot.database.enums
- [x] Creates ContentSet before ShopProduct
- [x] Uses await session.flush() to get content_set.id
- [x] Both seeders importable from bot.database.seeders

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 516f5e2 | feat(26-03): create shop products seeder with default products | shop.py, __init__.py |
| 7e5626a | feat(26-03): update seeders module exports | __init__.py |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] Created files exist: bot/database/seeders/shop.py
- [x] Modified files updated: bot/database/seeders/__init__.py
- [x] Commits exist: 516f5e2, 7e5626a
- [x] Imports work correctly
