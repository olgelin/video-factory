#!/usr/bin/env python3
"""
text_preprocessor.py - 文本预处理工具

解决TTS数字读法问题：
- 2000 → 两千
- 10000 → 一万
- 50% → 百分之五十
- 3.5% → 百分之三点五
"""

import re


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
            return str(num).replace("0", "零").replace("1", "一").replace("2", "二").replace("3", "三").replace("4", "四").replace("5", "五").replace("6", "六").replace("7", "七").replace("8", "八").replace("9", "九")
        elif num < 20:
            return "十" + (number_to_chinese(str(num - 10)) if num > 10 else "")
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


def preprocess_text_for_tts(text: str) -> str:
    """
    预处理文本，让TTS读得更自然
    
    处理：
    1. 数字转换（2000→两千）
    2. 百分比转换（50%→百分之五十）
    3. 标点优化（句号→逗号）
    """
    
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
    
    text = re.sub(r'(\d+(?:\.\d+)?)(亿|万千|百|[kKmMbB])', replace_number_with_unit, text)
    
    # 3. 年份：逐位读法（2026→二零二六）
    def replace_year(match):
        digits = match.group(1)
        digit_map = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
                     "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
        return "".join(digit_map.get(d, d) for d in digits) + "年"
    text = re.sub(r'(\d{4})年', replace_year, text)

    # 4. 纯数字
    def replace_number(match):
        num = match.group(0)
        return number_to_chinese(num)
    
    text = re.sub(r'\d+(?:\.\d+)?', replace_number, text)
    
    # 4. 标点优化
    text = text.replace("。", "，")  # 句号→逗号（避免生硬停顿）
    text = text.replace("！", "，")  # 感叹号→逗号
    text = text.replace("？，", "？")  # 保留问号
    
    # 5. 清理多余逗号
    text = re.sub(r'，+', '，', text)
    text = text.rstrip('，')
    
    return text


if __name__ == "__main__":
    # 测试
    test_cases = [
        "2024年销售额达到2000万",
        "用户数突破10000人",
        "增长率达到50%",
        "成本降低了3.5%",
        "项目预算为1.5亿",
        "团队规模从30人扩展到200人",
    ]
    
    for case in test_cases:
        result = preprocess_text_for_tts(case)
        print(f"原文: {case}")
        print(f"处理: {result}")
        print()
