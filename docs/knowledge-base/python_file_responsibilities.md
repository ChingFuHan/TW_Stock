# Python File Responsibilities

這份文件列出目前專案內每個 Python 檔案的責任範圍，方便後續交接、分工與定位修改點。

## Source

### [src/__init__.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/__init__.py)

- 保留 `src` 套件根目錄，內容目前為空。
- 功能上沒有業務邏輯，不建議在這裡放 crawler 行為。

### [src/tw_broker_flows/__init__.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/__init__.py)

- 定義套件版本資訊 `__version__`。
- 不負責 CLI、抓取、解析或 IO。

### [src/tw_broker_flows/__main__.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/__main__.py)

- 套件執行入口。
- `python -m src.tw_broker_flows` 會從這裡轉呼叫 `main.main()`。
- 如果 CLI 啟動失敗，先看這裡是否仍正確指向 `main`。

### [src/tw_broker_flows/main.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/main.py)

- 目前整個 daily pipeline 的協調中心。
- 負責:
  - 解析 CLI 參數
  - 載入手動 URL / JSON targets / branch CSV source
  - 驗證 `start_date` / `end_date`
  - 載入 lookup 資料並與 branch CSV 合併
  - 生成 daily URLs
  - 呼叫 `fetcher.py` 抓 HTML
  - 呼叫 `parser.py` 解析欄位與排行資料
  - 呼叫 `storage.py` 寫入 raw / processed / reference
  - 紀錄 run log
- 這次改動後，daily 批次主路徑使用:
  - `--branch-codes-file`
  - `--start-date`
  - `--end-date`
- 如果需求是「加新 CLI 參數」「改批次模式」「換 daily URL 規則」，優先改這個檔案。

### [src/tw_broker_flows/fetcher.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/fetcher.py)

- 純 function-based 的 HTTP 抓取模組。
- 負責:
  - 建立 request
  - 下載 HTML bytes
  - 判斷編碼
  - 回傳標準化 fetch result dict
- 不負責解析 HTML 結構、不負責 CSV 寫檔。
- 如果未來要加 retry、proxy、rate limit、HTTP client 替換，主要改這個檔案。

### [src/tw_broker_flows/broker_lookup.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/broker_lookup.py)

- 券商 / 分行 lookup 的 function-based 核心模組。
- 負責:
  - 解析 `zbrokerjs.djjs`
  - 建立 lookup dict
  - 從 branch source rows 重建 lookup
  - 合併 lookup 來源
  - `broker_code` / `branch_code` 對應中文名稱
  - 匯出 broker / branch rows
  - 依 `start_date + end_date + code1 + code2` 生成 daily URLs
  - 將 hex 形式 branch code 正規化成可讀值
- 如果需求是「變更 `code1/code2` source 格式」「改 URL 組法」「補名稱解析」，主要改這個檔案。

### [src/tw_broker_flows/parser.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/parser.py)

- 專門解析券商 / 分行頁面的 HTML 結構。
- 負責:
  - 判斷 trade date
  - 判斷 metric type
  - 解析 URL / HTML 中的 broker code、branch code
  - 解析 lookback 顯示文字
  - 找出買超 / 賣超排行表
  - 萃取股票代碼、股票名稱與數值欄位
  - 組成 processed CSV 所需的 records
- 這裡仍保留 `HTMLParser` 子類別與內部 table node class，因為 HTML 樹解析需要。
- 如果頁面 DOM 或欄位順序改版，優先調整這個檔案。

### [src/tw_broker_flows/storage.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/storage.py)

- 所有檔案命名與輸出格式的集中管理點。
- 負責:
  - 建立 output 目錄
  - raw / processed 檔名 slug 規則
  - broker / branch reference CSV 欄位順序
  - processed CSV 欄位順序
  - 寫出 raw HTML 與 CSV
- 這次改動後，reference CSV 欄位已改成:
  - brokers: `券商中文`, `code1`, `分行數`, `fetched_at`
  - branches: `券商中文`, `分行中文`, `code1`, `code2`, `is_broker_level`, `fetched_at`
- 如果需求是「改檔名規則」「改 CSV schema」「加欄位」，主要改這個檔案。

## Tests

### [tests/test_broker_lookup.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/tests/test_broker_lookup.py)

- 驗證 lookup 與 URL 生成規則。
- 目前覆蓋:
  - lookup 名稱解析
  - broker / branch row 匯出數量
  - hex branch code 正規化
  - daily URL 生成
  - 由 `券商中文, 分行中文, code1, code2` rows 重建 lookup

### [tests/test_parser.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/tests/test_parser.py)

- 驗證 sample HTML 的解析結果。
- 目前覆蓋:
  - amount 頁面解析
  - lots 頁面解析
  - broker / branch 名稱填補
  - 股票名稱與數值欄位

## 快速定位

- 改 CLI / daily 批次流程: [main.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/main.py)
- 改 lookup / `code1` / `code2` / URL 組法: [broker_lookup.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/broker_lookup.py)
- 改 HTML 解析: [parser.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/parser.py)
- 改輸出欄位 / 檔名: [storage.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/storage.py)
- 改抓取策略: [fetcher.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/fetcher.py)
