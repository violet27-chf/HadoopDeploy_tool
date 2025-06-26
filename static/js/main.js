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