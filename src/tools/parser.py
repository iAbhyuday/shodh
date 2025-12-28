import logging
import time
from pathlib import Path
from crewai_tools import BaseTool

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

_log = logging.getLogger(__name__)


class DoclingPDFParserTool(BaseTool):
    """
    Parse a PDF using Docling with full layout, equation, and image preservation.
    Exports:
    - Page images
    - Figure images
    - Table images
    - Markdown (embedded + referenced images)
    - HTML (referenced images)
    """

    name: str = "docling_pdf_parser"
    description: str = (
        "Parses a PDF using Docling with formula enrichment and high-resolution "
        "image extraction. Exports page images, figure images, table images, "
        "Markdown (embedded and referenced), and HTML."
    )

    def _run(
        self,
        pdf_path: str,
        output_dir: str = "parsed_output",
        image_resolution_scale: float = 2.0,
        embed_images_in_markdown: bool = False,
    ) -> str:
        start_time = time.time()

        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------
        # Configure Docling pipeline
        # -------------------------
        pipeline_options = PdfPipelineOptions(
            do_formula_enrichment=True
        )
        pipeline_options.images_scale = image_resolution_scale
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        # -------------------------
        # Convert document
        # -------------------------
        conv_res = doc_converter.convert(str(pdf_path))
        document = conv_res.document
        doc_stem = pdf_path.stem

        # -------------------------
        # Save page images
        # -------------------------
        page_image_count = 0
        for page in document.pages.values():
            page_image_count += 1
            page_image_path = output_dir / f"{doc_stem}-page-{page.page_no}.png"
            with page_image_path.open("wb") as fp:
                page.image.pil_image.save(fp, format="PNG")

        # -------------------------
        # Save figure & table images
        # -------------------------
        table_counter = 0
        picture_counter = 0

        for element, _level in document.iterate_items():
            if isinstance(element, TableItem):
                table_counter += 1
                table_path = output_dir / f"{doc_stem}-table-{table_counter}.png"
                with table_path.open("wb") as fp:
                    element.get_image(document).save(fp, "PNG")

            elif isinstance(element, PictureItem):
                picture_counter += 1
                picture_path = output_dir / f"{doc_stem}-figure-{picture_counter}.png"
                with picture_path.open("wb") as fp:
                    element.get_image(document).save(fp, "PNG")

        # -------------------------
        # Save Markdown
        # -------------------------
        if embed_images_in_markdown:
            md_path = output_dir / f"{doc_stem}-embedded.md"
            document.save_as_markdown(md_path, image_mode=ImageRefMode.EMBEDDED)
        else:
            md_path = output_dir / f"{doc_stem}-refs.md"
            document.save_as_markdown(md_path, image_mode=ImageRefMode.REFERENCED)

        # elapsed = time.time() - start_time

        return (
            f"PDF parsed successfully.\n"
            f"- Output directory: {output_dir}\n"
            f"- Pages exported: {page_image_count}\n"
            f"- Figures exported: {picture_counter}\n"
            f"- Tables exported: {table_counter}\n"
            f"- Markdown: {md_path.name}\n"
        )
