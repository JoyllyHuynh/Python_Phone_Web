from .hybrid import predict_comment_hybrid

def predict_comment(text: str):
    return predict_comment_hybrid(text)
