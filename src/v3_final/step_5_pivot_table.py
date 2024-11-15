from pathlib import Path

import pandas as pd
from fuzzywuzzy import fuzz

from src.config import DATA_DIR

# Define the standard level 1 criteria
STANDARD_L1_CRITERIA = ["Strategic Relevance", "Quality of Project Design", "Nature of External Context",
    "Effectiveness", "Financial Management", "Efficiency", "Monitoring and Reporting", "Sustainability",
    "Factors Affecting Performance", "Overall Project Performance Rating"]


def clean_criterion(text):
    """Clean criterion text by removing numbers, dots and extra whitespace"""
    import re
    # Handle NaN or non-string values
    if pd.isna(text):
        return ''
    # Convert to string if not already
    text = str(text)
    # Remove leading numbers and dots (e.g., "1.", "1.2.", etc.)
    text = re.sub(r'^\d+\.?\d*\.?\s*', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text


def match_criterion_to_l1(criterion, threshold=80):
    """
    Match a criterion to the standard L1 criteria using fuzzy matching
    Returns the best matching L1 criterion or None if no good match is found
    """
    # Handle empty or NaN values
    if pd.isna(criterion) or criterion == '':
        return None
        
    cleaned_criterion = clean_criterion(criterion)
    # If cleaned criterion is empty, return None
    if not cleaned_criterion:
        return None
        
    best_match = None
    best_score = 0

    for l1_criterion in STANDARD_L1_CRITERIA:
        # Try both ratio and partial ratio to catch both full and partial matches
        score1 = fuzz.ratio(cleaned_criterion.lower(), l1_criterion.lower())
        score2 = fuzz.partial_ratio(cleaned_criterion.lower(), l1_criterion.lower())
        score = max(score1, score2)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = l1_criterion

    return best_match


def pivot_table(df):
    """
    Transform the input dataframe to create a hierarchical structure with L1 and L2 criteria.

    Prompt:
输入表格的列为 Criterion Rating SummaryAssessment FileName

其中 Criterion 列里的值大致如下：
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

这些值里分一级（不带标号）、二级（带标号），但这只是某一份表格里的格式，其他表格可能不会有序号，或者会用英文字符标记等，而且二级指标是不可信赖的

因此，我的想法是，我们基于这些固定的一级指标，进行相似度匹配，以进行分类

接着，把原先的一列拆成两列（L1、L2），从上往下，L1 向前顺填，L2 的第一行则为空

最后把pivot 的表保存成 原文件名_pivot.xlsx
  
    
    Args:
        df: DataFrame with columns [Criterion, Rating, SummaryAssessment, FileName]
    
    Returns:
        DataFrame with columns [L1, L2, Rating, SummaryAssessment, FileName]
    """
    # Create new columns for L1 and L2
    df = df.copy()

    # Match each criterion to L1 category
    df['L1'] = df['Criterion'].apply(match_criterion_to_l1)

    # If criterion exactly matches an L1 category or is matched with high confidence,
    # set L2 as empty, otherwise use it as L2
    df['L2'] = df.apply(lambda row: '' if row['Criterion'] == row['L1'] else row['Criterion'], axis=1)

    # Forward fill L1 values for consecutive rows
    df['L1'] = df['L1'].ffill()
    # Drop the original Criterion column
    df = df.drop('Criterion', axis=1)

    # Reorder columns
    columns = ['L1', 'L2', 'Rating', 'SummaryAssessment', 'FileName']
    df = df[columns]

    # Save the pivot table
    output_path = excel_file.as_posix().replace('.xlsx', '_pivot.xlsx')
    df.to_excel(output_path, index=False)

    return df


if __name__ == "__main__":
    excel_file = DATA_DIR / "tables.xlsx"
    df = pd.read_excel(excel_file)
    pivot_table(df)
