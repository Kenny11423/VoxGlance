#!/usr/bin/env bash
# OmniTranslator - Trình Dịch Thuật Đa Phương Tiện Thời Gian Thực (100% Offline)
# Tự động mở Cửa sổ Cài Đặt (Settings Window) trên màn hình để chọn chế độ

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/src/main.py" "$@"
