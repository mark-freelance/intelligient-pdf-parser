from typing import List

import numpy as np
import pandas as pd


def data2df(data: List[List[str]]) -> pd.DataFrame:
    return pd.DataFrame(data[1:], columns=data[0])


def df2data(df: pd.DataFrame) -> List[List[str]]:
    """
    todo: cleaner approach
    """
    return np.vstack([df.columns.tolist(), df.values.tolist()]).tolist()
