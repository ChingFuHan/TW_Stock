# gemini_taiwan_stock

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

- Windows PowerShell
- Python 3.11.x
- 專案根目錄有 `.python-version = 3.11`

建立 venv:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 無法執行啟用腳本，可直接用:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

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

## 輸出

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

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 補充

- parser 仍保留 `HTMLParser` 所需的內部 helper class
- daily 抓取主流程、lookup 組裝、URL 生成都已改成 function-based
- 若要送 request，分行代碼請優先使用 `code2`
