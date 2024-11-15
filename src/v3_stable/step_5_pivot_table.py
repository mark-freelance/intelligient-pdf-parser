import pandas as pd
from fuzzywuzzy import fuzz

from src.config import PROJECT_SHEET_PATH

# Define the standard level 1 criteria
STANDARD_L1_CRITERIA = ["Strategic Relevance", "Quality of Project Design", "Nature of External Context",
                        "Effectiveness", "Financial Management", "Efficiency", "Monitoring and Reporting",
                        "Sustainability", "Factors Affecting Performance", "Overall Project Performance Rating"]


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
    
    Args:
        df: DataFrame with columns [Criterion, Rating, SummaryAssessment, FileName]
    
    Returns:
        DataFrame with columns [No., FileName, L1, L2, SummaryAssessment, Rating]
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

    # Reorder columns and add index starting from 1
    df = df.reset_index(drop=True)
    df.index = df.index + 1  # Start numbering from 1 instead of 0
    df = df.reset_index(names=['No.'])

    # Set final column order
    columns = ['No.', 'FileName', 'L1', 'L2', 'SummaryAssessment', 'Rating']
    df = df[columns]

    # Save the pivot table
    output_path = PROJECT_SHEET_PATH.as_posix().replace('.xlsx', '_pivot.xlsx')
    df.to_excel(output_path, index=False)

    return df


if __name__ == "__main__":
    df = pd.read_excel(PROJECT_SHEET_PATH)
    pivot_table(df)
