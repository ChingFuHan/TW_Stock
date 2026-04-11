# 歷史資料回補 / 每日更新指令

## 基本語法
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD [選項]
```

---

## 常用指令範例

### 1️⃣ 歷史回補（2017 年至今）
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10
```
- ⏱️ 耗時：約 50 小時（2415 工作日）
- 💾 輸出：CSV 到 `data\processed\{YYYYMMDD}\` 
- 📊 進度：自動保存至 `data\logs\backfill_progress.json`

### 2️⃣ 中斷後繼續（斷點續傳）
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume
```
- 自動跳過已完成的日期
- 空資料日期（≤30天）會重試
- 保留失敗記錄

### 3️⃣ 預覽要抓的日期（Dry-run）
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume --dry-run
```
- 顯示實際要抓幾天
- 不實際執行，可用來確認邏輯

### 4️⃣ 直接寫入資料庫
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-01 --end-date 2026-04-10 --db-name tw
```
- 邊抓邊寫入 PostgreSQL
- 仍存 CSV 到本地
- 執行 `ON CONFLICT DO NOTHING` 規則

### 5️⃣ 每日更新（排程用）
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-11 --end-date 2026-04-11 --resume --db-name tw
```
- 只抓取該日資料
- 適合設定為每日排程任務

### 6️⃣ 重試失敗的日期
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume --retry-failed
```
- 讀取進度檔中的失敗記錄
- 重新執行這些日期

### 7️⃣ 指定交易指標（成交金額）
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-01 --end-date 2026-04-10 --metric-type amount
```
- `lots` = 成交筆數（預設）
- `amount` = 成交金額
- `both` = 同時抓取兩種

### 8️⃣ 調整空資料重試窗口
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-01 --end-date 2026-04-10 --resume --empty-retry-days 0
```
- `--empty-retry-days 30`（預設）= 近 30 天的空資料會重試
- `--empty-retry-days 0` = 空資料一律不重試
- `--empty-retry-days 60` = 近 60 天的空資料會重試

---

## 參數說明

| 參數 | 說明 | 預設值 | 必填 |
|------|------|--------|------|
| `--start-date` | 開始日期 (YYYY-MM-DD) | - | ✅ |
| `--end-date` | 結束日期 (YYYY-MM-DD) | - | ✅ |
| `--resume` | 讀進度檔，自動跳過已完成 | - | - |
| `--dry-run` | 預覽待抓日期，不執行 | - | - |
| `--db-name` | 寫入 PostgreSQL 資料庫名 | - | - |
| `--metric-type` | lots \| amount \| both | `lots` | - |
| `--empty-retry-days` | 空資料重試窗口（天） | `30` | - |
| `--retry-failed` | 重試上次的失敗日期 | - | - |
| `--no-skip-existing` | 強制重抓已有 CSV 的日期 | - | - |
| `--max-workers` | 每日並行抓取數 | `15` | - |
| `--delay` | 日期間延遲秒數 | `1` | - |
| `--progress-file` | 進度檔案路徑 | `data/logs/backfill_progress.json` | - |

---

## 進度追蹤

### 查看進度檔案位置
```bash
echo data\logs\backfill_progress.json
```

### 查看已完成/失敗的日期數
```bash
.venv\Scripts\python.exe -c "
import json
p = json.load(open('data/logs/backfill_progress.json', encoding='utf-8'))
print(f'已完成: {len(p[\"completed_dates\"])} 日')
print(f'失敗: {len(p[\"failed_dates\"])} 日')
"
```

### 查看最近完成的日期
```bash
.venv\Scripts\python.exe -c "
import json
from datetime import datetime
p = json.load(open('data/logs/backfill_progress.json', encoding='utf-8'))
completed = sorted(p['completed_dates'].items(), reverse=True)[:5]
for date, info in completed:
    csv_count = info.get('csv_count', '?')
    completed_at = info.get('completed_at', '?')
    print(f'{date}: {csv_count} CSV - {completed_at}')
"
```

---

## 常見使用場景

### 場景 1：全新開始回補 2017 年至今
```bash
# 第一次執行（可能要 50 小時）
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10
```

### 場景 2：中途中斷，需要繼續
```bash
# 只需加 --resume 即可，自動跳過已完成的
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume
```

### 場景 3：排程每日自動更新
```bash
# 每天早上 9 點執行此指令（設定 Windows Task Scheduler）
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-11 --end-date 2026-04-11 --resume --db-name tw
```

### 場景 4：填補某個月份的遺漏資料
```bash
# 先 dry-run 確認有多少天待抓
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2025-01-01 --end-date 2025-01-31 --resume --dry-run

# 確認無誤後執行
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2025-01-01 --end-date 2025-01-31 --resume --db-name tw
```

### 場景 5：重試上次失敗的日期
```bash
.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume --retry-failed
```

---

## 進度檔案格式

進度檔案為 JSON 格式，位置：`data\logs\backfill_progress.json`

```json
{
  "completed_dates": {
    "2026-04-10": {
      "completed_at": "2026-04-12T05:02:32.123456",
      "csv_count": 819,
      "exit_code": 0,
      "source": "existing_files"
    }
  },
  "failed_dates": {
    "2026-04-09": {
      "failed_at": "2026-04-12T04:30:15.789012",
      "error": "timeout"
    }
  }
}
```

- `completed_dates`：成功完成的日期及統計
  - `csv_count`：該日產生的 CSV 檔案數
  - `exit_code`：程式返回碼
  - `source`：來源標記（existing_files 表示已有 CSV）
- `failed_dates`：失敗的日期及錯誤信息

---

## 注意事項

- ⏱️ 每日平均耗時約 71 秒
- 🔄 支援斷點續傳，可中途停止並稍後繼續
- 📊 空資料（csv_count=0）在 30 天內仍會重試
- 🗓️ 自動跳過週末，只抓工作日
- 🏢 不處理台灣股市假日，假日會產出空資料但視為完成
- 📝 所有進度自動保存，異常中斷後可用 `--resume` 恢復
