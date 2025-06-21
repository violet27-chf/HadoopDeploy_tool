/* 公共工具函数 */

/**
 * 显示加载状态
 * @param {HTMLElement} element - 要显示加载状态的元素
 * @param {string} [text='处理中...'] - 加载文本
 */
function showLoading(element, text = '处理中...') {
    element.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">${text}</p>
        </div>
    `;
}

/**
 * 显示错误消息
 * @param {HTMLElement} element - 要显示错误的元素
 * @param {string} message - 错误消息
 */
function showError(element, message) {
    element.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle-fill"></i> ${message}
        </div>
    `;
}