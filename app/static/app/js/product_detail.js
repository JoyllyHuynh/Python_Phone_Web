// Star Rating System
document.addEventListener('DOMContentLoaded', function() {
    const starContainer = document.getElementById('star-rating');
    const stars = document.querySelectorAll('#star-rating i');
    const ratingValue = document.getElementById('rating-value');
    const ratingText = document.getElementById('rating-text');

    // Initialize with 5 stars selected (default)
    let selectedRating = 5;

    stars.forEach(star => {
        // Click to select rating
        star.addEventListener('click', function() {
            const rating = parseInt(this.getAttribute('data-rating'));
            selectedRating = rating;
            ratingValue.value = rating;
            updateStarDisplay(rating);
            ratingText.textContent = rating + ' sao';
        });

        // Hover preview
        star.addEventListener('mouseenter', function() {
            const rating = parseInt(this.getAttribute('data-rating'));
            previewStarDisplay(rating);
        });
    });

    // Reset to selected state when mouse leaves
    starContainer.addEventListener('mouseleave', function() {
        updateStarDisplay(selectedRating);
    });

    // Update star display to show selected rating
    function updateStarDisplay(rating) {
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas', 'selected');
            } else {
                star.classList.remove('fas', 'selected');
                star.classList.add('far');
            }
        });
    }

    // Preview star display on hover
    function previewStarDisplay(rating) {
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas');
                // Remove selected class for preview
                if (index >= selectedRating) {
                    star.classList.remove('selected');
                }
            } else {
                star.classList.remove('fas', 'selected');
                star.classList.add('far');
            }
        });
    }

    // Review Form Submission
    const reviewForm = document.getElementById('review-form');
    reviewForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const comment = document.getElementById('review-comment').value;
        const rating = parseInt(ratingValue.value);

        if (!comment) {
            alert('Vui lòng nhập nội dung đánh giá!');
            return;
        }

        // Create review object with fixed name
        const review = {
            name: 'Nguyễn Văn A',
            comment: comment,
            rating: rating,
            date: new Date().toISOString()
        };

        // Save to storage
        saveReview(review);

        // Add to display
        addReviewToList(review);

        // Reset form
        reviewForm.reset();
        selectedRating = 5;
        ratingValue.value = 5;
        updateStarDisplay(5);
        ratingText.textContent = '5 sao';

        // Show success message
        alert('Cảm ơn bạn đã đánh giá sản phẩm!');

        // Scroll to new review
        document.getElementById('reviews-list').scrollIntoView({ behavior: 'smooth' });
    });

    // Load saved reviews
    loadReviews();
});

// Storage functions
function saveReview(review) {
    let reviews = JSON.parse(localStorage.getItem('productReviews') || '[]');
    reviews.unshift(review);
    localStorage.setItem('productReviews', JSON.stringify(reviews));
    updateReviewCount();
}

function loadReviews() {
    const reviews = JSON.parse(localStorage.getItem('productReviews') || '[]');
    const reviewsList = document.getElementById('reviews-list');

    // Clear existing reviews
    reviewsList.innerHTML = '';

    // Add default review first
    const defaultReview = {
        name: 'Nguyễn Văn A',
        comment: 'Sản phẩm dùng rất mượt, pin trâu, giao hàng nhanh chóng.',
        rating: 5,
        date: new Date().toISOString()
    };
    addReviewToList(defaultReview);

    // Add saved reviews
    reviews.forEach(review => {
        addReviewToList(review);
    });

    updateReviewCount();
}

function addReviewToList(review) {
    const reviewsList = document.getElementById('reviews-list');
    const reviewItem = document.createElement('div');
    reviewItem.className = 'review-item';

    // Generate stars HTML
    let starsHtml = '';
    for (let i = 0; i < 5; i++) {
        if (i < review.rating) {
            starsHtml += '<i class="fas fa-star"></i>';
        } else {
            starsHtml += '<i class="far fa-star"></i>';
        }
    }

    const date = new Date(review.date);
    const dateStr = date.toLocaleDateString('vi-VN') === new Date().toLocaleDateString('vi-VN')
        ? 'Hôm nay'
        : date.toLocaleDateString('vi-VN');

    reviewItem.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
                <div class="review-stars mb-1">
                    ${starsHtml}
                    <span class="ms-2 fw-bold">${review.rating}/5</span>
                </div>
                <span class="fw-bold">${review.name}</span>
            </div>
            <small class="text-muted">${dateStr}</small>
        </div>
        <p class="mb-0">${review.comment}</p>
    `;

    reviewsList.appendChild(reviewItem);
}

function updateReviewCount() {
    const reviews = JSON.parse(localStorage.getItem('productReviews') || '[]');
    const totalCount = 100 + reviews.length;
    document.getElementById('total-reviews').textContent = totalCount;
    document.getElementById('sidebar-total-reviews').textContent = totalCount;
}

function scrollToReviewForm() {
    document.getElementById('review-form-section').scrollIntoView({ behavior: 'smooth' });
}

// Price Update on Capacity Change
document.addEventListener('DOMContentLoaded', function() {
    const capacityInputs = document.querySelectorAll('input[name="capacity"]');
    const priceDisplay = document.getElementById('product-price');

    capacityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const newPrice = parseInt(this.getAttribute('data-price'));
            updatePriceDisplay(newPrice);
        });
    });

    function updatePriceDisplay(price) {
        const formattedPrice = price.toLocaleString('vi-VN') + '₫';
        priceDisplay.textContent = formattedPrice;

        // Add animation
        priceDisplay.style.transform = 'scale(1.1)';
        setTimeout(() => {
            priceDisplay.style.transform = 'scale(1)';
        }, 200);
    }
});

// Color selection
document.addEventListener('DOMContentLoaded', function() {
    const colorDots = document.querySelectorAll('.color-dot');
    colorDots.forEach(dot => {
        dot.addEventListener('click', function() {
            colorDots.forEach(d => d.classList.remove('active'));
            this.classList.add('active');
        });
    });
});