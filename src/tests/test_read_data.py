from pathlib import Path

import pytest
import pandas as pd

from src.read_data import standardize_unit, convert_value_to_kt, read_tables


def test_standardize_unit_kg():
    row = {"Valeur": 1000, "Unité": "kg"}
    assert standardize_unit(row) == 0.001


def test_standardize_unit_t():
    row = {"Valeur": 1, "Unité": "t"}
    assert standardize_unit(row) == 0.001


def test_standardize_unit_kt():
    row = {"Valeur": 2, "Unité": "kt"}
    assert standardize_unit(row) == 2


def test_standardize_unit_invalid():
    row = {"Valeur": 1, "Unité": "g"}
    with pytest.raises(ValueError):
        standardize_unit(row)


def test_convert_value_to_kt():
    df = pd.DataFrame({
        "Valeur": [1000, 2],
        "Unité": ["kg", "kt"]
    })

    result = convert_value_to_kt(df)

    assert "Valeur (kt)" in result.columns
    assert "Valeur" not in result.columns
    assert result["Valeur (kt)"].tolist() == [0.001, 2]


def test_read_tables_filieres(monkeypatch):

    def fake_read_excel(path, sheet_name=None, usecols=None, header=None):
        if sheet_name == "Métadonnées":
            return pd.DataFrame({"Matières": ["Fer"]})
        elif sheet_name == "Fer":
            return pd.DataFrame({
                "Valeur": [1000],
                "Unité": ["kg"],
                "A": [1], "B": [2], "C": [3]
            })
        else:
            raise ValueError("Unexpected sheet")

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    result = read_tables(Path("."), scope="filières")

    assert "Fer" in result
    assert "Valeur (kt)" in result["Fer"].columns
