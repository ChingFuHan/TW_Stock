# 資料庫 Schema 與從 0 建置指南

本專案使用 **PostgreSQL**。建表 DDL 位於 `pg_sample_code/create_*.sql`，共定義 **4 張表**。
本文件依**實際部署**的 schema 把每張表的完整欄位、型別、主鍵、外鍵與索引列出，並附完整 DDL 與「從空資料庫補到有資料」的流程。

## 總覽

| 表 | 用途 | 回補是否需要 | 由誰寫入 | 建表 SQL |
|---|---|---|---|---|
| `public.stock_flow_lots_detailed` | **回補主表**：每日券商分點個股買賣超（張數） | ✅ 必要 | `src/tw_broker_flows/db_writer.py`（`backfill_daily.py --db-name`） | `create_stock_flow_lots_detailed.sql` |
| `public.brokers` | 券商代碼 ↔ 名稱對照（參考表） | ⬜ 選用 | **回補時自動 upsert**（main.py，DB 模式）／`scripts/update_brokers.py` | `create_brokers_branches.sql` |
| `public.branches` | 分行代碼 ↔ 名稱對照（參考表，外鍵指向 brokers） | ⬜ 選用 | **回補時自動 upsert**（main.py，DB 模式）／`scripts/update_brokers.py` | `create_brokers_branches.sql` |
| `public.stock_flow_lots` | flow 的**替代 schema**（以 `trade_date`+`metric_type` 為鍵，**非實際部署表**） | ⬜ 替代 | 非預設寫入目標 | `create_stock_flow_lots.sql` |

關係：`branches.broker_code` →（FK `branches_fk_broker`，MATCH SIMPLE）→ `brokers.broker_code`。flow 表與 brokers/branches 無 FK（flow 表自帶 broker/branch 名稱欄位）。

> ℹ️ **欄名（重要）**：實際部署的 `stock_flow_lots_detailed` 用 **legacy 欄名 `code`/`cname`**（個股代碼/名稱），不是 `stock_code`/`stock_name`。`db_writer.py` 在執行期讀取目標表實際欄位並對應——把解析出的 `stock_code`/`stock_name` 寫進此表的 `code`/`cname`，因此回補正常運作。用本文件的 DDL 從 0 建表後，`init_db.py` 不會對 `code` 索引報 `[skip]`。

---

## 1. `public.stock_flow_lots_detailed`（回補主表）

