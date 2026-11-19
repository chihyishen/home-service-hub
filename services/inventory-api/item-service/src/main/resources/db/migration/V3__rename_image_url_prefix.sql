-- V3__rename_image_url_prefix.sql
-- MinIO is gone; the browser-facing image path is now /images/inventory-items/...
UPDATE items SET image_url = '/images' || SUBSTRING(image_url FROM 7)
WHERE image_url LIKE '/minio/%';

-- Legacy absolute MinIO URLs, e.g. http://192.168.0.100:9000/inventory-items/x.jpg
UPDATE items SET image_url = REGEXP_REPLACE(image_url, '^https?://[^/]+:9000/', '/images/')
WHERE image_url LIKE 'http%://%:9000/inventory-items/%';
