# Notes

## pymupdf 合并表格教程

参考：[PyMuPDF-Utilities/table-analysis/join_tables.ipynb at master · pymupdf/PyMuPDF-Utilities](https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/table-analysis/join_tables.ipynb)

## V3 Step 5 Relative

输入表格的列为 Criterion Rating SummaryAssessment FileName

其中 Criterion 列里的值大致如下：
```
Strategic Relevance
"1. Alignment to UNEPMTS, POW and strategicpriorities"
"2. Alignment to Donor/Partner strategic priorities"
"3. Relevance to global, regional, sub-regional and national environmental priorities"
"4. Complementarity with relevant existing interventions/coherence"
Quality of Project Design
Nature of External Context
Effectiveness
1. Availability of outputs
"2. Achievement of project outcomes"
3. Likelihood of impact
Financial Management
"1. Adherence to UNEP’s financial policies and procedures"
"2. Completeness of project financial information"
"3. Communication between finance and project management staff"
Efficiency
Monitoring and Reporting
"1. Monitoring design and budgeting"
"2. Monitoring of project implementation"
3. Project reporting
Sustainability
"1. Socio-political sustainability"
2. Financial sustainability
"3. Institutional sustainability"
"Factors Affecting Performance"
"1. Preparation and readiness"
"2. Quality of project management and supervision"
"2.1 UNEP/Implementing Agency:"
"2.2 Partners/Executing Agency:"
"3. Stakeholders’ participation and cooperation"
"4. Responsiveness to human rights and gender equality"
"5. Environmental and social safeguards"
"6. Country ownership and driven-ness"
"7. Communication and public awareness"
"Overall Project Performance Rating"
```

这些值里分一级（不带标号）、二级（带标号），但这只是某一份表格里的格式，其他表格可能不会有序号，或者会用英文字符标记等，而且二级指标是不可信赖的

因此，我的想法是，我们基于这些固定的一级指标，进行相似度匹配，以进行分类

接着，把原先的一列拆成两列（L1、L2），从上往下，L1 向前顺填，L2 的第一行则为空

最后把pivot 的表保存成 原文件名_pivot.xlsx