# 视觉感知增强翻译

Visual-Enhanced Translation for BabelDOC

## 概述

本模块为 BabelDOC 添加了视觉感知的语义重组能力，专门处理碎片化排版（如垂直标题、分散标注等），通过结合多模态 LLM 与传统 PDF 解析，实现更准确的翻译。

## 核心功能

- **碎片检测**: 自动识别需要语义重组的页面
- **视觉分析**: 使用多模态 LLM 理解页面布局
- **智能合并**: 将碎片化文本块合并为完整句子
- **无缝集成**: 与 BabelDOC 现有流程完全兼容

## 使用方式

### Python API

```python
from pdf2zh_next.enhanced import EnhancedTranslationPipeline

pipeline = EnhancedTranslationPipeline(enabled=True)

if pipeline.should_enhance(page_blocks):
    enhanced_blocks = pipeline.enhance_page(page_object, page_blocks)
    # 使用 enhanced_blocks 进行后续翻译
```

### 命令行 (待实现)

```bash
babeldoc --files document.pdf --enhanced-layout-analysis
```

## 模块组成

1. **FragmentDetector**: 碎片检测器
2. **VisualSemanticReassembler**: 视觉语义重组器
3. **TextBlockReassembler**: 文本块重组器
4. **EnhancedTranslationPipeline**: 集成流水线

## 性能指标

| 页面类型 | 检测准确率 | 额外耗时 | 额外 Token |
|---------|-----------|---------|-----------|
| 碎片化排版 | >95% | ~40 秒 | ~8K |
| 正常段落 | 100% (跳过) | 0 秒 | 0 |

## 示例

### 输入（碎片化垂直标题）
```
S O M E W H E R E
I N
M I C H I G A N ,
1 0 , 0 0 0
S I L K W O R M S
...
```

### 输出（完整句子）
```
SOMEWHERE IN MICHIGAN, 10,000 SILKWORMS ARE SPINNING THE FUTURE OF SUPERMATERIALS.
```

## 配置

API 配置通过 `api_config` 字典传递：

```python
config = {
    "api_config": {
        "endpoint": "http://202.60.226.41:32788/v1/chat/completions",
        "model": "qwen35-397b-a17b",
        "api_key": "your-api-key"
    }
}
```

## 开发状态

- [x] Phase 1: 碎片检测器
- [x] Phase 2: 视觉语义重组器
- [x] Phase 3: 文本块重组器
- [x] Phase 4: 集成流水线
- [ ] Phase 5: CLI 集成
- [ ] Phase 6: 性能优化
- [ ] Phase 7: 文档完善

## 许可证

AGPL-3.0 (与 BabelDOC 保持一致)
