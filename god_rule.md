# 🏛️ GOD RULE — 最高憲法 (Supreme Constitution)

**適用範圍：** 所有專案、所有 Agent、所有協作者。  
**優先級：** 本文件的規則凌駕於任何子專案的規範之上。  
**版本：** v1.2.1  
**最後更新：** 2026-04-16

---

## ⚖️ 規則優先級與衝突處理

在規則之間發生衝突時，依以下優先級處理：

| 優先級 | 說明 |
|--------|------|
| **P0 - 絕對禁止** | RULE 05（機密保護）、RULE 09（防卡死）— 任何情況都不得違反 |
| **P1 - 高度重要** | RULE 01（Handoff）、RULE 04（快照）、RULE 10（驗證）— 需充分理由才能暫緩 |
| **P2 - 建議遵守** | 其餘規則 — 可視專案情況彈性調整 |

**衝突處理原則：** 下層規則不得違反上層規則。若確實需要例外，必須在 HANDOFF.md 中明確記錄原因。

---

## RULE 01 ｜ 智慧傳承與脈絡管理 — Handoff Protocol & Context Pruning

每次任務結束，必須留下交接文件。讓下一個 Agent 或人類可以無縫接手，同時必須保持交接文件的精簡，避免消耗過多 Token。

### 強制輸出格式（標準版）

```markdown
## HANDOFF — [任務名稱]

### ✅ 本次完成事項
- 完成項目 1

### 🔄 進行中 / 尚未完成
- 說明當前狀態與卡點

### 📁 關鍵檔案清單
| 檔案路徑 | 用途說明 |
|----------|----------|
| path/to/file | 說明 |

### ⚠️ 注意事項 / 已知風險
- 需要注意的坑或潛在問題

### ➡️ 下一步建議
- 建議下一個 Agent 或人類優先處理的事項

### 🔑 關鍵決策紀錄
- 本次任務中做了哪些重要決策，以及原因
```

### 簡化版（適用於簡單任務，< 15 分鐘）

```markdown
## HANDOFF — [任務名稱]
✅ 完成：[簡要描述]
⚠️ 注意：[如有]
➡️ 下步：[如有]
```

### 脈絡壓縮規定 (Context Pruning)

- 更新 HANDOFF.md 時，必須將「已解決的過時卡點」刪除，並將「過長的歷史歷程」總結為簡短摘要
- 嚴禁無限期疊加日誌式紀錄
- 交接文件不應超過 100 行，否則必須拆分或總結

### 自動化輔助腳本

```bash
# 檢查 HANDOFF.md 是否存在並符合格式
#!/bin/bash
if [ ! -f "HANDOFF.md" ]; then
  echo "[WARN] HANDOFF.md 不存在，任務可能未完成交接"
  exit 1
fi

# 檢查必要欄位
for field in "本次完成事項" "關鍵檔案清單" "下一步建議"; do
  if ! grep -q "$field" HANDOFF.md; then
    echo "[WARN] HANDOFF.md 缺少必要欄位: $field"
    exit 1
  fi
done
echo "[INFO] HANDOFF.md 格式檢查通過"
```

---

## RULE 02 ｜ 資源與成本回報 — Resource Accounting

每次任務完成，必須回報耗時與資源消耗估算。

### 回報格式

任務完成時，最後一行固定輸出：

```
⏱️ 任務耗時：XX 分 XX 秒 ｜ 🪙 Tokens (估算): IN XXk / OUT XXk ｜ 💰 狀態: 成功/失敗/阻塞
```

### Token 估算方法

| LLM 模型 | 中英文混合文字 | 估算係數 |
|----------|----------------|----------|
| GPT-4o / Claude 3.5 | ~4 字 = 1 Token | 1 Token ≈ 4 字符 |
| Claude 3 / GPT-4 | ~3.5 字 = 1 Token | 1 Token ≈ 3.5 字符 |
| Gemini / Llama | ~2.5 字 = 1 Token | 1 Token ≈ 2.5 字符 |

