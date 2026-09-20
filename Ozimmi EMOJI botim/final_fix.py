#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, time

HOST = os.environ.get("VPS_HOST", "")
USER = os.environ.get("VPS_USER", "ubuntu")
PASSWD = os.environ.get("VPS_PASS", "")
REMOTE_DIR = "/home/ubuntu/taga_bot"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8988521463:AAFEDFpRPVAOO6DX0dG2oJInSxqKhcyvCws")

try:
    import paramiko
except ImportError:
    os.system('"' + sys.executable + '" -m pip install paramiko')
    import paramiko

def uprint(t):
    sys.stdout.buffer.write((str(t)+"\n").encode('utf-8', errors='replace'))
    sys.stdout.flush()

def connect(retries=6, delay=5):
    for i in range(retries):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(HOST, username=USER, password=PASSWD, timeout=90, banner_timeout=120, auth_timeout=90)
            return client
        except Exception as e:
            if i < retries-1:
                uprint("  Ulanish xato: " + type(e).__name__ + ". " + str(delay) + "s...")
                time.sleep(delay)
            else:
                raise

LINES = []
LINES.append("#!/bin/bash")
LINES.append("set +e")
LINES.append("LOG=\"" + REMOTE_DIR + "/FINAL_FIX.log\"")
LINES.append("echo \"==== $(date) BOSHLANDI ====\" > $LOG")
LINES.append("exec 3>&1 4>&2")
LINES.append("trap 'exec 2>&4 1>&3' 0 1 2 3")
LINES.append("exec 1>>$LOG 2>&1")
LINES.append("")
LINES.append("echo \"--- [1] Eski PM2 jarayonlarini o'chirish ---\"")
LINES.append("pm2 delete all 2>&1 || true")
LINES.append("pm2 kill 2>&1 || true")
LINES.append("pkill -9 -f 'sonnet_final' 2>&1 || true")
LINES.append("pkill -9 -f '/home/ubuntu/taga_bot/venv/bin/python' 2>&1 || true")
LINES.append("sleep 3")
LINES.append("echo 'Xotira (eski):' ; free -h")
LINES.append("")
LINES.append("echo \"--- [2] SWAP fayl yaratish (512MB) ---\"")
LINES.append("if [ ! -f /swapfile ]; then")
LINES.append("  sudo fallocate -l 512M /swapfile 2>&1 || sudo dd if=/dev/zero of=/swapfile bs=1M count=512 2>&1")
LINES.append("  sudo chmod 600 /swapfile 2>&1")
LINES.append("  sudo mkswap /swapfile 2>&1")
LINES.append("  sudo swapon /swapfile 2>&1")
LINES.append("  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab 2>&1")
LINES.append("fi")
LINES.append("sudo sysctl vm.swappiness=10 2>&1 | tail -1")
LINES.append("echo 'Xotira (swapdan keyin):' ; free -h")
LINES.append("")
LINES.append("echo \"--- [3] Keraksiz xotira ni tozalash ---\"")
LINES.append("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches 2>&1 >/dev/null || true")
LINES.append("")
LINES.append("echo \"--- [4] PM2 tozalandi, yangi pm2_home ---\"")
LINES.append("export PM2_HOME=/home/ubuntu/.pm2")
LINES.append("")
LINES.append("echo \"--- [5] PM2 ecosystem.js (to'g'ri format) ---\"")
LINES.append("cat > " + REMOTE_DIR + "/ecosystem.config.js << 'PM2END'")
LINES.append("module.exports = {")
LINES.append("  apps: [")
LINES.append("    {")
LINES.append("      name: 'taga_bot',")
LINES.append("      cwd: '" + REMOTE_DIR + "',")
LINES.append("      script: 'sonnet_final.py',")
LINES.append("      interpreter: '" + REMOTE_DIR + "/venv/bin/python3',")
LINES.append("      env: {")
LINES.append("        BOT_TOKEN: '__TOKEN_PLACEHOLDER__',")
LINES.append("        PYTHONUNBUFFERED: '1',")
LINES.append("        LANG: 'C.UTF-8'")
LINES.append("      },")
LINES.append("      instances: 1,")
LINES.append("      exec_mode: 'fork',")
LINES.append("      autorestart: true,")
LINES.append("      watch: false,")
LINES.append("      max_memory_restart: '380M',")
LINES.append("      error_file: '" + REMOTE_DIR + "/pm2-err.log',")
LINES.append("      out_file: '" + REMOTE_DIR + "/pm2-out.log',")
LINES.append("      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',")
LINES.append("      restart_delay: 4000,")
LINES.append("      min_uptime: '15s',")
LINES.append("      max_restarts: 10")
LINES.append("    }")
LINES.append("  ]")
LINES.append("};")
LINES.append("PM2END")
LINES.append("sed -i \"s|__TOKEN_PLACEHOLDER__|" + BOT_TOKEN + "|g\" " + REMOTE_DIR + "/ecosystem.config.js")
LINES.append("echo '--- Ecosystem content ---' ; cat " + REMOTE_DIR + "/ecosystem.config.js")
LINES.append("")
LINES.append("echo \"--- [6] PM2 start (ecosystem) ---\"")
LINES.append("cd " + REMOTE_DIR)
LINES.append("pm2 start ecosystem.config.js 2>&1 | tail -20")
LINES.append("sleep 3")
LINES.append("pm2 save 2>&1 | tail -3")
LINES.append("")
LINES.append("echo \"--- [7] PM2 startup systemd ---\"")
LINES.append("pm2 unstartup systemd 2>&1 | tail -2 || true")
LINES.append("STARTUP_OUT=$(pm2 startup systemd -u ubuntu --hp /home/ubuntu 2>&1)")
LINES.append("echo \"$STARTUP_OUT\" | tail -5")
LINES.append("STARTUP_CMD=$(echo \"$STARTUP_OUT\" | grep -o 'sudo env PATH=.*systemd -u ubuntu[^ ]*' | head -1)")
LINES.append("if [ -z \"$STARTUP_CMD\" ]; then")
LINES.append("  STARTUP_CMD=$(echo \"$STARTUP_OUT\" | grep 'sudo env' | head -1 | sed 's/\\\\$//')")
LINES.append("fi")
LINES.append("echo 'Startup cmd:' \"$STARTUP_CMD\"")
LINES.append("if [ -n \"$STARTUP_CMD\" ]; then eval \"$STARTUP_CMD\" 2>&1 | tail -5; fi")
LINES.append("")
LINES.append("echo \"--- [8] 20 soniya kutish ---\"")
LINES.append("sleep 20")
LINES.append("echo \"--- PM2 status ---\"")
LINES.append("pm2 status 2>&1")
LINES.append("echo \"--- PM2 logs (50 qator) ---\"")
LINES.append("pm2 logs taga_bot --lines 50 --nostream 2>&1 | tail -70")
LINES.append("echo \"--- Xotira ---\"")
LINES.append("free -h")
LINES.append("echo \"==== $(date) TUGALLANDI ====\"")

