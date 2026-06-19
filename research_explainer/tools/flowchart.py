"""
Programmatic flowchart generation tool.
"""

import graphviz
from google.adk.tools import ToolContext
from google.genai import types


async def generate_flowchart(
    nodes_and_colors: dict[str, str],
    edges: list[list[str]],
    title: str,
    tool_context: ToolContext,
) -> dict:
    """
    Generates a flowchart for a research paper based on the nodes to be included, and the connections between them.
    Returns a dictionary with the status and filename or error detail.

    Args:
        nodes_and_colors (dict[str,str]): dictionary of the nodes to be included in the flowchart, and their background colors in hex format. Eg: {'node1': '#c1e5f5', 'node2': '#88cc99'}
        edges (list[tuple[str,str]]): list of tuples of the nodes to be connected, and the connections between them. Eg: [('node1', 'node2'), ('node2', 'node3')] this would draw an arrow from node1 to node2, and from node2 to node3.
        title (str): the title of the flowchart.
        tool_context (ToolContext): The context for the tool execution.

    Returns:
        dict: Contains 'status' ('success' or 'failed'), and either 'filename' or 'detail'.
    """

    try:
        # Initialize the Digraph with a specific engine and global attributes
        dot = graphviz.Digraph(comment=title, engine="dot")
        dot.attr(rankdir="TB", splines="ortho", pad="0.5", nodesep="0.5")
        dot.attr("node", style="filled", fontname="Times-Roman", fontsize="16")
        dot.attr("edge", fontname="Times-Roman", fontsize="16")

        # Define a cluster for the main flow
        with dot.subgraph(name="cluster_1") as c:
            c.attr(rankdir="TB", splines="ortho")
            c.attr("node", shape="box", fontname="Times-Roman", fontsize="16")

            # Define the nodes with their specific colors and labels
            for node, color in nodes_and_colors.items():
                c.node(node, node, fillcolor=color)

            # Add edges with labels
            for edge in edges:
                c.edge(edge[0], edge[1])

        # Add the title at the top
        dot.attr(label=title, labelloc="t", fontname="Times-Roman", fontsize="20")

        png_bytes = dot.pipe(format="png")
        # Save the generated flowchart
        await tool_context.save_artifact(
            "flowchart.png",
            types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
        )
        return {
            "status": "success",
            "detail": "Flowchart generated successfully and stored in artifacts.",
            "filename": "flowchart.png",
        }

    except Exception as e:
        return {"status": "failed", "detail": f"Error generating flowchart: {str(e)}"}
