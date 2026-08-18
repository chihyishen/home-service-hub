# Local Inventory Image Storage Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the MinIO container with a local directory served by inventory-api, without changing existing item `imageUrl` values or the browser `/minio/inventory-items/**` path.

**Architecture:** Inventory writes UUID-named files under `INVENTORY_IMAGE_STORAGE_DIR`. Upload still returns `/minio/inventory-items/{uuid}.ext`. Gateway keeps the public path and method filter, but forwards GET/HEAD to inventory-api after stripping `/minio`. Existing MinIO on-disk layout is not raw JPEGs; one-shot S3 export is required before dropping the container.

**Tech Stack:** Java 21 / Spring Boot 4, Spring Cloud Gateway, Docker Compose, frontend proxy (path unchanged).

**Spec:** Conversation decision — local filesystem is enough for current inventory photos; no S3-compatible service.

## Global Constraints

- Keep stored and browser-facing URLs as `/minio/inventory-items/{filename}` so Postgres rows and frontend `normalizeItemImageUrl` stay valid.
- Image GET/HEAD remains public at the gateway; object names stay unguessable UUIDs.
- Inventory resource-server enforcement stays on for `/api/**`; only `/inventory-items/**` GET/HEAD is permitAll.
- Reject path traversal; never resolve `..` or separators outside the storage root.
- Do not add a new object-store container.
- MinIO Community data under `infra/minio-data` cannot be copied as files; export via S3 API.

---

## File Structure

- Modify: `StorageService.java` — filesystem upload/delete/load
- Create: `ImageController.java` — GET/HEAD `/inventory-items/{filename}`
- Delete: `MinioConfig.java`
- Modify: `ResourceServerSecurityConfig.java` — permit image reads
- Modify: `application.yml` — `storage.images.*`
- Modify: `build.gradle.kts` — drop `io.minio`
- Modify: `StorageServiceTest.java` — real temp dir, no MinIO mock
- Create: `ImageStorageIntegrationTest.java` — GET existing / missing / traversal
- Modify: gateway `application.yml` — image route uses `GATEWAY_INVENTORY_URI`
- Modify: `docker-compose.yml` — remove MinIO; mount image dir on inventory
- Modify: `.env.example`, `.env`, `.gitignore`, README, ROADMAP, CLAUDE.md, gateway-route-matrix
- Create: `scripts/export-minio-images.sh` — one-shot S3 export

---

### Task 1: Filesystem StorageService

**Files:**
- Test: `services/inventory-api/item-service/src/test/java/com/inventory/item/service/StorageServiceTest.java`
- Modify: `services/inventory-api/item-service/src/main/java/com/inventory/item/service/StorageService.java`
- Delete: `services/inventory-api/item-service/src/main/java/com/inventory/item/config/MinioConfig.java`
- Modify: `item-service/build.gradle.kts`, `application.yml`, `application-test.yml`, `IntegrationTestBase.java`

**Produces:**
- `StorageService(String directory, String publicEndpoint, String publicPrefix)`
- `String uploadFile(MultipartFile file)`
- `void deleteFile(String fileUrl)`
- `StoredImage loadFile(String filename)` record with `Resource`, `contentType`, `size`

- [x] Tests first: upload URL + bytes on disk; delete; load; reject `../secret`
- [x] Implement filesystem storage
- [x] Remove MinIO client/config/dependency

### Task 2: Serve images from inventory-api

**Files:**
- Create: `ImageController.java`
- Modify: `ResourceServerSecurityConfig.java`
- Test: `ImageStorageIntegrationTest.java`

- [x] GET `/inventory-items/{filename}` returns file with image content type
- [x] Missing / traversal → 404
- [x] Enforcement mode permits GET/HEAD `/inventory-items/**`

### Task 3: Point gateway and compose at inventory

**Files:**
- `services/gateway-service/src/main/resources/application.yml`
- `docker-compose.yml`
- `.env.example`, `.env`
- `docs/security/gateway-route-matrix.md`

- [x] Image route URI = inventory; StripPrefix=1 unchanged (smoke fixture already expects `/inventory-items/...`)
- [x] Remove `minio` service, `GATEWAY_MINIO_URI`, MinIO credentials
- [x] Mount `./infra/inventory-images` into inventory container

### Task 4: Export existing objects and docs

**Files:**
- `scripts/export-minio-images.sh`
- README, ROADMAP, CLAUDE.md, Item.java comment, `.gitignore`

- [x] Export via `mc` while MinIO still responds on :9000
- [x] Docs describe local directory + leftover `/minio` URL prefix