MASTER = "\n".join(LINES)

uprint("Serverga ulanmoqda...")
c = connect()
uprint("Ulandi!")

uprint("\n>>> Skriptni yozish...")
sftp = c.open_sftp()
with sftp.open(REMOTE_DIR + "/FINAL_FIX.sh", "w") as f:
    f.write(MASTER)
sftp.close()
stdin, stdout, stderr = c.exec_command("chmod +x " + REMOTE_DIR + "/FINAL_FIX.sh")
stdout.channel.recv_exit_status()

uprint("\n>>> Orqa fonda ishga tushurish...")
stdin, stdout, stderr = c.exec_command("nohup bash " + REMOTE_DIR + "/FINAL_FIX.sh > " + REMOTE_DIR + "/FINAL_FIX_nohup.log 2>&1 & echo PID=$!")
out = stdout.read().decode('utf-8', errors='replace')
uprint("  " + out.strip())
c.close()

uprint("\n>>> 35 soniya kuting...")
time.sleep(35)

def check_log():
    try:
        c2 = connect()
        _, o, _ = c2.exec_command("tail -180 " + REMOTE_DIR + "/FINAL_FIX.log 2>&1")
        t = o.read().decode('utf-8', errors='replace')
        c2.close()
        return t
    except Exception as e:
        return "[xato: " + str(e) + "]"

for cycle in range(1, 9):
    log = check_log()
    uprint("\n===== LOG " + str(cycle) + " =====")
    uprint(log[-6500:])
    if "TUGALLANDI" in log:
        uprint("\n✅ SKRIPT TUGALLANDI")
        break
    if cycle < 8:
        uprint("\n>>> 30 soniya kuting... (" + str(cycle) + "/8)")
        time.sleep(30)

uprint("\n===== YAKUNIY HOLAT =====")
try:
    c2 = connect()
    uprint("\n--- PM2 STATUS ---")
    _, o, _ = c2.exec_command("pm2 status 2>&1")
    uprint(o.read().decode('utf-8', errors='replace'))
    uprint("\n--- PM2 LOGS (70 qator) ---")
    _, o, _ = c2.exec_command("pm2 logs taga_bot --lines 70 --nostream 2>&1 | tail -90")
    uprint(o.read().decode('utf-8', errors='replace'))
    uprint("\n--- FREE (xotira) ---")
    _, o, _ = c2.exec_command("free -h 2>&1")
    uprint(o.read().decode('utf-8', errors='replace'))
    c2.close()
except Exception as e:
    uprint("Xato: " + str(e))

uprint("\n=== TUGALLANDI ===")
uprint("SSH: ssh " + USER + "@" + HOST)
uprint("  pm2 status / pm2 logs taga_bot / pm2 restart taga_bot")