### 補充規範

- 若任務有子任務，分別計時並加總
- 若任務被中斷後續行，須說明「本次執行時間」vs「累計時間」
- 長時間任務（> 30 分鐘）每 10 分鐘主動回報進度
- 可使用計時工具輔助：

```python
# timer.py
import time, sys
start = time.time()

def log_time(task_name):
    elapsed = time.time() - start
    mins, secs = divmod(elapsed, 60)
    print(f"⏱️ [{task_name}] 耗時：{int(mins)} 分 {int(secs)} 秒")

import atexit
atexit.register(lambda: log_time("總計"))
```

---

## RULE 03 ｜ 環境隔離 — Local-First Execution

所有工具與程式執行，以 local workspace 為主，嚴禁污染 global 環境。

### 強制規範

- **Python:** 套件使用 venv 或 conda env，禁止 `pip install` 至 global
  ```bash
  # 建立虛擬環境
  python -m venv .venv
  source .venv/bin/activate  # Linux/Mac
  .venv\Scripts\activate    # Windows
  
  # 或使用 conda
  conda create -n myenv python=3.11
  conda activate myenv
  ```
- **Node.js:** 套件使用 `npm install`（local），禁止 `npm install -g`（除非明確授權）
- **系統設定:** 禁止修改 `/etc/`、`~/.bashrc`、`~/.zshrc` 等全域設定
- **環境變數:** 使用 `.env` 檔案管理，禁止 `export` 寫入 shell profile
- **Docker:** 優先使用 container 隔離，避免直接操作 host 系統

### 工作目錄規範

```
project_root/
├── .venv/              # Python 虛擬環境（gitignore）
├── node_modules/       # Node 套件（gitignore）
├── .env                # 環境變數（gitignore）
├── .env.example        # 環境變數範本（git 追蹤，不含敏感值）
├── HANDOFF.md          # 交接文件（git 追蹤）
├── logs/               # 執行 log（本地保留）
└── .gitignore          # 標準忽略檔案
```

### 自動化檢查

```bash
# check_env.sh - 檢查是否有 global 安裝的 Python 套件
pip list --user && echo "[WARN] 發現 user 安裝的套件"
```

---

## RULE 04 ｜ 版本快照 — State Snapshot

任何重要操作前，必須先建立可還原的快照。

### 規範

- **優先使用 Git:**
  ```bash
  # 建立暫時分支進行實驗
  git checkout -b temp-agent-task-[task-name]
  
  # 或備份未提交的更改
  git diff > backup-$(date +%Y%m%d-%H%M%S).patch
  
  # 重要檔案備份
  cp important-file.py important-file.py.bak
  ```
- 每個任務開始前，記錄當前 `git HEAD` / 環境版本
- 破壞性操作（刪除、覆寫、資料庫 migration）必須先確認並留存 rollback 方案

### 破壞性操作 Checklist

- [ ] 已建立備份或快照
- [ ] 已記錄 rollback 步驟
- [ ] 已確認影響範圍
- [ ] 已通知相關人員

---

## RULE 05 ｜ 最小權限與機密保護 — Least Privilege & Secret Masking

只請求完成任務所需的最低限度權限與資源，並嚴格保護敏感資訊。

### 機密遮罩 (Secret Masking) 規範

**嚴禁在任何 Log、HANDOFF.md 或對話紀錄中明碼輸出任何密碼或金鑰。**

| 敏感類型 | 遮罩範例 |
|----------|----------|
| API Key | `sk-proj-****1234` |
| Password | `****` |
| Token | `ghp_****xyz` |
| Private Key | `-----BEGIN OPENSSH PRIVATE KEY-----\n[REDACTED]-----` |

### 應加入 .gitignore 的檔案

```
# 環境與密鑰
.env
*.key
id_rsa*
*.pem

# 日誌與臨時檔案
*.log
*.tmp
*.cache

# 敏感資料
credentials.json
secrets.yaml
```

