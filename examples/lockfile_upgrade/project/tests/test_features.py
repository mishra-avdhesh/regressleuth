import pandas as pd
from toy_features import clip_and_round


def test_clip_and_round():
    frame = pd.DataFrame({"a": [-0.5, 0.123, 1.7]})
    assert clip_and_round(frame)["a"].tolist() == [0.0, 0.12, 1.0]
