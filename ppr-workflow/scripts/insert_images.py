import re
import os
import sys

def insert_images(md_file, img_dir):
    """
    基于论文常见的图注（如：> **图 X：XXX** 或 Figure X），自动在文本段落间插入对应的本地图片。
    确保图片存在后，生成 Markdown 内联引用。
    避免大模型偷懒直接略缩全文的问题。
    """
    if not os.path.exists(md_file) or not os.path.exists(img_dir):
        print("Usage: python insert_images.py <markdown_file> <image_directory>")
        sys.exit(1)

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 简单匹配“图 1” 或 “Figure 1” 格式，紧随数字
    # 可根据实际图注规范调整正则表达式：如 `> \*\*图\s*(\d+)：`
    pattern = re.compile(r'(图\s*(\d+[a-zA-Z]*)|Figure\s*(\d+[a-zA-Z]*))', re.IGNORECASE)
    
    # 查找本地可用的图片（简单假定图片名为 fig_X.png 或 figure_X.jpg 等等）
    available_imgs = os.listdir(img_dir)
    img_map = {}
    
    for img in available_imgs:
        m = re.search(r'(fig|figure)_?(\d+[a-zA-Z]*)', img, re.IGNORECASE)
        if m:
            num = m.group(2)
            img_map[str(num).lower()] = img
    
    lines = content.split('\n')
    new_lines = []
    inserted = set()

    for line in lines:
        new_lines.append(line)
        # 如果当前行是粗体重点或引用块，并且含有图 X 字眼
        if "> **图" in line or "**Figure" in line:
            m = pattern.search(line)
            if m:
                # 提取出具体的数字字母标识
                num = m.group(2) if m.group(2) else m.group(3)
                num = str(num).lower()
                
                # 如果这个图在本地有对应图片，并且还未被强行插入过（防止死循环插入）
                if num in img_map and img_map[num] not in inserted:
                    img_path = os.path.join(img_dir, img_map[num])
                    md_img = f"![图{num}]({img_path})"
                    new_lines.append(md_img)
                    inserted.add(img_map[num])
                    print(f"🖼 成功插入: {md_img}")
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n✅ 图片自动化挂载完成，共插入 {len(inserted)} 张图片。")

if __name__ == "__main__":
    if len(sys.argv) < 3:
         print("Usage: python insert_images.py <markdown_file> <image_directory>")
         sys.exit(1)
    insert_images(sys.argv[1], sys.argv[2])
