from collections import defaultdict
from typing import Dict, Any, List

POS, NEG, NEU = "Positive", "Negative", "Neutral"

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def aggregate_aspects(reviews) -> Dict[str, Any]:
    """
    reviews: queryset/list Review, mỗi review có ai_result (list dict)
    return: dict aspect -> stats
    """
    acc = defaultdict(lambda: {"pos": 0.0, "neg": 0.0, "neu": 0.0, "count": 0, "examples_pos": [], "examples_neg": []})

    for rv in reviews:
        items = rv.ai_result or []
        text = (rv.content or "").strip()

        for it in items:
            asp = (it or {}).get("aspect")
            sent = (it or {}).get("sentiment")
            conf = float((it or {}).get("confidence") or 0.0)

            if not asp or conf <= 0:
                continue

            acc[asp]["count"] += 1

            if sent == POS:
                acc[asp]["pos"] += conf
                # lấy vài câu ví dụ (tuỳ bạn có muốn)
                if text and len(acc[asp]["examples_pos"]) < 2:
                    acc[asp]["examples_pos"].append(text)
            elif sent == NEG:
                acc[asp]["neg"] += conf
                if text and len(acc[asp]["examples_neg"]) < 2:
                    acc[asp]["examples_neg"].append(text)
            else:
                acc[asp]["neu"] += conf

    out = {}
    for asp, s in acc.items():
        total = s["pos"] + s["neg"] + s["neu"]
        if total <= 0:
            continue

        pos_pct = s["pos"] / total
        neg_pct = s["neg"] / total
        neu_pct = s["neu"] / total

        # sentiment score [-1..+1]
        score = (s["pos"] - s["neg"]) / total
        stars = clamp(3 + 2 * score, 1, 5)

        # label
        if pos_pct > 0.65:
            label = "Mostly Positive"
        elif neg_pct > 0.65:
            label = "Mostly Negative"
        elif pos_pct > 0.35 and neg_pct > 0.35:
            label = "Mixed"
        else:
            label = "Neutral"

        out[asp] = {
            "pos_pct": round(pos_pct * 100, 1),
            "neg_pct": round(neg_pct * 100, 1),
            "neu_pct": round(neu_pct * 100, 1),
            "stars": round(stars, 1),
            "mentions": s["count"],
            "label": label,
            "examples_pos": s["examples_pos"],
            "examples_neg": s["examples_neg"],
        }

    return out

def compute_overall_from_aspects(aspect_stats: dict) -> float:
    total_w = 0.0
    total = 0.0
    for asp, s in aspect_stats.items():
        w = float(s.get("mentions") or 0)
        stars = float(s.get("stars") or 0)
        if w <= 0 or stars <= 0:
            continue
        total += stars * w
        total_w += w
    if total_w <= 0:
        return 0.0
    return round(total / total_w, 1)
