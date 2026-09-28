## 🎮 Three.js 3D 技法（隐喻图 + 半透明粒子氛围层共存）

隐喻图（class="metaphor-bg"）是 z-index:0 的锚点画面（框架已注入）。你**可以**用 Three.js 粒子/星空/代码雨/银河做「半透明氛围层」叠在图上，让画面有持续动感——但**绝不能做实底全屏背景盖住隐喻图**。

### 🔴 层级铁律（照抄，不许改）

```
z-index:0  隐喻图 metaphor-bg（框架注入，锚点画面）
z-index:1  粒子氛围层 canvas（你写的，半透明，飘在图上）
z-index:2  暗化层 #metaphor-dim（框架注入，信息卡进来时压暗图+粒子）
z-index:3  信息卡 #content（你的内容容器）
```

你的粒子 canvas 固定 `z-index:1`，信息卡 `#content` 固定 `z-index:3`。

### 🔴 半透明铁律（违反 = 隐喻图被盖死，画面报废）

粒子氛围层必须满足**全部**条件：
- `<canvas>` 用 `alpha:true`（`new THREE.WebGLRenderer({canvas:c, alpha:true})`）
- 粒子材质 `transparent:true` + `depthWrite:false`
- 材质 `opacity:0.3~0.5`（半透明，隐喻图透出来）
- **禁止**实底 canvas（不透明背景色 / 不设 alpha / opacity≥0.8），否则把隐喻图整个盖死——这是 H3 回退踩过的 z-index 坑（bg3d z-index:1 实底盖背景 z-index:0）。

粒子是「氛围」，隐喻图是「主体」——粒子永远让隐喻图透出来。

### 🔴 Three.js 加载铁律（违反 = 渲染卡死）

框架已内联 `three.min.js`（全局 `THREE` 对象）。**禁止 `<script type="importmap">`、禁止 `<script type="module">`、禁止 `import * as THREE from "three"`**——module 异步执行，HyperFrames 截图时 WebGL 还没跑完，导致渲染卡死。直接写普通 `<script>`，用全局 `THREE`。

---

### 1. 半透明粒子场 — 氛围首选 ⭐

3000 粒子 + 双色渐变 + AdditiveBlending，半透明飘在隐喻图上：

