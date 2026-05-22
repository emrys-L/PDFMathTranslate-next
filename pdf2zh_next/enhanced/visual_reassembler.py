"""Visual semantic reassembler using multimodal LLM."""

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


@dataclass
class VisualAnalysisResult:
    """Result from visual analysis."""
    page_number: int
    has_fragmented_layout: bool
    has_vertical_text: bool
    reading_order: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: str = ""
    
    def get_merged_blocks(self, original_blocks: List[Any]) -> List[Dict[str, Any]]:
        """Convert visual analysis to merged block format."""
        merged = []
        
        for group in self.reading_order:
            fragment_ids = group.get("fragment_ids", [])
            
            if len(fragment_ids) == 1:
                merged.append({
                    "type": "single",
                    "block_id": fragment_ids[0],
                    "text": original_blocks[fragment_ids[0]].text if fragment_ids[0] < len(original_blocks) else ""
                })
            else:
                merged.append({
                    "type": "merged",
                    "block_ids": fragment_ids,
                    "text": group.get("merged_text", "")
                })
        
        return merged


class VisualSemanticReassembler:
    """Uses multimodal LLM to understand page layout and merge fragments."""
    
    def __init__(self, api_config: Optional[Dict[str, str]] = None):
        self.api_config = api_config or {
            "endpoint": "http://202.60.226.41:32788/v1/chat/completions",
            "model": "qwen35-397b-a17b",
            "api_key": "sSMCVe7TBAJPx0d0Ff4cB3569f7a41B7980bFd02888fA7A8"
        }
        
        self.config = {
            "image_zoom": 2.0,
            "max_retries": 3,
            "timeout": 120,
            "temperature": 0.3,
            "max_tokens": 4000
        }
    
    def analyze(self, page_or_image: Any, blocks: List[Any]) -> VisualAnalysisResult:
        """
        Analyze page layout and detect fragment relationships.
        
        Args:
            page_or_image: PDF page object or image path
            blocks: List of TextBlock objects
        
        Returns:
            VisualAnalysisResult with merged fragment groups
        """
        if isinstance(page_or_image, str):
            image_path = page_or_image
            image_base64 = self._encode_image(image_path)
        else:
            image_base64 = self._render_page_to_base64(page_or_image)
        
        block_info = self._extract_block_info(blocks)
        
        prompt = self._build_prompt(block_info)
        
        response = self._call_vision_api(image_base64, prompt)
        
        result = self._parse_response(response, len(blocks))
        
        return result
    
    def _render_page_to_base64(self, page) -> str:
        """Render PDF page to base64-encoded PNG."""
        zoom = self.config["image_zoom"]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        
        png_data = pix.tobytes("png")
        return base64.b64encode(png_data).decode("utf-8")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _extract_block_info(self, blocks: List[Any]) -> List[Dict[str, Any]]:
        """Extract block information for LLM prompt."""
        block_info = []
        
        for i, block in enumerate(blocks):
            block_info.append({
                "id": i,
                "text": block.text,
                "bbox": {
                    "x0": block.x0,
                    "y0": block.y0,
                    "x1": block.x1,
                    "y1": block.y1
                },
                "center": {
                    "x": (block.x0 + block.x1) / 2,
                    "y": (block.y0 + block.y1) / 2
                },
                "size": {
                    "width": block.x1 - block.x0,
                    "height": block.y1 - block.y0
                }
            })
        
        return block_info
    
    def _build_prompt(self, block_info: List[Dict[str, Any]]) -> str:
        """Build prompt for visual analysis."""
        return f"""请分析这个 PDF 页面的排版结构，识别哪些文本块在语义上属于同一句话或段落。

已知文本块信息：
{json.dumps(block_info, indent=2, ensure_ascii=False)}

特别注意：
1. 垂直排列的字母碎片（如 "S O M E W H E R E" 分成多行）应该合并为完整句子
2. 短文本块（<3 个单词）可能与相邻块属于同一段落
3. 相同字体/字号的分散块可能是同一段落
4. 识别阅读顺序（从上到下，从左到右）

请输出 JSON 格式：
{{
  "has_fragmented_layout": true/false,
  "has_vertical_text": true/false,
  "reading_order": [
    {{
      "group_id": "para_1",
      "type": "title|body|caption|label",
      "merged_text": "合并后的完整英文文本",
      "fragment_ids": [0, 1, 2],
      "layout_note": "垂直排列的标题"
    }}
  ]
}}

如果没有碎片化布局，reading_order 中每个 fragment_ids 只包含一个 ID。"""
    
    def _call_vision_api(self, image_base64: str, prompt: str) -> str:
        """Call multimodal vision API."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.api_config["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"]
        }
        
        for attempt in range(self.config["max_retries"]):
            try:
                response = requests.post(
                    self.api_config["endpoint"],
                    headers=headers,
                    json=payload,
                    timeout=self.config["timeout"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"API call failed (attempt {attempt + 1}): {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"API call error (attempt {attempt + 1}): {e}")
        
        raise RuntimeError(f"Failed to call vision API after {self.config['max_retries']} attempts")
    
    def _parse_response(self, response_text: str, block_count: int) -> VisualAnalysisResult:
        """Parse LLM response into VisualAnalysisResult."""
        try:
            json_match = self._extract_json(response_text)
            
            if not json_match:
                return self._create_fallback_result(block_count)
            
            data = json.loads(json_match)
            
            return VisualAnalysisResult(
                page_number=0,
                has_fragmented_layout=data.get("has_fragmented_layout", False),
                has_vertical_text=data.get("has_vertical_text", False),
                reading_order=data.get("reading_order", []),
                raw_response=response_text
            )
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return self._create_fallback_result(block_count)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from LLM response."""
        import re
        
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None
    
    def _create_fallback_result(self, block_count: int) -> VisualAnalysisResult:
        """Create fallback result (no merging)."""
        reading_order = [
            {
                "group_id": f"para_{i}",
                "type": "body",
                "merged_text": "",
                "fragment_ids": [i]
            }
            for i in range(block_count)
        ]
        
        return VisualAnalysisResult(
            page_number=0,
            has_fragmented_layout=False,
            has_vertical_text=False,
            reading_order=reading_order,
            raw_response=""
        )
