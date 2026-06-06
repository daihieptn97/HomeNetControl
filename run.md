sudo tee /etc/systemd/system/homenetcontrol.service > /dev/null <<'EOF'
[Unit]
Description=HomeNetControl Flask App
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/home/pi/HomeNetControl
EnvironmentFile=/home/pi/HomeNetControl/.env
ExecStart=/home/pi/HomeNetControl/.venv/bin/python /home/pi/HomeNetControl/run.py
Restart=always
RestartSec=5
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF


sudo systemctl daemon-reload
sudo systemctl enable homenetcontrol
sudo systemctl start homenetcontrol
sudo systemctl status homenetcontrol