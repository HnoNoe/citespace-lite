---
name: citespace-lite
description: 不装 CiteSpace，用纯 Python 复现 CiteSpace 核心功能：解析 CNKI RefWorks 题录（download_XX.txt），做年度发文统计、作者/机构合作网络、关键词共现网络、Louvain 聚类（Q 值/S 值）、Kleinberg 突现检测，并一键出 8 张知识图谱（趋势图、合作网络、共现网络、密度图、聚类图、时间线、突现图）。当任务涉及：CNKI 题录分析、文献计量、知识图谱、关键词共现/聚类/突现、CiteSpace 替代、VOSviewer 替代、研究热点演进分析时使用。触发词：文献计量、知识图谱、CiteSpace、CNKI 题录、共现、聚类、Q 值、突现词、研究热点。
---

# CiteSpace Lite：纯 Python 文献计量与知识图谱

对 CNKI 导出的 RefWorks 题录做完整文献计量分析，无需安装 CiteSpace/Java。适合快速验证、草稿出图、批量处理；正式投稿图建议再用 CiteSpace/VOSviewer 复核（见 references/interpretation.md 末节的复核口径）。

## 给人看的快速上手（30 秒）

1. 安装依赖：`pip install networkx numpy matplotlib`（Python 3.9+）
2. 去 CNKI 检索后勾选文献，导出格式选 **RefWorks**，得到 `download_XX.txt`（可多个文件放同一目录）
3. 把这个 skill 目录交给你的 AI agent（或解压后放进它的 skills 目录），说："用 citespace-lite 分析这个目录下的 CNKI 题录"
4. agent 会自动完成 解析 → 分析 → 出 8 张图；中途它会让你确认关键词清洗配置，照实回答即可

## 依赖

Python 3 + networkx / numpy / matplotlib，安装：`pip install networkx numpy matplotlib`。无 scipy：密度图用手写高斯核，凸包用单调链。中文字体自动回退（Windows 雅黑 / macOS 苹方 / Linux Noto/文泉驿），均无中文字体时会打印警告。

## 三步用法

```bash
# 1. 解析题录（输入：CNKI 导出的 download_XX.txt 或其所在目录）
python scripts/parse_cnki.py <题录txt或目录> data

# 2. 全量分析（可选关键词清洗配置；--thresh 为入网最低词频，默认 2）
python scripts/analyze.py data [--kw-config kw_config.json] [--thresh 2]

# 3. 出图 8 张到 figures/（可选样式配置）
python scripts/make_figures.py data figures [--config figure_config.json]
```

## 配置方法（先跑裸分析，再按主题补配置重跑）

- `kw_config.json`：`{"synonyms": {"待合并词": "统一词"}, "generic": ["泛词1", ...]}`。先看裸跑的 Top 词表，再决定合并哪些同义词、剔除哪些泛词（对策/现状/路径这类）。
- `figure_config.json`：`{"topic": "主题名", "source_label": "核心期刊", "stages": [{"span": [2005,2008], "label": "起步期"}], "policies": {"2015": "大众创业\n万众创新"}, "cluster_labels": {"0": "聚类名"}}`。聚类名由你读 network.json 里各 cluster 的 members 后命名。

两个配置的完整字段说明与判读标准见 references/interpretation.md。

## 产出与数据契约

| 文件 | 内容 |
|---|---|
| data/records.json | `[{title, authors[], orgs[], journal, year, keywords[], abstract}]` |
| data/stats.json | 年度分布、作者/机构频次、普赖斯阈值、关键词频次/首现年/文献映射 |
| data/network.json | Q、S_mean、clusters（成员/均年/轮廓值）、bursts（Kleinberg）、bursts2（窗口偏离度）、作者/机构网络指标 |
| data/networks.pkl | 作者/机构 networkx 图对象（二次开发用） |
| figures/图1—图8.png | 300dpi：趋势/作者/机构/共现/密度/聚类/时间线/突现 |

## 铁律

1. 突现给两种算法结果（Kleinberg + 窗口偏离度），互相印证；与 CiteSpace 不一致时以 CiteSpace 为准。
2. Q>0.3 聚类结构显著、S>0.7 可信（0.5—0.7 可接受）；本工具 S 为近似算法，通常偏低，报告中必须注明。
3. 解析阶段的"疑似非研究性文献"清单只提示不自动删，剔除口径由人确认。
