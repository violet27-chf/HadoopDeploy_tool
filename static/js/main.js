// Three.js 极简品牌H模型主视觉区
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 420/420, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setClearColor(0xe3f2fd, 1);
renderer.setSize(420, 420);
document.getElementById('three-canvas').appendChild(renderer.domElement);

// 品牌蓝色材质
const hMaterial = new THREE.MeshPhysicalMaterial({
  color: 0x2196F3,
  metalness: 0.6,
  roughness: 0.18,
  clearcoat: 0.4
});

// H字母由3个立方体组合
const barWidth = 0.35, barHeight = 2.0, barDepth = 0.5;
const crossWidth = 1.0, crossHeight = 0.35, crossDepth = 0.5;

// 左竖
const leftBar = new THREE.Mesh(
  new THREE.BoxGeometry(barWidth, barHeight, barDepth), hMaterial
);
leftBar.position.set(-0.5, 0, 0);
scene.add(leftBar);

// 右竖
const rightBar = new THREE.Mesh(
  new THREE.BoxGeometry(barWidth, barHeight, barDepth), hMaterial
);
rightBar.position.set(0.5, 0, 0);
scene.add(rightBar);

// 横杠
const crossBar = new THREE.Mesh(
  new THREE.BoxGeometry(crossWidth, crossHeight, crossDepth), hMaterial
);
crossBar.position.set(0, 0, 0);
scene.add(crossBar);

// 光源
const light1 = new THREE.PointLight(0xffffff, 1.1, 100);
light1.position.set(10, 10, 10);
scene.add(light1);
const light2 = new THREE.PointLight(0xFFEB3B, 0.5, 100);
light2.position.set(-10, -10, 10);
scene.add(light2);
const ambient = new THREE.AmbientLight(0xffffff, 0.45);
scene.add(ambient);

camera.position.z = 5.5;

// 动画：整体缓慢旋转
function animate() {
  requestAnimationFrame(animate);
  scene.rotation.y += 0.012;
  scene.rotation.x = Math.sin(Date.now() * 0.0007) * 0.08;
  renderer.render(scene, camera);
}
animate();

