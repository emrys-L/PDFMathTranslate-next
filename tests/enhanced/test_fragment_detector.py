"""Tests for fragment detector."""

import pytest
from pdf2zh_next.enhanced.fragment_detector import FragmentDetector, TextBlock


class TestFragmentDetector:
    
    @pytest.fixture
    def detector(self):
        return FragmentDetector()
    
    @pytest.fixture
    def vertical_title_blocks(self):
        return [
            TextBlock(id=i, text=t, x0=270+i, y0=200+i*14, x1=330, y1=210+i*14)
            for i, t in enumerate([
                'S O M E W H E R E', 'I N', 'M I C H I G A N ,',
                '1 0 , 0 0 0', 'S I L K W O R M S', 'A R E',
                'S P I N N I N G', 'T H E', 'F U T U R E', 'O F',
                'S U P E R M A T E R I A L S .'
            ])
        ]
    
    @pytest.fixture
    def normal_paragraph_block(self):
        return [
            TextBlock(
                id=0,
                text='Spider silk owes its special powers to both a unique molecular structure.',
                x0=56, y0=105, x1=257, y1=156
            )
        ]
    
    def test_detects_vertical_title(self, detector, vertical_title_blocks):
        assert detector.needs_visual_reassembly(vertical_title_blocks) is True
    
    def test_skips_normal_paragraph(self, detector, normal_paragraph_block):
        assert detector.needs_visual_reassembly(normal_paragraph_block) is False
    
    def test_detection_report_vertical(self, detector, vertical_title_blocks):
        report = detector.get_detection_report(vertical_title_blocks)
        
        assert report['needs_visual_reassembly'] is True
        assert report['signals']['vertical_alignment_count'] >= 5
        assert report['triggers']['vertical_alignment'] is True
    
    def test_detection_report_normal(self, detector, normal_paragraph_block):
        report = detector.get_detection_report(normal_paragraph_block)
        
        assert report['needs_visual_reassembly'] is False
        assert report['signals']['avg_words_per_block'] > 3
        assert all(not v for v in report['triggers'].values())
