# ActiveVLN Paper Parsing & Rendering (PPR) 

本项目包含了对具身智能前沿工作 *ActiveVLN: Towards Active Exploration via Multi-Turn RL in Vision-and-Language Navigation* 的深度翻译、解析与排版，同时作为 **PPR (Paper Parsing & Rendering) 工作流** 的标准跑通案例与技能库库源。

## 📂 项目结构

- **`activevln_arxiv.html`**: 论文原始 HTML 源文件（抓取自 arXiv）。
- **`figures_activevln/`**: 论文对应的原始配图存放目录。
- **`翻译_activevln.md`**: 阶段一产物，包含对原论文细致的结构化直译。
- **`分享_activevln.md`**: 阶段二产物，提取出的核心 insight、痛点背景以及面向读者的讲稿总结。
- **`全文_activevln.md`**: 阶段三～五的最终交付物，将直译内容与洞察深度融合，并完成了图片内联排版与复杂公式（如 GRPO 奖励机制）的大白话解析。
- **`.github/skills/ppr-workflow/`**: 在本项目中沉淀的 PPR 通用工作流 Agent Skill。包含：
  - `SKILL.md`: 技能流程定义与约束。
  - `scripts/`目录: 辅助防截断脚本群（如安全合并 `safe_merge.py`、图片排雷验重 `check_duplicate_images.sh`、内联自动化挂载 `insert_images.py`），能极大地预防 AI 在长文本合并操作中“偷懒缩略（...）”的普遍痛点。

## 🚀 PPR (Paper Parsing & Rendering) 核心工作流

通过本项目的实践，我们总结并封装了一套标准的 AI 辅助学术论文沉淀工作流。你可以在 `.github/skills/ppr-workflow/SKILL.md` 查看具体定义，主要分为五个固定节奏：

1. **翻译与基础提取（Translation）**：保留原格式与公式，完成基础本地化翻译。
2. **洞察与讲稿生成（Insight Extraction）**：提炼论文痛点与核心贡献，通俗化补充必要的背景知识（例如协变量偏移、DAgger 局限性等）。
3. **深度结构融合（Deep Merging）**：将讲稿中的精华 Insight 无缝定点嵌入到原翻译对应的章节中，摈弃生硬堆砌。
4. **图像自动化集成（Image Integration）**：对本地图像素材进行排查比对（跨过重复文件陷阱），并通过正则或脚本精准插入长文本对应的上下文。
5. **公式与概念通俗化（Formula Polish）**：使用特定高亮格式（如 `> 💡 讲稿补注`）定点拦截生涩的数学公式，转化输出为人类直觉视角的解释。

## 🛠 如何复用 PPR Skill

如果在 VS Code 中开启了 GitHub Copilot，你可以唤起 Agent，让其直接应用当前项目下的 `ppr-workflow` 技能。
未来，当你面临新的学术论文（HTML/PDF），只需抛出一句：
> “使用 ppr-workflow 技能，帮我处理 XXX 论文…”

Agent 即可按照上述五步法稳步推进，自动化、大规模地帮你把干涩的一手文献加工成为高可读性、高分发价值的深度长文。