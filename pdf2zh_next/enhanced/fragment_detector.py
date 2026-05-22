"""Fragment detection for visual-enhanced translation."""

from dataclasses import dataclass
from typing import List, Dict, Any
import math


@dataclass
class TextBlock:
    """Represents a text block extracted from PDF."""
    id: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float = 0.0
    font_name: str = ""
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2
    
    @property
    def word_count(self) -> int:
        text_no_spaces = self.text.replace(' ', '').replace('\n', '')
        if not text_no_spaces:
            return 0
        return len(self.text.split())


@dataclass
class FragmentSignals:
    """Detection signals for fragmented layout."""
    avg_words_per_block: float
    vertical_alignment_count: int
    all_caps_spaced_count: int
    has_short_fragments: bool
    has_uniform_spacing: bool
    total_blocks: int


class FragmentDetector:
    """Detects pages needing visual semantic reassembly."""
    
    def __init__(self):
        self.config = {
            "avg_words_threshold": 3.0,
            "vertical_count_threshold": 5,
            "caps_count_threshold": 3,
            "spacing_tolerance": 0.15,
            "alignment_tolerance": 10.0,
        }
    
    def needs_visual_reassembly(self, blocks: List[TextBlock]) -> bool:
        """
        Determine if a page needs visual semantic reassembly.
        
        Returns True if any of these conditions are met:
        1. Average words per block < 3 (likely fragmented)
        2. 5+ blocks vertically aligned with uniform spacing
        3. 3+ all-caps blocks with large character spacing
        """
        if not blocks:
            return False
        
        signals = self.analyze_signals(blocks)
        
        if signals.avg_words_per_block < self.config["avg_words_threshold"]:
            return True
        
        if (signals.vertical_alignment_count >= self.config["vertical_count_threshold"] 
            and signals.has_uniform_spacing):
            return True
        
        if signals.all_caps_spaced_count >= self.config["caps_count_threshold"]:
            return True
        
        return False
    
    def analyze_signals(self, blocks: List[TextBlock]) -> FragmentSignals:
        """Analyze page for fragmentation signals."""
        total_words = sum(b.word_count for b in blocks)
        avg_words = total_words / len(blocks) if blocks else 0
        
        short_fragments = [b for b in blocks if b.word_count < 3 and b.text.strip()]
        has_short = len(short_fragments) > len(blocks) * 0.3
        
        vertical_count = self._count_vertical_alignment(blocks)
        has_uniform = self._has_uniform_spacing(blocks)
        
        caps_count = self._count_all_caps_spaced(blocks)
        
        return FragmentSignals(
            avg_words_per_block=avg_words,
            vertical_alignment_count=vertical_count,
            all_caps_spaced_count=caps_count,
            has_short_fragments=has_short,
            has_uniform_spacing=has_uniform,
            total_blocks=len(blocks)
        )
    
    def _count_vertical_alignment(self, blocks: List[TextBlock]) -> int:
        """Count blocks that are vertically aligned."""
        if len(blocks) < 3:
            return 0
        
        tolerance = self.config["alignment_tolerance"]
        
        x_centers = [b.center_x for b in blocks if b.text.strip()]
        if not x_centers:
            return 0
        
        x_median = sorted(x_centers)[len(x_centers) // 2]
        
        aligned = [
            b for b in blocks 
            if b.text.strip() and abs(b.center_x - x_median) < tolerance
        ]
        
        return len(aligned)
    
    def _has_uniform_spacing(self, blocks: List[TextBlock]) -> bool:
        """Check if blocks have uniform vertical spacing."""
        if len(blocks) < 3:
            return False
        
        sorted_blocks = sorted(blocks, key=lambda b: b.y0)
        
        spacings = []
        for i in range(len(sorted_blocks) - 1):
            spacing = sorted_blocks[i + 1].y0 - sorted_blocks[i].y1
            if spacing > 0:
                spacings.append(spacing)
        
        if len(spacings) < 2:
            return False
        
        avg_spacing = sum(spacings) / len(spacings)
        if avg_spacing == 0:
            return False
        
        variance = sum((s - avg_spacing) ** 2 for s in spacings) / len(spacings)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg_spacing
        
        return cv < self.config["spacing_tolerance"]
    
    def _count_all_caps_spaced(self, blocks: List[TextBlock]) -> int:
        """Count blocks that are all-caps with large character spacing."""
        count = 0
        
        for block in blocks:
            text = block.text.strip()
            if not text or len(text) < 3:
                continue
            
            has_spaces = '  ' in text or (text.replace(' ', '').isupper() and len(text.split()) > 1)
            
            letters_only = ''.join(c for c in text if c.isalpha())
            is_all_caps = letters_only.isupper() if letters_only else False
            
            if is_all_caps and has_spaces:
                count += 1
        
        return count
    
    def get_detection_report(self, blocks: List[TextBlock]) -> Dict[str, Any]:
        """Generate detailed detection report."""
        signals = self.analyze_signals(blocks)
        needs = self.needs_visual_reassembly(blocks)
        
        return {
            "needs_visual_reassembly": needs,
            "signals": {
                "avg_words_per_block": round(signals.avg_words_per_block, 2),
                "vertical_alignment_count": signals.vertical_alignment_count,
                "all_caps_spaced_count": signals.all_caps_spaced_count,
                "has_short_fragments": signals.has_short_fragments,
                "has_uniform_spacing": signals.has_uniform_spacing,
                "total_blocks": signals.total_blocks
            },
            "triggers": {
                "low_avg_words": signals.avg_words_per_block < self.config["avg_words_threshold"],
                "vertical_alignment": (
                    signals.vertical_alignment_count >= self.config["vertical_count_threshold"]
                    and signals.has_uniform_spacing
                ),
                "all_caps_spaced": signals.all_caps_spaced_count >= self.config["caps_count_threshold"]
            }
        }
