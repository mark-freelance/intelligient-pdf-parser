from format_text import format_text
from src.table_finder import TableFinder


def main():
    pdf_path = "/Users/mark/Documents/Terminal evaluation report/1.10321_2024_ValTR_unep_gef_msp.pdf"
    finder = TableFinder(pdf_path)
    
    try:
        # 打印文档信息
        print(f"PDF文档信息:")
        print(f"页数: {len(finder.doc)}")
        print(f"元数据: {finder.doc.metadata}")
        
        tables = finder.find_tables_with_context()
        
        print(f"找到 {len(tables)} 个表格:")
        for i, table in enumerate(tables, 1):
            print(f"\n表格 {i}:")
            print(f"页码范围: {table.start_page + 1} - {table.end_page + 1}")
            print(f"坐标: ({table.bbox[0]:.1f}, {table.bbox[1]:.1f}, {table.bbox[2]:.1f}, {table.bbox[3]:.1f})")
            print(f"前置文本: {format_text(table.preceding_text)}")
            if table.headers:
                print(f"表头: {', '.join(format_text(header) for header in table.headers)}")
            
    finally:
        finder.close()

if __name__ == "__main__":
    main() 