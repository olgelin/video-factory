// 追加 {anim_count} 个新入场动画（stagger:0.12s）
tl.from('.card', {{y:60, opacity:0, duration:0.7, ease:'power3.out'}}, '-=0.3');
tl.from('.stat', {{scale:2.5, opacity:0, duration:0.6, ease:'back.out(1.7)'}}, '-=0.4');
tl.from('.progress-bar', {{width:0, duration:0.8, ease:'power2.inOut'}}, '-=0.5');
tl.from('.tag', {{y:20, opacity:0, scale:0.8, duration:0.5, ease:'back.out(1.5)'}}, '-=0.3');
// 呼吸动画（追加在最后）
tl.to('.card', {{scale:1.02, duration:3, repeat:-1, yoyo:true, ease:'sine.inOut'}}, '+=0.5');
tl.to('.stat', {{textShadow:'0 0 50px rgba(108,140,255,0.8)', duration:2, repeat:-1, yoyo:true}}, '+=0');
