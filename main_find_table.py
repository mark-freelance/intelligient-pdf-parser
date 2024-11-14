# 使用示例
from src.table_finder import find_first_table, get_table_summary


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
            print(row)
    else:
        print(f"从第 {start_page} 页开始未找到表格") 