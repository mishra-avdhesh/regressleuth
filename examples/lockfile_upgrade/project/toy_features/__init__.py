"""A tiny feature-engineering package whose tests break on a dependency upgrade."""

import pandas as pd


def clip_and_round(frame: pd.DataFrame) -> pd.DataFrame:
    """Clip every value to [0, 1] and round to two decimals, cell by cell."""
    return frame.applymap(lambda value: round(min(max(value, 0.0), 1.0), 2))
