# Kimo Video Engine (AutoClip Backend)

Flask HTTP API Wrapper untuk **Kimo MCP** (render video) dan **SenseNova** (generate thumbnail AI). Digunakan sebagai backend VPS dalam pipeline otomasi **AutoClip** berbasis n8n.

---

## Instalasi di VPS Ubuntu (Fresh)

```bash
# 1. Clone repositori
git clone https://github.com/burstbullet666-bit/kimo-video-engine.git
cd kimo-video-engine

# 2. Jalankan setup otomatis (harus root)
chmod +x setup.sh
sudo ./setup.sh

# 3. Isi konfigurasi
nano /var/www/thumbnail-api/config.py

# 4. Restart service
systemctl restart thumbnail-api

# 5. Test server berjalan
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/download/test -H "x-api-key: SECRET_MU"
# Harus balas 404 (bukan connection refused)
```

---

## Konfigurasi (`/var/www/thumbnail-api/config.py`)

| Variable | Keterangan |
|---|---|
| `SENSENOVA_API_KEY` | API Key dari SenseNova |
| `SENSENOVA_URL` | Endpoint SenseNova (sudah diisi default) |
| `SECRET_API_KEY` | Kunci rahasia untuk autentikasi semua endpoint |
| `WORKSPACE_DIR` | Direktori penyimpanan file sementara (default: `/var/www/kimo-workspace`) |
| `PORT` | Port Flask (default: `5000`) |

---

## Endpoint API

Semua endpoint membutuhkan header `x-api-key: <SECRET_API_KEY>`.

### `POST /api/edit`
Generate gambar thumbnail AI via SenseNova.

**Body:**
```json
{
  "image_url": "https://url-gambar-asli.jpg",
  "prompt": "deskripsi edit gambar"
}
```

**Response sukses:**
```json
{
  "data": [{ "url": "https://url-hasil-generate.jpg" }]
}
```

---

### `POST /api/render-kimo`
Render video Shorts (9:16) menggunakan Kimo MCP engine.

**Body:**
```json
{
  "video_id": "nama_unik_video",
  "downloads": {
    "clip1": "https://url-video-1.mp4",
    "clip2": "https://url-video-2.mp4",
    "intro": "https://url-thumbnail.jpg"
  },
  "mcp_commands": [
    { "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": { "name": "project_set", "arguments": { "width": 1080, "height": 1920, "fps": 30 } } }
  ],
  "srt_content": "1\n00:00:00,000 --> 00:00:05,000\nSubtitle teks"
}
```

> **Catatan:** `downloads.intro` bersifat opsional. `mcp_commands` wajib ada.

**Response sukses:**
```json
{
  "status": "success",
  "video_id": "nama_unik_video",
  "message": "Render selesai"
}
```

---

### `GET /api/download/<video_id>`
Download file video hasil render.

```bash
curl -O -J http://IP_VPS/api/download/nama_unik_video -H "x-api-key: SECRET_MU"
```

---

### `DELETE /api/cleanup/<video_id>`
Hapus semua file sementara terkait `video_id` dari workspace untuk menghemat storage.

```bash
curl -X DELETE http://IP_VPS/api/cleanup/nama_unik_video -H "x-api-key: SECRET_MU"
```

---

## Troubleshooting

### Service tidak mau start
```bash
journalctl -u thumbnail-api -n 50 --no-pager
```

### Error: Permission denied pada log
```bash
touch /var/log/thumbnail-api-access.log /var/log/thumbnail-api-error.log
chown www-data:www-data /var/log/thumbnail-api-access.log /var/log/thumbnail-api-error.log
systemctl restart thumbnail-api
```

### Error: Permission denied pada kimo-mcp
```bash
rm /usr/local/bin/kimo-mcp
ln -sf /usr/local/bin/kimo-v5.0.0-linux-x86_64-glibc/bin/kimo-mcp /usr/local/bin/kimo-mcp
chmod +x /usr/local/bin/kimo-v5.0.0-linux-x86_64-glibc/bin/kimo-mcp
```

### Test Kimo MCP berjalan
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"ping"}' | /usr/local/bin/kimo-mcp
# Harus balas: {"id":1,"jsonrpc":"2.0","result":{}}
```

### Cek log realtime
```bash
journalctl -u thumbnail-api -f
tail -f /var/log/thumbnail-api-error.log
```

---

## Struktur File

```
kimo-video-engine/
├── app.py              # Flask server utama
├── config.example.py   # Template konfigurasi
├── requirements.txt    # Python dependencies
├── setup.sh            # Auto-installer VPS Ubuntu
├── .gitignore
└── README.md
```
