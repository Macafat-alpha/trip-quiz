#!/usr/bin/env python3
"""fetch_plaud.py — 指定日のPlaud録音をまとめて取得し、実時刻付きの1ファイルにする

前提: Plaud CLI（npm i -g @plaud-ai/cli）をインストールし、plaud login 済みであること

使い方:
  python3 fetch_plaud.py 2026-09-27                      # その日の録音をすべて
  python3 fetch_plaud.py 2026-09-27 --from 08:00         # 8時以降に始まった録音だけ（日本時間）
  python3 fetch_plaud.py 2026-09-27 --out ./trip-quiz    # 保存先を指定（既定は ./trip-quiz）

出力: <out>/work/YYYY-MM-DD/day.txt（1行＝ [HH:MM] Speaker N: 発話）と、録音ごとの生テキスト
画面には録音のID・開始時刻・長さ・行数だけを出す。タイトルと中身は出さない（作る人も回答者のため）。
"""
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

JST = timedelta(hours=9)


def run(*args):
    r = subprocess.run(["plaud", *args], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"plaud {' '.join(args)} が失敗: {r.stderr.strip()[:200]}")
    return r.stdout


def list_ids(day):
    # recent は日数指定なので、対象日を含む範囲を取ってから日付で絞る
    days_back = (datetime.now().date() - day).days + 1
    out = run("recent", "-d", str(max(days_back, 1)))
    return re.findall(r"^\s*((?:of_)?[0-9a-f]{32})\s", out, re.M)


def start_at_jst(fid):
    out = run("file", fid)
    m = re.search(r"start_at:\s*(\S+)", out)
    if not m:
        return None
    return datetime.fromisoformat(m.group(1)[:19]) + JST


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    day = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    frm = None
    if "--from" in sys.argv:
        h, m = sys.argv[sys.argv.index("--from") + 1].split(":")
        frm = datetime.combine(day, datetime.min.time()).replace(hour=int(h), minute=int(m))

    base = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("trip-quiz")
    outdir = base / "work" / day.isoformat()
    outdir.mkdir(parents=True, exist_ok=True)

    recs = []
    for fid in list_ids(day):
        st = start_at_jst(fid)
        if not st or st.date() != day or (frm and st < frm):
            continue
        recs.append((st, fid))
    recs.sort()
    if not recs:
        print(f"{day} の録音が見つからない（文字起こしがまだの可能性あり）")
        sys.exit(1)

    lines_all = []
    print(f"{day} の録音 {len(recs)} 本")
    for st, fid in recs:
        raw = run("transcript", fid)
        (outdir / f"{fid}.txt").write_text(raw, encoding="utf-8")
        n = 0
        lines_all.append(f"\n=== 録音 {fid} 開始 {st:%H:%M} ===")
        for m in re.finditer(r"^\[(\d+):(\d+)(?::(\d+))?\s*-[^\]]*\]\s*(.*)$", raw, re.M):
            a, b, c, text = m.groups()
            sec = int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)
            t = st + timedelta(seconds=sec)
            lines_all.append(f"[{t:%H:%M}] {text.strip()}")
            n += 1
        dur = run("file", fid)
        dm = re.search(r"duration:\s*(\S+)", dur)
        print(f"  {st:%H:%M}  {dm.group(1) if dm else '?':>8}  {n:>5}行  {fid}")
        if n == 0:
            print("    ↑ 文字起こしが空。Plaudアプリで文字起こしが終わっているか確認")

    (outdir / "day.txt").write_text("\n".join(lines_all).strip() + "\n", encoding="utf-8")
    print(f"→ {outdir / 'day.txt'}")


if __name__ == "__main__":
    main()
