// 工具链页面交互功能
document.addEventListener('DOMContentLoaded', function() {
    
    // 初始化工具链页面
    initToolchainPage();
    
    // 添加滚动动画
    initScrollAnimations();
    
    // 添加工具项交互
    initToolInteractions();
    
    // 添加响应式处理
    initResponsiveHandling();
});

// 初始化工具链页面
function initToolchainPage() {
    console.log('工具链页面初始化完成');
    
    // 添加页面加载动画
    const flowStages = document.querySelectorAll('.flow-stage');
    flowStages.forEach((stage, index) => {
        stage.style.opacity = '0';
        stage.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            stage.style.transition = 'all 0.6s ease';
            stage.style.opacity = '1';
            stage.style.transform = 'translateY(0)';
        }, index * 200);
    });
}

// 初始化滚动动画
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // 观察所有需要动画的元素
    const animatedElements = document.querySelectorAll('.flow-stage, .feature-card, .stat-card');
    animatedElements.forEach(el => {
        observer.observe(el);
    });
}

// 初始化工具项交互
function initToolInteractions() {
    const toolItems = document.querySelectorAll('.tool-item');
    
    toolItems.forEach(item => {
        // 添加悬停效果
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.02)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

// 初始化响应式处理
function initResponsiveHandling() {
    // 处理移动端的横向滚动
    const flowDiagram = document.querySelector('.flow-diagram');
    
    if (flowDiagram && window.innerWidth <= 1024) {
        // 在移动端启用平滑滚动
        flowDiagram.style.scrollBehavior = 'smooth';
    }
    
    // 处理窗口大小变化
    window.addEventListener('resize', () => {
        // 重新初始化响应式功能
        initResponsiveHandling();
    });
}

// 添加统计数字动画
function animateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
        const target = parseInt(stat.textContent);
        const duration = 2000; // 2秒动画
        const step = target / (duration / 16); // 60fps
        let current = 0;
        
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            stat.textContent = Math.floor(current);
        }, 16);
    });
}

// 页面完全加载后执行
window.addEventListener('load', function() {
    // 启动统计动画
    animateStats();
    
    console.log('工具链页面完全加载完成');
}); 