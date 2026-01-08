print("🔥 USING RULES FILE:", __file__)

ENTITY_MAP = {
    "dien thoai": "ngoai_hinh",
    "may": "ngoai_hinh",
    "san pham": "ngoai_hinh",
}

import re
from unidecode import unidecode

# ================================
# NORMALIZE
# ================================
def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_no_accent(text):
    return unidecode(normalize_text(text))

def split_clauses(text):
    text = normalize_no_accent(text)
    separators = [
        " nhung ",
        " ma ",
        " tuy nhien ",
        " nhma ",
        " nhung la ",
        " nhung ma "
    ]
    clauses = [text]

    for sep in separators:
        tmp = []
        for c in clauses:
            tmp.extend(c.split(sep))
        clauses = tmp

    return [c.strip() for c in clauses if c.strip()]


# ================================
# ASPECT KEYWORDS
# ================================
ASPECT_KEYWORDS = {
    "pin": ["pin", "sac", "sac pin", "pin trau"],
    "camera": ["camera", "chup anh", "chup hinh"],
    "man_hinh": ["man hinh", "man hinh sang"],
    "hieu_nang": ["lag", "giat", "muot", "chip", "ram", "xu ly"],
    "nhiet_do": ["nong", "nong may", "nhiet do", "nhiet do cao",],
    "ngoai_hinh": ["ngoai hinh", "thiet ke", "cam giac cam"]
}
ASPECT_KEYWORDS["gia"] = [
    "gia",
    "gia ca",
    "gia tien",
    "gia ban",
    "muc gia",
    "gia thanh"
]
ASPECT_KEYWORDS["ngoai_hinh"] += [
    "dien thoai",
    "may",
]



# ================================
# IMPLICIT ASPECTS
# ================================
# >>> NEW: IMPLICIT ASPECT KEYWORDS (MAX SAFE SET)

IMPLICIT_ASPECTS = {
    "ngoai_hinh": [
        # trực tiếp
        "dien thoai dep",
        "may dep",
        "nhin dep",
        "nhin sang",
        "ngoai hinh dep",
        "thiet ke dep",
        "dep mat",
        "nhin rat dep",
        "khong xau",

        # tiêu cực
        "may xau",
        "nhin xau",
        "thiet ke xau",
        "nhin khong dep",
        "ngoai hinh xau",

    ],

    "hieu_nang": [
        "chay muot",
        "dung muot",
        "xu ly muot",
        "chay nhanh",
        "chay cham",
        "dung cham",
        "lag qua",
        "giat lag",
        "bi lag",
        "hay lag",
        "treo may",
        "dung bi lag",
    ],

    "pin": [
        "pin trau",
        "pin yeu",
        "xai duoc lau",
        "dung duoc lau",
        "xai ton pin",
        "pin hao",
        "pin sut",
        "pin tut",
        "het pin nhanh",
        "sac cham",
        "sac lau",
    ],

    "nhiet_do": [
        "may nong",
        "nong may",
        "nong qua",
        "rat nong",
        "nong ran",
        "nong khi dung",
        "dung la nong",
        "nong khi choi game",
        "nhiet do",       
        "nhiet do cao",
    ],

    "man_hinh": [
        "man hinh dep",
        "man hinh sang",
        "man hinh toi",
        "nhin ro",
        "hien thi tot",
        "hien thi kem",
        "man hinh mo",
        "man hinh choi",
    ],
}
IMPLICIT_ASPECTS["gia"] = [
    # tích cực
    "gia re",
    "re",
    "qua re",
    "gia hop ly",
    "gia tot",
    "dang tien",
    "rat dang tien",
    "gia phai chang",

    # tiêu cực
    "gia cao",
    "mac",
    "qua mac",
    "dat",
    "gia dat",
    "gia chat",
    "khong dang tien"
]
IMPLICIT_ASPECTS["ngoai_hinh"] += [
    "dien thoai dep",
    "dien thoai rat dep",
    "dien thoai xau",
    "dien thoai khong dep",
]


# ================================
# NEUTRAL WORDS
# ================================
NEUTRAL_WORDS = [
    "ok",
    "on",
    "on thoi",
    "tam on",
    "tam on thoi",
    "binh thuong",
    "binh thuong thoi",
    "chap nhan duoc",
    "dung duoc",
    "xai duoc",
    "khong te"
]
NEUTRAL_WORDS += [
    "trong tam gia nay",
    "voi tam gia nay",
    "o muc gia nay"
]

