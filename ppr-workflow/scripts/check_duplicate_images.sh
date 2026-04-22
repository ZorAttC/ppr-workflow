#!/bin/bash
# 检查本地图片目录中的重复文件（基于 md5 校验）
# 用法: bash check_duplicate_images.sh <image_directory>

DIR=${1:-"."}

if [ ! -d "$DIR" ]; then
  echo "Error: Directory $DIR not found."
  exit 1
fi

echo "🔍 正在扫描 $DIR 下的重复图片..."

# 查找所有文件并计算 md5，然后对md5进行排序，找出那些重复的哈希
find "$DIR" -type f -exec md5sum {} + | sort | awk '
BEGIN { prev_md5=""; prev_file=""; count=0 }
{
  md5=$1; file=$2;
  if (md5 == prev_md5) {
     if (count == 0) {
        print "重复组发现:"
        print "  -> " prev_file
     }
     print "  -> " file
     count++
  } else {
     count=0
  }
  prev_md5=md5; prev_file=file;
}
END {
  print "🏁 扫描结束"
}'
