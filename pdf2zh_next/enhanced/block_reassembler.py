"""Text block reassembler for merging fragmented blocks."""

from typing import List, Dict, Any
from dataclasses import dataclass
from pdf2zh_next.enhanced.fragment_detector import TextBlock
from pdf2zh_next.enhanced.visual_reassembler import VisualAnalysisResult


@dataclass
class ReassembledBlock:
    """A reassembled text block (either single or merged)."""
    id: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    font_name: str
    is_merged: bool = False
    original_block_ids: List[int] = None
    
    def __post_init__(self):
        if self.original_block_ids is None:
            self.original_block_ids = [self.id]


class TextBlockReassembler:
    """Merges fragmented text blocks based on visual analysis."""
    
    def __init__(self):
        self.config = {
            "min_font_size": 6.0,
            "max_font_size": 72.0,
        }
    
    def reassemble(
        self,
        original_blocks: List[TextBlock],
        analysis_result: VisualAnalysisResult
    ) -> List[ReassembledBlock]:
        """
        Reassemble text blocks based on visual analysis.
        
        Args:
            original_blocks: Original text blocks from PDF
            analysis_result: Visual analysis result with fragment groups
        
        Returns:
            List of reassembled blocks (some merged, some single)
        """
        reassembled = []
        
        for group in analysis_result.reading_order:
            fragment_ids = group.get("fragment_ids", [])
            merged_text = group.get("merged_text", "")
            
            if len(fragment_ids) == 1:
                block = self._create_single_block(
                    original_blocks[fragment_ids[0]],
                    fragment_ids[0]
                )
            else:
                fragments = [
                    original_blocks[i] 
                    for i in fragment_ids 
                    if i < len(original_blocks)
                ]
                block = self._merge_fragments(fragments, merged_text, fragment_ids)
            
            reassembled.append(block)
        
        return reassembled
    
    def _create_single_block(
        self,
        original: TextBlock,
        block_id: int
    ) -> ReassembledBlock:
        """Create a reassembled block from a single original block."""
        return ReassembledBlock(
            id=block_id,
            text=original.text,
            x0=original.x0,
            y0=original.y0,
            x1=original.x1,
            y1=original.y1,
            font_size=original.font_size or self.config["min_font_size"],
            font_name=original.font_name or "Helvetica",
            is_merged=False,
            original_block_ids=[block_id]
        )
    
    def _merge_fragments(
        self,
        fragments: List[TextBlock],
        merged_text: str,
        fragment_ids: List[int]
    ) -> ReassembledBlock:
        """Merge multiple fragment blocks into one coherent block."""
        if not fragments:
            raise ValueError("Cannot merge empty fragments")
        
        combined_bbox = self._calculate_combined_bbox(fragments)
        avg_font_size = self._calculate_average_font_size(fragments)
        dominant_font = self._get_dominant_font_name(fragments)
        
        return ReassembledBlock(
            id=min(fragment_ids),
            text=merged_text,
            x0=combined_bbox["x0"],
            y0=combined_bbox["y0"],
            x1=combined_bbox["x1"],
            y1=combined_bbox["y1"],
            font_size=avg_font_size,
            font_name=dominant_font,
            is_merged=True,
            original_block_ids=fragment_ids
        )
    
    def _calculate_combined_bbox(
        self,
        fragments: List[TextBlock]
    ) -> Dict[str, float]:
        """Calculate bounding box that encompasses all fragments."""
        x0 = min(f.x0 for f in fragments)
        y0 = min(f.y0 for f in fragments)
        x1 = max(f.x1 for f in fragments)
        y1 = max(f.y1 for f in fragments)
        
        return {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1
        }
    
    def _calculate_average_font_size(
        self,
        fragments: List[TextBlock]
    ) -> float:
        """Calculate average font size from fragments."""
        font_sizes = [
            f.font_size 
            for f in fragments 
            if f.font_size and f.font_size > 0
        ]
        
        if not font_sizes:
            return self.config["min_font_size"]
        
        avg_size = sum(font_sizes) / len(font_sizes)
        return max(
            self.config["min_font_size"],
            min(avg_size, self.config["max_font_size"])
        )
    
    def _get_dominant_font_name(
        self,
        fragments: List[TextBlock]
    ) -> str:
        """Get the most common font name from fragments."""
        font_names = [
            f.font_name 
            for f in fragments 
            if f.font_name
        ]
        
        if not font_names:
            return "Helvetica"
        
        from collections import Counter
        counter = Counter(font_names)
        return counter.most_common(1)[0][0]
    
    def reassemble_from_dict(
        self,
        original_blocks: List[TextBlock],
        merged_groups: List[Dict[str, Any]]
    ) -> List[ReassembledBlock]:
        """
        Reassemble blocks from a dictionary format (for compatibility).
        
        Args:
            original_blocks: Original text blocks
            merged_groups: List of merge groups from external source
        
        Returns:
            List of reassembled blocks
        """
        reassembled = []
        
        for i, group in enumerate(merged_groups):
            if group.get("type") == "merged":
                fragment_ids = group.get("block_ids", [])
                merged_text = group.get("text", "")
                
                fragments = [
                    original_blocks[j]
                    for j in fragment_ids
                    if j < len(original_blocks)
                ]
                
                block = self._merge_fragments(fragments, merged_text, fragment_ids)
            else:
                block_id = group.get("block_id", i)
                if block_id < len(original_blocks):
                    block = self._create_single_block(
                        original_blocks[block_id],
                        block_id
                    )
                else:
                    continue
            
            reassembled.append(block)
        
        return reassembled
