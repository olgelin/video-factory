"""
timeline.py — 字幕时间轴：读 whisperx 逐词数据 → 按场景切分 → 逐句按时间出现
"""
import json
from pathlib import Path
from typing import List, Dict


def load_transcript(path: str) -> list:
    """加载 whisperx transcript，返回 segments 列表"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("segments", [])


def split_by_scenes(segments: list, scenes: list) -> Dict[int, list]:
    """按场景时间轴切分 transcript 片段。
    
    scenes: storyboard 的 scenes 列表，每个有 duration 字段。
    返回: {scene_id: [segment, ...]}，segment 里的 start/end 已转为场景内相对时间。
    """
    t = 0.0  # 累计时间（视频时间轴）
    result = {}
    
    for i, scene in enumerate(scenes):
        sid = i + 1
        dur = scene.get("duration", 8.0)
        scene_start = t
        scene_end = t + dur
        
        # 找到落在这个场景内的片段
        scene_segs = []
        for seg in segments:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            # 片段中间点落在场景内
            seg_mid = (seg_start + seg_end) / 2
            if scene_start <= seg_mid < scene_end:
                # 复制并转为场景相对时间
                rel_seg = dict(seg)
                rel_seg["start"] = seg_start - scene_start
                rel_seg["end"] = seg_end - scene_start
                scene_segs.append(rel_seg)
        
        result[sid] = scene_segs
        t = scene_end
    
    return result


def build_captions(sid: int, scene_segs: list, dur: float) -> str:
    """为一个场景生成逐句出现的字幕 HTML + GSAP 动画。
    
    每句字幕在它的时间点淡入，下一句开始时淡出。
    最后一句在场景结束前一直显示。
    所有字幕叠加在同一位置，通过 opacity 切换。
    """
    if not scene_segs:
        return "", ""
    
    html_parts = []
    anim_lines = []
    
    # 容器
    html_parts.append(
        f'<div id="s{sid}-captions" style="position:absolute;bottom:50px;left:120px;right:120px;'
        f'z-index:500;text-align:center;pointer-events:none;">'
    )
    
    for i, seg in enumerate(scene_segs):
        text = seg.get("text", "")
        t_start = seg.get("start", 0)
        t_end = seg.get("end", 0)
        
        # 每个句子一个绝对定位的层，叠加在同一位置
        html_parts.append(
            f'<div id="s{sid}-cap{i}" style="position:absolute;bottom:0;left:0;right:0;'
            f'background:rgba(0,0,0,0.75);border-top:2px solid var(--color-accent-dim);'
            f'padding:14px 28px;border-radius:8px 8px 0 0;opacity:0;">'
            f'<span style="font-size:26px;font-weight:500;color:var(--color-fg);'
            f'line-height:1.4;text-shadow:0 1px 3px rgba(0,0,0,0.8);">{text}</span>'
            f'</div>'
        )
        
        # GSAP: 在开始时间淡入
        anim_lines.append(
            f'gsap.set("#s{sid}-cap{i}",{{opacity:0}});'
        )
        anim_lines.append(
            f'tl.to("#s{sid}-cap{i}",{{opacity:1,duration:0.3,ease:"power2.out"}},{t_start:.2f});'
        )
        
        # 如果不是最后一句，在下一句开始时淡出
        if i < len(scene_segs) - 1:
            next_start = scene_segs[i + 1].get("start", 0)
            anim_lines.append(
                f'tl.to("#s{sid}-cap{i}",{{opacity:0,duration:0.2,ease:"power2.in"}},{next_start:.2f});'
            )
        else:
            # 最后一句在场景结束前 0.5 秒淡出
            fade_out = max(t_end + 0.5, dur - 0.5)
            anim_lines.append(
                f'tl.to("#s{sid}-cap{i}",{{opacity:0,duration:0.3,ease:"power2.in"}},{fade_out:.2f});'
            )
    
    html_parts.append('</div>')
    
    return "\n".join(html_parts), "\n".join(anim_lines)


class CaptionTimeline:
    """完整的字幕时间轴：加载 transcript → 切分 → 按场景生成 HTML"""
    
    def __init__(self, transcript_path: str = None, storyboard_path: str = None):
        self.segments = []
        self.scenes = []
        self._scene_segs = {}  # {sid: [segment, ...]}
        
        if transcript_path and Path(transcript_path).exists():
            self.segments = load_transcript(transcript_path)
        
        if storyboard_path and Path(storyboard_path).exists():
            with open(storyboard_path, encoding="utf-8") as f:
                sb = json.load(f)
            self.scenes = sb if isinstance(sb, list) else sb.get("scenes", [])
        
        if self.segments and self.scenes:
            self._scene_segs = split_by_scenes(self.segments, self.scenes)
    
    def get_for_scene(self, sid: int) -> list:
        """获取某个场景的 transcript 片段"""
        return self._scene_segs.get(sid, [])
    
    def build_for_scene(self, sid: int, dur: float) -> tuple:
        """为一个场景生成字幕 HTML 和 GSAP 动画"""
        segs = self.get_for_scene(sid)
        return build_captions(sid, segs, dur)


# 全局实例（在 impl.py 中初始化一次，各场景复用）
_timeline = None

def init(transcript_path: str, storyboard_path: str):
    global _timeline
    _timeline = CaptionTimeline(transcript_path, storyboard_path)

def for_scene(sid: int, dur: float) -> tuple:
    if _timeline is None:
        return "", ""
    return _timeline.build_for_scene(sid, dur)
