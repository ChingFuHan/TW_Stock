# 專案快照

## 專案目標

建立可重複執行的台股券商 / 分行買賣資料爬蟲，抓取每日股票買進、賣出與可能的淨流向資料，供後續建立跟單分析指標使用。

## 目前階段

目前已完成第一版可執行爬蟲與離線測試，並已對 2 個範例網址完成端到端驗證。

已完成：

- 保留原始需求 `task.md`
- 建立強化需求文件 `task_enhanced.md`
- 建立可執行導向任務單 `task_agent.md`
- 建立知識傳遞庫 `docs/knowledge-base/`
- 建立 Python 爬蟲骨架 `src/tw_broker_flows/`
- 建立專案虛擬環境 `.venv`
- 保存真實樣本 HTML 與 lookup JS
- 支援全量券商 / 分行 lookup 匯出
- 支援依 lookup 全掃所有分行 URL
- 完成 parser、lookup、storage、CLI
- 完成離線測試與一次真實抓取驗證

尚未完成：

- 去重策略
- 長期批次排程
- 自訂日期區間驗證
- 更完整的錯誤分類與重試策略
- 更多券商 / 分點樣本驗證

## 已知資料來源

- `https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=1030&b=1030`
- `https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=8900&b=8900&c=E&d=1`

## 目標輸出

至少需要產出：

- 原始 HTML
- 清洗後表格資料
- 執行 log
- 可重複執行方式

建議落地路徑：

- `data/raw/`
- `data/processed/`
- `data/logs/`

## 技術方向

目前已落地：

- 語言：Python
- 抓取：Python 標準庫 `urllib.request`
- 解析：Python 標準庫 `html.parser` + 部分 regex
- 輸出：Python 標準庫 `csv`

第一版故意避免第三方套件，降低環境依賴與安裝成本。

## 目前重要限制

- 頁面欄位標題第一欄顯示為「券商名稱」，但實際資料列是股票，不能直接相信欄位名
- 券商 / 分點名稱不在原始 HTML 中，而是由 `/z/js/zbrokerjs.djjs` 動態生成
- 目前只驗證 `近一日` 與 `金額 / 張數` 兩種模式
- 還沒有驗證 `e`、`f` 自設區間查詢
- 還沒有做跨批次去重與合併策略
- 全掃模式尚未完成完整長時間驗證

## 已知風險

- 頁面使用 Big5，任何編碼處理走錯就會直接影響解析
- 來源站可能有限流，未來批次化時要保守控頻
- 部分股票列是透過 `GenLink2stk(...)` script 輸出，少數列則直接是 anchor text，parser 需要同時支援兩種格式
- 若 lookup JS 無法取得，名稱解析要退回 code-only 模式

## 推薦下一步

第一優先：

1. 驗證更多券商 / 分點樣本，確認 parser 是否能跨更多分點穩定使用
2. 釐清 `c/d/e/f` 參數與自訂日期區間
3. 補批次去重策略與增量寫入
4. 觀察全掃模式的失敗率與限流需求

第二優先：

1. 強化 log、錯誤分類與重試
2. 若後續資料量變大，改 Parquet 或資料庫落地
3. 補排程與長期執行方式

## 目前 repo 檔案地圖

- `task.md`：原始需求
- `task_enhanced.md`：細緻需求書
- `task_agent.md`：可執行導向任務單
- `docs/knowledge-base/README.md`：知識庫入口
- `docs/knowledge-base/project_snapshot.md`：本文件
- `docs/knowledge-base/decisions.md`：決策紀錄
- `docs/knowledge-base/open_questions.md`：待解問題
- `docs/knowledge-base/implementation_journal.md`：實作歷程
- `docs/knowledge-base/next_agent_handoff.md`：下位 agent 交接入口
