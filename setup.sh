#!/bin/bash
set -e

echo "======================================"
echo "  AutoClip - Kimo Video Engine Setup  "
echo "======================================"

echo ""
echo "[1/8] Update sistem dan install dependensi..."
apt update && apt upgrade -y
apt install -y ffmpeg python3 python3-venv python3-pip nginx wget tar git

echo ""
echo "[2/8] Mendownload dan menginstall Kimo MCP..."
KIMO_URL="https://github.com/naman-sharma12345/kimo/releases/download/v5.0.0/kimo-v5.0.0-linux-x86_64-glibc.tar.gz"
KIMO_TMP="/tmp/kimo.tar.gz"
wget -O "$KIMO_TMP" "$KIMO_URL"
tar -xzf "$KIMO_TMP" -C /usr/local/bin/
chmod +x /usr/local/bin/kimo-v5.0.0-linux-x86_64-glibc
ln -sf /usr/local/bin/kimo-v5.0.0-linux-x86_64-glibc /usr/local/bin/kimo-mcp
echo "Kimo MCP terinstall di: $(which kimo-mcp)"

echo ""
echo "[3/8] Membuat direktori workspace..."
mkdir -p /var/www/thumbnail-api
mkdir -p /var/www/kimo-workspace
chmod 777 /var/www/kimo-workspace
chmod 755 /var/www/thumbnail-api

echo ""
echo "[4/8] Menyalin file project..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/app.py" /var/www/thumbnail-api/
cp "$SCRIPT_DIR/requirements.txt" /var/www/thumbnail-api/
cp "$SCRIPT_DIR/config.example.py" /var/www/thumbnail-api/

if [ ! -f /var/www/thumbnail-api/config.py ]; then
    echo "config.py tidak ditemukan, menyalin dari config.example.py..."
    cp "$SCRIPT_DIR/config.example.py" /var/www/thumbnail-api/config.py
    echo "PERHATIAN: Edit /var/www/thumbnail-api/config.py dan isi API Key kamu!"
else
    echo "config.py sudah ada, melewati..."
fi

echo ""
echo "[5/8] Membuat virtual environment dan install requirements..."
cd /var/www/thumbnail-api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo ""
echo "[6/8] Membuat systemd service..."
cat > /etc/systemd/system/thumbnail-api.service << 'EOF'
[Unit]
Description=Kimo Video Engine (AutoClip Backend)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/thumbnail-api
Environment="PATH=/var/www/thumbnail-api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/var/www/thumbnail-api/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5000 \
    --timeout 600 \
    --access-logfile /var/log/thumbnail-api-access.log \
    --error-logfile /var/log/thumbnail-api-error.log \
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chown -R www-data:www-data /var/www/thumbnail-api
chown -R www-data:www-data /var/www/kimo-workspace

systemctl daemon-reload
systemctl enable thumbnail-api
systemctl start thumbnail-api
echo "Service thumbnail-api: $(systemctl is-active thumbnail-api)"

echo ""
echo "[7/8] Mengkonfigurasi Nginx..."
rm -f /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-available/thumbnail-api << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 900s;
        proxy_send_timeout 900s;
        proxy_read_timeout 900s;
        send_timeout 900s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/thumbnail-api /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
echo "Nginx status: $(systemctl is-active nginx)"

echo ""
echo "[8/8] Verifikasi instalasi..."
echo "Kimo MCP: $(kimo-mcp --version 2>/dev/null || echo 'OK (binary ada)')"
echo "Python: $(python3 --version)"
echo "Gunicorn: $(/var/www/thumbnail-api/venv/bin/gunicorn --version)"
echo "Nginx: $(nginx -v 2>&1)"

echo ""
echo "======================================"
echo "  INSTALASI SELESAI!                  "
echo "======================================"
echo ""
echo "LANGKAH SELANJUTNYA:"
echo "1. Edit file config:"
echo "   nano /var/www/thumbnail-api/config.py"
echo ""
echo "2. Restart service setelah edit config:"
echo "   systemctl restart thumbnail-api"
echo ""
echo "3. Cek log jika ada masalah:"
echo "   journalctl -u thumbnail-api -f"
echo "   tail -f /var/log/thumbnail-api-error.log"
echo ""
