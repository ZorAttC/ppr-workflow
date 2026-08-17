#!/usr/bin/env bash
# ============================================================================
# ppr-workflow · DSH 技能安装脚本
# ============================================================================
# 将本技能安装到 DSH 可发现的技能根目录，并在首次安装时与用户确认
# 「输出文档的解析路径」(papers 根目录 / 图片子目录)。
#
# 用法:
#   bash install.sh                 # 交互式安装到用户级 (~/.dsh/skills)
#   bash install.sh --project       # 安装到当前项目 (./.dsh/skills)
#   bash install.sh --dir <path>    # 安装到自定义技能根目录
#   bash install.sh --output <path> # 非交互指定解析路径
#   bash install.sh --force         # 覆盖已存在的安装
# ============================================================================

set -euo pipefail

SKILL_NAME="ppr-workflow"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
TARGET_ROOT=""
OUTPUT_PATH=""
FIGURES_DIRNAME=""
FORCE=0
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  TARGET_ROOT="$(pwd)/.dsh/skills"; shift ;;
    --dir)      TARGET_ROOT="$2"; shift 2 ;;
    --output)   OUTPUT_PATH="$2"; shift 2 ;;
    --figures)  FIGURES_DIRNAME="$2"; shift 2 ;;
    --force)    FORCE=1; shift ;;
    --yes|-y)   ASSUME_YES=1; shift ;;
    -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$TARGET_ROOT" ]] && TARGET_ROOT="$DSH_HOME/skills"
DEST="$TARGET_ROOT/$SKILL_NAME"
CONFIG_FILE="$DEST/config.json"

echo "============================================================"
echo "  ppr-workflow · Paper Parsing & Rendering"
echo "  DSH Agent Skill 安装程序"
echo "============================================================"
echo "技能源目录 : $SRC_DIR"
echo "安装目标   : $DEST"
echo ""

# ---------------------------------------------------------------------------
# 首次安装：与用户确认输出文档的解析路径
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT="papers"
DEFAULT_FIGURES="figures"

if [[ -f "$CONFIG_FILE" && $FORCE -eq 0 ]]; then
  echo "ℹ️  检测到已有配置，沿用现有解析路径设置："
  cat "$CONFIG_FILE"
  echo ""
  EXISTING=1
else
  EXISTING=0
fi

if [[ $EXISTING -eq 0 ]]; then
  if [[ -z "$OUTPUT_PATH" ]]; then
    if [[ $ASSUME_YES -eq 1 || ! -t 0 ]]; then
      OUTPUT_PATH="$DEFAULT_OUTPUT"
      echo "非交互模式，使用默认输出根目录: $OUTPUT_PATH"
    else
      echo "------------------------------------------------------------"
      echo "📁 请确认「输出文档的解析路径」"
      echo "------------------------------------------------------------"
      echo "该路径决定 PPR 工作流把翻译稿、讲稿、全文稿写到哪里。"
      echo "可填相对路径（相对于运行 Agent 时的工作目录）或绝对路径。"
      echo ""
      read -r -p "输出根目录 [默认: $DEFAULT_OUTPUT]: " OUTPUT_PATH
      OUTPUT_PATH="${OUTPUT_PATH:-$DEFAULT_OUTPUT}"
    fi
  fi

  if [[ -z "$FIGURES_DIRNAME" ]]; then
    if [[ $ASSUME_YES -eq 1 || ! -t 0 ]]; then
      FIGURES_DIRNAME="$DEFAULT_FIGURES"
    else
      read -r -p "图片子目录名 [默认: $DEFAULT_FIGURES]: " FIGURES_DIRNAME
      FIGURES_DIRNAME="${FIGURES_DIRNAME:-$DEFAULT_FIGURES}"
    fi
  fi

  echo ""
  echo "将采用以下布局："
  echo "  $OUTPUT_PATH/<paper_name>/翻译_<paper_name>.md"
  echo "  $OUTPUT_PATH/<paper_name>/分享_<paper_name>.md"
  echo "  $OUTPUT_PATH/<paper_name>/全文_<paper_name>.md"
  echo "  $OUTPUT_PATH/<paper_name>/$FIGURES_DIRNAME/"
  echo ""

  if [[ $ASSUME_YES -eq 0 && -t 0 ]]; then
    read -r -p "确认以上路径设置？[Y/n]: " CONFIRM
    case "${CONFIRM:-Y}" in
      [nN]*) echo "已取消安装。请重新运行以修改设置。"; exit 1 ;;
    esac
  fi
fi

# ---------------------------------------------------------------------------
# 复制技能文件
# ---------------------------------------------------------------------------
if [[ -d "$DEST" && $FORCE -eq 0 && $EXISTING -eq 0 ]]; then
  echo "⚠️  目标已存在但无配置文件: $DEST"
  echo "    使用 --force 覆盖安装。"
  exit 1
fi

mkdir -p "$DEST"
cp -f "$SRC_DIR/SKILL.md" "$DEST/SKILL.md"
mkdir -p "$DEST/scripts"
cp -f "$SRC_DIR"/scripts/*.py "$DEST/scripts/" 2>/dev/null || true
cp -f "$SRC_DIR"/scripts/*.sh "$DEST/scripts/" 2>/dev/null || true
chmod +x "$DEST"/scripts/*.sh "$DEST"/scripts/*.py 2>/dev/null || true

if [[ -d "$SRC_DIR/references" ]]; then
  mkdir -p "$DEST/references"
  cp -f "$SRC_DIR"/references/* "$DEST/references/" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 写入配置
# ---------------------------------------------------------------------------
if [[ $EXISTING -eq 0 ]]; then
  cat > "$CONFIG_FILE" <<EOF
{
  "output_root": "$OUTPUT_PATH",
  "figures_dirname": "$FIGURES_DIRNAME",
  "audit": {
    "expansion_ratio": 1.6,
    "coverage_threshold": 0.85,
    "section_threshold": 0.60
  },
  "installed_at": "$(date -Iseconds)"
}
EOF
  echo "✅ 配置已写入: $CONFIG_FILE"
fi

echo ""
echo "============================================================"
echo "✅ 安装完成"
echo "============================================================"
echo "技能位置 : $DEST"
echo "解析路径 : $(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["output_root"])' "$CONFIG_FILE" 2>/dev/null || echo "$OUTPUT_PATH")"
echo ""
echo "在 DSH 中唤起："
echo "  「使用 ppr-workflow 技能，帮我处理 <论文URL或文件>」"
echo "============================================================"
