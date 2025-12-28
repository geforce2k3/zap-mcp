"""
文字格式化服務
"""
import re
from typing import Dict


def clean_html(raw_html: str) -> str:
    """
    清除 HTML 標籤

    Args:
        raw_html: 含有 HTML 標籤的文字

    Returns:
        str: 清除標籤後的純文字
    """
    if raw_html is None:
        return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).strip()


def parse_ai_response(text: str) -> Dict[str, str]:
    """
    解析 AI 回應，分類為弱點說明、解決方法、參考資料

    Args:
        text: AI 生成的文字

    Returns:
        dict: 包含 explanation, solution, reference 的字典
    """
    sections = {'explanation': '', 'solution': '', 'reference': ''}
    current_section = None
    buffer = []
    lines = str(text).split('\n')

    # 標題識別正則表達式
    header_regex = re.compile(
        r'^(#+\s*|\*\*)?(弱點說明|修復建議|解決方法|參考資料|Explanation|Solution|Reference)([:：])?(\*\*)?\s*$'
    )

    for line in lines:
        stripped = line.strip()
        match = header_regex.match(stripped)

        if match:
            # 儲存前一個區塊
            if current_section and buffer:
                sections[current_section] = '\n'.join(buffer).strip()

            # 判斷新區塊類型
            header_text = match.group(2)
            if '弱點說明' in header_text or 'Explanation' in header_text:
                current_section = 'explanation'
            elif '解決方法' in header_text or '修復建議' in header_text or 'Solution' in header_text:
                current_section = 'solution'
            elif '參考資料' in header_text or 'Reference' in header_text:
                current_section = 'reference'

            buffer = []
            continue

        if current_section:
            buffer.append(line)
        else:
            # 若尚未識別到區塊，預設為 explanation
            if stripped and not sections['explanation']:
                current_section = 'explanation'
                buffer.append(line)

    # 儲存最後一個區塊
    if current_section and buffer:
        sections[current_section] = '\n'.join(buffer).strip()

    # 若完全無法解析，將所有內容放入 solution
    if not any(sections.values()):
        return {'solution': str(text)}

    return sections
