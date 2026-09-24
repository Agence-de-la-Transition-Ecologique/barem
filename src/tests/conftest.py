import pandas as pd
import pytest

@pytest.fixture
def simple_df():
    return pd.DataFrame({
        "Source": ["A"],
        "Cible": ["B"],
        "Lien": ["A/B"],
        "Valeur (kt)": [1.0]
    })
