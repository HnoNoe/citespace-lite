# -*- coding: utf-8 -*-
"""生成文献计量论文 8 张验证草图（投稿版须用 CiteSpace/VOSviewer 重出替换）
用法: python make_figures.py <data目录> <图输出目录> [--config figure_config.json]
figure_config.json（均可选）:
{
  "topic": "数字金融研究",                   # 图1 标题用
  "source_label": "核心期刊",             # 图1 标题用
  "stages": [{"span": [2005, 2008], "label": "起步期\\n(2005—2008，年均4.0篇)"}, ...],
  "policies": {"2009": "金融危机后\\n刺激政策", ...},
  "cluster_labels": {"0": "数字金融与融资约束", ...}
}
"""
import json, pickle, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import networkx as nx

# 跨平台中文字体自动回退：Windows 雅黑 / macOS 苹方 / Linux Noto 或文泉驿，都没有再退默认字体
from matplotlib import font_manager
_FONT_CANDIDATES = ["Microsoft YaHei", "PingFang SC", "Hiragino Sans GB",
                    "Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Micro Hei",
                    "SimHei", "Arial Unicode MS"]
_available_fonts = {f.name for f in font_manager.fontManager.ttflist}
_chosen = [f for f in _FONT_CANDIDATES if f in _available_fonts]
if not _chosen:
    print("警告: 未找到中文字体, 图中中文可能显示为方块; 请安装 Noto Sans CJK 或微软雅黑后重跑")
plt.rcParams["font.sans-serif"] = _chosen + ["sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

def convex_hull(points):
    P = sorted(set(map(tuple, points)))
    if len(P) <= 2:
        return P
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in P:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(P):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]

