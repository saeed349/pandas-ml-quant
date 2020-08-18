from typing import Union

import pandas as pd
from sklearn.preprocessing import LabelBinarizer

from pandas_ml_common.utils import has_indexed_columns


def ta_one_hot_encode_discrete(po: Union[pd.Series, pd.DataFrame], drop_na=True, nr_of_classes=None, offset=None) -> Union[pd.Series, pd.DataFrame]:
    if has_indexed_columns(po):
        return pd.DataFrame([ta_one_hot_encode_discrete(po[col]) for col in po.columns]).T
    else:
        if drop_na:
            po = po.dropna()

        if offset is None:
            offset = po.min()

        values = po.values.astype(int)
        values = values - offset

        if nr_of_classes is None:
            nr_of_classes = values.max() + 1

        label_binarizer = LabelBinarizer()
        label_binarizer.fit(range(int(nr_of_classes)))
        return pd.Series(label_binarizer.transform(values).tolist(), index=po.index, name=po.name)

