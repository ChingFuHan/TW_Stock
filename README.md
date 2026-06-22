# TW_Stock

台股券商 / 分行每日買賣超資料爬蟲。

目前流程已調整為:
- Python 3.11 為專案目標版本
- daily 抓取流程以 function 為主，不再依賴 `FetchResult` / `BrokerLookup` 這類 class 介面
- daily URL 生成改用 `start_date + end_date + code1 + code2`
- `code1` / `code2` 的來源改為 CSV 欄位: `券商中文`, `分行中文`, `code1`, `code2`

## 專案結構

```text
.
├─ config/
│  ├─ branch_codes.example.csv
│  └─ targets.example.json
├─ data/
│  ├─ logs/
│  ├─ processed/
│  ├─ raw/
│  └─ reference/
├─ docs/
├─ src/
│  └─ tw_broker_flows/
└─ tests/
```

## 環境需求

- Windows 10/11 + PowerShell
- Python 3.11.x（專案根目錄 `.python-version` 指定 3.11）
- 若要用 DB 模式（`--db-name`）：一個可連線的 PostgreSQL

## 安裝（fresh clone 後請依序完成）

> ⚠️ **最常見的錯誤是「建好 venv 卻忘了安裝套件」**。`.venv/` 不會進版控，clone 下來沒有它；而且建好 venv 後若沒跑 `pip install`，一執行 DB 回補就會出現
> `ModuleNotFoundError: No module named 'psycopg2'`。請務必完成下面**每一步**。

### 方式 A：一鍵設定（推薦）

```powershell
.\scripts\setup.ps1
```

此腳本會自動：建立 `.venv` → 安裝相依套件 → 由 `.env.example` 建立 `.env` → 驗證套件就緒。
完成後只要編輯 `.env` 填入連線資訊即可。

### 方式 B：手動逐步

```powershell
# 1) 建立虛擬環境（fresh clone 沒有 .venv，必須自己建）
py -3.11 -m venv .venv

# 2) 安裝相依套件 ★必做★（漏掉這步 DB 回補一定失敗）
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3) 驗證套件（印出 deps OK 就代表就緒）
.\.venv\Scripts\python.exe -c "import psycopg2, dotenv; print('deps OK')"
```

（若 PowerShell 允許執行啟用腳本，也可先 `.\.venv\Scripts\Activate.ps1` 再用 `python`。）

## DB 模式（`--db-name`）連線設定

DB 回補需要 `psycopg2-binary` 與 `python-dotenv`（已列入 `requirements.txt`，上面步驟會一併裝好）。連線機密放在 `.env`（已被 `.gitignore`，不進版控）：

```powershell
Copy-Item .env.example .env
# 編輯 .env，填入 PGHOST / PGPORT / PGUSER / PGPASSWORD（或單一 DATABASE_URL）
```

- `.env` 由 `python-dotenv` 載入 → 程式以環境變數讀取，原始碼不含任何機密。
- **若沒裝 `python-dotenv`，`.env` 不會被載入**，連線會用空密碼預設而失敗——這也是為什麼安裝步驟 2 不能略過。
- 資料表 schema 見 `pg_sample_code/create_*.sql`（用來建立 `stock_flow_lots_detailed` 等表）。

## Daily URL 規則

daily 模式會依照下列參數組 URL:

```python
start_date = "2026-04-02"
end_date = "2026-04-02"
code1 = "1030"
code2 = "1030"
```

實際查詢 URL 會組成:

```text
https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=1030&b=1030&c=B&e=2026-04-02&f=2026-04-02
```

其中:
- `code1` 是券商代碼
- `code2` 是分行代碼
- `code2` 必須使用可直接發 request 的原始值
- 部分分行代碼是上游的 hex 形式，例如 `0031003000320041`

## code1 / code2 來源

daily 批次抓取現在使用 CSV 作為 source，欄位格式如下:

```csv
券商中文,分行中文,code1,code2
土銀,土銀,1030,1030
法銀巴黎,法銀巴黎,8900,8900
```

範例檔:
- `config/branch_codes.example.csv`

lookup 匯出後的參考檔:
- `data/reference/branches.csv`

`data/reference/branches.csv` 的前四欄就是 daily source:
- `券商中文`
- `分行中文`
- `code1`
- `code2`

## 使用方式

只匯出券商 / 分行對照表:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows --export-lookup-only
```

使用 CSV source 抓 daily 資料:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --branch-codes-file config/branch_codes.example.csv `
  --start-date 2026-04-02 `
  --end-date 2026-04-02
```

直接抓指定 URL:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --url "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=1030&b=1030&c=B&e=2026-04-02&f=2026-04-02"
```

從 lookup 全量生成所有券商 / 分行的 daily targets:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --all-branches `
  --metric-type amount `
  --start-date 2026-04-02 `
  --end-date 2026-04-02
