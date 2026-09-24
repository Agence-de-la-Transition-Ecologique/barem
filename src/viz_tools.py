from itertools import cycle
from typing import Dict, List, Literal, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def compute_x(
        source_list: List[int],
        target_list: List[int],
        source_node_type_list: List[int],
        target_node_type_list: List[int]
) -> Dict[int, float]:
    """
    Computes the X coordinates of the nodes on the Sankey diagram, according to their node type.

    :param source_list: List of source node IDs.
    :param target_list: List of target node IDs.
    :param source_node_type_list: List of source node types.
    :param target_node_type_list: List of target node types.
    :return: A dictionary mapping each node ID to its X coordinate.
    """

    node_type_dict = dict(zip(source_list, source_node_type_list))
    node_type_dict.update(dict(zip(target_list, target_node_type_list)))

    x_dict = {x: y / (len(set(node_type_dict.values())) - 1) for x, y in node_type_dict.items()}

    return x_dict


def sort_layers(
        layers: Dict[int, List[int]],
        edges: List[Tuple[int, int]]
) -> Dict[int, List[int]]:
    """
    Sorts each node in each layer, from top to bottom, according to the position of its source nodes.

    :param layers: A dictionary mapping each layer ID to its nodes' IDs.
    :param edges: A list of tuples, each tuple representing a link between two nodes.
    :return: The layers dictionary, with each list of node sorted from top to bottom.
    """

    sorted_layers = {0: layers[0]}  # First layer remains fixed

    for i in range(1, len(layers)):  # Process each layer sequentially
        current_layer = layers[i]

        # Compute barycenter for each node in the current layer
        barycenters = {}
        for node in current_layer:
            incoming_nodes = [src for src, tgt in edges if tgt == node]
            if incoming_nodes:
                pos_list = []
                for p in incoming_nodes:
                    k = 1
                    while p not in layers[i - k]:
                        k += 1
                    pos_list.append(layers[i - k].index(p))
                barycenters[node] = np.mean(pos_list)
            else:
                barycenters[node] = float('inf')  # Place isolated nodes last

        # Sort nodes based on barycenter value
        sorted_layers[i] = sorted(current_layer, key=lambda x: barycenters[x])

    return sorted_layers


def compute_y(
        source_list: List[int],
        target_list: List[int],
        source_node_type_list: List[int],
        target_node_type_list: List[int],
        value_list: List[float],
        height: int,
        pad: int
) -> Dict[int, float]:
    """
    Computes the Y coordinates of the nodes on the Sankey diagram, with each node position as close to the mean
    positions of its source nodes.
    :param source_list: The list of source node IDs.
    :param target_list: The list of target node IDs.
    :param source_node_type_list: The list of source node types.
    :param target_node_type_list: The list of target node types.
    :param value_list: The list of each link's value.
    :param height: The total height of the diagram, in pixels.
    :param pad: The vertical padding between each node, in pixels.
    :return: A dictionary mapping each node ID to its Y coordinate.
    """

    complete_node_list = list(set(source_list + target_list))

    node_incoming_values = {node: 0 for node in complete_node_list}
    node_outgoing_values = {node: 0 for node in complete_node_list}

    # Compute the value of each node by summing the values of its incoming links on one hand, and the values of its
    # outgoing links of the other hand, and selecting the max value
    for i, (source_node, target_node) in enumerate(zip(source_list, target_list)):
        node_incoming_values[target_node] += value_list[i]
        node_outgoing_values[source_node] += value_list[i]
    node_values = {node: max(node_incoming_values[node], node_outgoing_values[node]) for node in complete_node_list}

    node_type_dict = dict(zip(source_list, source_node_type_list))
    node_type_dict.update(dict(zip(target_list, target_node_type_list)))

    dict_source = {x: source_list.count(x) for x in set(source_list)}
    dict_target = {x: target_list.count(x) for x in set(target_list)}
    count_links = {k: dict_source.get(k, 0) + dict_target.get(k, 0) for k in set(dict_source) | set(dict_target)}
    layers = {x: [y for y in node_type_dict if node_type_dict[y] == x] for x in node_type_dict.values()}
    layers = {layer: sorted(node_list, key=lambda item: count_links[item]) for layer, node_list in layers.items()}

    edges = list(zip(source_list, target_list))

    # Compute the value of each layer, by summing the values of its nodes
    layer_values = {layer: sum([node_values[node] for node in node_list]) for layer, node_list in layers.items()}
    biggest_layer = max(layer_values, key=lambda x: layer_values[x])

    # Compute alpha, the ratio between each node's height as rendered by plotly.js, and its value, and then computing
    # each node's height
    alpha = (height - (len(layers[biggest_layer]) - 1) * pad) / layer_values[biggest_layer]
    node_sizes = {node: int(np.ceil(alpha * node_values[node])) for node in complete_node_list}

    # Use the sort_layers() function to sort each layer's nodes, and repeat the process a few times, back and forth, to
    # converge towards a consistent sort
    cnt = 0
    layers = {max(layers.keys()) - k: v for k, v in layers.items()}
    edges = [(target, source) for (source, target) in edges]
    while cnt < 5:
        layers = {max(layers.keys()) - k: v for k, v in layers.items()}
        edges = [(target, source) for (source, target) in edges]
        layers = sort_layers(layers, edges)
        cnt += 1

    # Compute the Y positions of the first layer's nodes
    y_dict = {node: ((node_sizes[node] / 2) + sum([node_sizes[x] for x in layers[0][:i]]) + max(i, 0) * pad) / height
              for i, node in enumerate(layers[0])}

    # Compute, iteratively for each layer, the position of each of its nodes, by making each node as clode to possible
    # to the mean position of its source nodes
    for i in range(1, len(layers)):  # Process each layer sequentially
        current_layer = layers[i]

        previous_y = 0
        previous_size = 0
        for node in current_layer:
            min_possible_y = previous_y + (((previous_size + node_sizes[node]) / 2) + pad) / height
            incoming_nodes = [src for src, tgt in edges if tgt == node]
            if incoming_nodes:
                pos_list = []
                for p in incoming_nodes:
                    pos_list.append(y_dict[p] + ((node_sizes[node] - node_sizes[p]) / (2 * height)))
                pos = np.mean(pos_list)
                if pos < min_possible_y:
                    pos = min_possible_y
            else:
                pos = min_possible_y

            pos = float(round(pos, 3))

            y_dict[node] = pos
            previous_y = pos
            previous_size = node_sizes[node]

    # If a layer has nodes with a Y position > 1.0, rescale the layer's positions
    for node_list in layers.values():
        highest_y = max([y_dict[node] for node in node_list])
        if highest_y > 1.0:
            for node in node_list:
                y_dict[node] /= highest_y

    return y_dict


