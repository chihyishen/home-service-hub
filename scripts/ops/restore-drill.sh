#!/bin/zsh
# 還原演練：把最新備份還原到臨時資料庫，逐表比對筆數，比完刪掉臨時庫。
# 排程：~/Library/LaunchAgents/com.chihyi.home-service-hub.restore-drill.plist（每週日 03:47）
# 筆數以「備份當下」為準：先做一份新備份再比，避免白天新增的資料造成誤判。
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

HERE="${0:A:h}"
DEST="${BACKUP_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Backups/home-service-hub}"
STATUS_DIR="$HOME/Library/Logs/home-service-hub/status"
CONTAINER=inventory-postgres
PGUSER=chihyi
DBS=(inventory_db accounting_db stock_portfolio_db)

mkdir -p "$STATUS_DIR"
status() { print -r -- "{\"job\":\"restore-drill\",\"ok\":$1,\"at\":\"$(date -Iseconds)\",\"detail\":\"$2\"}" > "$STATUS_DIR/restore-drill.json"; }
trap 'status false "failed at line $LINENO"' ERR

"$HERE/backup.sh" >/dev/null
psql_in() { docker exec -i "$CONTAINER" psql -U "$PGUSER" -v ON_ERROR_STOP=1 -At "$@"; }
counts() {  # 每張表的筆數，排序後輸出 "table|rows"
  psql_in -d "$1" -c "select format('select %L || ''|'' || count(*) from %I.%I;', table_name, table_schema, table_name) from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1" \
    | psql_in -d "$1"
}

cleanup() { for db in $DBS; do psql_in -d postgres -c "drop database if exists restore_drill_$db" >/dev/null 2>&1 || true; done; }
trap cleanup EXIT

mismatch=0; tables=0
for db in $DBS; do
  dump=$(ls -t "$DEST/$db"-*.dump | head -1)
  scratch="restore_drill_$db"
  psql_in -d postgres -c "drop database if exists $scratch" >/dev/null 2>&1
  psql_in -d postgres -c "create database $scratch" >/dev/null
  docker exec -i "$CONTAINER" pg_restore -U "$PGUSER" --no-owner -d "$scratch" < "$dump"
  live=$(counts "$db"); restored=$(counts "$scratch")
  psql_in -d postgres -c "drop database $scratch" >/dev/null
  tables=$((tables + $(print -r -- "$live" | wc -l)))
  if [[ "$live" != "$restored" ]]; then
    mismatch=1
    print "MISMATCH in $db:"; diff <(print -r -- "$live") <(print -r -- "$restored") || true
  fi
done

if (( mismatch )); then status false "row counts differ"; exit 1; fi
status true "$tables tables restored, counts match"
print "restore drill ok ($tables tables)"
