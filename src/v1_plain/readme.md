## V1

## Overview

基于 rich 的并发可视化脚本，不过意义不是很大，不如基于数据库的增量控制系统：

![rich](../../assets/terminal-demo.png)

## 文本比对算法

基于 sentence-transformer 的 minilm 实现短距离（<= 256 token）语义相似度匹配，可用，但是遍历调用的时间成本太高（一页要 5 秒钟。。）。

![img.png](../../assets/all-minillm-l6-v2.png)

比对过程：

![img.png](../../assets/text-comparison-algo.png)

