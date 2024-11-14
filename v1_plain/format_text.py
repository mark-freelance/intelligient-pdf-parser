def format_text(text: str) -> str:
    """格式化文本，将换行符转换为\n"""
    if not text:
        return ""
    return text.replace('\r', '').replace('\n', '\\n')
