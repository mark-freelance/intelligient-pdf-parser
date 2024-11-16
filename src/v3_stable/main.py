from src.v3_stable.step_1_pages_local2db import step_1_pages_local2db
from src.v3_stable.step_2_add_candidate_tables import step_2_add_candidate_tables
from src.v3_stable.step_3_merge_tables import step_3_merge_tables
from src.v3_stable.step_4_dump_tables import step_4_dump_tables
from src.v3_stable.step_5_pivot_table import step_5_pivot_table
from src.v3_stable.step_6_update_publish_month import step_6_update_publish_month
from src.v3_stable.step_7_dump_stat_sheet import step_7_dump_stat_sheet

if __name__ == '__main__':
    step_1_pages_local2db()
    step_2_add_candidate_tables()
    step_3_merge_tables()
    step_4_dump_tables()
    step_5_pivot_table()
    step_6_update_publish_month()
    step_7_dump_stat_sheet()