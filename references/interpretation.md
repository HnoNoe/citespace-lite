# 指标判读与配置说明

## 一、指标怎么读

| 指标 | 出处 | 判读 |
|---|---|---|
| 普赖斯阈值 M = 0.749×√nmax | stats.json | 发文 ≥M 篇的为核心作者；核心作者占比低（<10%）说明领域尚无稳定核心群 |
| 网络密度 | network.json | 关键词共现 0.05—0.15 常见；作者合作网 <0.01 即"合作松散" |
| 连通分量数 | author_net.components | 分量多、最大分量小 = 合作碎片化 |
| Q（模块度） | network.json.Q | >0.3 聚类结构显著（CiteSpace 惯例） |
| S（轮廓值） | network.json.S_mean | >0.7 理想，0.5—0.7 可接受。**本工具为近似算法（共现向量余弦），普遍低于 CiteSpace 的 LLR 轮廓值**，报告中须注明 |
| 聚类均年 mean_year | clusters[].mean_year | 判断主题新老：均年晚 = 新兴方向 |
| 突现强度 | bursts / bursts2 | 只相对比较，不跨算法比较；起止年份比强度数值更有信息量 |

## 二、两种突现算法的差异

- `bursts`：Kleinberg 双状态自动机（泊松发射 + 状态切换惩罚 γ=0.5）。高频词年均>1 篇时自动缩放计数保证 p0<1，强度为缩放后单位。
- `bursts2`：窗口偏离度法（窗口内观测超出均匀期望的标准化偏离），对中文小样本（<300 篇）更稳定。

两法词目应大致重合；取交集写报告最稳。正式论文以 CiteSpace `Burstness`（γ=0.5, min duration=2）输出为准。

## 三、kw_config.json 编写要点

```json
{
  "synonyms": {
    "互联网金融": "数字金融",
    "中小微": "中小企业"
  },
  "generic": ["对策", "现状", "路径", "研究", "分析"]
}
```

- synonyms 键是"待合并词"，值是"统一词"；合并决定会显著改变网络结构，写论文时须列入方法节。
- generic 剔除的是无区分度的泛词（对策/现状/影响因素/路径/研究…），别剔主题词。
- 流程：先无配置裸跑 → 看 Top50 词 → 写配置 → 重跑 → 对比词表变化。

## 四、figure_config.json 全字段

```json
{
  "topic": "数字金融研究",
  "source_label": "核心期刊",
  "stages": [{"span": [2005, 2008], "label": "起步期"}, {"span": [2009, 2016], "label": "高峰期"}],
  "policies": {"2015": "大众创业\n万众创新"},
  "cluster_labels": {"0": "数字金融与融资约束"}
}
```

均可省略：无 stages 不画阶段背景；无 policies 不画政策线；无 cluster_labels 聚类只标编号。年份范围自动取数据的实际跨度。

## 五、与 CiteSpace 复核的口径对照

| 本工具 | CiteSpace 对应 | 一致性预期 |
|---|---|---|
| Louvain 聚类 | LLR 标签聚类 | 聚类数 ±2 正常，类团成员大致重合 |
| Q 值 | 左上角 Modularity Q | 接近，可互相印证 |
| S 值 | 左上角 Mean Silhouette | 本工具偏低，以 CiteSpace 为准 |
| bursts | Burstness (γ=0.5) | 词目重合，强度数值不可直接比 |

复核操作：CiteSpace → Data/Import/Export 选 CNKI 转换 → 建项目（Language=Chinese）→ Node Types=Keyword，g-index k=25，Pathfinder 剪枝 → 聚类记 Q/S → Burstness 取 Top15 → 导出 300dpi 图。
