import signal
import threading
import time
import os
from pathlib import Path
import webbrowser

import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd

from src.read_data import read_tables
from src.viz_tools import plot_sankey

# Read the data (the 2 .xlsx files)
data_path = Path("./data")

filieres_matieres = pd.read_excel(
    data_path / "filieres.xlsx",
    sheet_name="Métadonnées",
    usecols="A",
    header=0,
).dropna()["Matières"].tolist()
filieres_node_possible_types = pd.read_excel(
    data_path / "filieres.xlsx",
    sheet_name="Métadonnées",
    usecols="C",
    header=0,
).dropna()["Type de nœud (dans l'ordre)"].tolist()
filieres_data = read_tables(data_path, scope="filières")

batiment_node_possible_types = pd.read_excel(
    data_path / "batiment.xlsx",
    sheet_name="Métadonnées",
    usecols="A",
    header=0,
).dropna()["Type de nœud (dans l'ordre)"].tolist() + ["Travaux", "Typologie"]
batiment_data = read_tables(data_path, scope="bâtiment")


# Initialize Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])  # BOOTSTRAP, COSMO, CYBORG, etc.

@app.server.route("/shutdown", methods=["POST"])
def shutdown():
    os._exit(0)

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Dashboard - Disponibilité des Ressources", className="text-center text-primary mt-4"),
                width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    dbc.Tabs([
                        dbc.Tab(tab_id="tab-1", label="Filières"),
                        dbc.Tab(tab_id="tab-2", label="Secteur du bâtiment"),
                    ], id="tabs", active_tab="tab-1"),
                ),
                dbc.CardBody(id="card-content")
            ], style={"width": "100%"})
        ])
    ]),
], fluid=True)


# The callback to render each tab's content when switching between the 2
@app.callback(
    Output("card-content", "children"),
    Input("tabs", "active_tab"),
)
def switch_tab(at):
    if at == "tab-1":
        content = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Label("Ressource :", className="fw-bold"),
                    dcc.Dropdown(
                        id="ressource-dropdown",
                        options=filieres_matieres,
                        value="Gypse",
                        clearable=False,
                        multi=False,
                        className="mb-3",
                        style={'width': '400px'}
                    ),
                    dcc.Loading(
                        dcc.Graph(id="filieres-diagram"),
                        type="circle"
                    )
                ], className="mt-4"),
            ])
        ], fluid=True)

    elif at == "tab-2":
        type_lots_list = ["Gros oeuvre", "Second oeuvre", "Equipements"]
        typo_bat_list = batiment_data["Gros oeuvre"]["Typologie de bâtiment"].unique().tolist()
        travaux_list = batiment_data["Gros oeuvre"]["Type de travaux"].unique().tolist()

        content = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Lots :", className="fw-bold"),
                            dcc.Dropdown(
                                id="lots-dropdown",
                                options=type_lots_list,
                                value="Gros oeuvre",
                                clearable=False,
                                multi=False,
                                className="mb-3"
                            ),
                        ]),
                        dbc.Col([
                            html.Label("Typologies (usage) :", className="fw-bold"),
                            dcc.Dropdown(
                                id="typo-dropdown",
                                options=typo_bat_list,
                                value=typo_bat_list,
                                clearable=False,
                                multi=True,
                                className="mb-3"
                            ),
                        ]),
                        dbc.Col([
                            html.Label("Travaux :", className="fw-bold"),
                            dcc.Dropdown(
                                id="travaux-dropdown",
                                options=travaux_list,
                                value=travaux_list,
                                clearable=False,
                                multi=True,
                                className="mb-3"
                            )
                        ]),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Hr(style={"margin-top": "5px", "margin-bottom": "5px", "width": "50%"}),
                        ], width='auto', className='d-flex justify-content-center')
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Checklist(
                                    options=[
                                        {"label": "Matériaux agrégés", "value": "mat"},
                                        {"label": "PCE agrégés", "value": "pce"},
                                    ],
                                    value=[],
                                    id="agg-switches",
                                    switch=True,
                                ),
                            ]),
                        ], width='auto', className='d-flex justify-content-end'),
                        dbc.Col([
                            html.Div([
                                dbc.Checklist(
                                    options=[
                                        {"label": "Répartition selon le type de travaux", "value": "travaux"},
                                        {"label": "Répartition selon la typologie", "value": "typologie"},
                                    ],
                                    value=[],
                                    id="storeys-switches",
                                    switch=True,
                                ),
                            ]),
                        ], width='auto'),
                    ], className='d-flex justify-content-end'),
                    dbc.Row([
                        dbc.Spinner(
                            dcc.Graph(id="batiment-diagram")
                        )
                    ])
                ])
            ])
        ], fluid=True)

    return content

# Clear the Sankey diagram for "filières", a dirty fix to disable animation between Sankey diagrams, as the disabling
# with Plotly options doesn't work.
@app.callback(
    Output("filieres-diagram", "figure", allow_duplicate=True),
    Input("ressource-dropdown", "value"),
    prevent_initial_call=True
)
def clear_filieres_diagram(selected_ressource):
    return go.Figure()


# Callback to update graph based on dropdown selection
@app.callback(
    Output("filieres-diagram", "figure"),
    Output("filieres-diagram", "key"),
    Input("ressource-dropdown", "value"),
)
def update_filieres_diagram(selected_ressource):

    df = filieres_data[selected_ressource].copy()
    fig = plot_sankey(df, filieres_node_possible_types, height=800)

    fig.update_layout(transition_duration=0)

    time.sleep(0.1)  # allow spinner visibility

    return fig, f"filieres-{selected_ressource}"


