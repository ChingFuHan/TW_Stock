# HANDOFF - TW_Stock

## 現況
- 分支：`master`，本地領先 `origin/master`（尚未成功 push）。
- 工作樹乾淨；`.env`、`.venv`、`data/` 產出為本機檔（未追蹤）。

## 近期重要變更
- **回補改為 DB-only 不落地**：`scripts/backfill_daily.py` 加 `--db-name <db>` 時，只寫 PostgreSQL，不再輸出 `data/raw` / `data/processed`（節省硬碟）。CSV 模式（不帶 `--db-name`）行為不變。
- **機密改用 `.env`**：連線憑證放 gitignored 的 `.env`；committed 的是範本 `.env.example`。程式以 `python-dotenv` 載入後由 `os.environ` 讀取，原始碼不再寫死任何密碼/token。
- **相依套件**：`requirements.txt` 已加入 `psycopg2-binary`、`python-dotenv`。
- **git 歷史已清除舊機密**：用 `git filter-repo --replace-text` 把外洩過的 DB 密碼與 API token 換成 `***REMOVED***`，**所有 commit hash 已改變**。重寫前的完整備份在 `~/TW_Stock-backup-prescrub.bundle`（內含舊機密，確認無誤後請刪除或妥善保管）。

## 待辦 / 注意
- **強烈建議輪換憑證**：外洩過的 DB 密碼與 Eikon token 即使歷史已清，仍應改密碼/換 token 才算安全。
- **push 認證**：先前 origin 推送曾 403（帳號權限不符）。push 前需先處理 GitHub 認證（gh auth login 或改 SSH）；因歷史已重寫，首次 push 會是 force 性質。

## 新接手快速上手
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # 編輯 .env 填入 Postgres 連線
# 單日 DB 回補（不落地）
.\.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-10 --end-date 2026-04-10 --db-name tw
```
詳見 `README.md`、`QUICK_START.md`、`docs/knowledge-base/`、`god_rule.md`。
