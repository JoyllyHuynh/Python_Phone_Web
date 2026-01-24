from ..models import Review
from .aspect_aggregate import aggregate_aspects, compute_overall_from_aspects

def recompute_product_ai_rating(product):
    reviews = Review.objects.filter(product=product).exclude(ai_result__isnull=True)
    aspect_stats = aggregate_aspects(reviews)
    ai_overall = compute_overall_from_aspects(aspect_stats)
    return float(ai_overall or 0.0), reviews.count()
