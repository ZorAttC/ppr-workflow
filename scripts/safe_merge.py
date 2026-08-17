import os
import sys

def safe_merge(base_file, insight_file, output_file, anchor_text=None):
    """
    将洞察内容安全地合并到主翻译文档中，防止大模型由于 token 限制截断内容。
    如果不提供 anchor_text，则默认追加到文件末尾或特定章节。
    """
    if not os.path.exists(base_file) or not os.path.exists(insight_file):
        print(f"Error: {base_file} or {insight_file} does not exist.")
        sys.exit(1)

    with open(base_file, 'r', encoding='utf-8') as f:
        base_content = f.read()
    
    with open(insight_file, 'r', encoding='utf-8') as f:
        insight_content = f.read()

    # 如果有锚点，则在其后插入
    if anchor_text and anchor_text in base_content:
        parts = base_content.split(anchor_text, 1)
        merged_content = parts[0] + anchor_text + "\n\n" + insight_content + "\n\n" + parts[1]
        print(f"✅ 成功于锚点 '{anchor_text}' 处插入洞察内容。")
    else:
        # 默认追加
        merged_content = base_content + "\n\n" + insight_content
        print("✅ 未指定或未找到锚点，内容已追加至文档末尾。")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    
    print(f"📄 合并完成，已输出至: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python safe_merge.py <base_md> <insight_md> <output_md> [anchor_text]")
        sys.exit(1)
    
    anchor = sys.argv[4] if len(sys.argv) > 4 else None
    safe_merge(sys.argv[1], sys.argv[2], sys.argv[3], anchor)
