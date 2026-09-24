import pandas as pd

from src.viz_tools import format_flow, compute_x, compute_y, plot_sankey


def test_format_flow():
    assert format_flow(2000) == "2.00 Mt"
    assert format_flow(2) == "2.00 kt"
    assert format_flow(0.01) == "10.00 t"
    assert format_flow(0.0001) == "100.00 kg"


def test_compute_x():
    source = [0, 1]
    target = [2, 3]
    source_types = [0, 0]
    target_types = [1, 1]

    result = compute_x(source, target, source_types, target_types)

    assert result[0] == 0.0
    assert result[2] == 1.0


def test_compute_y_bounds():
    source = [0]
    target = [1]
    source_types = [0]
    target_types = [1]
    values = [1]

    result = compute_y(source, target, source_types, target_types, values, height=1000, pad=10)

    assert all(0 <= y <= 1 for y in result.values())


def test_plot_sankey_runs():
    df = pd.DataFrame({
        "Source": ["A"],
        "Cible": ["B"],
        "Lien": ["type1/type2"],
        "Valeur (kt)": [1.0]
    })

    fig = plot_sankey(df, node_possible_types=["type1", "type2"])

    assert fig is not None
    assert len(fig.data) == 1