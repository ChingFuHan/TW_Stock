# 實作歷程

本文件按時間累積重要實作事件。每次更新應聚焦：

- 本次做了什麼
- 為什麼做
- 產出了什麼
- 還缺什麼

---

## 2026-04-07 初始化需求整理

### 背景

專案剛建立，repo 內尚無程式碼，只有使用者提出的原始需求。

### 本次完成

- 讀取並確認原始需求檔 `task.md`
- 修正終端輸出編碼，確認 `task.md` 內容實際為 UTF-8
- 將原始需求整理成較完整的 `task_enhanced.md`
- 將需求拆成更適合直接執行的 `task_agent.md`

### 產出檔案

- `task.md`
- `task_enhanced.md`
- `task_agent.md`

### 目前判斷

- 使用者目標明確偏向資料工程與籌碼分析前置作業
- 第一優先是穩定抓取與正確解析，不是交易策略
- 現階段最大不確定性不在需求，而在資料來源真實結構

### 遺留事項

- 尚未驗證範例網址是否可連線
- 尚未確認頁面編碼、表格、欄位、資料日期
- 尚未建立任何執行程式

---

## 2026-04-07 建立知識傳遞庫

### 背景

使用者要求把實作歷程保存成知識傳遞庫，讓下一位 agent 更快接手。

### 本次完成

- 在 `docs/knowledge-base/` 下建立知識庫結構
- 新增知識入口、專案快照、決策紀錄、待解問題、交接文件
- 將目前 repo 現況與既有需求文件整理成可延續的工作上下文

### 產出檔案

- `docs/knowledge-base/README.md`
- `docs/knowledge-base/project_snapshot.md`
- `docs/knowledge-base/decisions.md`
- `docs/knowledge-base/open_questions.md`
- `docs/knowledge-base/implementation_journal.md`
- `docs/knowledge-base/next_agent_handoff.md`

### 目前判斷

- 因 repo 還在需求期，知識庫主要價值在於減少重複閱讀與重複猜測
- 後續只要 agent 每輪同步更新 journal 與 handoff，交接成本會大幅下降

### 遺留事項

- 知識庫目前還沒有真實抓取結果
- 一旦開始實作，需把每次驗證與失敗案例補進來

---

## 2026-04-07 第一版爬蟲落地與驗證

### 背景

開始把需求文件轉成可執行程式，先用最小可行版本完成真實抓取、解析、輸出與測試。

### 本次完成

- 驗證 2 個範例網址可成功抓取
- 確認回應編碼為 `big5`
- 保存真實樣本：
  - `data/raw/samples/1030_1030.html`
  - `data/raw/samples/8900_8900_cE_d1.html`
  - `data/raw/samples/zbrokerjs.djjs`
- 發現頁面表頭第一欄雖寫「券商名稱」，實際資料列是股票，並以 `GenLink2stk(...)` 或 anchor 呈現
- 解析 `/z/js/zbrokerjs.djjs`，補上 `broker_name` / `branch_name`
- 建立標準庫版爬蟲模組：
  - `fetcher.py`
  - `broker_lookup.py`
  - `parser.py`
  - `storage.py`
  - `main.py`
- 建立 CLI 入口 `py -m src.tw_broker_flows`
- 建立 README、targets 範例與離線測試
- 端到端跑過 2 個範例網址，成功輸出 raw HTML、CSV、log

### 修改檔案

- `README.md`
- `config/targets.example.json`
- `src/tw_broker_flows/`
- `tests/`
- `data/raw/samples/`

### 驗證

- 離線測試：
  - `py -m unittest discover -s tests -v`
  - 結果：3 個測試全部通過
- 真實抓取：
  - `py -m src.tw_broker_flows --targets-file config/targets.example.json`
  - 結果：
    - `data/raw/20260402/1030__amount__a-1030__b-1030.html`
    - `data/raw/20260402/8900__lots__a-8900__b-8900__c-E__d-1.html`
    - `data/processed/20260402/1030__amount__a-1030__b-1030.csv`
    - `data/processed/20260402/8900__lots__a-8900__b-8900__c-E__d-1.csv`
    - `data/logs/run_20260407_161537.log`

