# -*- coding: utf-8 -*-
"""文献计量全量分析：年度/作者/机构/关键词统计 + 共现网络 + Louvain 聚类(Q/S) + 突现检测(两法)
用法: python analyze.py <data目录> [--kw-config kw_config.json] [--thresh 2]
输入: <data目录>/records.json (parse_cnki.py 产物)
输出: <data目录>/stats.json, network.json, networks.pkl
kw_config.json 格式: {"synonyms": {"待合并词": "统一词", ...}, "generic": ["泛词", ...]}
"""
import json, re, math, itertools, sys, os, pickle
from collections import Counter, defaultdict
import networkx as nx
import numpy as np

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_dir = args[0] if args else "data"
    thresh = 2
    if "--thresh" in sys.argv:
        thresh = int(sys.argv[sys.argv.index("--thresh") + 1])
    syn, generic = {}, set()
    if "--kw-config" in sys.argv:
        cfg = json.load(open(sys.argv[sys.argv.index("--kw-config") + 1], encoding="utf-8"))
        syn = cfg.get("synonyms", {})
        generic = set(cfg.get("generic", []))

    recs = json.load(open(os.path.join(data_dir, "records.json"), encoding="utf-8"))
    N = len(recs)
    years_all = sorted({r["year"] for r in recs if r["year"]})
    YEARS = list(range(years_all[0], years_all[-1] + 1))
    T = len(YEARS)
    print(f"文献 {N} 篇, 年份跨度 {YEARS[0]}—{YEARS[-1]}")

    # ---------- 年度分布 ----------
    years = dict(sorted(Counter(r["year"] for r in recs if r["year"]).items()))
    print("=== 年度发文量 ===")
    for y, c in years.items():
        print(f"{y}: {'█' * c} {c}")

    # ---------- 作者 ----------
    au_cnt = Counter()
    for r in recs:
        for a in set(r["authors"]):
            au_cnt[a] += 1
    nmax = au_cnt.most_common(1)[0][1] if au_cnt else 0
    M_price = 0.749 * math.sqrt(nmax) if nmax else 0
    core = [a for a, c in au_cnt.items() if c >= M_price]
    print(f"\n=== 作者 === 总数 {len(au_cnt)}, 最高产 {au_cnt.most_common(1)}")
    print(f"普赖斯阈值 M={M_price:.2f}, 核心作者 {len(core)} ({len(core) / max(len(au_cnt), 1) * 100:.1f}%)")
    print("Top10:", au_cnt.most_common(10))

    # ---------- 机构 ----------
    def norm_org(o):
        m = re.match(r"(.+?(大学|学院|研究院|研究所|党校|中心))", o)
        return m.group(1) if m else o
    org_cnt = Counter()
    n_coop = 0
    for r in recs:
        if not r["orgs"]:
            continue
        firsts = {norm_org(o) for o in r["orgs"]}
        org_cnt[norm_org(r["orgs"][0])] += 1
        if len(firsts) > 1:
            n_coop += 1
    print(f"\n=== 机构 === 总数 {len(org_cnt)}, 机构合作文献 {n_coop} 篇")
    for o, c in org_cnt.most_common(15):
        print(f"  {c:3d}  {o}")

    # ---------- 关键词清洗 ----------
    def clean_kw(k):
        k = k.strip().strip("；;，,")
        return syn.get(k, k)
    kw_docs, kw_first_year = defaultdict(set), {}
    for i, r in enumerate(recs):
        kws = {clean_kw(k) for k in r["keywords"]}
        kws = {k for k in kws if k and k not in generic}
        for k in kws:
            kw_docs[k].add(i)
            if r["year"] and (k not in kw_first_year or r["year"] < kw_first_year[k]):
                kw_first_year[k] = r["year"]
    kw_freq = Counter({k: len(v) for k, v in kw_docs.items()})
    n_tagged = sum(1 for r in recs if r["keywords"])
    print(f"\n=== 关键词 === 有标引 {n_tagged}/{N} 篇, 清洗后词数 {len(kw_freq)}")
    for k, c in kw_freq.most_common(30):
        print(f"  {c:3d}  {k}  (首现 {kw_first_year.get(k, '?')})")

    stats = {"years": years, "authors": au_cnt.most_common(), "orgs": org_cnt.most_common(),
             "kw_freq": kw_freq.most_common(), "kw_first_year": kw_first_year,
             "kw_docs": {k: sorted(v) for k, v in kw_docs.items()},
             "n_total": N, "n_tagged": n_tagged, "price_M": round(M_price, 2), "core_authors": core}
    json.dump(stats, open(os.path.join(data_dir, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------- 关键词共现网络 ----------
    nodes = [k for k, c in kw_freq.items() if c >= thresh]
    doc_kws = defaultdict(set)
    for k in nodes:
        for d in kw_docs[k]:
            doc_kws[d].add(k)
    edge_w = Counter()
    for d, kws in doc_kws.items():
        for a, b in itertools.combinations(sorted(kws), 2):
            edge_w[(a, b)] += 1
    G = nx.Graph()
    for n in nodes:
        G.add_node(n, freq=kw_freq[n])
    for (a, b), w in edge_w.items():
        G.add_edge(a, b, weight=w)
    G.remove_nodes_from(list(nx.isolates(G)))
    print(f"\n=== 关键词网络(频次≥{thresh}) === 节点 {G.number_of_nodes()}, 边 {G.number_of_edges()}, 密度 {nx.density(G):.4f}")

    # ---------- Louvain 聚类 + Q/S ----------
    communities = nx.community.louvain_communities(G, weight="weight", resolution=1.0, seed=42)
    communities = sorted(communities, key=len, reverse=True)
    Q = nx.community.modularity(G, communities, weight="weight")
    main_comms = [c for c in communities if len(c) >= 3]
    print(f"聚类数 {len(communities)}, 主要聚类(≥3节点) {len(main_comms)}, Q = {Q:.4f}")

    node_list = list(G.nodes())
    idx = {n: i for i, n in enumerate(node_list)}
    MM = np.zeros((len(node_list), len(node_list)))
    for a, b, d in G.edges(data=True):
        MM[idx[a], idx[b]] = d["weight"]; MM[idx[b], idx[a]] = d["weight"]
    norms = np.linalg.norm(MM, axis=1, keepdims=True); norms[norms == 0] = 1
    S_cos = MM @ MM.T / (norms @ norms.T)
    np.fill_diagonal(S_cos, 0)
    node2comm = {n: ci for ci, c in enumerate(main_comms) for n in c}
    sil = {}
    for n in node2comm:
        i, own = idx[n], node2comm[n]
        own_m = [idx[m] for m in main_comms[own] if m != n]
        a = np.mean([S_cos[i, j] for j in own_m]) if own_m else 0
        b = max((np.mean([S_cos[i, idx[m]] for m in main_comms[c]]) for c in range(len(main_comms)) if c != own), default=0)
        sil[n] = (a - b) / max(a, b) if max(a, b) > 0 else 0
    comm_info = []
    for ci, c in enumerate(main_comms):
        members = sorted(c, key=lambda n: -kw_freq[n])
        yrs = [recs[d]["year"] for n in c for d in kw_docs[n] if recs[d]["year"]]
        s_val = float(np.mean([sil[n] for n in c]))
        comm_info.append({"id": ci, "members": members, "size": len(c),
                          "mean_year": round(sum(yrs) / len(yrs), 1) if yrs else None,
                          "silhouette": round(s_val, 3), "total_freq": sum(kw_freq[n] for n in c)})
        print(f"#{ci} 规模{len(c)} 总频{sum(kw_freq[n] for n in c)} 均年{comm_info[-1]['mean_year']} S={s_val:.3f} | {'、'.join(members[:8])}")
    S_mean = float(np.mean(list(sil.values()))) if sil else 0
    print(f"平均轮廓值 S = {S_mean:.3f}  (近似算法, 最终以 CiteSpace 输出为准)")

    # ---------- 突现检测 法1: Kleinberg 双状态自动机 ----------
    def kleinberg(counts, gamma=0.5, s=1.5):
        n = len(counts); total = sum(counts)
        if total < 2:
            return []
        p0 = total / T
        if p0 >= 0.5:
            # 年均频次过高时按比例缩小计数，保证 p0<1（泊松代价对非整数计数同样有效）
            scale = 0.4 / p0
            counts = [c * scale for c in counts]
            p0 = total * scale / T
        p1 = min(p0 * s, 1.0)
        INF = float("inf")
        cost = [[INF, INF] for _ in range(n + 1)]; cost[0][0] = 0.0
        parent = [[0, 0] for _ in range(n + 1)]
        for i in range(1, n + 1):
            x = counts[i - 1]
            for st in (0, 1):
                p = p0 if st == 0 else p1
                emit = -(x * math.log(p) - p) if p > 0 else INF
                for prev in (0, 1):
                    trans = 0.0 if prev == st else gamma * math.log(2)
                    c = cost[i - 1][prev] + emit + trans
                    if c < cost[i][st]:
                        cost[i][st] = c; parent[i][st] = prev
        st = 0 if cost[n][0] <= cost[n][1] else 1
        states = [0] * n
        for i in range(n, 0, -1):
            states[i - 1] = st; st = parent[i][st] or 0
        bursts = []; i = 0
        while i < n:
            if states[i] == 1:
                j = i
                while j < n and states[j] == 1:
                    j += 1
                seg = counts[i:j]
                strength = sum(seg) * (math.log(p1 / p0) if p0 > 0 else 1)
                bursts.append((round(strength, 2), i, j - 1))
                i = j
            else:
                i += 1
        return bursts

    # ---------- 突现检测 法2: 窗口偏离度 ----------
    def burst_deviation(k, min_dur=2):
        f = kw_freq[k]
        if f < 3:
            return None
        cnt = Counter(recs[d]["year"] for d in kw_docs[k] if recs[d]["year"])
        obs = [cnt.get(y, 0) for y in YEARS]
        e = f / T; best = None
        for i in range(T):
            for j in range(i + min_dur - 1, T):
                seg = obs[i:j + 1]
                dev = sum(o - e for o in seg)
                if dev <= 0 or sum(seg) < 2:
                    continue
                strength = dev / math.sqrt(e * (j - i + 1))
                if best is None or strength > best[0]:
                    best = (strength, i, j)
        if best:
            s, i, j = best
            return {"kw": k, "strength": round(s, 2), "begin": YEARS[i], "end": YEARS[j], "dur": j - i + 1, "freq": f}
        return None

    burst_k, burst_d = [], []
    for k in G.nodes():
        counts = [Counter(recs[d]["year"] for d in kw_docs[k] if recs[d]["year"]).get(y, 0) for y in YEARS]
        bs = [b for b in kleinberg(counts) if b[2] - b[1] + 1 >= 2]
        if bs:
            strength, bi, ei = max(bs, key=lambda b: b[0])
            burst_k.append({"kw": k, "strength": strength, "begin": YEARS[bi], "end": YEARS[ei],
                            "dur": ei - bi + 1, "freq": kw_freq[k]})
        bd = burst_deviation(k)
        if bd:
            burst_d.append(bd)
    burst_k.sort(key=lambda r: -r["strength"]); burst_d.sort(key=lambda r: -r["strength"])
    print("\n=== 突现词 Top15 (Kleinberg / 窗口偏离度, 持续≥2年; 最终以 CiteSpace Burstness 为准) ===")
    for r in burst_k[:15]:
        print(f"  {r['strength']:6.2f}  {r['begin']}-{r['end']}  {r['kw']} (频次{r['freq']})")

    # ---------- 作者/机构共现网络 ----------
    GA = nx.Graph(); au_freq2 = Counter()
    for r in recs:
        aus = sorted(set(r["authors"]))
        for a in aus:
            au_freq2[a] += 1; GA.add_node(a)
        for i in range(len(aus)):
            for j in range(i + 1, len(aus)):
                GA.add_edge(aus[i], aus[j], weight=GA.get_edge_data(aus[i], aus[j], {}).get("weight", 0) + 1)
    GI = nx.Graph()
    for r in recs:
        orgs = sorted({norm_org(o) for o in r["orgs"]})
        for o in orgs:
            GI.add_node(o)
        for i in range(len(orgs)):
            for j in range(i + 1, len(orgs)):
                GI.add_edge(orgs[i], orgs[j], weight=GI.get_edge_data(orgs[i], orgs[j], {}).get("weight", 0) + 1)
    comps = sorted(nx.connected_components(GA), key=len, reverse=True)
    n_iso_a = len(list(nx.isolates(GA))); n_iso_i = len(list(nx.isolates(GI)))
    print(f"\n作者网络: 节点{GA.number_of_nodes()} 边{GA.number_of_edges()} 密度{nx.density(GA):.5f} "
          f"孤立{n_iso_a} 分量{len(comps)} 最大分量{len(comps[0]) if comps else 0}")
    print(f"机构网络: 节点{GI.number_of_nodes()} 边{GI.number_of_edges()} 密度{nx.density(GI):.5f} 孤立{n_iso_i}")

    net = {"network": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "density": nx.density(G)},
           "Q": Q, "S_mean": S_mean, "clusters": comm_info, "bursts": burst_k, "bursts2": burst_d,
           "edges": [[a, b, w] for (a, b), w in edge_w.items() if G.has_edge(a, b)],
           "graph_nodes": {n: kw_freq[n] for n in G.nodes()},
           "author_net": {"nodes": GA.number_of_nodes(), "edges": GA.number_of_edges(),
                          "density": nx.density(GA), "isolates": n_iso_a,
                          "largest_component": len(comps[0]) if comps else 0, "components": len(comps)},
           "org_net": {"nodes": GI.number_of_nodes(), "edges": GI.number_of_edges(),
                       "density": nx.density(GI), "isolates": n_iso_i},
           "years_span": [YEARS[0], YEARS[-1]]}
    json.dump(net, open(os.path.join(data_dir, "network.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pickle.dump({"GA": GA, "GI": GI, "au_freq": dict(au_freq2)}, open(os.path.join(data_dir, "networks.pkl"), "wb"))
    print("\n已保存 stats.json / network.json / networks.pkl")

if __name__ == "__main__":
    main()
