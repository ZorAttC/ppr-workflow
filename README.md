# ppr-workflow · DSH 兼容技能插件

**Paper Parsing & Rendering (PPR)** —— 把学术论文（arXiv HTML / PDF / Markdown）
加工成高可读性中文深度长文的 Agent 工作流。

本分支（`dsh`）已将原 Claude/Copilot 技能改造为 **DeepSeek Harness (DSH) 兼容插件**，
并新增两项能力：

1. 🆕 **首次安装时与用户确认输出文档的解析路径**
2. 🆕 **翻译字数审计闸门** —— 预测应有字数、检测漏译、定位缺口并强制补译

---

## 📦 安装

```bash
git clone -b dsh git@github.com:ZorAttC/ppr-workflow.git
cd ppr-workflow
bash install.sh
```

安装时会**交互式询问输出文档的解析路径**：

```
------------------------------------------------------------
📁 请确认「输出文档的解析路径」
------------------------------------------------------------
输出根目录 [默认: papers]: my_papers
图片子目录名 [默认: figures]: imgs

将采用以下布局：
  my_papers/<paper_name>/翻译_<paper_name>.md
  my_papers/<paper_name>/分享_<paper_name>.md
  my_papers/<paper_name>/全文_<paper_name>.md
  my_papers/<paper_name>/imgs/

确认以上路径设置？[Y/n]:
```

确认后写入 `config.json`，后续复用；重复安装会自动沿用既有配置。

### 安装选项

| 参数 | 说明 |
|---|---|
| （无） | 安装到用户级 `~/.dsh/skills` |
| `--project` | 安装到当前项目 `./.dsh/skills` |
| `--dir <path>` | 安装到自定义技能根目录 |
| `--output <path>` | 非交互指定输出根目录 |
| `--figures <name>` | 非交互指定图片子目录名 |
| `--force` | 覆盖已有安装 |
| `-y, --yes` | 全部采用默认值，不提问 |

### DSH 技能发现路径

DSH 按以下顺序扫描技能根目录，本技能安装为 `<root>/ppr-workflow/SKILL.md`：

| 优先级 | 来源 | 路径 |
|---|---|---|
| 100 | project-dsh | `<项目根>/.dsh/skills` |
| 200 | project-agents | `<项目根>/.agents/skills` |
| 400 | user-dsh | `~/.dsh/skills` |
| 500 | user-agents | `~/.agents/skills` |

---

## 🚀 使用

在 DSH 中直接唤起：

> 「使用 ppr-workflow 技能，帮我处理 https://arxiv.org/abs/XXXX」

Agent 会按六步法推进：

| 步骤 | 名称 | 产物 |
|---|---|---|
| 0 | 确认解析路径 | `config.json` |
| 1 | 翻译与基础提取 | `翻译_<paper>.md` |
| 2 | 讲稿与洞察生成 | `分享_<paper>.md` |
| 3 | 深度融合 | `全文_<paper>.md` |
| 4 | 图像自动化集成 | 内联图片 |
| 5 | 公式与概念润色 | `> 💡 讲稿补注` |
| 6 | **翻译字数审计** | `audit_report.json` |

---

## 🛡 翻译字数审计（防偷懒闸门）

大模型在长文翻译中最常见的失败模式是**悄悄缩略**：跳过段落、整章漏译、
用 `...` 顶替正文。Step 6 通过量化手段拦截这类行为。

### 原理

1. 解析源文档，统计可翻译正文的「计费单位」（英文按词、中文按字）。
2. 按膨胀系数预测译文应有字数：`预期 = 英文词数 × 1.6 + 中文字数`。
3. 统计实际译文字数，计算达成率 `coverage = 实际 / 预期`。
4. 达成率显著偏低即判定漏译，**逐章节定位缺口**并输出待补译清单。

公式、代码块、图片链接、HTML 标签均不计入（不属于翻译工作量）；
参考文献、致谢、附录默认豁免。

### 运行

```bash
python3 scripts/wordcount_audit.py \
    --source papers/foo/foo_source.html \
    --target papers/foo/翻译_foo.md \
    --json   papers/foo/audit_report.json
```

### 判定规则

| 信号 | 阈值 | 含义 |
|---|---|---|
| 全文达成率 | `< 0.85` | 译文整体显著弱于预期 |
| 单章节达成率 | `< 0.60` | 该章节疑似缩略或跳译 |
| 章节缺失 | 源文有、译文无 | 整章漏译 |
| 省略号占位 | 出现即失败 | `...`／`（略）` 顶替正文 |

退出码：`0` 通过 · `2` 需补译 · `1` 用法错误 —— 可直接用于 CI 卡关。

### 示例输出

```
📊 翻译字数审计报告 (Translation Word-Count Audit)
==================================================
预期字数 : 427 (膨胀系数 1.6)
实际字数 : 265
达成率   : 62.0%  (阈值 85%)
--------------------------------------------------
❌ 缺失章节 (1 个) —— 完全未翻译：
   • [Experiments] 预期 ~70 字，实际 0 字

⚠️  偏短章节 (1 个) —— 疑似缩略：
   • [Method] 预期 ~102 字，实际 13 字 (达成 13%)

🚫 省略号占位 (1 处) —— 严禁：
   • 第 13 行: ...

❗ 审计未通过：译文显著弱于预期，必须补充翻译。
```

命中后，Agent 必须回到源文档**只补缺失章节**（不重译全文），
用 `safe_merge.py` 定点回写，再重跑审计直到退出码为 `0`。

### 章节对齐说明

中英标题通过内置词典映射（`Introduction` ↔ `引言`、`Method` ↔ `方法` 等）；
词典未覆盖的标题（如论文标题本身、自定义小节）按**文档出现顺序**兜底对齐，
避免把正常翻译误报为漏译。

### 参数调优

| 参数 | 默认 | 说明 |
|---|---|---|
| `--ratio` | `1.6` | 英译中膨胀系数；日译中、术语密集文本可下调 |
| `--threshold` | `0.85` | 全文达成率阈值 |
| `--section-threshold` | `0.60` | 单章节达成率阈值 |

---

## 🧰 脚本一览

| 脚本 | 用途 |
|---|---|
| `scripts/wordcount_audit.py` | 🆕 字数审计，检测漏译/缩略/省略号占位 |
| `scripts/safe_merge.py` | 长文无损定点合并，防截断 |
| `scripts/insert_images.py` | 按图注定点挂载本地图片 |
| `scripts/check_duplicate_images.sh` | 图片 md5 查重 |

## 📂 仓库结构

```
.
├── SKILL.md              # DSH 技能定义（含 name/description/whenToUse 前置元数据）
├── install.sh            # 安装脚本，首次安装交互确认解析路径
├── config.example.json   # 配置模板
├── scripts/              # 辅助脚本群
└── AEGNTS.md             # 原始需求记录
```

## 📄 License

MIT
