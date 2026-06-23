# 資料庫 Schema 與從 0 建置指南

本專案使用 **PostgreSQL**。建表 DDL 位於 `pg_sample_code/create_*.sql`，共定義 **4 張表**。
本文件把每張表的完整欄位、型別、主鍵、外鍵與索引列出，並提供「從空資料庫補到有資料」的完整流程。

## 總覽

| 表 | 用途 | 回補是否需要 | 由誰寫入 | 建表 SQL |
|---|---|---|---|---|
| `public.stock_flow_lots_detailed` | **回補主表**：每日券商分點個股買賣超（張數） | ✅ 必要 | `src/tw_broker_flows/db_writer.py`（`backfill_daily.py --db-name`） | `create_stock_flow_lots_detailed.sql` |
| `public.brokers` | 券商代碼 ↔ 名稱對照（參考表） | ⬜ 選用 | `scripts/update_brokers.py` | `create_brokers_branches.sql` |
| `public.branches` | 分行代碼 ↔ 名稱對照（參考表，外鍵指向 brokers） | ⬜ 選用 | `scripts/update_brokers.py` | `create_brokers_branches.sql` |
| `public.stock_flow_lots` | flow 的**替代 schema**（以 `trade_date`+`metric_type` 為鍵） | ⬜ 替代 | 非預設寫入目標 | `create_stock_flow_lots.sql` |

關係：`branches.broker_code` →（FK）→ `brokers.broker_code`。flow 表與 brokers/branches 無 FK 約束（flow 表自帶 broker/branch 名稱欄位）。

> ⚠️ **`stock_flow_lots` 與 `stock_flow_lots_detailed` 使用同名索引** `stock_flow_stock_date_idx`，**同一個資料庫不要兩張都建**（PostgreSQL 索引名稱在 schema 內唯一，第二張的索引會被略過）。一般只需要 `stock_flow_lots_detailed`。
>
> ℹ️ **欄名相容**：`db_writer.py` 在執行期讀取目標表實際欄位並對應，**同時相容** `stock_code`/`stock_name` 與 legacy 短欄名 `code`/`cname`。若既有表用 legacy 欄名，`init_db.py` 建索引那句可能印 `[skip]`（DDL 寫的是 `stock_code`），屬正常、不影響回補。

---

## 1. `public.stock_flow_lots_detailed`（回補主表）

主鍵：`(da, stock_code, broker_code, branch_code)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `da` | timestamp | NOT NULL | — | 交易日（由解析出的 `trade_date` 寫入） |
| `stock_code` | varchar(50) | NOT NULL | — | 個股代碼 |
| `stock_name` | varchar(100) | NOT NULL | — | 個股名稱 |
| `broker_code` | varchar(50) | — | — | 券商代碼（code1） |
| `branch_code` | varchar(50) | — | — | 分行代碼（正規化後） |
| `branch_code_raw` | text | — | — | 分行代碼原始值（可能為 hex 形式，如 `0031003000320041`） |
| `broker_name` | text | — | — | 券商名稱 |
| `branch_name` | text | — | — | 分行名稱 |
| `buy_lots` | bigint | — | — | 買進張數 |
| `sell_lots` | bigint | — | — | 賣出張數 |
| `net_lots` | bigint | — | — | 淨買賣張數（buy − sell） |
| `source_url` | text | — | — | 來源頁面 URL |
| `fetched_at` | timestamp | — | — | 抓取時間 |
| `created_at` | timestamp | — | `now()` | 入庫時間 |

索引：
- `stock_flow_stock_date_idx (stock_code, da DESC)`
- `stock_flow_da_idx (da)`
- `stock_flow_broker_branch_da_idx (broker_code, branch_code, da)`

完整 DDL：`pg_sample_code/create_stock_flow_lots_detailed.sql`

---

## 2. `public.brokers`（券商參考表）

主鍵：`(broker_code)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `broker_code` | varchar(50) | NOT NULL | — | 券商代碼（PK） |
| `broker_name` | varchar(200) | — | — | 券商中文名稱 |
| `fetched_at` | timestamptz | — | — | 抓取時間 |
| `created_at` | timestamptz | — | `now()` | 入庫時間 |

索引：`idx_brokers_name (broker_name)`

---

## 3. `public.branches`（分行參考表）

