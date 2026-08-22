## 🎮 Three.js 3D 技法（每场景必选 1 个）

HyperFrames 通过 Puppeteer+Chromium 渲染，原生支持 WebGL/Three.js。以下模式经过验证，直接复制骨架即可。Three.js 代码放在场景 div 内。

🔴 **Three.js 加载铁律（违反=渲染卡死）**：框架已内联 `three.min.js`（全局 `THREE` 对象）。**禁止写 `<script type="importmap">`、禁止 `<script type="module">`、禁止 `import * as THREE from "three"`**——module 异步执行，HyperFrames 截图时 WebGL 还没跑完，会导致渲染卡死。直接写普通 `<script>`，用全局 `THREE` 即可。

### 1. GPU 粒子场 — 氛围首选

3000 粒子 + 双色渐变 + AdditiveBlending：

```html
<canvas id="particles3d" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("particles3d"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1080,1920,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(60,1080/1920,0.1,50);
cam.position.z=10;
const COUNT=3000, pos=new Float32Array(COUNT*3), col=new Float32Array(COUNT*3);
const C1=new THREE.Color("#6C8CFF"), C2=new THREE.Color("#A855F7"); // 根据 mood 换色
for(let i=0;i<COUNT;i++){pos[i*3]=(Math.random()-0.5)*16;pos[i*3+1]=(Math.random()-0.5)*12;pos[i*3+2]=(Math.random()-0.5)*6;const t=Math.random(),cc=C1.clone().lerp(C2,t);col[i*3]=cc.r;col[i*3+1]=cc.g;col[i*3+2]=cc.b;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));g.setAttribute("color",new THREE.BufferAttribute(col,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.04,vertexColors:true,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.7}));
s.add(pts);
function renderAt(t){pts.rotation.y=t*0.15;pts.rotation.x=Math.sin(t*0.3)*0.08;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 2. 发光粒子（辉光替代）⭐

本地渲染**不支持 Bloom addons**（EffectComposer 需要 module import，会卡死渲染）。用「大 size + AdditiveBlending + 多层叠加」模拟电影级辉光：

```html
<canvas id="bg3d" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("bg3d"), r=new THREE.WebGLRenderer({canvas:c,alpha:true,antialias:true});
r.setSize(1080,1920,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(35,1080/1920,0.1,100);
cam.position.set(0,0,8);
// 三层粒子模拟辉光：外层大光晕(size 0.5 低opacity) + 中层(size 0.15) + 核心层(size 0.05 高opacity)
// ...粒子代码（同#1，用 2-3 个 Points 叠加模拟 bloom 光晕）...
function renderAt(t){ /* 粒子旋转 */ r.render(s,cam); }
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 3. 代码雨（Code Rain）— 赛博空间

垂直坠落粒子，AdditiveBlending，颜色根据 mood：

```html
<canvas id="coderain" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("coderain"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1080,1920,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(50,1080/1920,0.1,30);
cam.position.z=10;
const COLS=60, ROWS=40, COUNT=COLS*ROWS;
const pos=new Float32Array(COUNT*3), spd=new Float32Array(COUNT);
for(let i=0;i<COUNT;i++){
  const col=i%COLS, row=Math.floor(i/COLS);
  pos[i*3]=(col-COLS/2)*0.3; pos[i*3+1]=(row-ROWS/2)*0.4+Math.random()*8; pos[i*3+2]=(Math.random()-0.5)*3;
  spd[i]=0.02+Math.random()*0.08;
}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.08,color:0x00FF88,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.8}));
s.add(pts);
function renderAt(t){
  const p=pts.geometry.attributes.position.array;
  for(let i=0;i<COUNT;i++){p[i*3+1]-=spd[i];if(p[i*3+1]<-6)p[i*3+1]=6+Math.random()*2;}
  pts.geometry.attributes.position.needsUpdate=true;
  r.render(s,cam);
}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 4. 星空（Starfield）— 深空史诗

2000 星点 + 慢旋 + 闪烁，适合宏大氛围：

```html
<canvas id="stars" style="position:absolute;inset:0;z-index:0;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("stars"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1080,1920,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(45,1080/1920,0.1,50);
cam.position.set(0,0,12);
const COUNT=2000, pos=new Float32Array(COUNT*3);
for(let i=0;i<COUNT;i++){const theta=Math.random()*Math.PI*2, phi=Math.acos(2*Math.random()-1), r2=4+Math.random()*6;pos[i*3]=Math.sin(phi)*Math.cos(theta)*r2;pos[i*3+1]=Math.sin(phi)*Math.sin(theta)*r2;pos[i*3+2]=Math.cos(phi)*r2;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));
const mat=new THREE.PointsMaterial({size:0.06,color:0x8899CC,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.9,sizeAttenuation:true});
const stars=new THREE.Points(g,mat); s.add(stars);
function renderAt(t){stars.rotation.y=t*0.08;mat.opacity=0.75+Math.sin(t*1.5)*0.15;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 5. 银河漩涡（Galaxy Spiral）— 宇宙史诗

4臂螺旋 + 暖金→冷蓝渐变：

```html
<canvas id="galaxy" style="position:absolute;inset:0;z-index:0;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("galaxy"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1080,1920,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(45,1080/1920,0.1,50);
cam.position.set(0,3,10); cam.lookAt(0,0,0);
const COUNT=4000, pos=new Float32Array(COUNT*3), col=new Float32Array(COUNT*3);
const ARMS=4, CORE=new THREE.Color("#FFD700"), EDGE=new THREE.Color("#4488FF");
for(let i=0;i<COUNT;i++){const r=Math.random()*5, armAngle=(i%ARMS)/ARMS*Math.PI*2, spiral=r*2.5+armAngle, scatter=(Math.random()-0.5)*r*0.4;pos[i*3]=Math.cos(spiral)*r+scatter;pos[i*3+1]=(Math.random()-0.5)*r*0.3;pos[i*3+2]=Math.sin(spiral)*r+scatter;const t=r/5,cc=CORE.clone().lerp(EDGE,t);col[i*3]=cc.r;col[i*3+1]=cc.g;col[i*3+2]=cc.b;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));g.setAttribute("color",new THREE.BufferAttribute(col,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.05,vertexColors:true,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.85,sizeAttenuation:true}));
s.add(pts);
function renderAt(t){pts.rotation.y=t*0.1;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

| 场景 | 推荐技法 | 粒子颜色建议 |
|------|---------|------------|
| quote_hero | 星空+Bloom 或 银河+Bloom | 根据 mood |
| data_impact | 代码雨+Bloom | 数据=绿、警告=红 |
| compare | 粒子场（左右双色） | 左冷右暖 |
| flow | 粒子场+Bloom | 蓝紫渐变 |
| list_alert | 代码雨 | 红/橙 |
| timeline_event | 星空 或 银河 | 冷色为主 |
| hud | 代码雨 或 银河 | 根据 mood |

⚠️ 每个场景选不同技法，不连续重复。#1+#2 是最常用组合。

## 🔥 Three.js 灵动感注入（每场景三选一，禁止全用"旋转"）

下面 3 种行为模式必须选 1 个改造模板。不要只是套骨架旋转——要让它"有生命"。

### A. 变速呼吸 — 节奏跟随内容
粒子/星系不匀速旋转，而是：
- 0-2s 缓慢（0.03 rad/s），2-5s 加速到 0.2 rad/s（高潮），5s 后减速回落
- 透明度跟随节奏：`opacity = 0.4 + sin(t*π/高潮时长) * 0.3`
- 粒子大小随呼吸缩放：`size = baseSize * (0.7 + sin(t*2)*0.3)`
- 颜色随节奏冷暖切换：从冷色 lerp 到暖色再回来

### B. 交互响应 — 粒子与内容对话
粒子不是背景装饰，而是：
- 向中心标题聚拢（`position.lerp(targetPos, 0.02)`）+ 间歇性炸开（`position += randomDir * burst`）
- 扫光线穿过时粒子跟随闪亮（检测光线位置，距离 < 200px 的粒子 opacity=1.0，远离=0.3）
- 数字弹入时周围粒子短暂加速（`speed *= 3` for 0.5s then decay）
- 不同高度层的粒子运动方向相反（近层上浮、中层下沉、远层横移 → 视差漩涡）

### C. 叙事粒子 — 粒子形态承载含义
根据话题情绪改变粒子形态：
- 泡沫破裂 → 粒子从聚集态爆炸散开（初始 radius<1 密集，随时间 radius *= 1.1 + t*0.5 扩散）
- 数据冲击 → 粒子排列成柱状图/折线，然后散开重组
- 崩塌/恐慌 → 粒子从有序网格开始，逐步加入随机抖动，最终失序
- 希望/重建 → 粒子从混沌中逐步排列成几何图形（圆形/方形）

选 A 保持灵动，选 B 制造互动感，选 C 赋予叙事深度。禁止全用默认旋转。
