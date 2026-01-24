import re
import requests
from django.conf import settings

SEP = r"[.;!?]|,|\s+nhưng\s+|\s+tuy\s+|\s+song\s+|\s+mà\s+|\s+và\s+|\s+còn\s+"

KEYWORD_ASPECT = {
    "BATTERY": ["pin", "sạc", "tụt pin", "hao pin"],
    "SCREEN": ["màn hình", "hiển thị", "độ sáng", "full hd", "oled", "amoled"],
    "CAMERA": ["camera", "chụp", "ảnh", "video", "quay"],
    "PRICE": ["giá", "đắt", "rẻ", "khuyến mãi"],
    "PERFORMANCE": ["lag", "giật", "mượt", "nóng", "nhiệt", "nhiệt độ", "hiệu năng", "chip", "cpu"],
    "DESIGN": ["thiết kế", "đẹp", "xấu", "cầm", "mỏng", "nhẹ", "ngoại hình"],
    "STORAGE": ["bộ nhớ", "rom", "lưu trữ", "dung lượng"],
    "FEATURES": ["tính năng", "vân tay", "face id", "nhận diện", "bảo mật"],
    "SER&ACC": ["phụ kiện", "ốp", "sạc", "tai nghe", "dịch vụ", "bảo hành"],
    "GENERAL": ["tổng quan", "máy", "điện thoại", "sản phẩm"]
}

def allowed_aspects_for_text(part: str):
    t = part.lower()
    allowed = set()
    for asp, kws in KEYWORD_ASPECT.items():
        if any(k in t for k in kws):
            allowed.add(asp)
    return allowed  # có thể rỗng


def analyze_sentiment(text, threshold=0.3):
    payload = {"text": text, "threshold": threshold}
    res = requests.post(settings.AI_URL, json=payload, timeout=30)
    res.raise_for_status()
    return res.json().get("results", [])

def analyze_sentiment_detailed(text, threshold=0.3):
    parts = [p.strip() for p in re.split(SEP, text) if p.strip()]
    if not parts:
        return []

    bucket = {}  # aspect -> list(items)

    for part in parts:
        th = min(threshold, 0.25)
        allowed = allowed_aspects_for_text(part)  # ✅ lọc theo keyword

        try:
            results = analyze_sentiment(part, threshold=th)
        except Exception:
            results = []

        # ✅ nếu mệnh đề có keyword rõ (allowed không rỗng) thì chỉ giữ những aspect đó
        if allowed:
            results = [r for r in results if r.get("aspect") in allowed]

        for r in results:
            asp = r.get("aspect")
            if not asp:
                continue
            bucket.setdefault(asp, [])

            # giữ conf cao nhất cho mỗi sentiment trong cùng aspect
            found = False
            for old in bucket[asp]:
                if old.get("sentiment") == r.get("sentiment"):
                    if r["confidence"] > old["confidence"]:
                        old.update(r)
                    found = True
                    break
            if not found:
                bucket[asp].append(r)

    final = []
    for asp, items in bucket.items():
        items.sort(key=lambda x: -x.get("confidence", 0))
        final.extend(items[:2])

    final.sort(key=lambda x: -x.get("confidence", 0))
    return final