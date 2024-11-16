# Sentiment based PDF Parser

## Usage

### 配置

配置文件在 [config.py](../config.py)，主要配置一下 ROOT_PATH 即可

### 数据库

```shell
# 初始化数据库
alembic upgrade head
```

表定义在 [models.py](../models.py)

数据库在 [database.db](../../database.db)，是 sqlite，装了驱动后直接点击就可以看

数据库连接与工具函数在 [database.py](../database.py)

### 运行

```shell
# 在根目录
export PYTHONPATH=$(pwd)

poetry shell
poetry install

python src/v3_stable/main.py
```

## 二开

### 更新表结构后 （models)

```shell
alembic revision --autogenerate -m {MESSAGE}
alembic upgrade head
```
