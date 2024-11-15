import re
from pathlib import Path
from typing import List

root_path = Path('/Users/mark/Documents/Terminal evaluation report')
fn = '7.5799_2024_te_unep_spccm_msp_asia_pacific_ EE Lighting in Pakistan.pdf'

sorted_files: List[Path] = sorted(root_path.glob("*.pdf"), key=lambda x: int(re.search(r'^\d+', x.name).group()))

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / ".out"
OUTPUT_DIR.mkdir(exist_ok=True)  # 确保输出目录存在
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PROJECT_NAME = "terminal-evaluation-report"
VERSION = "0.1.0"
PROJECT_SHEET_NAME = f'{PROJECT_NAME}_{VERSION}.xlsx'
PROJECT_SHEET_PATH = DATA_DIR / PROJECT_SHEET_NAME
PROJECT_STAT_SHEET_NAME = f'{PROJECT_NAME}_{VERSION}_stat.xlsx'

if __name__ == '__main__':
    print(len(sorted_files))
