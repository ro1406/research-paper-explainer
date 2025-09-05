# Research Paper Explainer Agent

A specialized ADK based AI agent that analyzes research papers and provides detailed explanations with visual aids. Upload a PDF research paper, ask questions about specific concepts, and receive comprehensive explanations accompanied by flowcharts and diagrams. Made with Google's Agent Development Kit (ADK)

**My motivation to make this:** I often need to read several research papers and learn new advanced concepts in machine learning directly from highly technical papers to keep up with the literature and implement these new concepts at work and in my research. This tool will help me focus on the important parts of the paper and give me illustrations and diagrams to help me learn and visualize things faster. The agent is designed to use multiple diagrams to explain the concept, giving me more details than the one or two diagrams that are normally included in research papers.

## Features

- **PDF Analysis**: Upload and analyze research papers in PDF format
- **Concept Explanation**: Get detailed, accessible explanations of complex research concepts
- **Visual Learning**: Automatic generation of flowcharts and diagrams to enhance understanding
- **Context-Aware**: Explanations are grounded in the specific paper being analyzed
- **Interactive Q&A**: Ask follow-up questions and get clarifications

## Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Project with Vertex AI enabled
- ADK (Agent Development Kit) installed

### Installation

1. Clone or download this project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp env.example .env
   ```
   Edit `.env` and add your Google Cloud configuration:
   ```
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=your-region
   ```

### Running the Agent

The main way to use this agent is through the ADK web interface:

```bash
adk web
```

1. Navigate to the web interface (`http://127.0.0.1:8000/dev-ui/?app=research_explainer`)
2. Upload a PDF research paper
3. Ask questions about specific concepts, methods, or findings
4. Receive detailed explanations with visual aids

## How It Works

### Core Functionality

The Research Explainer agent follows a structured workflow:

1. **Paper Analysis**: Reads and understands the uploaded PDF research paper
2. **Concept Identification**: Identifies the specific concept you're asking about
3. **Detailed Explanation**: Provides a clear, structured explanation including:
   - Definition of the concept
   - How it works (step-by-step if applicable)
   - Why it's important in the context of the paper
   - Key mathematical formulas or technical details
4. **Visual Generation**: Creates appropriate flowcharts or diagrams to illustrate the concept
5. **Integration**: Seamlessly integrates visual aids into the explanation

### Response Structure

Each explanation follows this format:
- **Brief Overview**: What the concept is and why it matters
- **Detailed Explanation**: Step-by-step breakdown with technical details
- **Paper Context**: How this concept fits into the broader research
- **Visual Aid**: Flowchart or diagram (integrated at the most relevant point)
- **Key Takeaways**: Summary of the most important points

## Tools

The agent is equipped with two specialized tools for visual learning:

### 1. Flowchart Generator (`generate_flowchart`)

Creates programmatically generated flowcharts to illustrate processes, workflows, and relationships between concepts.

**Features:**
- Customizable node colors and labels
- Flexible connection patterns
- Professional styling with clean typography
- Automatic layout optimization

**Use Cases:**
- Algorithm workflows
- Process diagrams
- System architectures
- Decision trees
- Data flow diagrams

### 2. Diagram Generator (`generate_diagram`)

Creates abstract diagrams and illustrations to explain complex concepts that don't fit into flowchart format.

**Features:**
- AI-generated technical illustrations
- High-resolution, clean design
- Context-aware visualizations
- Support for abstract concepts

**Use Cases:**
- Mathematical concepts
- Scientific phenomena
- Abstract relationships
- Conceptual models
- Technical illustrations

## Example Usage

### Sample Questions

- "Explain the machine learning algorithm described in this paper"
- "How does the proposed method work step by step?"
- "What is the architecture of the system described?"
- "Can you explain the mathematical formulation in section 3?"
- "What are the key contributions of this research?"

### Sample Response

The agent will provide:
1. Paper title and main contributions
2. Detailed explanation of the requested concept
3. Relevant flowcharts showing the process flow
4. Additional diagrams illustrating key concepts
5. Page references and citations from the paper

## Technical Details

### Model
- **Primary Model**: Gemini 2.5 Pro for text generation and analysis
- **Image Generation**: Gemini 2.5 Flash Image Preview for diagram creation
- **Flowchart Engine**: Graphviz for programmatic flowchart generation


## Troubleshooting

### Common Issues

1. **PDF Upload Fails**: Ensure the PDF is not password-protected and is readable
2. **No Visuals Generated**: The agent may determine that a concept doesn't need visual aids
3. **Environment Errors**: Verify your Google Cloud credentials and project configuration

### Getting Help

If you encounter issues:
1. Check your Google Cloud project configuration
2. Verify that Vertex AI is enabled in your project
3. Ensure all dependencies are properly installed
4. Check the console output for detailed error messages

## Contributing

This agent is designed to be easily extensible. You can:
- Add new tools for different types of visualizations
- Modify the prompt to specialize in specific research domains
- Enhance the PDF processing capabilities
- Add support for additional file formats

## License

Created by Rohan Mitra (rohanmitra8@gmail.com)
Copyright © 2025

---

**Note**: This agent requires a Google Cloud project with Vertex AI enabled and proper authentication configured.
