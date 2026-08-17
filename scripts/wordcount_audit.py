#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译字数审计 (Translation Word-Count Audit)
============================================

目的：防止 Agent 在长文翻译中“偷懒”——跳过段落、用省略号缩写、
或整章漏译。本脚本通过“预期字数模型”对翻译产物做量化体检。

工作原理
--------
1. 解析源文档（HTML / Markdown / 纯文本），统计其可翻译正文的
   计费单位数（英文按词计，中文按字计）。
2. 按膨胀系数（expansion ratio）预测翻译后应有的字数。
   英文 -> 中文：1 个英文词 ≈ 1.6 个中文字（默认，可配置）。
3. 统计实际译文字数，计算达成率 coverage = actual / expected。
4. 若达成率低于阈值（默认 0.85），判定为“显著弱于预期”，
   并逐章节（section）定位缺口，输出待补译清单。

退出码
------
0  通过（达成率 >= 阈值，且无缺失章节）
2  未通过（存在明显漏译，需要补充翻译）
1  用法/IO 错误

用法
----
    python wordcount_audit.py --source paper.html --target 翻译_paper.md
    python wordcount_audit.py --source paper.html --target 翻译_paper.md \
        --ratio 1.6 --threshold 0.85 --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field

# --------------------------------------------------------------------------
# 文本抽取
# --------------------------------------------------------------------------

# 需要从源文档中剔除的非正文区域（不计入翻译工作量）
_HTML_DROP_BLOCKS = re.compile(
    r"<(script|style|noscript|svg|math)\b.*?</\1>", re.IGNORECASE | re.DOTALL
)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")

# arXiv HTML 中常见的非正文尾部区域
_HTML_BOILERPLATE = re.compile(
    r"<(footer|nav|header)\b.*?</\1>", re.IGNORECASE | re.DOTALL
)

_MD_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_MD_INLINE_CODE = re.compile(r"`[^`\n]+`")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_HTML_TAG = re.compile(r"<[^>]+>")

# 数学公式：不计入翻译字数（公式本身不翻译）
_MATH_BLOCK = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_MATH_INLINE = re.compile(r"\$[^$\n]+\$")
_LATEX_ENV = re.compile(
    r"\\begin\{(equation|align|gather|displaymath)\*?\}.*?"
    r"\\end\{\1\*?\}",
    re.DOTALL,
)

_HTML_ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")

CJK_RANGE = (
    "\u4e00-\u9fff"      # CJK 统一表意文字
    "\u3400-\u4dbf"      # 扩展 A
    "\uf900-\ufaff"      # 兼容表意文字
)
_CJK_CHAR = re.compile(f"[{CJK_RANGE}]")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def strip_html(text: str) -> str:
    """将 HTML 源文档还原为纯正文文本。"""
    text = _HTML_COMMENT.sub(" ", text)
    text = _HTML_DROP_BLOCKS.sub(" ", text)
    text = _HTML_BOILERPLATE.sub(" ", text)
    text = _HTML_TAG.sub(" ", text)
    text = _HTML_ENTITY.sub(" ", text)
    return text


