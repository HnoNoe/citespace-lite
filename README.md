# CiteSpace Lite

不装 CiteSpace / Java，用纯 Python 复现 CiteSpace 核心功能的 **AI Agent Skill**：解析 CNKI RefWorks 题录，一键完成文献计量分析并出 8 张 300dpi 知识图谱。

## 功能

- 解析 CNKI 导出的 RefWorks 题录（`download_XX.txt`，支持多文件批量）
- 年度发文统计、作者 / 机构合作网络（普赖斯阈值、网络密度、连通分量）
- 关键词共现网络 + Louvain 聚类（Q 值 / S 值）
- Kleinberg 突现检测 + 窗口偏离度双算法互证
- 一键出 8 张图：发文趋势 / 作者合作 / 机构合作 / 共现网络 / 密度图 / 聚类图谱 / 聚类时间线 / 突现词图谱

适合快速验证、草稿出图、批量处理；**正式投稿图请用 CiteSpace / VOSviewer 复核**（S 值为近似算法，详见 `references/interpretation.md`）。

## 30 秒上手

```bash
pip install -r requirements.txt   # 或 pip install networkx numpy matplotlib
```

1. 去 CNKI 检索文献，导出格式选 **RefWorks**，得到 `download_XX.txt`
2. 把本仓库（或 `dist/` 里的 `.skill` 包）交给你的 AI agent，说："用 citespace-lite 分析这个目录下的 CNKI 题录"
3. Agent 自动完成 解析 → 分析 → 出图，中途会和你确认关键词清洗配置

## 手动三步用法（不经过 agent 也行）

```bash
python scripts/parse_cnki.py <题录txt或目录> data      # 1. 解析
python scripts/analyze.py data [--kw-config kw_config.json] [--thresh 2]   # 2. 分析
python scripts/make_figures.py data figures [--config figure_config.json]  # 3. 出图
```

## 安装为 Agent Skill

- **Claude**：直接上传 `dist/citespace-lite-v1.1.skill`
- **Kimi Work / 其他 agent**：解压 `.skill` 包，把 `citespace-lite/` 目录放进 agent 的 skills 目录

## 兼容性

- Python 3.9+，仅依赖 networkx / numpy / matplotlib（无 scipy）
- 中文字体自动回退：Windows 微软雅黑 / macOS 苹方 / Linux Noto·文泉驿
- Windows / macOS / Linux 全平台可用

## 目录结构

```
SKILL.md                  # Agent 读取的技能说明（含数据契约与铁律）
requirements.txt
scripts/
  parse_cnki.py           # 题录解析
  analyze.py              # 计量分析 + 聚类 + 突现
  make_figures.py         # 出 8 张图
references/
  interpretation.md       # 指标判读、配置说明、CiteSpace 复核口径
dist/
  citespace-lite-v1.1.skill   # 可直接分发的打包文件（zip）
```

## License

MIT
