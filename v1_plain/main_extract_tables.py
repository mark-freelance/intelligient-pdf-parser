import sys
from v1_plain.src import TableFinder

def main():
    if len(sys.argv) != 2:
        print("Usage: python main_extract_tables.py <pdf_path>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    finder = TableFinder(pdf_path)
    
    try:
        tables = finder.find_tables_with_context()
        
        print(f"找到 {len(tables)} 个表格:")
        for i, table in enumerate(tables, 1):
            print(f"\n表格 {i}:")
            print(f"页码范围: {table.start_page + 1} - {table.end_page + 1}")
            print(f"坐标: ({table.bbox[0]:.1f}, {table.bbox[1]:.1f}, {table.bbox[2]:.1f}, {table.bbox[3]:.1f})")
            print(f"前置文本: {table.preceding_text}")
            
    finally:
        finder.close()

if __name__ == "__main__":
    main() 