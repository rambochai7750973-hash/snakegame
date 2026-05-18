#!/bin/bash
# 构建贪吃蛇 APK (需要 Linux 或 WSL2)
# 安装依赖:
#   sudo apt update
#   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
#   pip3 install --user buildozer cython

# 构建 APK
buildozer android debug

# APK 文件在 bin/ 目录下
echo "APK 已生成: bin/"
