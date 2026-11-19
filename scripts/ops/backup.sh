#!/bin/zsh
# 每日備份：三個服務的資料庫 + 物品照片 → iCloud Drive，保留 14 天。
# 排程：~/Library/LaunchAgents/com.chihyi.home-service-hub.backup.plist（每天 03:17）
# 結果寫到 status 檔，早報讀它判斷昨晚有沒有成功。
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

DEST="${BACKUP_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Backups/home-service-hub}"
STATUS_DIR="$HOME/Library/Logs/home-service-hub/status"
REPO="${0:A:h:h:h}"
CONTAINER=inventory-postgres
PGUSER=chihyi
DBS=(inventory_db accounting_db stock_portfolio_db)
KEEP_DAYS=14
stamp=$(date +%Y-%m-%d)

mkdir -p "$DEST" "$STATUS_DIR"
status() { print -r -- "{\"job\":\"backup\",\"ok\":$1,\"at\":\"$(date -Iseconds)\",\"detail\":\"$2\"}" > "$STATUS_DIR/backup.json"; }
trap 'status false "failed at line $LINENO"' ERR

for db in $DBS; do
  out="$DEST/$db-$stamp.dump"
  docker exec "$CONTAINER" pg_dump -U "$PGUSER" -Fc "$db" > "$out.tmp"
  mv "$out.tmp" "$out"
done
tar -czf "$DEST/inventory-images-$stamp.tar.gz.tmp" -C "$REPO/infra" inventory-images
mv "$DEST/inventory-images-$stamp.tar.gz.tmp" "$DEST/inventory-images-$stamp.tar.gz"

find "$DEST" -type f \( -name '*.dump' -o -name '*.tar.gz' \) -mtime +$KEEP_DAYS -delete
size=$(du -sh "$DEST" | cut -f1)
status true "${#DBS} dbs + images, folder $size"
print "backup ok ($size)"