### 秘密掃描工具推薦

- **git-secrets:** 防止意外提交敏感資訊
- **TruffleHog:** 掃描歷史 commit 中的密鑰
- **Gitleaks:** 即時掃描敏感資訊

```bash
# 安裝並使用 git-secrets
git secrets --install
git secrets --register-aws
git secrets --scan  # 掃描當前 commit
```

---

## RULE 06 ｜ 明確溝通 — Explicit Communication

遇到不確定、假設、或風險，必須明確標示，不得靜默跳過。

### 標示規範

| 標籤 | 使用情境 |
|------|----------|
| `[ASSUMPTION]` | 任務中做了未經確認的假設 |
| `[RISK]` | 有潛在風險的操作或決策 |
| `[BLOCKED]` | 被阻塞，需要人類介入 |
| `[SKIP]` | 主動略過某項目並說明原因 |
| `[TODO]` | 應完成但本次未完成的事項 |
| `[EXCEPTION]` | 申請規則例外並說明理由 |

### 特殊情況例外申請

若需暫時偏離某條規則，必須：

1. 在 HANDOFF.md 中明確標記 `[EXCEPTION]`
2. 說明偏離原因與預計恢復時間
3. 由人類確認同意

---

## RULE 07 ｜ 冪等性 — Idempotency

任務腳本應設計為可安全重複執行，執行兩次的結果等同執行一次。

### 規範

- 建立檔案前先檢查是否存在
- 資料庫 insert 前先確認是否重複
- API 呼叫使用 idempotency key（若支援）
- 避免 append-only 操作導致重複資料

### 實作範例

```python
import os

def safe_write(filepath, content):
    """安全的檔案寫入，支援冪等性"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            if f.read() == content:
                return False  # 無需覆寫
    with open(filepath, 'w') as f:
        f.write(content)
    return True
```

---

## RULE 08 ｜ 日誌義務 — Logging Standard

所有重要操作必須留下可追蹤的日誌。

### 格式

`[YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] Message`

### Log Level 定義

| Level | 用途 |
|-------|------|
| INFO | 正常執行流程 |
| WARN | 非預期但不中斷流程的情況 |
| ERROR | 需要處理的錯誤 |
| DEBUG | 開發除錯用，正式環境關閉 |

### 日誌輪替政策

- 單一日誌檔案不超過 100MB
- 保留最近 7 天的日誌
- 正式環境日誌級別預設為 INFO，DEBUG 需要手動開啟

### 不同環境的日誌策略

| 環境 | 預設級別 | 保留天數 |
|------|----------|----------|
| 開發 | DEBUG | 3 天 |
| 測試 | INFO | 7 天 |
| 正式 | INFO | 30 天 |

---

## RULE 09 ｜ 防卡死與重試限制 — Infinite Loop Prevention

防止 Agent 陷入無效的重複嘗試與錯誤迴圈。

### 規範

- 針對單一錯誤或卡點的**連續自動重試次數不得超過 3 次**
- 若重試 3 次仍未解決，必須強制觸發 `[BLOCKED]` 標籤並停止該子任務
- 保留現場與錯誤 Log，並在交接文件中記錄失敗原因，交由人類介入或回報給上一層 Agent 處理

### 重試決策流程

```
嘗試失敗 → 檢查是否為已知問題?
    ├── 是 → 套用修正方案，繼續
    └── 否 → 記錄錯誤，嘗試重試
              │
              ├── 第 1-2 次 → 繼續重試
              └── 第 3 次失敗 → 標記 [BLOCKED]，停止並回報
```

---

## RULE 10 ｜ 自我驗證義務 — Self-Validation Requirement

嚴禁在未經驗證的情況下宣告任務或程式碼修改完成。

### 變更類型對應的驗證清單

