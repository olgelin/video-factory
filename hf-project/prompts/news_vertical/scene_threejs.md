## 🎮 Three.js 3D 技法（🔴 隐喻图时代：禁止全屏背景）

⚠️ **硬性禁令（最高优先级，违反 = 画面报废）**：所有管线（vox/news/news_vertical）都已用隐喻图（Qwen 生图）或纯色背景做背景层，**禁止生成任何 Three.js 全屏背景 canvas**（粒子场/星空/代码雨/银河/扫光）。

原因：全屏 canvas 是 `z-index:1`，会盖住 `z-index:0` 的隐喻图，穿插式的「图段」就废了——这是 H3 回退时踩过的 z-index 冲突坑（bg3d z-index:1 盖背景 z-index:0）。

Three.js 只可用于「信息卡内的局部 3D 装饰」，且必须满足**全部**条件：
- canvas 放在 `#content` 容器内（作为信息卡的一部分，不是全屏背景）
- `z-index ≥ 2`（在信息卡之上）
- canvas 是卡片的**局部小区域**（如 300×300 的小仪表盘 / 3D 图标），**禁止 `inset:0` 全屏铺**

🔴 **Three.js 加载铁律（违反 = 渲染卡死）**：框架已内联 `three.min.js`（全局 `THREE` 对象）。**禁止 `<script type="importmap">`、禁止 `<script type="module">`、禁止 `import * as THREE from "three"`**——module 异步执行，HyperFrames 截图时 WebGL 还没跑完，会导致渲染卡死。直接写普通 `<script>`，用全局 `THREE` 即可。

### 局部 3D 装饰示例（信息卡内，非全屏）

```html
<!-- #content 容器承载信息卡（z-index≥2，叠加在隐喻图之上） -->
<div id="content" style="position:absolute;inset:0;z-index:5;">
  <div style="/* 信息卡样式 */">
    <div class="title">数据仪表盘</div>
    <!-- 卡内局部 3D 小元素（小 canvas，z-index≥2，非全屏） -->
    <canvas id="gauge3d" style="width:300px;height:300px;position:relative;z-index:2;pointer-events:none;"></canvas>
  </div>
</div>
<script>
const c=document.getElementById("gauge3d"), r=new THREE.WebGLRenderer({canvas:c,alpha:true});
r.setSize(300,300,false); r.setPixelRatio(1);
const s=new THREE.Scene(), cam=new THREE.PerspectiveCamera(45,1,0.1,50);
cam.position.set(0,0,8);
// ... 卡内局部 3D 元素（小尺寸，旋转/呼吸）...
function renderAt(t){ /* 更新 + 渲染 */ r.render(s,cam); }
window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
renderAt(window.__hfThreeTime||0);
</script>
```

⚠️ **记住**：隐喻图是「会呼吸的锚点画面」（z-index:0），信息卡（z-index≥2）是叠加在上面的内容层。Three.js 只能作为信息卡内的局部点缀，**绝不能整屏铺在隐喻图之上**。

**若场景不需要卡内 3D 装饰，就完全不用 Three.js**——纯 HTML/CSS/GSAP 信息卡完全够用，不要为了"用"而硬塞一个全屏 canvas。
