import re
from typing import List, Dict, Any, Optional, Sequence
from llama_index.core.extractors import BaseExtractor
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.bridge.pydantic import Field
from llama_index.core.llms import LLM

DEFAULT_FIGURE_EXTRACT_PROMPT_TMPL = """\
Extract all figure references mentioned in the following text.
Rules:
1. Do NOT extract tables.
2. If a subfigure is mentioned (e.g., "Figure 3(a)", "Fig. 4b"), return only the main figure number (e.g., "Figure 3", "Figure 4").
3. Normalize "Fig." to "Figure".
4. Return ONLY a comma-separated list of the unique main figure references.
5. If no figures are mentioned, return "None".

Text: {context_str}

References:"""

class FigureExtractor(BaseExtractor):
    """
    Extracts figure and table references from the node content.
    """
    llm: LLM = Field(description="The LLM to use for extraction.")
    prompt_template: str = Field(
        default=DEFAULT_FIGURE_EXTRACT_PROMPT_TMPL,
        description="Prompt template for extraction."
    )

    def __init__(
        self,
        llm: Optional[LLM] = None,
        prompt_template: str = DEFAULT_FIGURE_EXTRACT_PROMPT_TMPL,
            num_workers: int = 4,
        **kwargs: Any,
    ) -> None:
        """Init params."""
        # Ensure figures are excluded from embedding by default, unless overridden
        if "excluded_embed_metadata_keys" not in kwargs:
             kwargs["excluded_embed_metadata_keys"] = ["figures"]
             
        super().__init__(
            llm=llm,
            prompt_template=prompt_template,
            num_workers=num_workers,
            **kwargs,
        )

    @classmethod
    def class_name(cls) -> str:
        return "FigureExtractor"

    async def aextract(self, nodes: Sequence[BaseNode]) -> List[Dict]:
        """
        Extracts figures from nodes.
        """
        metadata_list = []
        for node in nodes:
            if not isinstance(node, TextNode):
                metadata_list.append({})
                continue

            figures = await self._aextract_figures_from_node(node)
            metadata_list.append({"figures": figures})
        return metadata_list

    async def _aextract_figures_from_node(self, node: BaseNode) -> str:
        """
        Extracts figures from a single node.
        """
        context_str = node.get_content(metadata_mode="all")
        prompt = self.prompt_template.format(context_str=context_str)
        
        try:
            response = await self.llm.acomplete(prompt)
            figures_str = response.text.strip()
            
            if figures_str.lower() == "none":
                return ""
                
            return figures_str
        except Exception as e:
            # Fallback or log error
            return ""
