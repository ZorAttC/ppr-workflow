---
name: ppr-workflow
description: 'Paper Parsing & Rendering (PPR) workflow. Use this to transform translated academic papers into polished, presentation-ready documents or blog posts. Triggers when asked to format, parse, render, or merge an academic paper translation with insights, images, and colloquial formula explanations.'
---

# Paper Parsing & Rendering (PPR) Workflow

## When to Use
- 将生涩的学术论文翻译件转化为高质量、可直接分享的讲稿或博客长文。
- 需要合并“原文直译”与“背景/Insight 解析”。
- 需要在长文中自动化插入本地图片并处理公式的通俗化解释。

## Procedure (五步工作流)

**重要准则 (Core Principle)**：在进行长篇 Markdown 合并、批量图片插入与查重时，应当优先使用或参考配套脚本，**避免由于大模型上下文阶段导致的“偷懒”或误删原文细节现象**。注意命名方式，默认保存在当前目录的papers/目录下。图片另起一个papers/paper_name/figures目录保存

### Step 1: 翻译与基础提取 (Translation & Baseline)
- 读取论文原始 HTML、LaTeX 或 Markdown 源文件。
- 进行忠实原文结构、公式与图表占位符的初步翻译。
- 产出物示例：`翻译_[paper_name].md`。

### Step 2: 讲稿与洞察生成 (Insight & Script Extraction)
- 在翻译基础上，跳出原论文的八股文框架，以“演讲者/分享者”视角提取核心痛点。
- 补充前置背景知识（例如领域痛点、历史方法的局限性等）。
- 提炼核心 Insight（如为什么选择特定的模型架构或强化学习奖励设计）。
- 产出物示例：`分享_[paper_name].md`。

### Step 3: 深度融合 (Deep Merging & Formatting)
- 将 Step 2 提炼的洞察与背景知识，深度且自然地融合回 Step 1 的主干翻译中。
- 避免简单的头尾拼接，应根据上下文插入到“引言”、“相关工作”或核心“方法”章节中。
- **推荐操作**：长文本合并时，大模型应使用 [safe_merge.py](./scripts/safe_merge.py) 进行断点无损拼接，严禁擅自使用省略号 `...` 缩减任何非相关段落。
- 产出物示例：`全文_[paper_name].md`。

### Step 4: 图像自动化集成 (Image Integration)
- 扫描本地图片目录（如 `figures/`）。
- 校验图片是否有重复（可通过辅助脚本 [check_duplicate_images.sh](./scripts/check_duplicate_images.sh) 避免指代同一图引发冗余）。
- 基于 Markdown 语法 `![图X](相对路径)` 将图片精准插入到融合文档的对应段落处，避免因手动替换导致文本损坏。
- **推荐操作**：可使用配套基建 [insert_images.py](./scripts/insert_images.py) 在含有图注的段落定点无损挂载内链。

### Step 5: 公式与生涩概念润色 (Formula Polish & Colloquial Explanation)
- 定位论文中复杂的数学公式或抽象概念。
- 使用高亮引用块（如 `> 💡 讲稿补注：...`）补充通俗化的大白话解释。
- 确保整篇文档从学术级向大众科普级顺滑过渡。