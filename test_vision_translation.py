#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

IMAGE_PATH = "/tmp/pdf_extract/images/page_1_physical_21_23.png"
OUTPUT_DIR = "/tmp/pdf_extract/vision_test"

API_ENDPOINTS = {
    "qwen": {
        "url": "http://202.60.226.41:32788/v1/chat/completions",
        "model": "qwen35-397b-a17b",
        "api_key": "sSMCVe7TBAJPx0d0Ff4cB3569f7a41B7980bFd02888fA7A8"
    },
    "minimax": {
        "url": "https://api.minimaxi.com/anthropic/v1/messages",
        "model": "MiniMax-M2.7",
        "api_key": "sk-cp-Hfog_S9Kz0esy9Ij_ir-lDsY94vw_X7Z3nevqPsJsz0VIwjeLW9AzVzC-rRX4KJh04Jei8HNCbZ470Ug_5nxE32nEwpN2DQEyjUL3JsxG_PdlV5aCqHXhvg4"
    },
    "claude": {
        "url": "https://max.ticketpro.cc/v1/messages",
        "model": "claude-opus-4-6",
        "api_key": "sk-79f1ed93ce767825e09578783fb1e2fdeac92ebca1b986495e4a242113a0d47d3"
    }
}

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def prepare_prompt() -> str:
    return """请详细分析这个国家地理杂志页面的完整内容：

1. **识别所有文字区域**：
   - 逐字逐句读出页面上的所有英文文字
   - 特别注意：垂直排列的字母（如 "S O M E W H E R E / I N / M I C H I G A N..."）应该识别为完整的一句话
   - 标注每段文字的位置（顶部/中部/底部/左侧/右侧）

2. **理解排版关系**：
   - 哪些文字属于同一个段落或句子？
   - 哪些文字是图片的标注或说明？
   - 文字之间的空间关系（上下、左右、环绕）

3. **翻译所有内容**：
   - 将识别出的完整句子翻译成中文
   - 保持原文的语义连贯性
   - 对于专业术语（如科学名词）保持准确

4. **输出格式**：
```
【区域 1】位置描述
原文：[完整的英文句子或段落]
译文：[流畅的中文翻译]

【区域 2】位置描述
原文：...
译文：...
```

请尽可能详细和准确，这是测试多模态模型对复杂排版的理解能力。"""

def call_qwen_vision_api(image_base64: str, prompt: str) -> dict:
    import requests
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_ENDPOINTS['qwen']['api_key']}"
    }
    
    payload = {
        "model": API_ENDPOINTS['qwen']['model'],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 4000,
        "temperature": 0.3
    }
    
    start_time = time.time()
    response = requests.post(
        API_ENDPOINTS['qwen']['url'],
        headers=headers,
        json=payload,
        timeout=120
    )
    elapsed_time = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        return {
            "success": True,
            "time": elapsed_time,
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {})
        }
    else:
        return {
            "success": False,
            "time": elapsed_time,
            "error": f"HTTP {response.status_code}: {response.text}"
        }

def save_results(results: dict, output_path: str):
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "vision_analysis_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "vision_analysis_text.md", "w", encoding="utf-8") as f:
        f.write("# 视觉模型分析结果\n\n")
        f.write(f"测试时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"处理耗时：{results.get('time', 0):.2f} 秒\n\n")
        f.write("---\n\n")
        if results.get("success"):
            f.write(results.get("content", ""))
        else:
            f.write(f"❌ 失败：{results.get('error', '未知错误')}\n")
    
    print(f"✅ 结果已保存到：{output_dir}")

def main():
    print("="*80)
    print("多模态视觉翻译测试 - 国家地理杂志第 21 页")
    print("="*80)
    print()
    
    image_path = Path(IMAGE_PATH)
    if not image_path.exists():
        print(f"❌ 图片文件不存在：{image_path}")
        return
    
    print(f"📷 测试图片：{image_path}")
    print(f"   文件大小：{image_path.stat().st_size / 1024 / 1024:.2f} MB")
    print()
    
    print("🔄 正在编码图片为 base64...")
    start_time = time.time()
    image_base64 = encode_image_to_base64(str(image_path))
    encode_time = time.time() - start_time
    print(f"   编码完成：{encode_time:.2f} 秒")
    print(f"   Base64 长度：{len(image_base64)} 字符")
    print()
    
    prompt = prepare_prompt()
    print("📝 Prompt 长度：", len(prompt), "字符")
    print()
    
    print("🚀 正在调用 Qwen 视觉 API...")
    print("   模型：", API_ENDPOINTS['qwen']['model'])
    print("   端点：", API_ENDPOINTS['qwen']['url'])
    print()
    
    result = call_qwen_vision_api(image_base64, prompt)
    
    print("="*80)
    print("测试结果")
    print("="*80)
    print(f"状态：{'✅ 成功' if result.get('success') else '❌ 失败'}")
    print(f"耗时：{result.get('time', 0):.2f} 秒")
    
    if result.get("success"):
        print("\n📄 分析结果预览：")
        print("-"*80)
        content = result.get("content", "")
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-"*80)
        
        save_results(result, OUTPUT_DIR)
        
        usage = result.get("usage", {})
        if usage:
            print("\n📊 Token 使用：")
            print(f"   输入：{usage.get('prompt_tokens', 0)}")
            print(f"   输出：{usage.get('completion_tokens', 0)}")
            print(f"   总计：{usage.get('total_tokens', 0)}")
    else:
        print(f"\n❌ 错误：{result.get('error', '未知错误')}")
    
    print()
    print("="*80)
    print("测试完成")
    print("="*80)

if __name__ == "__main__":
    main()
