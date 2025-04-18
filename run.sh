#!/usr/bin/env bash
set -euo pipefail

# Ép OpenCV/Qt chạy qua X11 để tránh lỗi Wayland
export QT_QPA_PLATFORM=xcb

# Ép FFmpeg/RTSP dùng TCP transport để tránh lỗi “Unsupported Transport”
RTSP_OPTS="-rtsp_transport tcp"
SESSION="auto_session"

# 1) Nếu có tmux → mở 2 pane trong một cửa sổ tmux
if command -v tmux &>/dev/null; then
  tmux kill-session -t "${SESSION}" 2>/dev/null || true
  tmux new-session -d -s "${SESSION}" -n main

  # Pane chính (80%): render.py
  tmux send-keys -t "${SESSION}":0 "python3 render.py" C-m

  # Split pane dưới (20%): rtsp_process.py
  tmux split-window -v -t "${SESSION}":0 -p 20 "python3 rtsp_process.py ${RTSP_OPTS}"

  # Tự động focus pane render
  tmux select-pane -t "${SESSION}":0.0
  tmux attach -t "${SESSION}"
  exit 0
fi

# 2) Không có tmux → dò terminal emulator GUI
for TERM_CMD in xterm gnome-terminal konsole xfce4-terminal terminator mate-terminal lxterminal urxvt kitty; do
  if command -v "${TERM_CMD}" &>/dev/null; then
    echo "→ Dùng ${TERM_CMD} để mở rtsp_process.py kích thước nhỏ"
    # Chạy render.py nền
    python3 render.py &

    case "${TERM_CMD}" in
      xterm)
        xterm -geometry 80x10 -hold -e "python3 rtsp_process.py ${RTSP_OPTS}" &
        ;;
      gnome-terminal|mate-terminal)
        "${TERM_CMD}" --geometry=80x10+200+200 -- bash -c "python3 rtsp_process.py ${RTSP_OPTS}; exec bash" &
        ;;
      konsole)
        konsole --geometry 80x10 -e bash -c "python3 rtsp_process.py ${RTSP_OPTS}; exec bash" &
        ;;
      xfce4-terminal)
        xfce4-terminal --geometry=80x10 -e "bash -c \"python3 rtsp_process.py ${RTSP_OPTS}; exec bash\"" &
        ;;
      terminator)
        terminator --geometry=80x10 -x bash -c "python3 rtsp_process.py ${RTSP_OPTS}; exec bash" &
        ;;
      lxterminal)
        lxterminal --geometry=80x10 -e "bash -c \"python3 rtsp_process.py ${RTSP_OPTS}; exec bash\"" &
        ;;
      urxvt|kitty)
        "${TERM_CMD}" -geometry 80x10 -e bash -c "python3 rtsp_process.py ${RTSP_OPTS}; exec bash" &
        ;;
    esac

    wait
    exit 0
  fi
done

# 3) Fallback: không tìm thấy terminal nào
echo "Không tìm thấy tmux hay GUI terminal. Sẽ chạy render.py nền và rtsp_process.py foreground."
python3 render.py > render.log 2>&1 &
echo "→ render.py đang chạy nền, log lưu ở render.log"
exec python3 rtsp_process.py ${RTSP_OPTS}
