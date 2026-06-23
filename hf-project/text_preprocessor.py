#!/usr/bin/env python3
"""
text_preprocessor.py - 文本预处理工具 v2

解决TTS数字读法问题：
- 2000 → 两千
- 10000 → 一万
- 50% → 百分之五十
- 3.5% → 百分之三点五
- 一六万 → 十六万（中文数字序列修正）
- 一二九零万 → 一千二百九十万

核心问题：LLM生成文案时经常把数字写成中文逐位形式（"一六万"），
但TTS模型会按字读（"一-六-万"），需要转成正确读法（"十六万"）。
"""

import re


# 中文数字映射
DIGIT_MAP = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
DIGIT_MAP_REVERSE = {0: "零", 1: "一", 2: "二", 3: "三", 4: "四",
                     5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}


def number_to_chinese(num_str: str) -> str:
    """将数字字符串转换为中文读法"""
    try:
        num = float(num_str)
        if num == int(num):
            num = int(num)
    except ValueError:
        return num_str

    # 特殊处理
    if isinstance(num, int):
        if num == 0:
            return "零"
        elif num < 0:
            return "负" + number_to_chinese(str(-num))
        elif num < 10:
            return DIGIT_MAP_REVERSE.get(num, str(num))
        elif num < 20:
            return "十" + (DIGIT_MAP_REVERSE.get(num - 10, "") if num > 10 else "")
        elif num < 100:
            shi = num // 10
            ge = num % 10
            return number_to_chinese(str(shi)) + "十" + (number_to_chinese(str(ge)) if ge > 0 else "")
        elif num < 1000:
            bai = num // 100
            shi = (num % 100) // 10
            ge = num % 10
            result = number_to_chinese(str(bai)) + "百"
            if shi > 0:
                result += number_to_chinese(str(shi)) + "十"
            elif ge > 0:
                result += "零"
            if ge > 0:
                result += number_to_chinese(str(ge))
            return result
        elif num < 10000:
            qian = num // 1000
            bai = (num % 1000) // 100
            shi = (num % 100) // 10
            ge = num % 10
            result = number_to_chinese(str(qian)) + "千"
            if bai > 0:
                result += number_to_chinese(str(bai)) + "百"
            elif shi > 0 or ge > 0:
                result += "零"
            if shi > 0:
                result += number_to_chinese(str(shi)) + "十"
            elif ge > 0:
                result += "零"
            if ge > 0:
                result += number_to_chinese(str(ge))
            return result
        elif num < 100000000:
            wan = num // 10000
            qian = (num % 10000) // 1000
            bai = (num % 1000) // 100
            shi = (num % 100) // 10
            ge = num % 10
            result = number_to_chinese(str(wan)) + "万"
            if qian > 0:
                result += number_to_chinese(str(qian)) + "千"
            elif bai > 0 or shi > 0 or ge > 0:
                result += "零"
            if bai > 0:
                result += number_to_chinese(str(bai)) + "百"
            elif shi > 0 or ge > 0:
                result += "零"
            if shi > 0:
                result += number_to_chinese(str(shi)) + "十"
            elif ge > 0:
                result += "零"
            if ge > 0:
                result += number_to_chinese(str(ge))
            return result
        else:
            return str(num)  # 太大的数字直接返回
    else:
        # 浮点数
        int_part = int(num)
        dec_part = num - int_part
        if dec_part == 0:
            return number_to_chinese(str(int_part))
        else:
            # 保留一位小数
            dec_str = f"{dec_part:.1f}"[2:]  # 去掉"0."
            return number_to_chinese(str(int_part)) + "点" + number_to_chinese(dec_str)


def chinese_digits_to_number(digit_str: str) -> int:
    """将中文数字序列转为整数。如 '一二九零' → 1290, '一六' → 16"""
    result = 0
    for ch in digit_str:
        if ch in DIGIT_MAP:
            result = result * 10 + DIGIT_MAP[ch]
        else:
            return -1  # 非数字字符
    return result


