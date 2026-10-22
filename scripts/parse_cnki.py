# -*- coding: utf-8 -*-
"""解析 CNKI RefWorks 导出题录（download_XX.txt），输出 records.json
用法: python parse_cnki.py <输入txt文件或所在目录> <输出目录>
输出: <输出目录>/records.json  字段: title/authors/orgs/journal/year/keywords/abstract
"""
import re, json, sys, glob, os

def parse_records(raw):
    recs = []
    for chunk in raw.split("RT Journal Article")[1:]:
        rec = {}
        fields = re.split(r"\n(?=[A-Z][A-Z0-9] )", chunk)
        for f in fields:
            m = re.match(r"([A-Z][A-Z0-9]) (.*)", f, re.S)
            if not m:
                continue
            tag, val = m.group(1), m.group(2).strip()
            rec[tag] = rec[tag] + " " + val if tag in rec else val
        recs.append(rec)
    return recs

def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    if os.path.isdir(src):
        files = sorted(glob.glob(os.path.join(src, "download_*.txt")) or glob.glob(os.path.join(src, "*.txt")))
    else:
        files = [src]
    assert files, "未找到题录 txt 文件"
    raw = ""
    for fp in files:
        raw += open(fp, encoding="utf-8", errors="ignore").read() + "\n"
    print(f"读入文件 {len(files)} 个:", [os.path.basename(f) for f in files])

    recs = parse_records(raw)
    print("解析记录数:", len(recs))

    n_k1 = sum(1 for r in recs if r.get("K1"))
    print(f"有关键词: {n_k1}, 有摘要: {sum(1 for r in recs if r.get('AB'))}, "
          f"有机构: {sum(1 for r in recs if r.get('AD'))}, 有年份: {sum(1 for r in recs if r.get('YR'))}")

    # 非研究性文献初筛（人工确认后再剔除，不要自动删）
    noise_pat = re.compile(r"征稿|启事|通知|公告|书评|卷首|编者按|选题指南|会议纪要|会议综述|致辞|索引$|总目录")
    noise = [r for r in recs if noise_pat.search(r.get("T1", ""))]
    print("疑似非研究性文献:", len(noise))
    for r in noise:
        print("  -", r.get("T1", "")[:50], "|", r.get("JF", ""), r.get("YR", ""))

    out = [{
        "title": r.get("T1", ""),
        "authors": [a.strip() for a in r.get("A1", "").split(";") if a.strip()],
        "orgs": [o.strip() for o in r.get("AD", "").split(";") if o.strip()],
        "journal": r.get("JF", ""),
        "year": int(r["YR"]) if re.match(r"^\d{4}$", r.get("YR", "")) else None,
        "keywords": [k.strip() for k in re.split(r"[;；]", r.get("K1", "")) if k.strip()],
        "abstract": r.get("AB", ""),
    } for r in recs]
    outpath = os.path.join(outdir, "records.json")
    json.dump(out, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已保存", outpath)

if __name__ == "__main__":
    main()