# ================================
# ASPECT SENTIMENT VOCAB
# ================================
ASPECT_SENTIMENT = {

    # ===== PIN =====
    "pin": {
        "pos": [
            "trau",
            "pin trau",
            "pin tot",
            "pin khoe",
            "pin ben",
            "xai lau",
            "xai duoc lau",
            "su dung lau",
            "xai ca ngay",
            "xai ca ngay khong lo"
        ],
        "neg": [
            "yeu",
            "pin yeu",
            "pin kem",
            "pin te",
            "hao",
            "hao pin",
            "tut",
            "tut nhanh",
            "sut pin",
            "pin nhanh het",
            "pin mau het",
            "sac cham",
            "sac lau"
        ]
    },

    # ===== CAMERA =====
    "camera": {
        "pos": [
            "chup dep",
            "chup anh dep",
            "chup ro",
            "anh net",
            "lay net nhanh",
            "chup tot"
        ],
        "neg": [
            "chup mo",
            "anh mo",
            "chup kem",
            "nhieu",
            "nhieu hat",
            "be hat",
            "lay net cham"
        ]
    },

    # ===== HIỆU NĂNG =====
    "hieu_nang": {
        "pos": [
            "muot",
            "chay muot",
            "chay muot ma",
            "manh",
            "nhanh",
            "xu ly nhanh",
            "phan hoi nhanh",
            "chay on dinh"
        ],
        "neg": [
            "lag",
            "hay lag",
            "lag nhe",
            "lag nhieu",
            "giat",
            "cham",
            "cham chap",
            "xu ly cham",
            "xu ly lau",
            "phan hoi cham",
            "khung hinh",
            "treo may"
        ]
    },

    # ===== NHIỆT ĐỘ =====
    "nhiet_do": {
        "pos": [
            "may mat",
            "it nong",
            "nhiet do on"
        ],
        "neg": [
            "nong",
            "nong ran",
            "qua nong",
            "nong nhanh",
            "nong khi choi game",
            "nong khi sac",
            "nong hon binh thuong",
            "nong ran tay",
            "nhiet do cao", 
            "cao qua",
        ]
    },

    # ===== MÀN HÌNH =====
    "man_hinh": {
        "pos": [
            "man hinh dep",
            "man hinh sang",
            "hien thi dep",
            "nhin ro",
            "nhin ro rang",
            "mau sac dep",
            "sac net"
        ],
        "neg": [
            "man hinh xau",
            "man hinh kem",
            "toi",
            "am mau",
            "nhin mo",
            "nhin khong ro",
            "mau sac kem",
            "choi"
        ]
    },

    # ===== NGOẠI HÌNH =====
    "ngoai_hinh": {
        "pos": [
            "ngoai hinh dep",
            "nhin dep",
            "nhin sang",
            "thiet ke dep",
            "thiet ke gon",
            "cam nam tot",
            "nhin hien dai",
            "gon gang"
        ],
        "neg": [
            "ngoai hinh xau",
            "nhin xau",
            "thiet ke xau",
            "cam nam khong tot",
            "thon day",
            "nhin re tien"
        ]
    }
}
ASPECT_SENTIMENT["gia"] = {
    "pos": [
        "re",
        "gia re",
        "qua re",
        "gia hop ly",
        "gia tot",
        "dang tien",
        "rat dang tien",
        "gia phai chang"
    ],
    "neg": [
        "mac",
        "qua mac",
        "dat",
        "gia cao",
        "gia chat",
        "khong dang tien"
    ]
}
ASPECT_SENTIMENT["pin"]["neg"] += [
    "nhanh het",
    "het nhanh",
    "pin thi nhanh het",
]
ASPECT_SENTIMENT["ngoai_hinh"]["pos"] += [
    "ngoai hinh thi dep",
    "thi dep"
]
ASPECT_SENTIMENT["camera"]["neg"] += [
    "xau",
    "camera xau",
    "thi xau"
]
ASPECT_SENTIMENT["ngoai_hinh"]["pos"] += [
    "dep",
    "rat dep",
    "nhin dep",
    "ngoai hinh dep"
]
ASPECT_SENTIMENT["ngoai_hinh"]["neg"] += [
    "xau",
    "rat xau",
    "qua xau",
    "xau xi",
]

# ================================
# IMPLICIT SENTIMENT
# ================================
IMPLICIT_SENTIMENT = {
    "ngoai_hinh": {
        "positive": [
            "may dep",
            "nhin dep",
            "nhin sang",
            "khong xau"
        ],
        "negative": [
            "may xau",
            "nhin xau",
        ]
    },

    "camera": {
        "positive": [
            "chup hinh dep",
            "chup anh dep",
            "hinh chup dep",
            "anh dep"
        ]
    },

    "man_hinh": {
        "negative": [
            "khong dep"
        ]
    }
}
IMPLICIT_SENTIMENT["gia"] = {
    "positive": [
        "gia re",
        "dang tien",
        "rat dang tien",
        "gia hop ly"
    ],
    "negative": [
        "gia cao",
        "qua mac",
        "khong dang tien"
    ]
}

# ================================
# ASPECT DETECT
# ================================
def detect_aspects_rule(text):
    text = normalize_no_accent(text)
    found = []
    for asp, kws in ASPECT_KEYWORDS.items():
        for kw in sorted(kws, key=len, reverse=True):
            idx = text.find(kw)
            if idx != -1:
                found.append((asp, idx))
                break
    return found

