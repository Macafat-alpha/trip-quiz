#!/usr/bin/env python3
"""validate_quiz.py — 旅行クイズJSON（スキーマv1）の形式チェック

使い方:
  python3 validate_quiz.py quiz-20260927.json
  python3 validate_quiz.py quiz.json --min 15   # 出題可能な問題数の下限

作る人も回答者なので、出力には問題文・選択肢・正解を一切出さない。
表示するのは件数の内訳と、エラーの「問題ID＋項目名」だけ。
終了コード: 0=OK / 1=エラーあり / 2=ファイルが読めない
"""
import json
import sys
from collections import Counter

TYPES = {"choice", "who", "truefalse", "number", "open"}
DIFFICULTIES = {"easy", "normal", "hard"}
VIBES = {"kudaranai", "omoshiroi", "sasai"}
CONFIDENCES = {"high", "low"}


def player_names(players):
    names = []
    for p in players:
        if isinstance(p, str):
            names.append(p)
        elif isinstance(p, dict) and isinstance(p.get("name"), str):
            names.append(p["name"])
    return names


def validate(data):
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["トップレベルがオブジェクトではない"], warnings

    if data.get("version") != 1:
        errors.append("version が 1 ではない")
    if not isinstance(data.get("title"), str) or not data.get("title"):
        errors.append("title がない")

    players = data.get("players")
    if not isinstance(players, list) or len(players) < 2:
        errors.append("players が2人未満")
        players = []
    names = player_names(players)
    if len(names) != len(players):
        errors.append("players に name のない要素がある")
    if len(set(names)) != len(names):
        errors.append("players の name が重複している")

    qs = data.get("questions")
    if not isinstance(qs, list) or not qs:
        errors.append("questions が空")
        return errors, warnings

    seen = set()
    for i, q in enumerate(qs):
        qid = q.get("id") if isinstance(q, dict) else None
        tag = f"[{qid or f'#{i+1}'}]"
        if not isinstance(q, dict):
            errors.append(f"{tag} オブジェクトではない")
            continue
        if not isinstance(qid, str) or not qid:
            errors.append(f"{tag} id がない")
        elif qid in seen:
            errors.append(f"{tag} id が重複")
        seen.add(qid)

        t = q.get("type")
        if t not in TYPES:
            errors.append(f"{tag} type が不正")
            continue
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            errors.append(f"{tag} question がない")
        for key, allowed in (("difficulty", DIFFICULTIES), ("vibe", VIBES), ("confidence", CONFIDENCES)):
            if key in q and q[key] not in allowed:
                errors.append(f"{tag} {key} が不正")
        if "spicy" in q and not isinstance(q["spicy"], bool):
            errors.append(f"{tag} spicy が真偽値ではない")
        if "points" in q and not (isinstance(q["points"], int) and q["points"] >= 1):
            errors.append(f"{tag} points が1以上の整数ではない")
        for key in ("speech", "explanation", "segment"):
            if key in q and not isinstance(q[key], str):
                errors.append(f"{tag} {key} が文字列ではない")
        ev = q.get("evidence")
        if ev is not None and not (isinstance(ev, dict) and isinstance(ev.get("quote", ""), str)):
            errors.append(f"{tag} evidence の形が不正")

        ans = q.get("answer")
        choices = q.get("choices")
        cs = q.get("choices_speech")
        if cs is not None and not (isinstance(cs, list) and isinstance(choices, list)
                                   and len(cs) == len(choices) and all(isinstance(x, str) for x in cs)):
            errors.append(f"{tag} choices_speech は choices と同じ数の文字列")
        answers = ans if isinstance(ans, list) else [ans]
        if isinstance(ans, list) and (not ans or len(set(map(str, ans))) != len(ans)):
            errors.append(f"{tag} answer の配列が空か重複")
        if t == "choice":
            if not (isinstance(choices, list) and 2 <= len(choices) <= 4 and all(isinstance(c, str) and c for c in choices)):
                errors.append(f"{tag} choices は2〜4個の文字列")
            elif len(set(choices)) != len(choices):
                errors.append(f"{tag} choices が重複")
            elif not all(a in choices for a in answers):
                errors.append(f"{tag} answer が choices に含まれない")
        elif t == "who":
            pool = choices if choices is not None else names
            if choices is not None and not (isinstance(choices, list) and all(c in names for c in choices)):
                errors.append(f"{tag} who の choices に players 以外の名前がある")
            if not all(a in pool for a in answers):
                errors.append(f"{tag} answer が players（choices）に含まれない")
            if q.get("confidence") == "low":
                warnings.append(f"{tag} who で confidence=low（アプリでは出題しない）")
        elif t == "truefalse":
            if not isinstance(ans, bool):
                errors.append(f"{tag} answer が true/false ではない")
        elif t == "number":
            if isinstance(ans, bool) or not isinstance(ans, (int, float)):
                errors.append(f"{tag} answer が数値ではない")
            if "unit" in q and not isinstance(q["unit"], str):
                errors.append(f"{tag} unit が文字列ではない")
        elif t == "open":
            if not all(isinstance(a, str) and a.strip() for a in answers):
                errors.append(f"{tag} answer（模範解答）がない")

    return errors, warnings


def playable(q):
    return not (q.get("type") == "who" and q.get("confidence") == "low")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    path = args[0]
    min_count = int(args[args.index("--min") + 1]) if "--min" in args else 0
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"NG: ファイルを読めない（{type(e).__name__}: {e}）")
        sys.exit(2)

    errors, warnings = validate(data)
    qs = [q for q in data.get("questions", []) if isinstance(q, dict)] if isinstance(data, dict) else []
    ok_qs = [q for q in qs if playable(q)]
    if min_count and len(ok_qs) < min_count:
        errors.append(f"出題できる問題が {len(ok_qs)} 問で、下限 {min_count} 問に届かない")

    print(f"問題数: {len(qs)}（出題可能 {len(ok_qs)}）")
    for label, key in (("形式", "type"), ("種類", "vibe"), ("難易度", "difficulty"), ("時間帯", "segment")):
        c = Counter(q.get(key, "-") for q in ok_qs)
        print(f"{label}: " + " / ".join(f"{k} {v}" for k, v in c.most_common()))
    print(f"きわどい問題: {sum(1 for q in ok_qs if q.get('spicy'))}")
    for w in warnings:
        print(f"注意: {w}")
    for e in errors:
        print(f"NG: {e}")
    print("結果: " + ("OK" if not errors else f"エラー {len(errors)} 件"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
