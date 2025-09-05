"""
Author: Rohan Mitra (rohanmitra8@gmail.com)
tools.py (c) 2025
Desc: Tools for the Research Explainer agent to process PDFs and extract information
Created:  2025-09-05T18:00:00.000Z
Modified: 2025-09-05T21:32:26.315Z
"""


from google import genai
from google.genai import types
from google.adk.tools import ToolContext
import graphviz


client = genai.Client()


async def generate_diagram(image_gen_prompt: str, concept_to_explain: str, tool_context: ToolContext) -> dict:
    """
    Generates a technical diagram for a research paper based on a detailed prompt describing the flow and design requirements.
    Returns a dictionary with the status and filename or error detail.

    Args:
        image_gen_prompt (str): The detailed prompt describing the flow and design requirements.
        concept_to_explain (str): The concept to explain.
        tool_context (ToolContext): The context for the tool execution.

    Returns:
        dict: Contains 'status' ('success' or 'failed'), and either 'filename' or 'detail'.
    """
    print("Generate diagram tool called!")
    try:
        # Create a comprehensive prompt for diagram generation
        enhanced_prompt = f"""
        Create a technical, high-quality diagram for a research paper to explain the concept "{concept_to_explain}", based on the following specifications:
        
        {image_gen_prompt}
        
        Requirements:
        - Clear, readable, and precise design
        - High resolution and clean design
        - Use of appropriate colors and typography
        - Helps explain the concept to a student
        
        Generate a diagram that represents the flow and design requirements.
        """

        content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=enhanced_prompt),
            ],
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=content,
            config=types.GenerateContentConfig(
                temperature=0.8, top_p=0.95, max_output_tokens=8192, response_modalities=["TEXT", "IMAGE"]
            ),
        )

        if not response or not getattr(response, "candidates", None):
            return {"status": "failed", "detail": "No response or candidates from model."}

        image_bytes_out = None
        candidate = response.candidates[0] if response.candidates else None
        content_out = getattr(candidate, "content", None) if candidate is not None else None

        if content_out is not None:
            for part in getattr(content_out, "parts", []):
                part_inline = getattr(part, "inline_data", None)
                part_data = getattr(part_inline, "data", None) if part_inline is not None else None
                if part_data:
                    image_bytes_out = part_data
                    break

        if not image_bytes_out:
            return {"status": "failed", "detail": "No image bytes found in model response."}

        # Save the generated logo
        await tool_context.save_artifact(
            "diagram.png",
            types.Part.from_bytes(data=image_bytes_out, mime_type="image/png"),
        )

        return {
            "status": "success",
            "detail": "Diagram generated successfully and stored in artifacts.",
            "filename": "diagram.png",
        }

    except Exception as e:
        return {"status": "failed", "detail": f"Error generating diagram: {str(e)}"}


async def generate_flowchart(
    nodes_and_colors: dict[str, str], edges: list[list[str]], title: str, tool_context: ToolContext
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
        # Save the generated logo
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
