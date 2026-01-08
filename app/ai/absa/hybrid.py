print(">>> USING STABLE HYBRID ABSA <<<")

from .rules import predict_comment as rule_predict
from .ml_sentiment import predict_sentiment_ml


STRONG_RULE_SENTIMENT = {"positive", "negative"}


def predict_comment_hybrid(text: str):
    """
    STABLE HYBRID ABSA
    - Aspect: RULE
    - Sentiment:
        + RULE nếu rõ
        + ML nếu RULE = neutral
    """

    rule_results = rule_predict(text)
    final = []

    for asp, rule_sent in rule_results:

        # 1️⃣ Nếu rule đã chắc → dùng luôn
        if rule_sent in STRONG_RULE_SENTIMENT:
            final.append((asp, rule_sent))
            continue

        # 2️⃣ Rule mơ hồ → gọi ML
        ml_sent = predict_sentiment_ml(text)

        final.append((asp, ml_sent))

    return final
