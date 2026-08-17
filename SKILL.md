---
name: ppr-workflow
description: 'Paper Parsing & Rendering (PPR) 论文解析与排版工作流。把学术论文（arXiv HTML / PDF / Markdown）加工成高质量的中文深度长文：逐句翻译、洞察提炼、深度融合、图片内联、公式通俗化，并通过字数审计强制校验翻译完整性。当用户要求翻译、解析、精读、排版论文，或要求生成论文分享讲稿/博客时使用。'
whenToUse: '用户提供论文链接或文件，要求全文翻译、精读解析、生成分享讲稿或博客长文时。也用于检查既有译文是否存在漏译、缩略、跳章。'
---

# Paper Parsing & Rendering (PPR) Workflow

把生涩的一手文献加工成高可读性的中文深度长文。核心约束是**完整性**：
整个流程围绕「不许偷懒」设计，任何缩略、跳译、省略号占位都会被 Step 6 的
字数审计拦截并强制返工。

## Core Principles（必须遵守）

1. **严禁省略**：任何情况下不得用 `...`、`（略）`、`此处省略` 顶替正文。
   翻译是逐段落逐句的，不是摘要。
2. **严禁整文件重写**：长文修改一律用 `scripts/safe_merge.py` 做定点拼接，
   避免一次性重写导致其他章节静默丢失。
3. **量化验收**：Step 1 与 Step 3 产出后必须跑 `scripts/wordcount_audit.py`，
   达成率不达标就补译，不得进入下一步。
4. **路径统一**：所有产物写入安装时确认的输出根目录，不要散落在别处。

---

## Step 0: 确认输出解析路径（首次必做）

首次在一个工作区使用本技能时，**必须先确认输出文档的解析路径**，
不要擅自假定目录。

1. 读取技能目录下的 `config.json`。若存在，直接采用其中的
   `output_root` 与 `figures_dirname`，并向用户口头复述一次确认。
2. 若 `config.json` 不存在（未通过 `install.sh` 安装），**主动向用户提问**：

   > 请确认输出文档的解析路径：
   > - 输出根目录（默认 `papers`）
   > - 图片子目录名（默认 `figures`）

   等待用户回答后再继续，并把结果写入 `config.json` 以便后续复用。
3. 确定后建立目录结构：

```
<output_root>/<paper_name>/
├── <paper_name>_source.html      # 原始抓取源，供审计比对
├── 翻译_<paper_name>.md           # Step 1 产物
├── 分享_<paper_name>.md           # Step 2 产物
├── 全文_<paper_name>.md           # Step 3~5 最终交付
└── <figures_dirname>/            # 图片素材
```

> ⚠️ 源文件必须落盘保存。Step 6 的字数审计需要源文档做基准，
> 没有源文件就无法判断是否漏译。

---

## Step 1: 翻译与基础提取 (Translation & Baseline)

- 抓取论文原始 HTML/LaTeX/Markdown，**完整保存到本地**（不要只留在上下文里）。
- 逐章节、逐段落、逐句翻译，保留原文的标题层级、公式与图表占位符。
- 公式保持 LaTeX 原样，不翻译、不改写。
- 图片全部下载到 `<figures_dirname>/`。
- 产出：`翻译_<paper_name>.md`

**完成后立即执行审计（见 Step 6），达成率不达标必须先补译。**

---

## Step 2: 讲稿与洞察生成 (Insight & Script Extraction)

- 跳出论文的八股框架，以「分享者」视角重写。
- 补充前置背景知识（领域痛点、历史方法的局限性，如协变量偏移、DAgger 缺陷等）。
- 提炼核心 Insight：为什么是这个架构？奖励为什么这样设计？
- 产出：`分享_<paper_name>.md`

---

## Step 3: 深度融合 (Deep Merging)

- 把 Step 2 的洞察**定点嵌入** Step 1 主干翻译的对应章节，而非头尾拼接。
- 使用 `scripts/safe_merge.py` 做无损拼接：

```bash
python3 scripts/safe_merge.py \
    翻译_<paper>.md 分享_<paper>.md 全文_<paper>.md "## 引言"
```

