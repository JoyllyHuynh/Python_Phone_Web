document.addEventListener('DOMContentLoaded', function() {

    /* =========================================
       1. CẤU HÌNH & TIỆN ÍCH
       ========================================= */

    // BẢNG GIÁ VẬN CHUYỂN (Phải khớp với HTML value="...")
    const SHIPPING_RATES = {
        'standard': 30000, // Tiêu chuẩn
        'express': 50000   // Giao nhanh
    };

    // Hàm định dạng tiền tệ (VD: 30000 -> 30,000₫)
    function formatMoney(amount) {
        return amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + "₫";
    }

    // Hàm lấy giá trị số từ data-attribute trong HTML
    function getRawValue(elementId) {
        const el = document.getElementById(elementId);
        if (!el) return 0;
        // Lấy từ data-value (số thô) thay vì lấy text (có chữ '₫' và dấu phẩy)
        return parseFloat(el.getAttribute('data-value')) || 0;
    }

    /* =========================================
       2. LOGIC TÍNH TOÁN GIÁ TIỀN (SHIPPING)
       ========================================= */
    // Lấy danh sách các nút radio vận chuyển
    const shippingRadios = document.querySelectorAll('input[name="shipping_method"]');

    // Lấy các phần tử hiển thị giá
    const shippingFeeDisplay = document.getElementById('shippingFeeDisplay');
    const finalTotalDisplay = document.getElementById('finalTotalDisplay');

    function updateOrderSummary() {
        // BƯỚC 1: Tìm xem option nào đang được chọn (:checked)
        const selectedRadio = document.querySelector('input[name="shipping_method"]:checked');

        // Nếu không chọn gì thì mặc định là 'standard'
        const shippingType = selectedRadio ? selectedRadio.value : 'standard';

        // Tra cứu giá tiền từ bảng cấu hình
        const shippingCost = SHIPPING_RATES[shippingType] || 0;

        // BƯỚC 2: Lấy Tạm tính & Giảm giá (Dữ liệu tĩnh từ Server)
        const subtotal = getRawValue('subtotalDisplay');
        const discount = getRawValue('discountAmountDisplay');

        // BƯỚC 3: Tính toán lại Tổng cộng
        // Công thức: Tổng = Tạm tính + Phí Ship (mới) - Giảm giá
        let total = subtotal + shippingCost - discount;
        if (total < 0) total = 0;

        // BƯỚC 4: Cập nhật giao diện (Thay đổi số tiền trên màn hình)

        // Cập nhật dòng "Phí vận chuyển"
        if (shippingFeeDisplay) {
            shippingFeeDisplay.innerText = formatMoney(shippingCost);
            // Cập nhật cả data-value để đồng bộ (nếu cần dùng lại)
            shippingFeeDisplay.setAttribute('data-value', shippingCost);
        }

        // Cập nhật dòng "Tổng cộng"
        if (finalTotalDisplay) {
            finalTotalDisplay.innerText = formatMoney(total);

            // Hiệu ứng nháy màu xanh để báo hiệu giá đã đổi
            finalTotalDisplay.classList.remove('price-changed');
            void finalTotalDisplay.offsetWidth; // Reset animation
            finalTotalDisplay.classList.add('price-changed');
        }

        // Cập nhật giao diện thẻ Card (thêm viền xanh cho ô được chọn)
        document.querySelectorAll('.radio-card').forEach(card => card.classList.remove('selected'));
        if (selectedRadio) {
            const parentCard = selectedRadio.closest('.radio-card');
            if (parentCard) parentCard.classList.add('selected');
        }
    }

    // BƯỚC 5: Gắn "máy nghe" (Event Listener)
    // Mỗi khi người dùng đổi option, chạy hàm updateOrderSummary
    shippingRadios.forEach(radio => {
        radio.addEventListener('change', updateOrderSummary);
    });

    /* =========================================
       3. LOGIC ẨN/HIỆN PHƯƠNG THỨC THANH TOÁN
       ========================================= */
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
    const bankInfo = document.getElementById('bank-transfer-info');
    const creditCardForm = document.getElementById('credit-card-form');
    const allPaymentOptions = document.querySelectorAll('.payment-option');

    function handlePaymentChange() {
        const selectedRadio = document.querySelector('input[name="payment_method"]:checked');
        if (!selectedRadio) return;

        const selectedValue = selectedRadio.value;

        // Reset: Ẩn hết
        if(bankInfo) bankInfo.classList.add('hidden');
        if(creditCardForm) creditCardForm.classList.add('hidden');
        allPaymentOptions.forEach(opt => opt.classList.remove('selected'));

        // Highlight ô đang chọn
        const parentLabel = selectedRadio.closest('.payment-option');
        if (parentLabel) parentLabel.classList.add('selected');

        // Hiện form tương ứng
        if (selectedValue === 'bank_transfer' && bankInfo) {
            bankInfo.classList.remove('hidden');
        } else if (selectedValue === 'credit_card' && creditCardForm) {
            creditCardForm.classList.remove('hidden');
        }
    }

    paymentRadios.forEach(radio => {
        radio.addEventListener('change', handlePaymentChange);
    });

    /* =========================================
       4. UX: TỰ ĐỘNG FORMAT SỐ THẺ TÍN DỤNG
       ========================================= */
    const cardInput = document.getElementById('cardNumber');
    const cardExpiry = document.getElementById('cardExpiry');

    if (cardInput) {
        cardInput.addEventListener('input', function (e) {
            e.target.value = e.target.value.replace(/\D/g, '').replace(/(.{4})/g, '$1 ').trim();
        });
    }

    if (cardExpiry) {
        cardExpiry.addEventListener('input', function (e) {
            let val = e.target.value.replace(/\D/g, '');
            if (val.length >= 2) {
                e.target.value = val.slice(0, 2) + '/' + val.slice(2, 4);
            } else {
                e.target.value = val;
            }
        });
    }

    /* =========================================
       5. KHỞI CHẠY LẦN ĐẦU
       ========================================= */
    // Chạy ngay khi tải trang để tính toán đúng số liệu ban đầu
    updateOrderSummary();
    handlePaymentChange();
});