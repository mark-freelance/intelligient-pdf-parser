import pandas as pd
from sqlalchemy import null
from sqlmodel import select

from database import get_db
from models.paper import Paper
from src.config import DATA_DIR
from src.log import logger
from src.utils.dataframe import data2df

def normalize_column_name(col):
    """Normalize column names by removing newlines and extra spaces"""
    col = ' '.join(str(col).replace('\n', ' ').split()).strip()
    # Standardize columns starting with 'Rating'
    if col.lower().startswith('rating'):
        return 'Rating'
    return col

if __name__ == '__main__':
    dfs = []  # Create a list to store DataFrames
    all_columns = set()  # Track all unique columns

    with get_db() as session:
        query = select(Paper).where(Paper.merged_criterion_table != null(), )
        papers = session.scalars(query).all()
        logger.info(f'papers count={len(papers)}')
        
        for (index, paper) in enumerate(papers[:100]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper.name}")

            table = paper.merged_criterion_table
            if not table:
                continue

            try:
                paper_df = data2df(table)
                # Normalize column names
                paper_df.columns = [normalize_column_name(col) for col in paper_df.columns]
                
                # If there are multiple 'Rating' columns after normalization, 
                # keep only the first one
                if paper_df.columns.value_counts().get('Rating', 0) > 1:
                    # Get indices of all 'Rating' columns
                    rating_cols = paper_df.columns.get_indexer_for(['Rating'])
                    # Keep the first Rating column, drop the rest
                    cols_to_drop = paper_df.columns[rating_cols[1:]]
                    paper_df = paper_df.drop(columns=cols_to_drop)
                
                paper_df = paper_df.reset_index(drop=True)
                paper_df['file_name'] = paper.name
                
                # Remove any duplicate columns
                paper_df = paper_df.loc[:, ~paper_df.columns.duplicated()]
                
                # Track all columns we've seen
                all_columns.update(paper_df.columns)
                
                dfs.append(paper_df)
                logger.info(f"Successfully processed paper {paper.name}")
            except Exception as e:
                logger.error(f"Error processing paper {paper.name}: {str(e)}")
                continue

    # Concatenate all DataFrames at once
    if dfs:
        try:
            logger.info(f"Attempting to concatenate {len(dfs)} DataFrames")
            
            # Convert all_columns to a sorted list for consistent ordering
            all_columns = sorted(list(all_columns))
            
            # Create an empty DataFrame with all columns
            result_df = pd.DataFrame(columns=all_columns)
            
            # Append each DataFrame one by one
            for df in dfs:
                # Add missing columns
                for col in all_columns:
                    if col not in df.columns:
                        df[col] = pd.NA
                # Ensure column order matches
                df = df[all_columns]
                # Append to result
                result_df = pd.concat([result_df, df], ignore_index=True)
            
            logger.info(f"Successfully concatenated. Final shape: {result_df.shape}")
            result_df.to_excel(DATA_DIR / 'tables.xlsx', index=False)
        except Exception as e:
            logger.error(f"Error during concatenation: {str(e)}")
            # Log more detailed information
            if dfs:
                logger.error(f"First DataFrame info:")
                logger.error(f"Columns: {dfs[0].columns.tolist()}")
                logger.error(f"Shape: {dfs[0].shape}")
                logger.error(f"Index: {dfs[0].index}")
                logger.error(f"Column types: {dfs[0].dtypes}")
    else:
        logger.warning("No valid DataFrames to concatenate")
