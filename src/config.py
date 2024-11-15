from pathlib import Path

root_dir = '/Users/mark/Documents/Terminal evaluation report'
fn = '7.5799_2024_te_unep_spccm_msp_asia_pacific_ EE Lighting in Pakistan.pdf'

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / ".out"
OUTPUT_DIR.mkdir(exist_ok=True)  # 确保输出目录存在
