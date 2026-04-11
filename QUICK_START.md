# 快速开始指南

## 🚀 基本命令

### 最简单的用法
```bash
cd C:\Users\User\Documents\TW_Stock

# 爬取最近一天的数据（推荐新手用）
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --all-branches --metric-type lots \
  --start-date 2026-04-10 --end-date 2026-04-10 \
  --max-workers 15
```

### 爬取多天
```bash
# 爬取过去一周
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --all-branches --metric-type lots \
  --start-date 2026-04-07 --end-date 2026-04-10 \
  --max-workers 15
```

### 完整爬取（推荐）
```bash
# 爬取所有可用数据（2025-12-01 ~ 2026-04-10）
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --all-branches --metric-type lots \
  --start-date 2025-12-01 --end-date 2026-04-10 \
  --max-workers 15
```

---

## ⚙️ 性能调优

### 参数说明
```
--max-workers N        # 并发线程数（默认15）
  - 推荐范围: 10-20
  - CPU少用: 5
  - CPU多用: 30

--retry-count N        # 失败重试次数（默认3）
--retry-delay S        # 重试延迟秒数（默认1.0）

--metric-type          # 数据类型
  - lots:   股票数量
  - amount: 金额
```

### 针对不同场景

**❌ 网络差**:
```bash
--max-workers 10 --retry-count 5 --retry-delay 2.0
```

**✅ 网络好**:
```bash
--max-workers 20 --retry-count 2 --retry-delay 0.5
```

**⚡ 追求速度**:
```bash
--max-workers 30
```

---

## 📂 输出文件位置

爬取完后查看这些位置的文件：

```
data/
├── processed/          # 解析后的 CSV 文件（按日期组织）
│   ├── 20260410/      # 2026-04-10 的数据
│   ├── 20260409/      # 2026-04-09 的数据
│   └── ...
├── raw/               # 原始 HTML 文件（备份）
│   ├── 20260410/
│   └── ...
├── logs/              # 执行日志
│   └── run_YYYYMMDD_HHMMSS.log
└── reference/         # 参考数据
    ├── brokers.csv
    └── branches.csv
```

---

## 🔍 监控运行进度

爬取时可以打开日志文件实时查看进度：

```bash
# 在另一个终端中实时查看日志
Get-Content data/logs/run_20260412_*.log -Wait
```

日志会显示：
```
INFO [100/2529] Parsed 100 rows for branch=1020
INFO [200/2529] Flushed 400 records into DB=tw
ERROR [300/2529] Parse failed: ...
INFO Finished. successes=2292 failures=237
```

---

## 🎯 常见任务

### 任务1: 爬取最新的一个月数据
```bash
# 2026-03-16 ~ 2026-04-10 约 20 个工作日
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --all-branches --metric-type lots \
  --start-date 2026-03-16 --end-date 2026-04-10 \
  --max-workers 15
```

**预期**: 16,860 URLs, 3 分钟, 90%+ 成功率

### 任务2: 爬取特定券商的数据
```bash
# 仅爬取第一新证券 (code 1020)
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --broker-code 1020 \
  --metric-type lots \
  --start-date 2026-04-10 --end-date 2026-04-10 \
  --max-workers 15
```

### 任务3: 爬取金额数据而不是股票数量
```bash
.venv\Scripts\python.exe -m src.tw_broker_flows \
  --all-branches --metric-type amount \
  --start-date 2026-04-10 --end-date 2026-04-10 \
  --max-workers 15
```

---

## 📊 预期性能

根据最新测试结果：

| 数据范围 | URL 数 | 执行时间 | 成功率 |
|--------|-------|--------|------|
| 1 天 (843 分支) | 843 | 2-3 分钟 | 90% |
| 1 周 (5 个工作日) | 4,215 | 5-8 分钟 | 90% |
| 1 月 (20 个工作日) | 16,860 | 20-30 分钟 | 81-90% |

> 成功率不是 100% 因为某些分支没有交易数据（例如节假日闭市）

---

## ⚠️ 重要提示

### ✅ 可用的日期范围
```
2025-12-01 ~ 2026-04-10
```

### ❌ 不建议使用的日期
```
2026-01-01 ~ 2026-02-28     # 网站无数据
2017-01-01 ~ 2025-11-30     # 可能无数据
```

### 🤖 自动处理
```
周末 (Saturday, Sunday)      # 自动过滤，不生成 URL
节假日                      # 网站无数据，解析会失败
```

---

## 🐛 故障排查

### 问题: "Connection refused" 或网络错误
**原因**: 网络连接问题或目标网站无响应
**解决**:
```bash
# 增加重试次数和延迟
--retry-count 5 --retry-delay 2.0
```

### 问题: 爬虫很慢 (1-2 URL/秒)
**原因**: max-workers 太低或网络慢
**解决**:
```bash
# 增加并发度
--max-workers 20
```

### 问题: "No stock flow rows were parsed"
**原因**: 该日期/分支无交易数据
**解决**: 正常现象，属于失败项，程序会继续

### 问题: 内存持续增长
**原因**: max-workers 太高
**解决**:
```bash
# 减少并发度
--max-workers 5

# 或分批爬取
--start-date 2026-04-08 --end-date 2026-04-08  # 一天一天
```

---

## 💡 小建议

1. **第一次运行**: 先用单日测试
   ```bash
   --start-date 2026-04-10 --end-date 2026-04-10
   ```

2. **大规模爬取**: 在后台运行
   ```bash
   # 终端中 (Ctrl+C 暂停)
   nohup .venv\Scripts\python.exe -m src.tw_broker_flows ... > crawl.log 2>&1 &
   ```

3. **监控进度**: 打开日志文件
   ```bash
   Get-Content data/logs/run_*.log -Wait
   ```

4. **网络不稳定**: 降低并发和增加重试
   ```bash
   --max-workers 5 --retry-count 10
   ```

---

祝您爬取顺利！🎉

如有问题，查看日志文件 `data/logs/` 获取详细信息。