```html
<canvas id="particles3d" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("particles3d"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1920,1080,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(60,1920/1080,0.1,50);
cam.position.z=10;
const COUNT=3000, pos=new Float32Array(COUNT*3), col=new Float32Array(COUNT*3);
const C1=new THREE.Color("#6C8CFF"), C2=new THREE.Color("#A855F7"); // 根据 mood 换色
for(let i=0;i<COUNT;i++){pos[i*3]=(Math.random()-0.5)*16;pos[i*3+1]=(Math.random()-0.5)*12;pos[i*3+2]=(Math.random()-0.5)*6;const t=Math.random(),cc=C1.clone().lerp(C2,t);col[i*3]=cc.r;col[i*3+1]=cc.g;col[i*3+2]=cc.b;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));g.setAttribute("color",new THREE.BufferAttribute(col,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.04,vertexColors:true,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.4})); // opacity 0.3~0.5
s.add(pts);
function renderAt(t){pts.rotation.y=t*0.15;pts.rotation.x=Math.sin(t*0.3)*0.08;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 2. 星空 — 深空史诗

2000 星点 + 慢旋 + 闪烁，半透明：

```html
<canvas id="stars" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("stars"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1920,1080,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(45,1920/1080,0.1,50);
cam.position.set(0,0,12);
const COUNT=2000, pos=new Float32Array(COUNT*3);
for(let i=0;i<COUNT;i++){const theta=Math.random()*Math.PI*2, phi=Math.acos(2*Math.random()-1), r2=4+Math.random()*6;pos[i*3]=Math.sin(phi)*Math.cos(theta)*r2;pos[i*3+1]=Math.sin(phi)*Math.sin(theta)*r2;pos[i*3+2]=Math.cos(phi)*r2;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));
const mat=new THREE.PointsMaterial({size:0.06,color:0x8899CC,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.45,sizeAttenuation:true});
const stars=new THREE.Points(g,mat); s.add(stars);
function renderAt(t){stars.rotation.y=t*0.08;mat.opacity=0.35+Math.sin(t*1.5)*0.1;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 3. 代码雨 — 赛博空间

垂直坠落粒子，半透明：

```html
<canvas id="coderain" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("coderain"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1920,1080,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(50,1920/1080,0.1,30);
cam.position.z=10;
const COLS=60, ROWS=40, COUNT=COLS*ROWS;
const pos=new Float32Array(COUNT*3), spd=new Float32Array(COUNT);
for(let i=0;i<COUNT;i++){const col=i%COLS, row=Math.floor(i/COLS);pos[i*3]=(col-COLS/2)*0.3; pos[i*3+1]=(row-ROWS/2)*0.4+Math.random()*8; pos[i*3+2]=(Math.random()-0.5)*3; spd[i]=0.02+Math.random()*0.08;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.08,color:0x00FF88,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.35}));
s.add(pts);
function renderAt(t){const p=pts.geometry.attributes.position.array;for(let i=0;i<COUNT;i++){p[i*3+1]-=spd[i];if(p[i*3+1]<-6)p[i*3+1]=6+Math.random()*2;}pts.geometry.attributes.position.needsUpdate=true;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

### 4. 银河漩涡 — 宇宙史诗

4 臂螺旋 + 暖金→冷蓝渐变，半透明：

```html
<canvas id="galaxy" style="position:absolute;inset:0;z-index:1;pointer-events:none;"></canvas>
<script>
const c=document.getElementById("galaxy"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(1920,1080,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(45,1920/1080,0.1,50);
cam.position.set(0,3,10); cam.lookAt(0,0,0);
const COUNT=4000, pos=new Float32Array(COUNT*3), col=new Float32Array(COUNT*3);
const ARMS=4, CORE=new THREE.Color("#FFD700"), EDGE=new THREE.Color("#4488FF");
for(let i=0;i<COUNT;i++){const r=Math.random()*5, armAngle=(i%ARMS)/ARMS*Math.PI*2, spiral=r*2.5+armAngle, scatter=(Math.random()-0.5)*r*0.4;pos[i*3]=Math.cos(spiral)*r+scatter;pos[i*3+1]=(Math.random()-0.5)*r*0.3;pos[i*3+2]=Math.sin(spiral)*r+scatter;const t=r/5,cc=CORE.clone().lerp(EDGE,t);col[i*3]=cc.r;col[i*3+1]=cc.g;col[i*3+2]=cc.b;}
const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));g.setAttribute("color",new THREE.BufferAttribute(col,3));
const pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.05,vertexColors:true,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0.4,sizeAttenuation:true}));
s.add(pts);
function renderAt(t){pts.rotation.y=t*0.1;r.render(s,cam);}
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

| 场景 | 推荐技法 | 粒子颜色建议 |
|------|---------|------------|
| quote_hero | 星空 或 银河 | 根据 mood |
| data_impact | 代码雨 或 粒子场 | 数据=绿、警告=红 |
| compare | 粒子场（左右双色） | 左冷右暖 |
| flow | 粒子场 | 蓝紫渐变 |
| list_alert | 代码雨 或 粒子场 | 红/橙 |
| timeline_event | 星空 或 粒子场 | 冷色为主 |
| hud | 代码雨 或 银河 | 根据 mood |

⚠️ 每个场景选不同技法，不连续重复。粒子颜色呼应话题情绪（冷静蓝青 / 冲突红金 / 压迫紫暗 / 希望金白）。

### 卡内局部 3D 装饰（可选加分）

除了半透明氛围层，还可在信息卡内放小型 3D 元素（300×300 仪表盘/3D 图标），`z-index≥3`、放 `#content` 容器内。**若场景不需要，就只用半透明氛围层 + 纯 CSS 卡，别硬塞。**