@app.callback(
    Output("typo-dropdown", "options"),
    Input("lots-dropdown", "value"),
)
def update_typo_dropdown_options(selected_lots):
    possible_typologies = batiment_data[selected_lots]["Typologie de bâtiment"].unique().tolist()
    return possible_typologies


@app.callback(
    Output("typo-dropdown", "value"),
    Input("lots-dropdown", "value"),
    State("typo-dropdown", "value"),
)
def update_typo_dropdown_value(selected_lots, current_typologies):
    possible_typologies = batiment_data[selected_lots]["Typologie de bâtiment"].unique().tolist()
    return list(set(possible_typologies) & set(current_typologies))


@app.callback(
    Output("travaux-dropdown", "options"),
    Input("lots-dropdown", "value"),
)
def update_travaux_dropdown_options(selected_lots):
    possible_travaux = batiment_data[selected_lots]["Type de travaux"].unique().tolist()
    return possible_travaux


@app.callback(
    Output("travaux-dropdown", "value"),
    Input("lots-dropdown", "value"),
    State("travaux-dropdown", "value"),
)
def update_travaux_dropdown_value(selected_lots, current_travaux):
    possible_travaux = batiment_data[selected_lots]["Type de travaux"].unique().tolist()
    return list(set(possible_travaux) & set(current_travaux))

# Clear the Sankey diagram for "bâtiment", a dirty fix to disable animation between Sankey diagrams, as the disabling
# with Plotly options doesn't work.
@app.callback(
    Output("batiment-diagram", "figure", allow_duplicate=True),
    [
        Input("lots-dropdown", "value"),
        Input("typo-dropdown", "value"),
        Input("travaux-dropdown", "value"),
        Input("agg-switches", "value"),
        Input("storeys-switches", "value")
    ],
    prevent_initial_call=True
)
def clear_batiment_diagram(selected_lots, selected_typologies, selected_travaux, agg_list, storeys_list):
    return go.Figure()

# Callback to update the "bâtiment" Sankey diagram, based on dropdown and filter selection
@app.callback(
    Output("batiment-diagram", "figure"),
    Output("batiment-diagram", "key"),
    Input("lots-dropdown", "value"),
    Input("typo-dropdown", "value"),
    Input("travaux-dropdown", "value"),
    Input("agg-switches", "value"),
    Input("storeys-switches", "value")
)
def update_batiment_diagram(selected_lots, selected_typologies, selected_travaux, agg_list, storeys_list):

    df = batiment_data[selected_lots].copy()

    selected_typologies = [selected_typologies] if isinstance(selected_typologies, str) else selected_typologies
    selected_travaux = [selected_travaux] if isinstance(selected_travaux, str) else selected_travaux

    filtered_df = df[df["Typologie de bâtiment"].isin(selected_typologies)]
    filtered_df = filtered_df[filtered_df["Type de travaux"].isin(selected_travaux)].reset_index(drop=True)

    if "mat" in agg_list:
        filtered_df["Source"] = filtered_df.apply(
            lambda row: row["Source agrégée"] if row["Lien"] == "Matériau/PCE" else row["Source"], axis=1)
    if "pce" in agg_list:
        filtered_df["Source"] = filtered_df.apply(
            lambda row: row["Source agrégée"] if row["Lien"] == "PCE/Lot" else row["Source"], axis=1)
        filtered_df["Cible"] = filtered_df.apply(
            lambda row: row["Cible agrégée"] if row["Lien"] == "Matériau/PCE" else row["Cible"], axis=1)

    filtered_df = filtered_df[['Lien', 'Source', 'Cible', 'Valeur (kt)', 'Typologie de bâtiment', 'Type de travaux']]

    add_df = pd.DataFrame(
        columns=['Lien', 'Source', 'Cible', 'Valeur (kt)', 'Typologie de bâtiment', 'Type de travaux'])
    if "typologie" in storeys_list and "travaux" in storeys_list:
        for _, row in filtered_df[filtered_df['Lien'] == "PCE/Lot"].iterrows():
            add_df.loc[len(add_df)] = ["Lot/Travaux", row["Cible"], row["Type de travaux"], row["Valeur (kt)"], "", ""]
        for _, row in filtered_df[filtered_df['Lien'] == "PCE/Lot"].iterrows():
            add_df.loc[len(add_df)] = ["Travaux/Typologie", row["Type de travaux"], row["Typologie de bâtiment"],
                                       row["Valeur (kt)"], "", ""]
    elif "travaux" in storeys_list:
        for _, row in filtered_df[filtered_df['Lien'] == "PCE/Lot"].iterrows():
            add_df.loc[len(add_df)] = ["Lot/Travaux", row["Cible"], row["Type de travaux"], row["Valeur (kt)"], "", ""]
    elif "typologie" in storeys_list:
        for _, row in filtered_df[filtered_df['Lien'] == "PCE/Lot"].iterrows():
            add_df.loc[len(add_df)] = [
                "Lot/Typologie", row["Cible"], row["Typologie de bâtiment"], row["Valeur (kt)"], "", ""
            ]

    if len(add_df):
        filtered_df = pd.concat([filtered_df, add_df])

    grouped = filtered_df[['Lien', 'Source', 'Cible', 'Valeur (kt)']].groupby(['Source', 'Cible'])

    data_df = pd.DataFrame()
    data_df['Valeur (kt)'] = grouped['Valeur (kt)'].sum()
    data_df['Lien'] = grouped['Lien'].first()
    data_df = data_df.reset_index()

    fig = plot_sankey(data_df, batiment_node_possible_types, height=1000)
    fig.update_layout(transition_duration=0)

    time.sleep(0.1)

    key = f"bat-{selected_lots}-{hash(str(selected_typologies)+str(selected_travaux)+str(agg_list)+str(storeys_list))}"

    return fig, key


# Run the app
if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:8050")
    app.run(port=8050, debug=False)