def fix_chinese_number_sequences(text: str) -> str:
    """
    修正LLM生成的错误中文数字序列。
    
    问题：LLM经常把"16万"写成"一六万"，"1290万"写成"一二九零万"。
    TTS会按字读成"一-六-万"而不是"十六万"。
    
    策略：检测"中文数字字符+单位"的模式，转成正确的中文读法。
    """
    # 中文数字字符集
    cn_digits = "零一二三四五六七八九"
    # 单位
    units = "万亿"
    
    # 模式：2-8个中文数字字符 + 单位（万/亿）
    # 排除已经是正确读法的（如"十六万"中的"十"不在数字字符集中）
    pattern = f'([{cn_digits}]{{2,8}})([{units}])'
    
    def replace_sequence(match):
        digit_chars = match.group(1)
        unit = match.group(2)
        
        # 转成数字
        num = chinese_digits_to_number(digit_chars)
        if num < 0:
            return match.group(0)  # 转换失败，保持原样
        
        # 转成正确中文读法
        chinese_num = number_to_chinese(str(num))
        return chinese_num + unit
    
    text = re.sub(pattern, replace_sequence, text)
    
    # 也处理没有单位的纯中文数字序列（4位以上，如"二零二六"年份除外）
    # 这个比较危险，只处理明确的场景
    # 比如"一七六五万"已经被上面处理了
    
    return text


def preprocess_text_for_tts(text: str) -> str:
    """
    预处理文本，让TTS读得更自然

    处理：
    0. 中文数字序列修正（一六万→十六万）
    1. 数字转换（2000→两千）
    2. 百分比转换（50%→百分之五十）
    3. 标点优化（句号→逗号）
    """

    # 0. 先修正LLM生成的错误中文数字序列
    text = fix_chinese_number_sequences(text)

    # 1. 百分比处理
    def replace_percent(match):
        num = match.group(1)
        return "百分之" + number_to_chinese(num)

    text = re.sub(r'(\d+(?:\.\d+)?)%', replace_percent, text)

    # 2. 带单位的数字
    def replace_number_with_unit(match):
        num = match.group(1)
        unit = match.group(2)
        unit_map = {
            "亿": "亿",
            "万": "万",
            "千": "千",
            "百": "百",
            "k": "千",
            "K": "千",
            "m": "百万",
            "M": "百万",
            "b": "十亿",
            "B": "十亿",
        }
        if unit in unit_map:
            return number_to_chinese(num) + unit_map[unit]
        return number_to_chinese(num) + unit

    text = re.sub(r'(\d+(?:\.\d+)?)(亿|万|千|百|[kKmMbB])', replace_number_with_unit, text)

    # 3. 年份：逐位读法（2026→二零二六）
    def replace_year(match):
        digits = match.group(1)
        return "".join(DIGIT_MAP_REVERSE.get(int(d), d) for d in digits) + "年"
    text = re.sub(r'(\d{4})年', replace_year, text)

    # 4. 纯数字
    def replace_number(match):
        num = match.group(0)
        return number_to_chinese(num)

    text = re.sub(r'\d+(?:\.\d+)?', replace_number, text)

    # 5. 标点优化
    text = text.replace("。", "，")  # 句号→逗号（避免生硬停顿）
    text = text.replace("！", "，")  # 感叹号→逗号
    text = text.replace("？，", "？")  # 保留问号

    # 6. 清理多余逗号
    text = re.sub(r'，+', '，', text)
    text = text.rstrip('，')

    return text


if __name__ == "__main__":
    # 测试
    test_cases = [
        # LLM生成的错误中文数字序列
        "花一六万买了辆路虎，购置税要交三二万",
        "今年高考考生一二九零万，全网热度值冲到一七六五万",
        "热度值冲到一一七九万",
        # 阿拉伯数字
        "花16万买了辆路虎，购置税要交32万",
        "今年高考考生1290万人",
        "2024年销售额达到2000万",
        "用户数突破10000人",
        "增长率达到50%",
        "成本降低了3.5%",
        "项目预算为1.5亿",
        # 已经正确的中文数字
        "花十六万买了辆路虎",
        "一千二百九十万考生",
    ]

    for case in test_cases:
        result = preprocess_text_for_tts(case)
        changed = "✅" if result != case else "—"
        print(f"{changed} 原文: {case}")
        if result != case:
            print(f"   处理: {result}")
        print()
