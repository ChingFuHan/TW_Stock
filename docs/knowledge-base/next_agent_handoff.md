# Next Agent Handoff

## Current State

這個專案目前可以抓台股券商 / 分行頁面的 daily 買超賣超資料，並寫出:
- raw HTML
- processed CSV
- broker / branch reference CSV
- run log

這次已完成的核心變更:
- 專案目標 Python 版本改為 `3.11`
- daily 抓取主流程改成 function-based
- `FetchResult` / `BrokerLookup` 的對外 class 介面已移除
- daily URL 生成改成 `start_date + end_date + code1 + code2`
- `code1/code2` 來源改成 `券商中文, 分行中文, code1, code2`
- `data/reference/branches.csv` 已改成可直接作為 daily source 的欄位格式

## Where To Start

先看這幾份文件:
- [README.md](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/README.md)
- [python_file_responsibilities.md](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/docs/knowledge-base/python_file_responsibilities.md)
- [project_snapshot.md](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/docs/knowledge-base/project_snapshot.md)

再看主要程式:
- [main.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/main.py)
- [broker_lookup.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/broker_lookup.py)
- [parser.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/parser.py)
- [storage.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/storage.py)

## Python File Ownership Map

完整對照表在:
- [python_file_responsibilities.md](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/docs/knowledge-base/python_file_responsibilities.md)

快速摘要:
- `main.py`: CLI、daily pipeline orchestration
- `broker_lookup.py`: lookup 解析、名稱對應、daily URL 生成
- `fetcher.py`: HTTP 抓取與編碼判斷
- `parser.py`: HTML 表格解析
- `storage.py`: raw / processed / reference 寫檔規則
- `tests/*.py`: regression tests

## Daily Input Contract

目前 daily 批次輸入格式固定為 CSV:

```csv
券商中文,分行中文,code1,code2
土銀,土銀,1030,1030
法銀巴黎,法銀巴黎,8900,8900
```

注意:
- `code1` 是券商代碼
- `code2` 是實際 request 要用的分行代碼原始值
- 某些 `code2` 不是純數字，而是 hex 形式，例如 `0031003000320041`
- 顯示分析時可以看 parser 產出的 `branch_code`
- 重新組 URL 或重新抓取時要用 `code2`

## Daily URL Rule

目前生成規則是:

```python
url = f"{base_url}?a={code1}&b={code2}&c={metric}&e={start_date}&f={end_date}"
```

例如:

```text
https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=1030&b=1030&c=B&e=2026-04-02&f=2026-04-02
```

## Commands To Reproduce

建立或重建 venv:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

只匯出 reference:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows --export-lookup-only
```

用 branch CSV 跑 daily:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --branch-codes-file config/branch_codes.example.csv `
  --start-date 2026-04-02 `
  --end-date 2026-04-02
```

從 lookup 全量生成 daily targets:

```powershell
.\.venv\Scripts\python.exe -m src.tw_broker_flows `
  --all-branches `
  --metric-type both `
  --start-date 2026-04-02 `
  --end-date 2026-04-02
```

跑測試:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Verified In This Handoff

這次實際驗證過:
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- `.\.venv\Scripts\python.exe -m src.tw_broker_flows --export-lookup-only`
- `.\.venv\Scripts\python.exe -m src.tw_broker_flows --branch-codes-file config\branch_codes.example.csv --start-date 2026-04-02 --end-date 2026-04-02 --max-targets 1`
- `.\.venv\Scripts\python.exe -m src.tw_broker_flows --all-branches --start-date 2026-04-02 --end-date 2026-04-02 --max-targets 1`

## Known Constraints

- repo 內 `.python-version` 已設定為 `3.11`，但本機當前 `.venv` 仍是 Python `3.13`
- 本次驗證是用現有 `.venv` 跑過的，不是用 3.11 runtime 重新建環境
- parser 仍依賴上游頁面結構與 Big5 編碼，如果站方改版，優先檢查 [parser.py](/C:/Users/marshall.han/Documents/gemini_taiwan_stock/src/tw_broker_flows/parser.py)

## Suggested Next Steps

1. 在機器上安裝 Python 3.11，重建 `.venv`，確認 3.11 下測試與 CLI 都正常。
2. 以 `data/reference/branches.csv` 為 source 做更大規模的 daily 抓取驗證。
3. 如果要長期跑批次，優先補 retry、rate limiting、失敗重跑策略。
4. 如果未來要做分析管線，再考慮把 processed CSV 匯出成更適合分析的格式。