主鍵：`(broker_code, branch_code_raw)`　外鍵：`broker_code` → `brokers(broker_code)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `broker_code` | varchar(50) | NOT NULL | — | 券商代碼（PK 之一、FK） |
| `branch_code_raw` | text | NOT NULL | — | 分行代碼原始值（PK 之一） |
| `branch_code` | varchar(50) | — | — | 分行代碼（正規化後） |
| `branch_name` | varchar(200) | — | — | 分行中文名稱 |
| `is_broker_level` | boolean | — | `FALSE` | 是否為券商總表層級（非個別分行） |
| `fetched_at` | timestamptz | — | — | 抓取時間 |
| `created_at` | timestamptz | — | `now()` | 入庫時間 |

索引：`idx_branches_branch_code (branch_code)`、`idx_branches_name (branch_name)`

完整 DDL（brokers + branches）：`pg_sample_code/create_brokers_branches.sql`

---

## 4. `public.stock_flow_lots`（替代 schema，非預設）

與 `stock_flow_lots_detailed` 同樣存買賣超，但以 `trade_date`（date）為時間鍵、且多一個 `metric_type` 欄（可同時存 `lots` 與 `amount`）。**預設不寫入此表**；若要使用需把 `db_writer.insert_records(..., table="stock_flow_lots")` 指定，且**不要與 detailed 同庫並存**（索引同名）。

主鍵：`(trade_date, broker_code, branch_code, stock_code, metric_type)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `trade_date` | date | NOT NULL | — | 交易日 |
| `metric_type` | varchar(16) | NOT NULL | `'lots'` | 指標類型：`lots`（張數）/ `amount`（金額） |
| `broker_code` | varchar(32) | NOT NULL | — | 券商代碼 |
| `branch_code` | varchar(32) | NOT NULL | — | 分行代碼 |
| `branch_code_raw` | text | — | — | 分行代碼原始值 |
| `broker_name` | text | — | — | 券商名稱 |
| `branch_name` | text | — | — | 分行名稱 |
| `stock_code` | varchar(32) | NOT NULL | — | 個股代碼 |
| `stock_name` | text | — | — | 個股名稱 |
| `buy_lots` | bigint | — | — | 買進張數 |
| `sell_lots` | bigint | — | — | 賣出張數 |
| `net_lots` | bigint | — | — | 淨張數 |
| `source_url` | text | — | — | 來源 URL |
| `fetched_at` | timestamptz | — | — | 抓取時間 |
| `created_at` | timestamptz | — | `now()` | 入庫時間 |

索引：
- `stock_flow_stock_date_idx (stock_code, trade_date DESC)`
- `stock_flow_trade_date_idx (trade_date)`
- `stock_flow_broker_branch_date_idx (broker_code, branch_code, trade_date)`

完整 DDL：`pg_sample_code/create_stock_flow_lots.sql`

---

## 從 0 開始：建表並回補

全新環境把資料庫從空的補到有資料的完整步驟（PowerShell）：

```powershell
# 0) 安裝環境並設定 .env（見 README「安裝」一節，或一鍵： .\scripts\setup.ps1）
#    .env 需填好 PGHOST / PGPORT / PGUSER / PGPASSWORD（指向目標 PostgreSQL）

# 1) 建立資料表（idempotent，可重複執行；不需要 psql）
.\.venv\Scripts\python.exe scripts\init_db.py --db tw
#    等同手動執行：
#    psql -U <user> -d tw -f pg_sample_code\create_brokers_branches.sql
#    psql -U <user> -d tw -f pg_sample_code\create_stock_flow_lots_detailed.sql

# 2) （選用）灌券商/分行參考表 brokers / branches
.\.venv\Scripts\python.exe scripts\update_brokers.py --db tw

# 3) 回補 flow 資料到 stock_flow_lots_detailed（DB 模式不落地、可斷點續跑）
.\.venv\Scripts\python.exe scripts\backfill_daily.py `
  --start-date 2026-06-18 --end-date 2026-06-22 --db-name tw --resume
#    要回補全部歷史就把區間拉大，例如 --start-date 2025-12-01 --end-date 2026-04-10
```

### 驗證資料量

```sql
SELECT count(*) FROM public.stock_flow_lots_detailed;          -- flow 筆數
SELECT count(*) FROM public.brokers;                           -- 券商數
SELECT count(*) FROM public.branches;                          -- 分行數
SELECT max(da), min(da) FROM public.stock_flow_lots_detailed;  -- 已回補的日期範圍
```

### 注意事項
- **表必須先建好（步驟 1）**，否則回補會報 `Could not find columns for table ... stock_flow_lots_detailed`。
- 所有寫入皆 `ON CONFLICT DO NOTHING`，**重複回補同一天不會產生重複資料**，可安心重跑。
- DB 模式（`--db-name`）只寫 Postgres、**不**輸出 `data/raw` / `data/processed`。
