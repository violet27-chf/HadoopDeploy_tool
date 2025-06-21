/* 首页特定JS逻辑 */

// 服务器管理
let serverCount = 1;

/**
 * 添加新服务器表单
 */
function addServer() {
    serverCount++;
    const serverList = document.getElementById('serverList');
    const newServer = document.createElement('div');
    newServer.className = 'server-item mb-4 p-3 border rounded';
    newServer.innerHTML = `
        <h5>服务器 #${serverCount}</h5>
        <div class="mb-3">
            <label class="form-label">服务器地址</label>
            <input type="text" class="form-control" name="hostname[]" required>
        </div>
        <div class="mb-3">
            <label class="form-label">用户名</label>
            <input type="text" class="form-control" name="username[]" required>
        </div>
        <div class="mb-3">
            <label class="form-label">密码</label>
            <input type="password" class="form-control" name="password[]" required>
        </div>
        <button type="button" class="btn btn-sm btn-danger" onclick="removeServer(this)">
            <i class="bi bi-trash"></i> 移除
        </button>
    `;
    serverList.appendChild(newServer);
}

/**
 * 移除服务器表单
 * @param {HTMLElement} button - 点击的按钮元素
 */
function removeServer(button) {
    if (serverCount > 1) {
        button.closest('.server-item').remove();
        serverCount--;
        // 重新编号
        const items = document.querySelectorAll('.server-item');
        items.forEach((item, index) => {
            item.querySelector('h5').textContent = `服务器 #${index + 1}`;
        });
    }
}

// 表单提交处理
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('serverForm');
    const results = document.getElementById('results');
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            showLoading(results, '部署进行中，请稍候...');
            
            try {
                const formData = new FormData(form);
                const response = await fetch('/deploy', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`请求失败: ${response.status}`);
                }
                
                const result = await response.text();
                results.innerHTML = result;
            } catch (error) {
                showError(results, `部署失败: ${error.message}`);
            }
        });
    }
});