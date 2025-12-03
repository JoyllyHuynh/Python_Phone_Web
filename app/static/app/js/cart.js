var updateBtns = document.getElementsByClassName('update-cart')

// 1. Dùng var cho biến i (Tốt hơn)
for (var i = 0; i < updateBtns.length; i++) {
    updateBtns[i].addEventListener('click', function () {   
        // 2. Chú ý: Dùng 'product' nếu HTML là data-product="..."
        var productId = this.dataset.product
        var action = this.dataset.action
        
        console.log('productId:', productId, 'action:', action)
        console.log('user:', user)

        if (user == 'AnonymousUser') {
            console.log('User not logged in, show login prompt or use cookie session')
        } else {
            updateUserOrder(productId, action)
        }
    })
}

function updateUserOrder(productId, action) {
    console.log('User is logged in, sending data...')   
    var url = '/update_item/'
    
    // Gửi yêu cầu AJAX
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken, // Rất quan trọng cho POST request
        },
        body: JSON.stringify({'productId': productId, 'action': action})
    })
    .then((response) => {
        // Kiểm tra xem request có thành công không trước khi parse JSON
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json()
    })
    .then((data) => {
        console.log('data:', data)
        // Tải lại trang để hiển thị kết quả mới
        location.reload()
    })
    .catch((error) => {
        console.error('Fetch error:', error);
        alert('Có lỗi xảy ra khi cập nhật giỏ hàng. Vui lòng thử lại.');
    });
}