### 目前結論

- 範例網址可以直接抓，不需要瀏覽器自動化
- 主表已內嵌於 HTML，可直接用 `html.parser` 做結構化抽取
- `a/b` 可以對應券商 / 分行 code
- `c=E/B` 可以切換張數 / 金額
- `d=1` 對應近一日

### 遺留事項

- 還沒驗證更多券商 / 分行樣本
- 還沒驗證 `e/f` 自設日期區間
- 還沒做去重與增量合併
- 還沒做更細緻的重試 / 限流 / 失敗恢復策略

---

## 2026-04-07 補上 venv 工作流

### 背景

使用者要求專案改成有虛擬環境的工作流。

### 本次完成

- 在 repo 內建立 `.venv`
- 透過 `ensurepip` 補上 venv 內的 `pip`
- 新增 `requirements.txt`
- 更新 `README.md`，把執行與測試命令改成使用 `.venv`
- 更新 `.gitignore` 排除 `.venv/` 與 `.tmp/`

### 驗證

- 會使用 `.venv\\Scripts\\python.exe` 重跑測試確認環境可用

### 遺留事項

- 目前 `requirements.txt` 只有註解，因為專案仍是標準庫版本
- 若未來引入第三方套件，需把依賴明確寫入 `requirements.txt`

---

## 2026-04-07 補上券商 / 分行全量匯出與全掃模式

### 背景

使用者要求不要只依賴範例網址，希望把全量券商 / 分行清單另存成檔案，並能從 lookup 自動全掃。

### 本次完成

- 在 `BrokerLookup` 新增：
  - 全量券商列輸出
  - 全量分行列輸出
  - 全量 branch target URL 生成
- 在 CLI 新增：
  - `--all-branches`
  - `--metric-type`
  - `--lookback-days`
  - `--export-lookup-only`
  - `--max-targets`
- 會自動輸出：
  - `data/reference/brokers.csv`
  - `data/reference/branches.csv`
- 補上 lookup 與 target generation 測試

### 目前判斷

- 依現有 sample lookup，券商數量為 81，分行 / branch 級 target 數量為 843
- 全掃邏輯已可生成完整 target URL，不再需要手寫範例

### 遺留事項

- 尚未對 843 個全量 targets 做完整長時間實跑驗證
- 尚未統計全掃模式下的失敗率與節流最佳值

---

## 2026-04-07 補上 branch code 原始值與可讀值雙欄

### 背景

使用者發現 `branches.csv` 中部分分行 code 在 Excel 顯示成科學記號，且看起來不像純數字。

### 本次完成

- 確認上游部分 `branch_code` 是以 4 碼一組的 Unicode hex 形式儲存
  - 例如 `0031003000320041` 實際可解碼成 `102A`
- 在 lookup 匯出中新增：
  - `branch_code`：解碼後的人類可讀值
  - `branch_code_raw`：網站原始值
- 在 processed CSV 也同步新增 `branch_code_raw`
- 重新匯出：
  - `data/reference/branches.csv`
  - `data/processed/20260402/*.csv`

### 目前結論

- 後續若要做人看得懂的分析，優先看 `branch_code`
- 後續若要重建請求 URL 或追查上游原始值，使用 `branch_code_raw`

### 驗證

- 測試 6/6 通過
- `branches.csv` 已驗證存在：
  - `branch_code=102A`
  - `branch_code_raw=0031003000320041`

---

## 後續更新模板

未來可依照以下格式追加：

### YYYY-MM-DD [短標題]

#### 背景

一句話說明本輪目標。

#### 本次完成

- 項目 1
- 項目 2

#### 修改檔案

- `path/to/file`

#### 驗證

- 執行了什麼
- 結果如何

#### 遺留事項

- 尚未完成 1
- 風險 2