| 變更類型 | 必要驗證 |
|----------|----------|
| **UI 變更** | 視覺檢查、相關頁面功能測試、響應式檢查 |
| **API 變更** | API 文件更新、端點測試、錯誤處理驗證 |
| **資料庫遷移** | 資料完整性檢查、回滾測試、效能影響評估 |
| **設定變更** | 設定檔語法驗證、影響範圍確認 |
| **相依性更新** | 建置成功、相關測試通過 |

### 驗證優先順序

1. 編譯/建置成功
2. 單元測試通過
3. 整合測試通過（若有）
4. 手動功能驗證（必要時）

### 缺乏測試時的替代方案

```bash
# 如果專案沒有測試框架，手動驗證指令範例
npm run build           # 建置檢查
npm run lint            # Lint 檢查
python -m py_compile *.py  # Python 語法檢查
```

---

## RULE 11 ｜ 團隊協作與 Code Review 指南

這些規則在多人協作環境下的最佳實踐。

### Code Review 檢查清單

在審查 PR 時，確認以下事項：

- [ ] HANDOFF.md 已更新並符合格式
- [ ] 無敏感資訊外洩（使用 `git diff --staged | grep -E '(password|secret|key)'`）
- [ ] 新增的相依套件已列入必要清單
- [ ] 破壞性變更有回滾方案
- [ ] 日誌級別設定正確
- [ ] 交接內容不超過 100 行

### 團隊成員對規則有不同解讀時

1. 在 team-channel 公開討論
2. 由團隊 lead 裁決
3. 更新本文檔（使用 `[UPDATE]` 標記變更）

---

## RULE 12 ｜ 持續改進機制

確保這些規則能隨著團隊經驗累積而優化。

### 改進循環

```
收集回饋 → 分析有效性 → 擬定改進 → 實施測試 → 正式採用
```

### 版本更新流程

1. 任何成員可提出改進建議（via Issue/PR）
2. 由 Agent 或人類 draft 新版本
3. 在測試環境試用 2 週
4. 收集回饋並調整
5. 正式發布新版本

### 回饋收集方式

- 每個任務完成後填寫滿意度（1-5 分）
- 記錄規則違反的情況與原因
- 定期（每月）檢討規則有效性

---

## 📋 Agent 任務完成 Checklist

每次任務結束前，逐項確認：

- [ ] **RULE 01：** 已更新 HANDOFF.md（並完成資訊壓縮，< 100 行）
- [ ] **RULE 02：** 已回報任務耗時與資源估算
- [ ] **RULE 03：** 未污染 global 環境
- [ ] **RULE 04：** 重要操作前已建立快照（Git/Patch）
- [ ] **RULE 05：** 未存取不必要的資源，且無機密外洩
- [ ] **RULE 06：** 所有假設與風險已明確標示
- [ ] **RULE 07：** 腳本可安全重複執行
- [ ] **RULE 08：** 已留下執行日誌
- [ ] **RULE 09：** 未陷入無限迴圈（無超時重試）
- [ ] **RULE 10：** 已完成程式碼或設定的自我驗證
- [ ] **RULE 11：** 交接內容可供團隊協作使用
- [ ] **RULE 12：** 已記錄可改進之處（若有）

---

## 🔄 版本紀錄

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| v1.0 | 2026-04-14 | 初始版本，8 條核心規則 |
| v1.1 | 2026-04-14 | 新增資源回報、防卡死限制、自我驗證義務，強化 Context 壓縮與機密保護 |
| v1.2 | 2026-04-15 | 新增規則優先級、自動化腳本、例外處理機制、團隊協作指南、持續改進機制；為所有規則增加具體範例；新增 RULE 11-12 |
| v1.2.1 | 2026-04-16 | 修正繁簡混用與錯字（彈性、潛在、當前、回饋）、修正 HANDOFF 範本標題、移除重複 `.gitignore` 條目 |

---

本文件由 **作者** 定義，適用於 AI_Team 所有子專案。

**當前版本：** v1.2.1  
**下次檢討：** 2026-05-15