def strip_markdown(text: str) -> str:
    """将 Markdown 还原为纯正文文本（保留链接锚文本）。"""
    text = _MD_CODE_FENCE.sub(" ", text)
    text = _MD_IMAGE.sub(" ", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_INLINE_CODE.sub(" ", text)
    text = _MD_HTML_TAG.sub(" ", text)
    return text


def strip_math(text: str) -> str:
    """剔除数学公式，公式不属于翻译工作量。"""
    text = _LATEX_ENV.sub(" ", text)
    text = _MATH_BLOCK.sub(" ", text)
    text = _MATH_INLINE.sub(" ", text)
    return text


def normalize(path: str, raw: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm", ".xhtml"):
        body = strip_html(raw)
    elif ext in (".md", ".markdown"):
        body = strip_markdown(raw)
    else:
        body = raw
    return strip_math(body)


# --------------------------------------------------------------------------
# 计数
# --------------------------------------------------------------------------


@dataclass
class Count:
    """一段文本的计费单位统计。"""

    cjk_chars: int = 0
    latin_words: int = 0

    @property
    def units(self) -> int:
        """归一化的“计费单位”：中文按字，英文按词。"""
        return self.cjk_chars + self.latin_words

    def __add__(self, other: "Count") -> "Count":
        return Count(
            self.cjk_chars + other.cjk_chars,
            self.latin_words + other.latin_words,
        )


def count_text(text: str) -> Count:
    return Count(
        cjk_chars=len(_CJK_CHAR.findall(text)),
        latin_words=len(_LATIN_WORD.findall(text)),
    )


# --------------------------------------------------------------------------
# 章节切分：用于定位“缺少的翻译项目”
# --------------------------------------------------------------------------

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_HTML_HEADING = re.compile(
    r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL
)

# 归一化标题以便跨语言/跨格式匹配：去掉编号、标点、空白
_HEADING_NOISE = re.compile(r"[\s0-9.．、,:：;；()（）\[\]【】\-—_*#`]+")

# 常见章节标题的中英对照，用于把英文源标题映射到中文译文标题
_CANONICAL = {
    "abstract": "abstract", "摘要": "abstract",
    "introduction": "introduction", "引言": "introduction", "简介": "introduction",
    "relatedwork": "relatedwork", "相关工作": "relatedwork",
    "method": "method", "methods": "method", "methodology": "method",
    "方法": "method", "方法论": "method",
    "approach": "method", "我们的方法": "method",
    "experiment": "experiment", "experiments": "experiment",
    "实验": "experiment", "实验设置": "experiment",
    "result": "result", "results": "result", "结果": "result",
    "ablation": "ablation", "ablationstudy": "ablation", "消融实验": "ablation",
    "消融": "ablation", "消融研究": "ablation",
    "discussion": "discussion", "讨论": "discussion",
    "conclusion": "conclusion", "结论": "conclusion",
    "limitation": "limitation", "limitations": "limitation", "局限性": "limitation",
    "appendix": "appendix", "附录": "appendix",
    "acknowledgment": "acknowledgment", "acknowledgments": "acknowledgment",
    "acknowledgement": "acknowledgment", "致谢": "acknowledgment",
    "reference": "reference", "references": "reference", "参考文献": "reference",
}

# 这些章节通常无需逐字翻译，不计入缺口告警
SKIPPABLE = {"reference", "acknowledgment", "appendix"}


def canonical_key(title: str) -> str:
    """把章节标题归一化成可跨语言比较的键。"""
    flat = _HEADING_NOISE.sub("", title).lower()
    return _CANONICAL.get(flat, flat)


@dataclass
class Section:
    title: str
    key: str
    level: int
    count: Count = field(default_factory=Count)


def split_sections(path: str, raw: str) -> list[Section]:
    """按标题切分文档，返回每个章节及其正文计数。"""
    ext = os.path.splitext(path)[1].lower()
    is_html = ext in (".html", ".htm", ".xhtml")

    if is_html:
        matches = [
            (m.start(), m.end(), int(m.group(1)), _HTML_TAG.sub("", m.group(2)))
            for m in _HTML_HEADING.finditer(raw)
        ]
    else:
        matches = [
            (m.start(), m.end(), len(m.group(1)), m.group(2))
            for m in _MD_HEADING.finditer(raw)
        ]

    sections: list[Section] = []
    if not matches:
        body = normalize(path, raw)
        return [Section("(整篇文档)", "__whole__", 0, count_text(body))]

    # 标题之前的前言部分
    preamble = raw[: matches[0][0]]
    if preamble.strip():
        c = count_text(normalize(path, preamble))
        if c.units > 0:
            sections.append(Section("(前言)", "__preamble__", 0, c))

    for i, (_, end, level, title) in enumerate(matches):
        stop = matches[i + 1][0] if i + 1 < len(matches) else len(raw)
        body = normalize(path, raw[end:stop])
        title = title.strip()
        sections.append(
            Section(title, canonical_key(title), level, count_text(body))
        )
    return sections


# --------------------------------------------------------------------------
# 审计
# --------------------------------------------------------------------------


def expected_units(source: Count, ratio: float) -> float:
    """
    预测翻译后应有的字数（计费单位）。

    英文词 -> 中文字：乘以 ratio（默认 1.6）。
    源文中已有的 CJK 字符按 1:1 计入（通常是引文或术语）。
    """
    return source.latin_words * ratio + source.cjk_chars


def audit(
    source_path: str,
    target_path: str,
    ratio: float,
    threshold: float,
    section_threshold: float,
) -> dict:
    with open(source_path, "r", encoding="utf-8", errors="replace") as f:
        source_raw = f.read()
    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
        target_raw = f.read()

    src_total = count_text(normalize(source_path, source_raw))
    tgt_total = count_text(normalize(target_path, target_raw))

    expected = expected_units(src_total, ratio)
    actual = float(tgt_total.units)
    coverage = (actual / expected) if expected > 0 else 1.0

    # ---- 章节级缺口定位 ----
    src_sections = split_sections(source_path, source_raw)
    tgt_sections = split_sections(target_path, target_raw)

    tgt_by_key: dict[str, Count] = {}
    for s in tgt_sections:
        tgt_by_key[s.key] = tgt_by_key.get(s.key, Count()) + s.count

    # 论文标题、自定义小节等无法靠词典跨语言匹配，改用「文档顺序」兜底：
    # 把两侧未被词典命中的章节按出现次序一一对齐，避免误报为漏译。
    src_unmatched = [
        s
        for s in src_sections
        if not s.key.startswith("__")
        and s.key not in SKIPPABLE
        and s.key not in tgt_by_key
    ]
    tgt_unmatched = [
        s
        for s in tgt_sections
        if not s.key.startswith("__")
        and s.key not in SKIPPABLE
        and s.key not in {x.key for x in src_sections}
    ]
    positional: dict[str, Count] = {}
    for src_sec, tgt_sec in zip(src_unmatched, tgt_unmatched):
        positional[src_sec.key] = tgt_sec.count

    missing: list[dict] = []
    weak: list[dict] = []

    for s in src_sections:
        if s.key in SKIPPABLE or s.key.startswith("__"):
            continue
        s_expected = expected_units(s.count, ratio)
        # 过短的章节噪声太大，不做单独判定
        if s_expected < 50:
            continue

        if s.key in tgt_by_key:
            matched = tgt_by_key[s.key]
        elif s.key in positional:
            matched = positional[s.key]
        else:
            missing.append(
                {
                    "title": s.title,
                    "key": s.key,
                    "expected_units": round(s_expected),
                    "actual_units": 0,
                    "coverage": 0.0,
                    "reason": "译文中未找到对应章节标题",
                }
            )
            continue

        s_actual = float(matched.units)
        s_cov = s_actual / s_expected if s_expected > 0 else 1.0
        if s_cov < section_threshold:
            weak.append(
                {
                    "title": s.title,
                    "key": s.key,
                    "expected_units": round(s_expected),
                    "actual_units": round(s_actual),
                    "coverage": round(s_cov, 3),
                    "reason": "章节存在但正文明显偏短，疑似缩略或跳译",
                }
            )

    # ---- 偷懒信号：省略号占位 ----
    ellipsis_hits = []
    for lineno, line in enumerate(target_raw.splitlines(), 1):
        stripped = line.strip()
        # 只匹配“整行/段落被省略号顶替”的可疑形态
        if re.fullmatch(r"[>*\s]*(\.{3,}|…+|\(略\)|（略）|\[省略\])[>*\s]*", stripped):
            ellipsis_hits.append({"line": lineno, "text": stripped[:120]})

    passed = (
        coverage >= threshold and not missing and not weak and not ellipsis_hits
    )

    return {
        "source": source_path,
        "target": target_path,
        "ratio": ratio,
        "threshold": threshold,
        "section_threshold": section_threshold,
        "source_count": asdict(src_total),
        "target_count": asdict(tgt_total),
        "expected_units": round(expected),
        "actual_units": round(actual),
        "coverage": round(coverage, 3),
        "missing_sections": missing,
        "weak_sections": weak,
        "ellipsis_placeholders": ellipsis_hits,
        "passed": passed,
    }


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------


def render(report: dict) -> str:
    L: list[str] = []
    A = L.append
    cov_pct = report["coverage"] * 100
    thr_pct = report["threshold"] * 100

    A("=" * 66)
    A("📊 翻译字数审计报告 (Translation Word-Count Audit)")
    A("=" * 66)
    A(f"源文档   : {report['source']}")
    A(f"译文档   : {report['target']}")
    sc, tc = report["source_count"], report["target_count"]
    A(f"源文统计 : {sc['latin_words']} 英文词 + {sc['cjk_chars']} 中文字")
    A(f"译文统计 : {tc['cjk_chars']} 中文字 + {tc['latin_words']} 英文词")
    A("-" * 66)
    A(f"预期字数 : {report['expected_units']} (膨胀系数 {report['ratio']})")
    A(f"实际字数 : {report['actual_units']}")
    A(f"达成率   : {cov_pct:.1f}%  (阈值 {thr_pct:.0f}%)")
    A("-" * 66)

    if report["missing_sections"]:
        A(f"❌ 缺失章节 ({len(report['missing_sections'])} 个) —— 完全未翻译：")
        for s in report["missing_sections"]:
            A(f"   • [{s['title']}] 预期 ~{s['expected_units']} 字，实际 0 字")
        A("")

    if report["weak_sections"]:
        A(f"⚠️  偏短章节 ({len(report['weak_sections'])} 个) —— 疑似缩略：")
        for s in report["weak_sections"]:
            A(
                f"   • [{s['title']}] 预期 ~{s['expected_units']} 字，"
                f"实际 {s['actual_units']} 字 (达成 {s['coverage']*100:.0f}%)"
            )
        A("")

    if report["ellipsis_placeholders"]:
        A(f"🚫 省略号占位 ({len(report['ellipsis_placeholders'])} 处) —— 严禁：")
        for h in report["ellipsis_placeholders"]:
            A(f"   • 第 {h['line']} 行: {h['text']}")
        A("")

    if report["passed"]:
        A("✅ 审计通过：译文字数符合预期，未发现漏译或缩略迹象。")
    else:
        A("❗ 审计未通过：译文显著弱于预期，必须补充翻译。")
        A("")
        A("👉 补救步骤：")
        A("   1. 打开上面列出的每个缺失/偏短章节，回到源文档对照。")
        A("   2. 逐段落逐句补全翻译，不得使用 '...' 或 '(略)' 占位。")
        A("   3. 用 safe_merge.py 回写，避免整文件重写导致其他章节丢失。")
        A("   4. 重新运行本脚本，直到达成率 >= 阈值且无缺失章节。")
    A("=" * 66)
    return "\n".join(L)


def main() -> int:
    p = argparse.ArgumentParser(
        description="审计翻译产物的字数完整性，检测漏译与缩略。"
    )
    p.add_argument("--source", required=True, help="源文档 (HTML/Markdown/TXT)")
    p.add_argument("--target", required=True, help="译文档 (Markdown)")
    p.add_argument(
        "--ratio",
        type=float,
        default=1.6,
        help="英文词 -> 中文字 的膨胀系数 (默认 1.6)",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="全文达成率阈值 (默认 0.85)",
    )
    p.add_argument(
        "--section-threshold",
        type=float,
        default=0.60,
        help="单章节达成率阈值 (默认 0.60)",
    )
    p.add_argument("--json", help="将报告写入指定 JSON 文件")
    args = p.parse_args()

    for path in (args.source, args.target):
        if not os.path.isfile(path):
            print(f"Error: 文件不存在: {path}", file=sys.stderr)
            return 1

    report = audit(
        args.source,
        args.target,
        args.ratio,
        args.threshold,
        args.section_threshold,
    )
    print(render(report))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 JSON 报告已写入: {args.json}")

    return 0 if report["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
