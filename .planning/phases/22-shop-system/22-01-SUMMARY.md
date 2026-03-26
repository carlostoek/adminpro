# Phase 22 Plan 01: Shop Database Foundation Summary

**Plan:** 22-01
**Phase:** 22-shop-system
**Completed:** 2026-02-13
**Duration:** ~3 minutes

## Overview

Created the database foundation for the shop system with three new models and two new enums. This enables the shop system to store products, track purchases, and deliver content via Telegram file_ids.

## Changes Made

### New Enums (`bot/database/enums.py`)

1. **ContentType** - Types of content for ContentSet
   - `PHOTO_SET` - Set de Fotos
   - `VIDEO` - Video
   - `AUDIO` - Audio
   - `MIXED` - Mixto
   - Includes `display_name` property with Spanish translations

2. **ContentTier** - Access tiers for content and products
   - `FREE` - Gratis (🌸)
   - `VIP` - VIP (⭐)
   - `PREMIUM` - Premium (💎)
   - `GIFT` - Regalo (🎁)
   - Includes `display_name` and `emoji` properties

### New Models (`bot/database/models.py`)

1. **ContentSet** - Centralized content storage
   - Stores `file_ids` as JSON array for Telegram content delivery
   - Fields: `name`, `description`, `file_ids`, `content_type`, `tier`, `category`, `is_active`
   - `file_count` property returns len(file_ids)
   - Relationships: `shop_products`, `user_accesses`
   - Indexes: `(tier, is_active)`, `(content_type, is_active)`

2. **ShopProduct** - Catalog items for the shop
   - Fields: `name`, `description`, `content_set_id`, `besitos_price`
   - VIP pricing: `vip_discount_percentage` (0-100), `vip_besitos_price` (optional override)
   - `vip_price` property auto-calculates price with discount
   - `has_vip_discount` property
   - Fields: `tier`, `is_active`, `sort_order`, `purchase_count`
   - Relationships: `content_set`, `purchase_records`
   - Indexes: `(is_active, tier)`, `besitos_price`, `sort_order`

3. **UserContentAccess** - Purchase tracking
   - Tracks what content each user has received and how
   - Fields: `user_id`, `content_set_id`, `shop_product_id`, `access_type`
   - `access_type`: shop_purchase, reward_claim, gift, narrative
   - `besitos_paid` tracks purchase price (null for free rewards)
   - `access_metadata` JSON for extensibility
   - **Unique constraint**: `(user_id, content_set_id)` - prevents duplicate purchases
   - Helper properties: `is_purchased`, `is_reward`, `is_expired`
   - Relationships: `user`, `content_set`, `shop_product`
   - Indexes: `(user_id, content_set_id)`, `(user_id, access_type)`, `(user_id, accessed_at)`

## Key Design Decisions

1. **ContentSet as centralized storage** - All content files stored as Telegram file_ids array, enabling efficient delivery
2. **VIP discount system** - Percentage-based discounts with optional manual override price
3. **Unified access tracking** - Single table tracks purchases, rewards, gifts, and narrative content
4. **Unique constraint on user+content** - Prevents duplicate purchases of same content
5. **Soft delete via is_active** - Content can be deactivated without deleting records

## Files Modified

- `bot/database/enums.py` - Added ContentType and ContentTier enums
- `bot/database/models.py` - Added ContentSet, ShopProduct, UserContentAccess models

## Commits

| Commit | Description |
|--------|-------------|
| 5806faa | feat(22-01): add ContentType and ContentTier enums |
| dfc0b22 | feat(22-01): create ContentSet model |
| c9d5e37 | feat(22-01): create ShopProduct model |
| 8d53ab2 | feat(22-01): create UserContentAccess model |

## Verification

- [x] Models import correctly: `from bot.database.models import ContentSet, ShopProduct, UserContentAccess`
- [x] Enums import correctly: `from bot.database.enums import ContentType, ContentTier`
- [x] No circular imports
- [x] Bidirectional relationships verified:
  - `content_set.shop_products` ↔ `product.content_set`
  - `content_set.user_accesses` ↔ `access.content_set`
  - `shop_product.purchase_records` ↔ `access.shop_product`

## Success Criteria Met

- [x] ContentSet model stores file_ids as JSON array for Telegram file delivery
- [x] ShopProduct has besitos_price, vip_discount_percentage, and vip_price property
- [x] UserContentAccess has unique constraint on (user_id, content_set_id) preventing duplicate purchases
- [x] ContentType enum supports photo_set, video, audio, mixed
- [x] ContentTier enum supports free, vip, premium, gift
- [x] All models have proper indexes for query performance
- [x] Relationships allow: content_set.shop_products, product.content_set, user_access.content_set

## Next Steps

Phase 22 Plan 02 will implement the ShopService with purchase flow, catalog browsing, and delivery mechanisms.
