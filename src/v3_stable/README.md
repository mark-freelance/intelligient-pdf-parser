# Sentiment based PDF Parser

## Usage

### 配置

配置文件在 [config.py](../config.py)，主要配置一下 ROOT_PATH 即可

### 数据库

表定义在 [models.py](../models.py)

数据库在 [database.db](../../database.db)，是 sqlite，装了驱动后直接点击就可以看

数据库连接与工具函数在 [database.py](../database.py)

### 初始化项目

```shell
# 在根目录
export PYTHONPATH=$(pwd)
poetry shell
poetry install
cd src/v3_stable
```

### 初始化数据：一步步来即可

```shell
# init
python step_1_pages_from_local.py

# table relative
python step_2_add_candidate_tables.py
python step_3_merge_tables.py
python step_4_dump_tables.py
python step_5_pivot_table.py

# date relative
python step_6_update_publish_month.py
python step_7_dump_stat_sheet.py
```

### 更新表结构后 （models)

```shell
alembic revision --autogenerate -m {MESSAGE}
alembic upgrade head
```

## Other References

- [analysis.md](../../docs/analysis.md)
- [notes.md](../../docs/notes.md)