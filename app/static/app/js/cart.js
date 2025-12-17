// app/js/cart.js - PHIÊN BẢN RELOAD ĐƠN GIẢN VÀ ĐÁNG TIN CẬY

// Giả định các biến csrftoken và user đã được định nghĩa ở đây

var updateBtns = document.getElementsByClassName('update-cart')

for (var i = 0; i < updateBtns.length; i++) {
    // Truyền đối tượng event vào hàm xử lý
    updateBtns[i].addEventListener('click', function (e) { 
        var productId = this.dataset.product
        var action = this.dataset.action
        
        if (user === 'AnonymousUser') {
            alert('Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng.');
        } else {
            // TRUYỀN ĐỐI TƯỢNG EVENT (e) VÀO HÀM updateUserOrder
            updateUserOrder(productId, action, e) 
        }
    })
}

function updateUserOrder(productId, action, event) { 
    var url = '/update_item/' 
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({'productId': productId, 'action': action})
    })
    .then((response) => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json()
    })
    .then((data) => {
        // TẢI LẠI TRANG: Đảm bảo tất cả mọi thứ (header, số lượng, tổng tiền)
        // đều được render lại chính xác bởi Django.
        location.reload() 
    })
    .catch((error) => {
        console.error('Fetch error:', error);
        alert('Có lỗi xảy ra khi cập nhật giỏ hàng. Vui lòng thử lại.');
        location.reload() 
    });
}