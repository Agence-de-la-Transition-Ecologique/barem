from typing import Literal
from pathlib import Path

import pandas as pd


def standardize_unit(row):
    if row["Unité"] == "kg":
        return row["Valeur"] * 1e-6
    elif row["Unité"] == "t":
        return row["Valeur"] * 1e-3
    elif row["Unité"] == "kt":
        return row["Valeur"]
    else:
        raise ValueError("Unit not recognized, should be 'kg', 't', 'kt'")


def convert_value_to_kt(df: pd.DataFrame) -> pd.DataFrame:
    df["Valeur (kt)"] = df.apply(standardize_unit, axis=1)
    df = df.drop(["Valeur", "Unité"], axis=1)
    return df


def read_tables(data_path: Path, scope: Literal["filières", "bâtiment"]):
    """
    Function used to read the data Excel (filieres.xlsx or batiment.xlsx), and create a dictionary with the resulting
    dataframes, with the values in kt.

    :param data_path: The path to the directory with the two .xlsx files
    :param scope: Whether to read the "filières" data or "bâtiment" data
    :return: A dictionary with the resulting dataframes
    """
    filieres_data_path = data_path / "filieres.xlsx"
    batiment_data_path = data_path / "batiment.xlsx"

    if scope == "filières":
        matieres = pd.read_excel(
            filieres_data_path,
            sheet_name="Métadonnées",
            usecols="A",
            header=0,
        ).dropna()["Matières"].tolist()

        filiere_data_dict = {}
        # Loop over the list of "matières" in the "Métadonnées" sheet
        for matiere in matieres:
            filiere_data_dict[matiere] = convert_value_to_kt(
                pd.read_excel(
                    filieres_data_path,
                    sheet_name=matiere,
                    usecols="A:E",
                    header=0,
                )
            )

        return filiere_data_dict

    elif scope == "bâtiment":

        # Dictionnaire de nomenclature agrégée
        agg_mat_df = pd.read_excel(
            batiment_data_path,
            sheet_name="Métadonnées",
            usecols="C:D",
            header=0,
        )
        agg_pce_df = pd.read_excel(
            batiment_data_path,
            sheet_name="Métadonnées",
            usecols="F:G",
            header=0,
        )
        agg_map = dict(zip(agg_mat_df["Matériau"], agg_mat_df["Matériau agrégé"]))
        agg_map.update(dict(zip(agg_pce_df["PCE"], agg_pce_df["PCE agrégé"])))

        # Données de gros oeuvre
        gros_oeuvre_df = pd.read_excel(
            batiment_data_path,
            sheet_name="Gros oeuvre",
            usecols="A:G",
            header=0,
        )
        gros_oeuvre_df = convert_value_to_kt(gros_oeuvre_df)
        gros_oeuvre_df["Source agrégée"] = gros_oeuvre_df["Source"].apply(lambda x: agg_map.get(x, x))
        gros_oeuvre_df["Cible agrégée"] = gros_oeuvre_df["Cible"].apply(lambda x: agg_map.get(x, x))

        # Données second oeuvre
        second_oeuvre_df = pd.read_excel(
            batiment_data_path,
            sheet_name="Second oeuvre",
            usecols="A:G",
            header=0,
        )
        second_oeuvre_df = convert_value_to_kt(second_oeuvre_df)
        second_oeuvre_df["Source agrégée"] = second_oeuvre_df["Source"].apply(lambda x: agg_map.get(x, x))
        second_oeuvre_df["Cible agrégée"] = second_oeuvre_df["Cible"].apply(lambda x: agg_map.get(x, x))

        # Données équipements
        equipements_df = pd.read_excel(
            batiment_data_path,
            sheet_name="Equipements",
            usecols="A:G",
            header=0,
        )
        equipements_df = convert_value_to_kt(equipements_df)
        equipements_df["Source agrégée"] = equipements_df["Source"].apply(lambda x: agg_map.get(x, x))
        equipements_df["Cible agrégée"] = equipements_df["Cible"].apply(lambda x: agg_map.get(x, x))

        return {
            "Gros oeuvre": gros_oeuvre_df,
            "Second oeuvre": second_oeuvre_df,
            "Equipements": equipements_df
        }

    else:
        print("Scope unknown...")