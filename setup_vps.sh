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

# 1. Cập nhật hệ thống và cài đặt gói phụ thuộc
echo -e "\n${YELLOW}[1/4] Đang cập nhật hệ thống và cài đặt gói hệ thống...${NC}"
if command -v apt-get &>/dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git tmux curl
elif command -v yum &>/dev/null; then
    sudo yum update -y
    sudo yum install -y python3 python3-pip git tmux curl
fi

# 2. Chuẩn bị thư mục mã nguồn
echo -e "\n${YELLOW}[2/4] Kiểm tra mã nguồn...${NC}"
REPO_DIR="$HOME/discord-bot-auto-quest"

if [ -d "$REPO_DIR/.git" ]; then
    echo -e "${GREEN}Đã tìm thấy thư mục repository, tiến hành kéo cập nhật mới nhất...${NC}"
    cd "$REPO_DIR"
    git pull origin main
else
    echo -e "${GREEN}Đang clone mã nguồn từ GitHub về $REPO_DIR...${NC}"
    git clone https://github.com/Mhna3112/discord-bot-auto-quest.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# 3. Tạo môi trường ảo Python (Virtualenv) & Cài đặt thư viện
echo -e "\n${YELLOW}[3/4] Cài đặt môi trường Python ảo và các thư viện...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Hoàn tất cài đặt
echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}                   CÀI ĐẶT THÀNH CÔNG TRÊN VPS!                       ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "\n${CYAN}Để treo voice 24/7 không bị tắt khi bạn đóng Termius, hãy chạy:${NC}"
echo -e "  ${YELLOW}tmux new -s voice${NC}             # Mở cửa sổ chạy ngầm tmux"
echo -e "  ${YELLOW}source venv/bin/activate${NC}      # Kích hoạt môi trường Python"
echo -e "  ${YELLOW}python treo_voice.py${NC}          # Khởi động tool treo voice"
echo -e "\n${CYAN}Các phím tắt quan trọng trong tmux:${NC}"
echo -e "  - Rời khỏi cửa sổ mà vẫn để tool chạy: Bấm ${YELLOW}Ctrl + B${NC}, sau đó bấm phím ${YELLOW}D${NC}"
echo -e "  - Mở lại xem tiến trình đang chạy: Gõ lệnh ${YELLOW}tmux attach -t voice${NC}"
echo -e "======================================================================\n"

# Hỏi người dùng có muốn chạy tool luôn không
read -p "👉 Bạn có muốn chạy tool Treo Voice ngay bây giờ không? (y/n): " RUN_NOW
if [[ "$RUN_NOW" =~ ^[Yy]$ ]]; then
    python treo_voice.py
fi
