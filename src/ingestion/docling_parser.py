"""
Docling-based PDF parser for research papers.
Extracts structured content including sections, tables, and figures.
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import time

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


import json
import os
from typing import Optional
import requests
from docling_core.types.doc.page import SegmentedPage
from dotenv import load_dotenv

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    VlmPipelineOptions,
)
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline
from src.db.sql_db import SessionLocal, Figures, PaperStructure
logger = logging.getLogger(__name__)

# db = SessionLocal()  <-- Removed global session


@dataclass
class Figure:
    """Represents figure."""
    id: str
    caption: str


@dataclass
class Section:
    """Represents a parsed section from a paper."""
    title: str
    content: str
    section_type: str
    section: Optional[str] = None
    figures: Optional[List[Figure]] = None



@dataclass
class ParsedTable:
    """Represents a parsed table from a paper."""
    caption: str
    content: str  # Markdown representation
    page_number: Optional[int] = None


@dataclass
class ParsedFigure:
    """Represents a parsed figure from a paper."""
    caption: str
    figure_path: Optional[str] = None  # Path to extracted image
    page_number: Optional[int] = None


@dataclass
class PaperDocument:
    """Complete parsed document structure."""
    paper_id: str
    title: str
    abstract: str
    markdown_content: str = ""  # Full markdown representation
    sections: List[Section] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    

class DoclingParser:
    """Parses PDFs using Docling library."""
    
    # Section type keywords for classification
    SECTION_KEYWORDS = {
        'abstract': ['abstract'],
        'introduction': ['introduction', 'intro'],
        'methods': ['method', 'methodology', 'approach', 'model', 'architecture'],
        'results': ['result', 'experiment', 'evaluation', 'performance'],
        'discussion': ['discussion', 'analysis', 'limitation'],
        'conclusion': ['conclusion', 'summary', 'future work'],
        'related_work': ['related work', 'background', 'literature'],
    }
    
    def __init__(self):
        self._converter = None
        
    @property
    def converter(self):
        """Lazy load Docling converter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
            except ImportError:
                raise ImportError("docling is required. Install with: pip install docling")
        return self._converter
    
    def _classify_section(self, title: str) -> str:
        """Classify section type based on title."""
        title_lower = title.lower()
        for section_type, keywords in self.SECTION_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return section_type
        return 'other'
    
    def _table_to_markdown(self, table_data: Any) -> str:
        """Convert table data to markdown format."""
        # Docling provides table in structured format
        # Convert to markdown for text indexing
        try:
            if hasattr(table_data, 'to_markdown'):
                return table_data.to_markdown()
            elif isinstance(table_data, dict):
                # Handle dict representation
                headers = table_data.get('headers', [])
                rows = table_data.get('rows', [])
                if headers and rows:
                    md = "| " + " | ".join(headers) + " |\n"
                    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    for row in rows:
                        md += "| " + " | ".join(str(cell) for cell in row) + " |\n"
                    return md
            return str(table_data)
        except Exception as e:
            logger.warning(f"Failed to convert table to markdown: {e}")
            return str(table_data)
    

    def _docling_parse(self, input_doc_path):
        # Use project-relative scratch directory
        output_dir = Path("./data/scratch")
        pipeline_options = PdfPipelineOptions()
        IMAGE_RESOLUTION_SCALE = 2.0
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        # pipeline_options.do_formula_enrichment = True
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options,
                                                # pipeline_cls=VlmPipeline
                                                 )
            }
        )
        start_time = time.time()
        conv_res = doc_converter.convert(input_doc_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        doc_filename = conv_res.input.file.stem
        # Save page images
        # for page_no, page in conv_res.document.pages.items():
        #     page_no = page.page_no
        #     page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
        #     with page_image_filename.open("wb") as fp:
        #         page.image.pil_image.save(fp, format="PNG")
        # # Save images of figures and tables
        # table_counter = 0
        # picture_counter = 0
        # for element, _level in conv_res.document.iterate_items():
        #     if isinstance(element, TableItem):
        #         table_counter += 1
        #         element_image_filename = (
        #             output_dir / f"{doc_filename}-table-{table_counter}.png"
        #         )
        #         with element_image_filename.open("wb") as fp:
        #             element.get_image(conv_res.document).save(fp, "PNG")
        #     if isinstance(element, PictureItem):
        #         picture_counter += 1
        #         element_image_filename = (
        #             output_dir / f"{doc_filename}-picture-{picture_counter}.png"
        #         )
        #         with element_image_filename.open("wb") as fp:
        #             element.get_image(conv_res.document).save(fp, "PNG")
        # Save markdown with embedded pictures
        # md_filename = output_dir / f"{doc_filename}-with-images.md"
        # conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)
        # Save markdown with externally referenced pictures
        # md_filename = output_dir / f"{doc_filename}-with-image-refs.md"
        # conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)
        # # Save HTML with externally referenced pictures
        # html_filename = output_dir / f"{doc_filename}-with-image-refs.html"
        # conv_res.document.save_as_html(html_filename, image_mode=ImageRefMode.REFERENCED)
        end_time = time.time() - start_time
        print(f"Time taken: {end_time}s")
        return conv_res

    def scan_markdown_structure(self, md_path: str):
        """
        Scan markdown headings and return a structured outline.

        Returns:
        [
            {
                "level": 1,
                "title": "Introduction",
                "content": "...",
                "line": 3
            },
            ...
        ]
        """
        HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
        structure = {}
        lines = Path(md_path).read_text(encoding="utf-8").splitlines()
        lines = list(map(lambda x: x.lower(), lines))
        for idx, line in enumerate(lines, start=1):
            match = HEADING_PATTERN.match(line)
            if match:
                title = match.group(2).strip()
                # Collect content until next heading
                content_lines = []
                for next_idx in range(idx, len(lines)):
                    next_line = lines[next_idx]
                    if HEADING_PATTERN.match(next_line) and next_idx > idx - 1:
                        break
                    if next_idx > idx - 1:
                        content_lines.append(next_line)
                content = "\n".join(content_lines).strip()
                structure[title] = content
        if "references" in structure:
            structure["references"] = structure["references"].split("\n")
        return structure

    def _extract_fig_remove_data(self, pattern, original_string):
        """
        Extracts all matching data (based on capturing groups in the pattern)
        from a given string, and then returns the original string with these
        matched blocks removed.

        Args:
            pattern (str): The regular expression pattern to match and extract.
                           It should contain capturing groups for the data you want to extract.
                           The entire match will be removed from the original_string.
            original_string (str): The input string containing the patterns.

        Returns:
            tuple: A tuple containing:
                   - list: A list of tuples, where each inner tuple contains
                           the data captured by the pattern's groups for one match.
                           Returns an empty list if no matches are found.
                   - str: The original string with all identified blocks removed.
        """
        extracted_data = []
        remaining_string_parts = []
        last_end_index = 0

        # re.finditer returns an iterator yielding match objects for all non-overlapping matches.
        for match_object in re.finditer(pattern, original_string, re.DOTALL):
            # 1. Extract the data from the current match's capturing groups
            # We'll get all captured groups as a tuple and append it.
            # We'll also apply .strip() to string groups for cleanliness,
            # and convert numbers if they are expected.
            current_match_data = []
            for i, group_value in enumerate(match_object.groups()):
                if i == 0: # Assuming the first group is the figure number
                    current_match_data.append(int(group_value))
                elif isinstance(group_value, str):
                    current_match_data.append(group_value.strip())
                else:
                    current_match_data.append(group_value)
            extracted_data.append(tuple(current_match_data))

            # 2. Add the text *before* the current match to our parts list
            remaining_string_parts.append(original_string[last_end_index:match_object.start()])

            # 3. Update the last_end_index to the end of the current match
            last_end_index = match_object.end()

        # 4. Add any remaining text *after* the last match to our parts list
        remaining_string_parts.append(original_string[last_end_index:])

        # 5. Join all the non-matched parts to form the cleaned string
        cleaned_string = "".join(remaining_string_parts)

        return extracted_data, cleaned_string

    def _extract_and_remove_data(self, pattern, original_string):
        """
        Extracts all matching data (based on capturing groups in the pattern)
        from a given string, and then returns the original string with these
        matched blocks removed.

        Args:
            pattern (str): The regular expression pattern to match and extract.
                           It should contain capturing groups for the data you want to extract.
                           The entire match will be removed from the original_string.
            original_string (str): The input string containing the patterns.

        Returns:
            tuple: A tuple containing:
                   - list: A list of tuples, where each inner tuple contains
                           the raw strings captured by the pattern's groups for one match.
                           Returns an empty list if no matches are found.
                   - str: The original string with all identified blocks removed.
        """
        extracted_data = []
        remaining_string_parts = []
        last_end_index = 0

        # re.finditer returns an iterator yielding match objects for all non-overlapping matches.
        for match_object in re.finditer(pattern, original_string, re.DOTALL):
            # Extract all captured groups as a tuple of strings.
            # The caller is responsible for interpreting and converting these values.
            extracted_data.append(match_object.groups()[0])

            # Add the text *before* the current match to our parts list
            remaining_string_parts.append(original_string[last_end_index:match_object.start()])

            # Update the last_end_index to the end of the current match
            last_end_index = match_object.end()

        # Add any remaining text *after* the last match to our parts list
        remaining_string_parts.append(original_string[last_end_index:])

        # Join all the non-matched parts to form the cleaned string
        cleaned_string = "".join(remaining_string_parts)

        return extracted_data, cleaned_string


    def extract_figures(self, outline, paper_id) -> Tuple[Dict, Dict[str, Any]]:
        
        base64_only_pattern = r"!\[image\]\(data:image\/png;base64,([^)]+)\)"
        pattern = r"figure (\d+): (.*?)\.\n\n!\[image\]\(data:image\/png;base64,([^)]+)\)"
        all_figures = []
        for i in outline:
            if i == "references":
                continue
            content = outline[i]
            outline[i] = {"figs": []}
            # extract figure
            fig, cleaned_string = self._extract_fig_remove_data(pattern, content)
            content = cleaned_string
            if len(fig) > 0:
                for idx, cap, data in fig:
                    fig_meta = {
                            "figure_id": idx,
                            "caption": cap,
                        }
                    outline[i]["figs"].append(fig_meta)
                    fig_meta["section"] = i
                    fig_meta["paper_id"] = paper_id
                    fig_meta["data"] = data
                    all_figures.append(fig_meta)

            _, cleaned_string = self._extract_and_remove_data(base64_only_pattern, content)
            content = cleaned_string
            outline[i]["content"] = content
        return all_figures, outline

    def insert_figures(self, figures, db: SessionLocal):
        logger.info("Inserting figures to DB")
        for i in figures:
            logger.info(f"Inserting: Paper[{i['paper_id']}] Section[{i['section']}] Figure[{i['figure_id']}]")
            db.merge(Figures(
                figure_id=i["figure_id"],
                section=i["section"],
                paper_id=i["paper_id"],
                caption=i["caption"],
                data=i["data"]
            ))
        logger.info("Figure insertion complete.")
        # Commit should be handled by caller or here? 
        # Since we passed the session, we can flush/commit here but caller context is safer.
        # But previous code committed here.
        db.commit()
            


    def parse(self, pdf_path: Path, paper_id: str) -> PaperDocument:
        """
        Parse a PDF document using Docling.
        
        Args:
            pdf_path: Path to PDF file
            paper_id: Unique paper identifier
            
        Returns:
            PaperDocument with extracted content
        """
        
        logger.info(f"Parsing PDF: {pdf_path}")
        parent = pdf_path.parent
        try:
            # Convert PDF to MD using Docling
            logger.info("parisng via docling....")
            result = self._docling_parse(pdf_path)
            out_path = parent.joinpath(f"{pdf_path.stem}.md")
            result.document.save_as_markdown(parent.joinpath(f"{pdf_path.stem}.md"), image_mode=ImageRefMode.EMBEDDED)
            logger.info(f"parsed md save at: {parent.joinpath(f"{pdf_path.stem}.md")}....")
            paper_ir = self.scan_markdown_structure(out_path)
            structure = "\n".join(list(paper_ir.keys()))
            # Create local session for this parsing task
            with SessionLocal() as db:
                logger.info("Inserting paper outline...")
                db.merge(PaperStructure(
                    paper_id=paper_id,
                    outline=structure
                ))
                db.commit()
                logger.info("Inserted paper outline.")
                logger.info(f"Paper IR generated: {structure}....")
                logger.info("Extracting figures....")
                
                figures, paper_ir = self.extract_figures(paper_ir, paper_id)
                logger.info("Extraction complete....")
                for i in figures:
                    print(f"Paper: {i['paper_id'] } Section: {i['section']} Fig: {i['figure_id']}")
                self.insert_figures(figures, db)
            logger.info(f"Cleaned Paper IR generated: {paper_ir.keys()}....")
            title, _ = next(iter(paper_ir.items())) 
            logger.info(f"Title: {title}....")
            del paper_ir[title]
            abs = paper_ir["abstract"]["content"] if "abstract" in paper_ir else ""
            logger.info(f"Abstract: {abs[:30]}....")
            # intro = paper_ir["introduction"] if "introdiction" in paper_ir else ""
            # logger.info(f"Intro: {intro[:20]}....")
            references = paper_ir["references"] if "references" in paper_ir else []
            logger.info(f"references: {references[:4]}....")
            sections = []
            del paper_ir["references"]
            logger.info(f"Parsing sections....")
            for i in paper_ir:
                t = i
                sec = None
                sec_type = "section"
                logger.info(f"Section: {t}....")
                if i[0].isdigit():
                    print(i.split(" ", 1)[0])
                    sec, _ = i.split(" ", 1)
                    if sec[-1] == ".":
                        sec = sec[:-1]
                    if len(sec.split(".")) > 1:
                        sec_type = "subsection"
                        logger.info(f"Subsection: {sec}....")
                sections.append(
                    Section(
                        title=t.strip(),
                        content=paper_ir[i]["content"],
                        section_type=sec_type,
                        section=sec,
                        figures=[Figure(
                            id=f["figure_id"],
                            caption=f["caption"]
                        ) for f in paper_ir[i]["figs"]]
                    )
                )
            logger.info("Returning document.....")
            paper = PaperDocument(
                paper_id=pdf_path.stem,
                title=title.strip(),
                abstract=abs,
                markdown_content="",
                sections=sections,
                references=references
            )
            return paper
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise RuntimeError(f"PDF parsing failed: {e}")