def assign_colors(
        source_list: List[int],
        target_list: List[int],
        source_node_type_list: List[int],
        target_node_type_list: List[int],
        y_dict: Dict[int, float],
        opacity: float=0.8
)  -> (List[str], List[str], List[str]):
    """
    Associate each node, and each link to a color.

    :param source_list: The list of source node IDs.
    :param target_list: The list of target node IDs.
    :param source_node_type_list: The list of source node types.
    :param target_node_type_list: The list of target node types.
    :param y_dict: The dictionary mapping nodes to their Y positions.
    :param opacity: The opacity of the links.
    :return: Three lists of string representing the colors of nodes, links when hovered on, and links.
    """


    complete_node_list = list(set(source_list + target_list))
    color_map = {node: color for node, color in zip(y_dict.keys(), cycle(px.colors.qualitative.Set3))}
    node_colors = [color_map[x] for x in complete_node_list]
    hover_colors = [color_map[x] for x in source_list]

    link_colors = []
    # Creates link colors by copying hover links' colors and reducing the opacity
    for source_node, source_type, target_node, target_type in zip(
            source_list, source_node_type_list, target_list, target_node_type_list
    ):
        op = opacity - 0.2 * (target_type - source_type - 1)
        link_colors.append(f"{color_map[source_node][:-1]}, {op})".replace('rgb', 'rgba'))

    return node_colors, hover_colors, link_colors


def format_flow(value):
    """Formats the value based on size (kg, t, kt)."""
    if value >= 1000:
        return f"{value / 1e3:.2f} Mt"
    if value >= 1:
        return f"{value:.2f} kt"
    elif value >= 0.001:
        return f"{value * 1e3:.2f} t"
    else:
        return f"{value * 1e6:.2f} kg"


def plot_sankey(
        df: pd.DataFrame,
        node_possible_types: List[str],
        height: int=1200
) -> go.Figure:
    """
    Plot the Sankey diagram, using the functions above.

    :param df: The dataframe to represent.
    :param node_possible_types: The possible node types, as strings.
    :param height: The height of the diagram.
    :return: A plotly.graph_objects Figure object
    """

    pad = int(height / 100)

    df = df.dropna(subset="Lien").reset_index(drop=True)

    df["type_source"] = df["Lien"].apply(lambda x: x.split('/')[0])
    df["type_cible"] = df["Lien"].apply(lambda x: x.split('/')[1])

    source_list = df["Source"].tolist()
    target_list = df["Cible"].tolist()

    source_node_type_list = df["type_source"].tolist()
    target_node_type_list = df["type_cible"].tolist()

    value_list = df["Valeur (kt)"].tolist()
    formatted_values_list = [format_flow(v) for v in value_list]

    node_map = {x: i for i, x in enumerate(set(source_list + target_list))}

    node_possible_types = list(
        filter(lambda x: x in source_node_type_list + target_node_type_list, node_possible_types))

    node_type_map = {x: i for i, x in enumerate(node_possible_types)}

    source_list = [node_map[x] for x in source_list]
    target_list = [node_map[x] for x in target_list]
    source_node_type_list = [node_type_map[x] for x in source_node_type_list]
    target_node_type_list = [node_type_map[x] for x in target_node_type_list]

    # Compute the X and Y positions for each node
    x_dict = compute_x(source_list, target_list, source_node_type_list, target_node_type_list)
    y_dict = compute_y(source_list, target_list, source_node_type_list, target_node_type_list, value_list, height, pad)
    x_y = {node_idx: (x_dict[node_idx], y_dict[node_idx]) for node_idx in node_map.values()}
    x = [.001 if v[0] == 0 else .999 if v[0] == 1 else v[0] for v in x_y.values()]
    y = [.001 if v[1] == 0 else .999 if v[1] == 1 else v[1] for v in x_y.values()]

    # Determine the colors
    node_colors, hover_colors, link_colors = assign_colors(
        source_list, target_list, source_node_type_list, target_node_type_list, y_dict)

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=pad,
                line=dict(color="black", width=0.2),
                label=list(node_map.keys()),
                hovertemplate="%{label} : %{value} kt<extra></extra>",
                color=node_colors,
                x=x,
                y=y
            ),
            link=dict(
                source=source_list,
                target=target_list,
                value=value_list,
                color=link_colors,
                hovercolor=hover_colors,
                customdata=formatted_values_list,
                hovertemplate="%{source.label} -> %{target.label}<extra>%{customdata}</extra>"
            ),
            domain=dict(
                x=[0.0, 1.0],
                y=[0.0, 1.0]
            )
        ),
        layout=dict(
            height=height,
            margin=dict(b=height / 3)
        )
    )

    return fig

