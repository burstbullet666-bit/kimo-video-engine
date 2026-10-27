# Kimo Video Engine (AutoClip Backend)

Flask HTTP API Wrapper untuk **Kimo MCP** (render video) dan **SenseNova** (generate thumbnail AI). Digunakan sebagai backend VPS dalam pipeline otomasi **AutoClip** berbasis n8n.

---

## Instalasi

```bash
# 1. Clone repositori
git clone https://github.com/USERNAME/kimo-video-engine.git
cd kimo-video-engine

# 2. Jalankan setup otomatis (sebagai root di VPS Ubuntu)
chmod +x setup.sh
sudo ./setup.sh

# 3. Isi konfigurasi
nano /var/www/thumbnail-api/config.py

# 4. Restart service
systemctl restart thumbnail-api
```

## Konfigurasi (`config.py`)

| Variable | Keterangan |
|---|---|
| `SENSENOVA_API_KEY` | API Key dari SenseNova |
| `SENSENOVA_URL` | Endpoint SenseNova (sudah diisi default) |
| `SECRET_API_KEY` | Kunci rahasia untuk autentikasi endpoint |
| `WORKSPACE_DIR` | Direktori penyimpanan file sementara |
| `PORT` | Port Flask (default: 5000) |

---

## Endpoint API

Semua endpoint membutuhkan header `x-api-key: <SECRET_API_KEY>`.

### `POST /api/edit`
Generate gambar thumbnail AI via SenseNova.

**Body:**
```json
{
  "image_url": "https://...",
  "prompt": "deskripsi edit gambar"
}
```

---

### `POST /api/render-kimo`
Render video Shorts menggunakan Kimo MCP.

**Body:**
```json
{
  "video_id": "abc123",
  "downloads": {
    "intro": "https://url-ke-thumbnail.jpg",
    "clip1": "https://url-ke-video.mp4"
  },
  "mcp_commands": [...],
  "srt_content": "1\n00:00:00,000 --> 00:00:05,000\nSubtitle..."
}
```

---

### `GET /api/download/<video_id>`
Download file video hasil render.

---

### `DELETE /api/cleanup/<video_id>`
Hapus semua file sementara terkait `video_id` dari workspace.

---

## Cek Log

```bash
journalctl -u thumbnail-api -f
tail -f /var/log/thumbnail-api-error.log
```
