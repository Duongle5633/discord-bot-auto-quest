#!/usr/bin/env bash
# ==============================================================================
# Script tự động cài đặt và cấu hình Discord Tool / Treo Voice 24/7 trên Linux VPS
# ==============================================================================

set -e

# Màu sắc hiển thị
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}       AUTO SETUP DISCORD TOOL / TREO VOICE 24/7 TRÊN VPS LINUX       ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# Xác định quyền root / sudo an toàn
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        echo -e "${RED}Vui lòng chạy script dưới quyền root hoặc cài đặt sudo!${NC}"
        exit 1
    fi
fi

# 1. Cập nhật hệ thống và kiểm tra phiên bản Python
echo -e "\n${YELLOW}[1/4] Đang cập nhật hệ thống và kiểm tra phiên bản Python...${NC}"
PYTHON_CMD="python3"

if command -v apt-get &>/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update -y
    $SUDO apt-get install -y python3 python3-pip python3-venv git tmux curl build-essential libffi-dev software-properties-common

    # Kiểm tra phiên bản Python hiện tại
    PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)

    # Discord Voice bắt buộc giao thức DAVE mới (yêu cầu discord.py-self 2.1.0+ và Python >= 3.10)
    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
        echo -e "${YELLOW}Phát hiện Python $PY_MAJOR.$PY_MINOR cũ. Đang tự động nâng cấp lên Python 3.11...${NC}"
        $SUDO add-apt-repository -y ppa:deadsnakes/ppa
        $SUDO apt-get update -y
        $SUDO apt-get install -y python3.11 python3.11-venv python3.11-dev
        PYTHON_CMD="python3.11"
    else
        PYTHON_CMD="python3"
    fi
elif command -v yum &>/dev/null; then
    $SUDO yum update -y
    $SUDO yum install -y python3 python3-pip git tmux curl gcc libffi-devel
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}Sử dụng trình thông dịch: $PYTHON_CMD ($($PYTHON_CMD --version))${NC}"

# 2. Chuẩn bị thư mục mã nguồn
echo -e "\n${YELLOW}[2/4] Kiểm tra mã nguồn...${NC}"
REPO_DIR="$HOME/discord-bot-auto-quest"

if [ -d "$REPO_DIR/.git" ]; then
    echo -e "${GREEN}Đã tìm thấy thư mục repository, tiến hành kéo cập nhật mới nhất...${NC}"
    cd "$REPO_DIR"
    git fetch origin
    git reset --hard origin/main
else
    echo -e "${GREEN}Đang clone mã nguồn từ GitHub về $REPO_DIR...${NC}"
    git clone https://github.com/Mhna3112/discord-bot-auto-quest.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# 3. Tạo môi trường ảo Python (Virtualenv) & Cài đặt thư viện
echo -e "\n${YELLOW}[3/4] Cài đặt môi trường Python ảo và các thư viện...${NC}"

# Luôn làm mới venv nếu venv dùng Python < 3.10
if [ -d "venv" ]; then
    VENV_PY_MINOR=$(./venv/bin/python3 -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
    if [ "$VENV_PY_MINOR" -lt 10 ]; then
        echo -e "${YELLOW}Xóa môi trường ảo Python cũ ($VENV_PY_MINOR) để tạo mới bằng $PYTHON_CMD...${NC}"
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

./venv/bin/pip install --upgrade pip setuptools wheel
./venv/bin/pip install -r requirements.txt

# 4. Hoàn tất cài đặt
echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}                   CÀI ĐẶT THÀNH CÔNG TRÊN VPS!                       ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "\n${CYAN}Để treo voice 24/7 không bị tắt khi bạn đóng Termius, hãy chạy:${NC}"
echo -e "  ${YELLOW}tmux new -s voice${NC}             # Mở cửa sổ chạy ngầm tmux"
echo -e "  ${YELLOW}cd ~/discord-bot-auto-quest${NC}   # Vào thư mục bot"
echo -e "  ${YELLOW}source venv/bin/activate${NC}      # Kích hoạt môi trường Python"
echo -e "  ${YELLOW}python treo_voice.py${NC}          # Khởi động tool treo voice"
echo -e "\n${CYAN}Các phím tắt quan trọng trong tmux:${NC}"
echo -e "  - Rời khỏi cửa sổ mà vẫn để tool chạy: Bấm ${YELLOW}Ctrl + B${NC}, sau đó bấm phím ${YELLOW}D${NC}"
echo -e "  - Mở lại xem tiến trình đang chạy: Gõ lệnh ${YELLOW}tmux attach -t voice${NC}"
echo -e "======================================================================\n"

# Hỏi người dùng có muốn chạy tool luôn không
read -p "👉 Bạn có muốn chạy tool Treo Voice ngay bây giờ không? (y/n): " RUN_NOW
if [[ "$RUN_NOW" =~ ^[Yy]$ ]]; then
    ./venv/bin/python treo_voice.py
fi