```

同時抓 amount + lots:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --all-branches `
  --metric-type both `
  --start-date 2026-04-02 `
  --end-date 2026-04-02
```

## 歷史回補 / 每日更新（Backfill）

`scripts/backfill_daily.py` 會逐日呼叫主程式，支援斷點續傳與空資料重試。

> **重要**：回補請一律加 `--db-name <資料庫名>`。
> 此模式只會把資料寫進 PostgreSQL，**不會**產生 `data/raw` 與 `data/processed` 檔案，避免佔用硬碟。
> 因為 DB 模式不產 CSV，跳過已完成日期請改用 `--resume`（讀取進度檔 `data/logs/backfill_progress.json`）。

歷史回補進 DB（推薦）:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_daily.py `
  --start-date 2017-01-01 `
  --end-date 2026-04-10 `
  --db-name tw `
  --resume
```

每日更新（只抓今天）進 DB:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_daily.py `
  --start-date 2026-06-23 `
  --end-date 2026-06-23 `
  --db-name tw
```

指定 metric-type（`lots` / `amount` / `both`，預設 `lots`）:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_daily.py `
  --start-date 2025-01-01 --end-date 2025-12-31 `
  --metric-type lots --db-name tw --resume
```

Dry-run（只列出要抓的日期，不實際執行）:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_daily.py `
  --start-date 2024-01-01 --end-date 2024-01-31 --dry-run
```

常用選項:
- `--resume`：從上次進度繼續，自動跳過已完成日期
- `--retry-failed`：重新嘗試之前失敗的日期
- `--empty-retry-days 30`：距今 N 天內的空資料仍會重試，超過視為非交易日（預設 30，設 0 則不重試）
- `--max-workers 15`：每日抓取的並行數（預設 15）
- `--delay 1.0`：每日之間的延遲秒數，避免被封鎖

## 輸出

> 使用 `--db-name` 時，資料直接寫入 PostgreSQL，**不會**輸出 `data/raw` / `data/processed` 檔案（僅保留小體積的 `data/logs/run_*.log` 與 `data/reference/*.csv`）。下列為**未指定** `--db-name` 的 CSV 模式輸出。

執行後會輸出:
- `data/raw/{trade_date}/...html`
- `data/processed/{trade_date}/...csv`
- `data/logs/run_*.log`
- `data/reference/brokers.csv`
- `data/reference/branches.csv`

processed CSV 主要欄位:
- `trade_date`
- `broker_code`
- `branch_code`
- `branch_code_raw`
- `broker_name`
- `branch_name`
- `stock_code`
- `stock_name`
- `metric_type`
- `source_url`
- `fetched_at`

## 疑難排解（Troubleshooting）

| 症狀 / 錯誤訊息 | 原因 | 解法 |
|---|---|---|
| `.\.venv\Scripts\python.exe` 不存在 / 無法辨識 | fresh clone 沒有 `.venv`（已被 gitignore） | 先建 venv：`py -3.11 -m venv .venv`（或直接跑 `.\scripts\setup.ps1`） |
| `ModuleNotFoundError: No module named 'psycopg2'` | 建了 venv 但**沒安裝相依套件** | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `[warn] python-dotenv 未安裝，.env 不會被載入` | 同上，`python-dotenv` 沒裝 | 同上，跑 `pip install -r requirements.txt` |
| DB 回補全失敗 / 密碼錯，但 `.env` 看起來有填 | `python-dotenv` 沒裝 → `.env` 沒被載入 → 連線用空預設 | 同上，安裝相依套件後再跑 |
| `could not connect` / `Connection refused` | PostgreSQL 沒開、或 `.env` 的 host/port/帳密不對 | 確認 PG 有在跑、`.env` 連線資訊正確、網路/防火牆可達 |
| `Could not find columns for table ... stock_flow_lots_detailed` | 目標資料表不存在 | 用 `pg_sample_code/create_stock_flow_lots_detailed.sql` 建表 |
| DB 模式跑完 `data/raw`、`data/processed` 沒檔案 | 正常行為 | DB 模式不落地、只寫 Postgres；要本地 CSV 請改用**不帶** `--db-name` 的指令 |
| 某些分點「無資料 / 解析失敗」 | 該日/分點本來就沒交易資料（假日、非交易日） | 正常現象，程式會跳過繼續 |

> **自我檢查一鍵指令**：
> ```powershell
> .\.venv\Scripts\python.exe -c "import psycopg2, dotenv; print('deps OK')"
> ```
> 印出 `deps OK` 代表套件就緒；若報 `ModuleNotFoundError` 就是還沒安裝相依套件（跑安裝步驟 2）。

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 補充

- parser 仍保留 `HTMLParser` 所需的內部 helper class
- daily 抓取主流程、lookup 組裝、URL 生成都已改成 function-based
- 若要送 request，分行代碼請優先使用 `code2`
