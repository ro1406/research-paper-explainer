"""
AI-generated diagram tool.
"""

import os

import dotenv
from google import genai
from google.adk.tools import ToolContext
from google.genai import types

dotenv.load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


async def generate_diagram(
    image_gen_prompt: str, concept_to_explain: str, tool_context: ToolContext
) -> dict:
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
                temperature=0.8,
                top_p=0.95,
                max_output_tokens=8192,
                response_modalities=["TEXT", "IMAGE"],
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
                part_data = (
                    getattr(part_inline, "data", None)
                    if part_inline is not None
                    else None
                )
                if part_data:
                    image_bytes_out = part_data
                    break

        if not image_bytes_out:
            return {"status": "failed", "detail": "No image bytes found in model response."}

        # Save the generated diagram
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
