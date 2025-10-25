#!/bin/bash

# Matar qualquer Xvfb anterior
pkill -f "Xvfb :99" 2>/dev/null || true
sleep 1

# Iniciar Xvfb
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
sleep 2

# Exportar DISPLAY
export DISPLAY=:99

# Iniciar scheduler
cd /home/ubuntu/tiktok-react/beckend
/home/ubuntu/tiktok-react/beckend/venv/bin/python start_scheduler.py start

# Quando o scheduler parar, matar Xvfb
kill $XVFB_PID 2>/dev/null || true
