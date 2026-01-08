import os
import joblib
from django.conf import settings

MODEL_PATH = os.path.join(
    settings.BASE_DIR, "app", "ai", "absa", "aspect_model.pkl"
)

_model = None


def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            print("❌ aspect_model.pkl not found")
            return False
        _model = joblib.load(MODEL_PATH)
    return True


def predict_sentiment_ml(text: str) -> str:
    """
    Output: positive | negative | neutral
    """
    if not load_model():
        return "neutral"

    pred = _model.predict([text])[0]

    if pred in ("positive", "negative", "neutral"):
        return pred

    # fallback nếu model train kiểu số
    if pred == 1:
        return "positive"
    if pred == -1:
        return "negative"
    return "neutral"
