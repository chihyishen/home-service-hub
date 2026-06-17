-- V2__drop_unused_item_fields.sql
ALTER TABLE items DROP COLUMN target_quantity;
ALTER TABLE items DROP COLUMN is_consumable;
ALTER TABLE items DROP COLUMN status;
ALTER TABLE items DROP COLUMN last_restocked_at;
