import sys
import os
# Add src to path
sys.path.append(os.getcwd())

from src.agents.visualization_agent import VisualizationAgent

def test_visualization():
    print("Testing Visualization Agent...")
    
    # Mock paper data
    paper = {
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
    }
    
    vis_agent = VisualizationAgent()
    print(f"Generating mindmap for: {paper['title']}")
    
    mermaid_code = vis_agent.generate_mindmap(paper)
    
    print("\n--- Generated Mermaid Code ---")
    print(mermaid_code)
    print("------------------------------")
    
    if "mindmap" in mermaid_code:
         print("SUCCESS: Valid Mermaid code generated.")
    else:
         print("FAILURE: Output does not look like Mermaid code.")

if __name__ == "__main__":
    test_visualization()