def detect_implicit_aspects(text):
    text = normalize_no_accent(text)
    found = []

    # 1️⃣ Detect implicit patterns (như cũ)
    for asp, patterns in IMPLICIT_ASPECTS.items():
        for p in patterns:
            if p in text:
                found.append(asp)
                break

    # 2️⃣ Entity → Aspect fallback (PHẦN QUAN TRỌNG)
    for entity, asp in ENTITY_MAP.items():
        if entity in text and asp not in found:
            found.append(asp)

    return found


def extract_clause(text, aspect, source, pos):
    text = normalize_no_accent(text)

    # chỉ lấy 1 cửa sổ ngắn quanh aspect (±40 ký tự)
    start = max(0, pos - 40)
    end = min(len(text), pos + 40)
    window = text[start:end]

    for sep in [" nhung ", " ma ", " tuy nhien ", " nhma "]:
        if sep in window:
            left, right = window.split(sep, 1)
            return (
                left.strip() if pos - start < len(left) else right.strip(),
                "before_contrast" if pos - start < len(left) else "after_contrast"
            )

    return window.strip(), "no_contrast"


# ================================
# SENTIMENT RULE ADVANCED
# ================================
def sentiment_rule_advanced(text, aspect, source, contrast_pos=None):
    text = text.lower()
    senti = ASPECT_SENTIMENT.get(aspect, {})
    pos_words = senti.get("pos", [])
    neg_words = senti.get("neg", [])

    # ===== 1. IMPLICIT SENTIMENT (ƯU TIÊN CAO NHẤT)
    for pol, phrases in IMPLICIT_SENTIMENT.get(aspect, {}).items():
        for p in phrases:
            if p in text:
                return pol

    # ===== 2. PHỦ ĐỊNH ĐÚNG NGỮ NGHĨA
    for p in pos_words:
        if f"khong {p}" in text:
            return "negative"
    for n in neg_words:
        if f"khong {n}" in text:
            return "positive"

    # ===== 3. TRƯỚC "NHƯNG"
    if contrast_pos == "before_contrast":
        if any(p in text for p in pos_words):
            return "positive"
        if any(n in text for n in neg_words):
            return "negative"
        if any(nw in text for nw in NEUTRAL_WORDS):
            return "neutral"
        return None

    # ===== 4. SAU "NHƯNG"
    if contrast_pos == "after_contrast":
        if any(p in text for p in pos_words):
            return "positive"
        if any(n in text for n in neg_words):
            return "negative"
        if any(nw in text for nw in NEUTRAL_WORDS):
            return "neutral"

    # ===== 5. EXPLICIT ASPECT KHÔNG CÓ SENTIMENT → BỎ
    if source == "explicit":
        if not any(w in text for w in pos_words + neg_words + NEUTRAL_WORDS):
            return None

    # ===== 6. FINAL FALLBACK (QUAN TRỌNG)
    # ⚠️ POSITIVE PHẢI ƯU TIÊN TRƯỚC
    if any(p in text for p in pos_words):
        return "positive"
    if any(n in text for n in neg_words):
        return "negative"
    if any(nw in text for nw in NEUTRAL_WORDS):
        return "neutral"

    return None


# ================================
# MAIN PREDICT
# ================================
def predict_comment(text):
    raw = normalize_text(text)
    text_norm = normalize_no_accent(raw)
    clauses = split_clauses(text_norm)

    explicit, implicit = [], []
    cursor = 0
    for c in clauses:
        for asp, pos in detect_aspects_rule(c):
            explicit.append((asp, cursor + pos))
        implicit.extend(detect_implicit_aspects(c))
        cursor += len(c) + 1

    aspect_info = {}
    for asp, pos in explicit:
        aspect_info[asp] = {"source": "explicit", "pos": pos}

    for asp in implicit:
        if asp not in aspect_info:
            pos = None

            # 1️⃣ Ưu tiên vị trí implicit pattern
            for p in IMPLICIT_ASPECTS.get(asp, []):
                idx = text_norm.find(p)
                if idx != -1:
                    pos = idx
                    break

            # 2️⃣ Nếu là entity map → lấy vị trí entity
            if pos is None:
                for entity, mapped_asp in ENTITY_MAP.items():
                    if mapped_asp == asp:
                        idx = text_norm.find(entity)
                        if idx != -1:
                            pos = idx
                            break

            # 3️⃣ Fallback cuối
            if pos is None:
                pos = 0

            aspect_info[asp] = {"source": "implicit", "pos": pos}


    aspects_sorted = sorted(aspect_info.items(), key=lambda x: x[1]["pos"])
    results = []

    for asp, info in aspects_sorted:
        clause, contrast_pos = extract_clause(
                text_norm,   # 🔥 BẮT BUỘC
                asp,
                info["source"],
                info["pos"]
            )
        sent = sentiment_rule_advanced(clause, asp, info["source"], contrast_pos)
        results.append((asp, sent or "neutral"))

    return results