- 产出：`全文_<paper_name>.md`

**融合后再次执行审计**：全文稿字数应 ≥ 翻译稿（因为叠加了洞察），
若反而变短，说明合并过程吃掉了原文，必须排查。

---

## Step 4: 图像自动化集成 (Image Integration)

```bash
bash scripts/check_duplicate_images.sh <output_root>/<paper>/<figures>
python3 scripts/insert_images.py 全文_<paper>.md <output_root>/<paper>/<figures>
```

- 先查重，避免同一张图被重复挂载。
- 再按图注定点插入 `![图X](相对路径)`。

---

## Step 5: 公式与生涩概念润色 (Formula Polish)

- 定位复杂公式与抽象概念，用高亮引用块补充大白话解释：

```markdown
> 💡 讲稿补注：这个式子说白了就是……
```

- 确保全文从学术腔顺滑过渡到科普腔。

---

## Step 6: 翻译字数审计 (Word-Count Audit) — 防偷懒闸门

这是本工作流的**强制质量门禁**。原理：先根据源文档预测「翻译完成后
应有的字数」，再与实际译文对比；显著偏低即判定为漏译，并逐章节定位缺口。

### 运行

```bash
python3 scripts/wordcount_audit.py \
    --source <output_root>/<paper>/<paper>_source.html \
    --target <output_root>/<paper>/翻译_<paper>.md \
    --json   <output_root>/<paper>/audit_report.json
```

### 预期字数模型

- 英文按**词**计，中文按**字**计，统称「计费单位」。
- 英译中膨胀系数默认 **1.6**（1 个英文词 ≈ 1.6 个中文字）。
- 数学公式、代码块、图片链接、HTML 标签均不计入（这些不属于翻译工作量）。
- 参考文献、致谢、附录默认豁免逐字翻译。

### 判定规则

| 信号 | 阈值 | 含义 |
|---|---|---|
| 全文达成率 | `< 0.85` | 译文整体显著弱于预期 |
| 单章节达成率 | `< 0.60` | 该章节疑似缩略或跳译 |
| 章节缺失 | 源文有、译文无 | 整章漏译 |
| 省略号占位 | 出现即失败 | `...`／`（略）` 顶替正文 |

退出码：`0` 通过，`2` 未通过（需补译），`1` 用法错误。

### 未通过时的补救流程（必须执行，不得跳过）

1. 读取报告中的 `missing_sections` 与 `weak_sections`，拿到**具体缺哪些章节**。
2. 回到源文档，定位这些章节的原文。
3. **逐段落补全翻译**——只补缺失部分，不要重译全文。
4. 用 `safe_merge.py` 或定点 edit 把补译内容写回原文档对应位置，
   **严禁整文件覆盖重写**。
5. 重新运行审计，直到退出码为 `0`。
6. 若连续两轮仍不达标，向用户报告具体卡点，不要伪装成功。

> ⚠️ 达成率是启发式指标，不是绝对真理。若某章节确实因为原文是
> 大段表格/公式/参考文献而合理偏短，在报告中说明理由即可，
> 但**必须逐条解释**，不允许笼统地宣称"已检查无问题"。

---

## Scripts 一览

| 脚本 | 用途 |
|---|---|
| [wordcount_audit.py](./scripts/wordcount_audit.py) | 字数审计，检测漏译/缩略/省略号占位 |
| [safe_merge.py](./scripts/safe_merge.py) | 长文无损定点合并，防截断 |
| [insert_images.py](./scripts/insert_images.py) | 按图注定点挂载本地图片 |
| [check_duplicate_images.sh](./scripts/check_duplicate_images.sh) | 图片 md5 查重 |

## 交付前自检清单

- [ ] 输出路径已与用户确认，产物均在 `<output_root>` 下
- [ ] 源文档已落盘保存
- [ ] `翻译_*.md` 审计退出码为 0
- [ ] `全文_*.md` 字数 ≥ `翻译_*.md`
- [ ] 全文无 `...`／`（略）` 占位
- [ ] 图片无重复且已正确内联
- [ ] 复杂公式均有 `> 💡 讲稿补注`