def main():
    data_dir, fig_dir = sys.argv[1], sys.argv[2]
    cfg = {}
    if "--config" in sys.argv:
        cfg = json.load(open(sys.argv[sys.argv.index("--config") + 1], encoding="utf-8"))
    os.makedirs(fig_dir, exist_ok=True)
    topic = cfg.get("topic", "该领域")
    src_label = cfg.get("source_label", "核心期刊")
    stages = cfg.get("stages", [])
    policies = {int(k): v for k, v in cfg.get("policies", {}).items()}
    clabels = {int(k): v for k, v in cfg.get("cluster_labels", {}).items()}

    recs = json.load(open(os.path.join(data_dir, "records.json"), encoding="utf-8"))
    stats = json.load(open(os.path.join(data_dir, "stats.json"), encoding="utf-8"))
    net = json.load(open(os.path.join(data_dir, "network.json"), encoding="utf-8"))
    nets = pickle.load(open(os.path.join(data_dir, "networks.pkl"), "rb"))
    kw_docs = {k: set(v) for k, v in stats["kw_docs"].items()}
    kw_freq = dict(stats["kw_freq"])
    y0, y1 = net["years_span"]
    xs = list(range(y0, y1 + 1))

    # ============ 图1 年度发文量趋势 ============
    years = {int(k): v for k, v in stats["years"].items()}
    ys = [years.get(x, 0) for x in xs]
    ymax = max(ys) + 3
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.bar(xs, ys, color="#9DB2C8", edgecolor="#5B7A99", width=0.7, zorder=2)
    ax.plot(xs, ys, color="#264653", marker="o", ms=4, lw=1.5, zorder=3)
    stage_colors = ["#F4E9DC", "#E8F0E4", "#E4E9F0", "#F0E4EC", "#E4F0F0"]
    for si, st in enumerate(stages):
        a, b = st["span"]
        ax.axvspan(a - 0.5, b + 0.5, color=stage_colors[si % len(stage_colors)], zorder=0)
        ax.text((a + b) / 2, ymax - 1.8, st["label"], ha="center", va="top", fontsize=9, color="#444444")
    for x, lab in policies.items():
        ax.axvline(x, color="#C0504D", ls="--", lw=1, zorder=1)
        ax.annotate(lab, xy=(x, years.get(x, 0)), xytext=(x, ymax - 3.5), fontsize=7.5, ha="center",
                    color="#C0504D", arrowprops=dict(arrowstyle="-", color="#C0504D", lw=0.7))
    ax.set_ylim(0, ymax)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs], rotation=45, fontsize=8)
    ax.set_ylabel("发文量（篇）")
    ax.set_title(f"{y0}—{y1} 年{topic}{src_label}发文量与政策节点", fontsize=12)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图1_年度发文量趋势.png")); plt.close()
    print("图1 done")

    # ============ 关键词网络布局（图4/5/6共用） ============
    G = nx.Graph()
    for n, f in net["graph_nodes"].items():
        G.add_node(n, freq=f)
    for a, b, w in net["edges"]:
        if G.has_node(a) and G.has_node(b):
            G.add_edge(a, b, weight=w)
    pos = nx.spring_layout(G, k=1.6, weight="weight", seed=42, iterations=200)
    node2comm = {m: c["id"] for c in net["clusters"] for m in c["members"] if m in G}
    PALETTE = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD"]

    # ============ 图4 关键词共现网络 ============
    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    for a, b, d in G.edges(data=True):
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]],
                color="#AAAAAA", lw=0.5 + d["weight"] * 0.4, alpha=0.55, zorder=1)
    for n in G.nodes():
        f = G.nodes[n]["freq"]
        ax.scatter(*pos[n], s=40 + f * 22, color=PALETTE[node2comm.get(n, 0) % 6],
                   alpha=0.85, edgecolor="white", lw=0.8, zorder=2)
        if f >= 3:
            ax.annotate(f"{n}({f})", xy=pos[n], xytext=(pos[n][0], pos[n][1] + 0.045), fontsize=8, ha="center", zorder=3)
    ax.set_title(f"关键词共现网络（节点数{G.number_of_nodes()}，连线{G.number_of_edges()}）", fontsize=12)
    ax.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图4_关键词共现网络.png")); plt.close()
    print("图4 done")

    # ============ 图5 密度图（numpy 手写高斯核密度，免 scipy） ============
    pts = np.array([pos[n] for n in G.nodes()])
    wts = np.array([G.nodes[n]["freq"] for n in G.nodes()], dtype=float)
    wts = wts / wts.sum()
    bw = 0.35 * pts.std(axis=0).mean() + 1e-6
    gx, gy = np.mgrid[pts[:, 0].min() - 0.25:pts[:, 0].max() + 0.25:200j,
                      pts[:, 1].min() - 0.25:pts[:, 1].max() + 0.25:200j]
    gz = np.zeros(gx.shape)
    for (px, py), w in zip(pts, wts):
        gz += w * np.exp(-((gx - px) ** 2 + (gy - py) ** 2) / (2 * bw ** 2))
    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    ax.contourf(gx, gy, gz, levels=18, cmap="RdYlBu_r", alpha=0.9)
    for n in G.nodes():
        if G.nodes[n]["freq"] >= 3:
            ax.annotate(n, xy=pos[n], fontsize=8, ha="center", color="#222222")
    ax.set_title("关键词密度分布（红=高密度热点区，蓝=低密度边缘区）", fontsize=12)
    ax.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图5_关键词密度图.png")); plt.close()
    print("图5 done")

    # ============ 图6 聚类图谱 ============
    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    for c in net["clusters"]:
        members = [m for m in c["members"] if m in G]
        if len(members) >= 3:
            hull_pts = convex_hull(np.array([pos[m] for m in members]))
            if len(hull_pts) >= 3:
                ax.add_patch(Polygon(np.array(hull_pts), closed=True, alpha=0.12,
                                     color=PALETTE[c["id"] % 6], zorder=0))
    for a, b, d in G.edges(data=True):
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#BBBBBB", lw=0.6, alpha=0.6, zorder=1)
    for n in G.nodes():
        f = G.nodes[n]["freq"]
        ax.scatter(*pos[n], s=40 + f * 22, color=PALETTE[node2comm.get(n, 0) % 6],
                   alpha=0.9, edgecolor="white", lw=0.8, zorder=2)
        if f >= 3:
            ax.annotate(n, xy=pos[n], xytext=(pos[n][0], pos[n][1] + 0.045), fontsize=8, ha="center", zorder=3)
    for c in net["clusters"]:
        members = [m for m in c["members"] if m in G]
        if members:
            cx = np.mean([pos[m][0] for m in members])
            cy = max(pos[m][1] for m in members) + 0.12
            ax.text(cx, cy, f"#{c['id']} {clabels.get(c['id'], '')}", fontsize=9,
                    ha="center", color=PALETTE[c["id"] % 6], weight="bold", zorder=4)
    ax.text(0.02, 0.02, f"Q = {net['Q']:.3f}    S = {net['S_mean']:.3f}（近似值，以 CiteSpace 复核为准）",
            transform=ax.transAxes, fontsize=9, color="#333333")
    ax.set_title(f"关键词聚类图谱（Louvain，{len(net['clusters'])} 个主要聚类）", fontsize=12)
    ax.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图6_关键词聚类图谱.png")); plt.close()
    print("图6 done")

    # ============ 图7 时间线 ============
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=300)
    main_clusters = [c for c in net["clusters"] if c["size"] >= 3]
    for row, c in enumerate(main_clusters):
        yrs_all = [(recs[d]["year"], kw_freq[m]) for m in c["members"]
                   for d in kw_docs.get(m, []) if recs[d]["year"]]
        if not yrs_all:
            continue
        ys_c = [y for y, _ in yrs_all]
        ax.hlines(row, min(ys_c), max(ys_c), color=PALETTE[c["id"] % 6], lw=2, alpha=0.5)
        for y, f in yrs_all:
            ax.scatter(y, row + np.random.uniform(-0.18, 0.18), s=12 + f * 8,
                       color=PALETTE[c["id"] % 6], alpha=0.75, zorder=3)
        ax.text(y1 + 0.6, row, f"#{c['id']} {clabels.get(c['id'], '')}（均年{c['mean_year']}）",
                va="center", fontsize=8.5, color=PALETTE[c["id"] % 6])
    ax.set_yticks([])
    ax.set_xlim(y0 - 1, y1 + 10)
    ax.set_xticks(range(y0, y1 + 1, 2))
    ax.set_xlabel("年份")
    ax.set_title("关键词聚类时间线（每个点=某成员词在该年的1篇文献）", fontsize=12)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图7_聚类时间线.png")); plt.close()
    print("图7 done")

    # ============ 图8 突现词 ============
    bursts = net["bursts2"][:15]
    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=300)
    for i, b in enumerate(reversed(bursts)):
        ax.barh(i, y1 + 1 - y0, left=y0, height=0.5, color="#E8E8E8", zorder=1)
        ax.barh(i, b["end"] - b["begin"] + 1, left=b["begin"], height=0.5, color="#C0504D", zorder=2)
        ax.text(y1 + 1.2, i, f"{b['strength']:.2f}", va="center", fontsize=8, color="#333333")
    ax.set_yticks(range(len(bursts)))
    ax.set_yticklabels([b["kw"] for b in reversed(bursts)], fontsize=9)
    ax.set_xlim(y0, y1 + 4)
    ax.set_xticks(range(y0, y1 + 1, 2))
    ax.set_title("关键词突现图谱（Top15，红色=突现区间，右侧=突现强度）", fontsize=12)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "图8_突现词图谱.png")); plt.close()
    print("图8 done")

    # ============ 图2/图3 作者/机构共现 ============
    an, on = net["author_net"], net["org_net"]
    for key, fname, title, minshow in [
            ("GA", "图2_作者共现图谱.png", f"作者共现网络（节点{an['nodes']}，连线{an['edges']}，密度{an['density']:.4f}）", 2),
            ("GI", "图3_机构共现图谱.png", f"机构共现网络（节点{on['nodes']}，连线{on['edges']}，孤立机构{on['isolates'] / max(on['nodes'], 1) * 100:.1f}%）", 4)]:
        GX = nets[key]
        fig, ax = plt.subplots(figsize=(8.5, 6.5), dpi=300)
        comps = [c for c in nx.connected_components(GX) if len(c) > 1]
        if not comps:
            print(fname, "无连通分量, 跳过"); plt.close(); continue
        sub = GX.subgraph(set().union(*comps))
        posx = nx.spring_layout(sub, k=1.8, seed=42)
        for a, b, d in sub.edges(data=True):
            ax.plot([posx[a][0], posx[b][0]], [posx[a][1], posx[b][1]], color="#AAAAAA", lw=0.7, alpha=0.6)
        freq_map = nets["au_freq"] if key == "GA" else {o: c for o, c in stats["orgs"]}
        for n in sub.nodes():
            f = freq_map.get(n, 1)
            ax.scatter(*posx[n], s=30 + f * 18, color="#4C72B0", alpha=0.8, edgecolor="white", lw=0.6)
            if f >= minshow:
                ax.annotate(f"{n}({f})", xy=posx[n], xytext=(posx[n][0], posx[n][1] + 0.05), fontsize=7.5, ha="center")
        ax.set_title(title, fontsize=12)
        ax.axis("off")
        plt.tight_layout(); plt.savefig(os.path.join(fig_dir, fname)); plt.close()
        print(fname, "done")
    print("\n全部图已生成")

if __name__ == "__main__":
    main()
