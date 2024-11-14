# 使用示例
from src.pdf_parser.table import find_first_table, get_table_summary

if __name__ == "__main__":
    pdf_path = "/Users/mark/Documents/Terminal evaluation report/1.10321_2024_ValTR_unep_gef_msp.pdf"
    start_page = 71
    
    table, found_page = find_first_table(pdf_path, start_page)
    
    if table:
        print("\n找到的第一个表格信息:")
        summary = get_table_summary(table)
        
        for key, value in summary.items():
            print(f"{key}: {value}")
            
        print("\n表格内容预览（前5行）:")
        for row in table.content[:5]:
            # 显示每个单元格的文本和是否加粗
            formatted_row = [
                f"{cell['text']}{'(粗体)' if cell['is_bold'] else ''}" 
                for cell in row
            ]
            print(formatted_row)
    else:
        print(f"从第 {start_page} 页开始未找到表格") 