主鍵：`(da, code, broker_code, branch_code)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `da` | timestamp without time zone | NOT NULL | — | 交易日（由解析出的 `trade_date` 寫入） |
| `code` | varchar(50) | NOT NULL | — | 個股代碼（PK 之一） |
| `cname` | varchar(50) | NOT NULL | — | 個股名稱 |
| `broker_code` | varchar(50) | NOT NULL | — | 券商代碼（code1，PK 之一） |
| `branch_code` | varchar(50) | NOT NULL | — | 分行代碼（正規化後，PK 之一） |
| `branch_code_raw` | text | — | — | 分行代碼原始值（可能為 hex，如 `0031003000320041`） |
| `broker_name` | text | — | — | 券商名稱 |
| `branch_name` | text | — | — | 分行名稱 |
| `buy_lots` | bigint | — | — | 買進張數 |
| `sell_lots` | bigint | — | — | 賣出張數 |
| `net_lots` | bigint | — | — | 淨買賣張數（buy − sell） |
| `source_url` | text | — | — | 來源頁面 URL |
| `fetched_at` | timestamp without time zone | — | — | 抓取時間 |
| `created_at` | timestamp without time zone | — | `now()` | 入庫時間 |

索引（共 5 個，其中兩對為生產累積的重複索引）：
- `idx_stock_flow_broker_branch_da (broker_code, branch_code, da)`
- `idx_stock_flow_code_da (code, da DESC)`
- `idx_stock_flow_da (da)`
- `stock_flow_broker_branch_da_idx (broker_code, branch_code, da)` — 與 `idx_stock_flow_broker_branch_da` **重複**
- `stock_flow_da_idx (da)` — 與 `idx_stock_flow_da` **重複**

完整 DDL：

```sql
CREATE TABLE IF NOT EXISTS public.stock_flow_lots_detailed
(
    da timestamp without time zone NOT NULL,
    code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    cname character varying(50) COLLATE pg_catalog."default" NOT NULL,
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code_raw text COLLATE pg_catalog."default",
    broker_name text COLLATE pg_catalog."default",
    branch_name text COLLATE pg_catalog."default",
    buy_lots bigint,
    sell_lots bigint,
    net_lots bigint,
    source_url text COLLATE pg_catalog."default",
    fetched_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT stock_flow_lots_detailed_pkey PRIMARY KEY (da, code, broker_code, branch_code)
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.stock_flow_lots_detailed OWNER to postgres;

CREATE INDEX IF NOT EXISTS idx_stock_flow_broker_branch_da
    ON public.stock_flow_lots_detailed USING btree
    (broker_code ASC NULLS LAST, branch_code ASC NULLS LAST, da ASC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_stock_flow_code_da
    ON public.stock_flow_lots_detailed USING btree
    (code ASC NULLS LAST, da DESC NULLS FIRST);
CREATE INDEX IF NOT EXISTS idx_stock_flow_da
    ON public.stock_flow_lots_detailed USING btree (da ASC NULLS LAST);
-- 下面兩個與上面重複（生產累積，全新建置可省略）
CREATE INDEX IF NOT EXISTS stock_flow_broker_branch_da_idx
    ON public.stock_flow_lots_detailed USING btree
    (broker_code ASC NULLS LAST, branch_code ASC NULLS LAST, da ASC NULLS LAST);
CREATE INDEX IF NOT EXISTS stock_flow_da_idx
    ON public.stock_flow_lots_detailed USING btree (da ASC NULLS LAST);
```

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

```sql
CREATE TABLE IF NOT EXISTS public.brokers
(
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    broker_name character varying(200) COLLATE pg_catalog."default",
    fetched_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT brokers_pkey PRIMARY KEY (broker_code)
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.brokers OWNER to postgres;

CREATE INDEX IF NOT EXISTS idx_brokers_name
    ON public.brokers USING btree (broker_name ASC NULLS LAST);
```

---

## 3. `public.branches`（分行參考表）

主鍵：`(broker_code, branch_code_raw)`　外鍵：`broker_code` → `brokers(broker_code)`（MATCH SIMPLE, ON UPDATE/DELETE NO ACTION）

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `broker_code` | varchar(50) | NOT NULL | — | 券商代碼（PK 之一、FK） |
| `branch_code_raw` | text | NOT NULL | — | 分行代碼原始值（PK 之一） |
| `branch_code` | varchar(50) | — | — | 分行代碼（正規化後） |
| `branch_name` | varchar(200) | — | — | 分行中文名稱 |
| `is_broker_level` | boolean | — | `false` | 是否為券商總表層級（非個別分行） |
| `fetched_at` | timestamptz | — | — | 抓取時間 |
| `created_at` | timestamptz | — | `now()` | 入庫時間 |

索引：`idx_branches_branch_code (branch_code)`、`idx_branches_name (branch_name)`

```sql
CREATE TABLE IF NOT EXISTS public.branches
(
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code_raw text COLLATE pg_catalog."default" NOT NULL,
    branch_code character varying(50) COLLATE pg_catalog."default",
    branch_name character varying(200) COLLATE pg_catalog."default",
    is_broker_level boolean DEFAULT false,
    fetched_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT branches_pkey PRIMARY KEY (broker_code, branch_code_raw),
    CONSTRAINT branches_fk_broker FOREIGN KEY (broker_code)
        REFERENCES public.brokers (broker_code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.branches OWNER to postgres;

CREATE INDEX IF NOT EXISTS idx_branches_branch_code
    ON public.branches USING btree (branch_code ASC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_branches_name
    ON public.branches USING btree (branch_name ASC NULLS LAST);
```

---

## 4. `public.stock_flow_lots`（替代 schema，非實際部署）

倉庫附帶的**替代** flow schema：以 `trade_date`(date) 為時間鍵、多一個 `metric_type` 欄（可同時存 `lots` 與 `amount`），且個股欄位用 `stock_code`/`stock_name`。**目前未部署、預設不寫入**；若要使用需把 `db_writer.insert_records(..., table="stock_flow_lots")` 指定。

主鍵：`(trade_date, broker_code, branch_code, stock_code, metric_type)`

| 欄位 | 型別 | Null | 預設 | 說明 |
|---|---|---|---|---|
| `trade_date` | date | NOT NULL | — | 交易日 |
| `metric_type` | varchar(16) | NOT NULL | `'lots'` | `lots`（張數）/ `amount`（金額） |
| `broker_code` | varchar(32) | NOT NULL | — | 券商代碼 |
| `branch_code` | varchar(32) | NOT NULL | — | 分行代碼 |
| `branch_code_raw` | text | — | — | 分行代碼原始值 |
| `broker_name` | text | — | — | 券商名稱 |
| `branch_name` | text | — | — | 分行名稱 |
| `stock_code` | varchar(32) | NOT NULL | — | 個股代碼 |
| `stock_name` | text | — | — | 個股名稱 |
| `buy_lots` / `sell_lots` / `net_lots` | bigint | — | — | 買/賣/淨張數 |
| `source_url` | text | — | — | 來源 URL |
| `fetched_at` | timestamptz | — | — | 抓取時間 |
| `created_at` | timestamptz | — | `now()` | 入庫時間 |

索引：`stock_flow_stock_date_idx (stock_code, trade_date DESC)`、`stock_flow_trade_date_idx (trade_date)`、`stock_flow_broker_branch_date_idx (broker_code, branch_code, trade_date)`。完整 DDL 見 `pg_sample_code/create_stock_flow_lots.sql`。

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

# 2) brokers / branches 參考表：DB 模式回補（步驟 3）會「自動 upsert」完整 lookup，
#    通常不需手動。若想先單獨灌或手動刷新，才需要這行（選用）：
# .\.venv\Scripts\python.exe scripts\update_brokers.py --db tw

# 3) 回補 flow 資料到 stock_flow_lots_detailed（DB 模式不落地、可斷點續跑）
#    這步會同時自動把 brokers / branches 補齊（每天呼叫、ON CONFLICT 跳過已存在者）
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

### brokers / branches 自動補齊（完整性）
- DB 模式回補時，`main.py` 會把**完整 lookup（全部券商/分點）** upsert 進 `brokers`/`branches`，**與爬取成敗無關**——即使某分點當天頁面失敗或空資料，它的對照仍會被寫入。
- 寫入採「批次 + 失敗自動退回逐列」，單列問題不影響其餘；無效列（缺 `broker_code`/`branch_code_raw`）會被略過並計入 `skipped_invalid`。
- log 會印 `brokers total/inserted | branches total/inserted | skipped_invalid | row_failures`，可用 `SELECT count(*)` 與 `total` 核對。回補每天都呼叫一次，**缺漏隔天自動補齊**。

### 注意事項
- **表必須先建好（步驟 1）**，否則回補會報 `Could not find columns for table ... stock_flow_lots_detailed`（brokers/branches 未建則 upsert 只警告、不中斷）。
- 所有寫入皆 `ON CONFLICT DO NOTHING`，**重複回補同一天不會產生重複資料**，可安心重跑。
- DB 模式（`--db-name`）只寫 Postgres、**不**輸出 `data/raw` / `data/processed`。