// 导航栏移动端菜单交互
document.addEventListener('DOMContentLoaded', function() {
  const navbarToggle = document.querySelector('.navbar-toggle');
  const navbarMenu = document.querySelector('.navbar-menu');
  
  if (navbarToggle && navbarMenu) {
    navbarToggle.addEventListener('click', function() {
      navbarMenu.classList.toggle('active');
      
      // 添加汉堡菜单动画效果
      const spans = navbarToggle.querySelectorAll('span');
      spans.forEach((span, index) => {
        if (navbarMenu.classList.contains('active')) {
          if (index === 0) span.style.transform = 'rotate(45deg) translate(5px, 5px)';
          if (index === 1) span.style.opacity = '0';
          if (index === 2) span.style.transform = 'rotate(-45deg) translate(7px, -6px)';
        } else {
          span.style.transform = 'none';
          span.style.opacity = '1';
        }
      });
    });
    
    // 点击菜单项后关闭菜单
    const menuItems = navbarMenu.querySelectorAll('a');
    menuItems.forEach(item => {
      item.addEventListener('click', function() {
        navbarMenu.classList.remove('active');
        const spans = navbarToggle.querySelectorAll('span');
        spans.forEach(span => {
          span.style.transform = 'none';
          span.style.opacity = '1';
        });
      });
    });
    
    // 点击页面其他区域关闭菜单
    document.addEventListener('click', function(event) {
      if (!navbarToggle.contains(event.target) && !navbarMenu.contains(event.target)) {
        navbarMenu.classList.remove('active');
        const spans = navbarToggle.querySelectorAll('span');
        spans.forEach(span => {
          span.style.transform = 'none';
          span.style.opacity = '1';
        });
      }
    });
  }
  
  // 侧边栏显示控制
  const sidebarGuide = document.querySelector('.sidebar-guide');
  const deploymentComparison = document.querySelector('.deployment-comparison');
  
  // 在桌面端显示侧边栏
  function showSidebars() {
    if (window.innerWidth > 768) {
      if (sidebarGuide) sidebarGuide.style.display = 'block';
      if (deploymentComparison) deploymentComparison.style.display = 'block';
    } else {
      if (sidebarGuide) sidebarGuide.style.display = 'block';
      if (deploymentComparison) deploymentComparison.style.display = 'block';
    }
  }
  
  // 初始化显示
  showSidebars();
  
  // 窗口大小改变时重新显示
  window.addEventListener('resize', showSidebars);
  
  // 添加侧边栏显示/隐藏按钮（可选）
  const noticeLink = document.querySelector('.notice-link');
  if (noticeLink && sidebarGuide) {
    noticeLink.addEventListener('click', function(e) {
      // 延迟显示教程，让用户先访问链接
      setTimeout(() => {
        if (sidebarGuide.style.display === 'none') {
          sidebarGuide.style.display = 'block';
        }
      }, 1000);
    });
  }
  
  // 开发者工具检测和布局调整
  function adjustLayoutForDevTools() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    // 检测开发者工具是否打开（通过宽高比判断）
    const aspectRatio = width / height;
    const isDevToolsOpen = aspectRatio < 1.2 && width < 1200;
    
    // 调整侧边栏显示
    if (isDevToolsOpen) {
      if (width <= 900) {
        // 隐藏侧边栏避免重叠
        if (sidebarGuide) sidebarGuide.style.display = 'none';
        if (deploymentComparison) deploymentComparison.style.display = 'none';
      } else if (width <= 1000) {
        // 缩小侧边栏
        if (sidebarGuide) {
          sidebarGuide.style.display = 'block';
          sidebarGuide.style.width = '240px';
          sidebarGuide.style.left = '8px';
          sidebarGuide.style.maxHeight = '45vh';
        }
        if (deploymentComparison) {
          deploymentComparison.style.display = 'block';
          deploymentComparison.style.width = '240px';
          deploymentComparison.style.right = '8px';
          deploymentComparison.style.maxHeight = '45vh';
        }
      } else {
        // 正常显示但调整大小
        if (sidebarGuide) {
          sidebarGuide.style.display = 'block';
          sidebarGuide.style.width = '260px';
          sidebarGuide.style.left = '10px';
          sidebarGuide.style.maxHeight = '50vh';
        }
        if (deploymentComparison) {
          deploymentComparison.style.display = 'block';
          deploymentComparison.style.width = '260px';
          deploymentComparison.style.right = '10px';
          deploymentComparison.style.maxHeight = '50vh';
        }
      }
    } else {
      // 开发者工具关闭，恢复正常显示
      if (sidebarGuide) {
        sidebarGuide.style.display = 'block';
        sidebarGuide.style.width = '280px';
        sidebarGuide.style.left = '20px';
        sidebarGuide.style.maxHeight = '60vh';
      }
      if (deploymentComparison) {
        deploymentComparison.style.display = 'block';
        deploymentComparison.style.width = '280px';
        deploymentComparison.style.right = '20px';
        deploymentComparison.style.maxHeight = '60vh';
      }
    }
    
    // 防止水平滚动
    document.body.style.overflowX = 'hidden';
    document.documentElement.style.overflowX = 'hidden';
  }
  
  // 初始化布局调整
  adjustLayoutForDevTools();
  
  // 监听窗口大小变化
  let resizeTimeout;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(adjustLayoutForDevTools, 100);
  });
  
  // 监听开发者工具打开/关闭
  let devToolsCheck = setInterval(function() {
    const threshold = 160;
    const widthThreshold = window.outerWidth - window.innerWidth > threshold;
    const heightThreshold = window.outerHeight - window.innerHeight > threshold;
    
    if (widthThreshold || heightThreshold) {
      // 开发者工具打开
      adjustLayoutForDevTools();
    }
  }, 500);
  
  // 清理定时器
  window.addEventListener('beforeunload', function() {
    clearInterval(devToolsCheck);
  });
}); 