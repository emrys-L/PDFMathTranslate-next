"""Integration module for connecting enhanced translation to BabelDOC pipeline."""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from pdf2zh_next.enhanced.fragment_detector import FragmentDetector, TextBlock
from pdf2zh_next.enhanced.visual_reassembler import VisualSemanticReassembler, VisualAnalysisResult
from pdf2zh_next.enhanced.block_reassembler import TextBlockReassembler, ReassembledBlock

logger = logging.getLogger(__name__)


class EnhancedTranslationPipeline:
    """
    Enhanced translation pipeline that integrates visual semantic reassembly
    into the BabelDOC translation workflow.
    
    Usage:
        pipeline = EnhancedTranslationPipeline()
        if pipeline.should_enhance(page_blocks):
            enhanced_blocks = pipeline.enhance_page(page_object, page_blocks)
        # Continue with normal translation using enhanced_blocks
    """
    
    def __init__(self, enabled: bool = True, api_config: Optional[Dict[str, str]] = None):
        self.enabled = enabled
        self.api_config = api_config
        
        self.detector = FragmentDetector()
        self.visual_reassembler = VisualSemanticReassembler(api_config=api_config)
        self.block_reassembler = TextBlockReassembler()
        
        self.stats = {
            "pages_analyzed": 0,
            "pages_enhanced": 0,
            "pages_skipped": 0,
            "fragments_merged": 0
        }
    
    def should_enhance(self, blocks: List[TextBlock]) -> bool:
        """Check if a page needs visual enhancement."""
        if not self.enabled:
            return False
        
        return self.detector.needs_visual_reassembly(blocks)
    
    def enhance_page(
        self,
        page_object: Any,
        blocks: List[TextBlock]
    ) -> List[ReassembledBlock]:
        """
        Enhance a page by detecting and merging fragmented text blocks.
        
        Args:
            page_object: PyMuPDF page object
            blocks: List of TextBlock objects extracted from the page
        
        Returns:
            List of ReassembledBlock objects (some merged, some single)
        """
        self.stats["pages_analyzed"] += 1
        
        if not self.should_enhance(blocks):
            self.stats["pages_skipped"] += 1
            
            return [
                ReassembledBlock(
                    id=b.id,
                    text=b.text,
                    x0=b.x0, y0=b.y0, x1=b.x1, y1=b.y1,
                    font_size=b.font_size or 10.0,
                    font_name=b.font_name or "Helvetica"
                )
                for b in blocks
            ]
        
        logger.info(f"Page needs visual enhancement, analyzing...")
        
        analysis_result = self.visual_reassembler.analyze(page_object, blocks)
        
        reassembled_blocks = self.block_reassembler.reassemble(blocks, analysis_result)
        
        merged_count = sum(1 for b in reassembled_blocks if b.is_merged)
        self.stats["pages_enhanced"] += 1
        self.stats["fragments_merged"] += merged_count
        
        logger.info(
            f"Enhancement complete: {len(blocks)} blocks → {len(reassembled_blocks)} blocks "
            f"({merged_count} merged)"
        )
        
        return reassembled_blocks
    
    def get_stats(self) -> Dict[str, int]:
        """Get enhancement statistics."""
        return self.stats.copy()
    
    def convert_to_babeldoc_format(
        self,
        reassembled_blocks: List[ReassembledBlock]
    ) -> List[Dict[str, Any]]:
        """
        Convert reassembled blocks to BabelDOC's internal format.
        
        This provides compatibility with BabelDOC's existing translation pipeline.
        
        Args:
            reassembled_blocks: List of ReassembledBlock objects
        
        Returns:
            List of dictionaries in BabelDOC's expected format
        """
        return [
            {
                "id": block.id,
                "text": block.text,
                "bbox": [block.x0, block.y0, block.x1, block.y1],
                "font_size": block.font_size,
                "font_name": block.font_name,
                "is_merged": block.is_merged,
                "original_ids": block.original_block_ids
            }
            for block in reassembled_blocks
        ]


def create_enhanced_pipeline(
    enabled: bool = True,
    config: Optional[Dict[str, Any]] = None
) -> EnhancedTranslationPipeline:
    """
    Factory function to create an enhanced translation pipeline.
    
    Args:
        enabled: Whether to enable enhancement (default: True)
        config: Optional configuration dictionary
    
    Returns:
        Configured EnhancedTranslationPipeline instance
    """
    api_config = None
    if config:
        api_config = config.get("api_config")
    
    return EnhancedTranslationPipeline(enabled=enabled, api_config=api_config)
