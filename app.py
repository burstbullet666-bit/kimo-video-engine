from flask import Flask, request, jsonify, send_file
import requests
import os
import subprocess
import json
import re
import uuid
import traceback
import time
from config import SENSENOVA_API_KEY, SENSENOVA_URL, SECRET_API_KEY, WORKSPACE_DIR, PORT

app = Flask(__name__)

os.makedirs(WORKSPACE_DIR, exist_ok=True)

def check_api_key():
    auth_header = request.headers.get('x-api-key') or request.headers.get('Authorization')
    if not auth_header: return False
    return auth_header.replace('Bearer ', '').strip() == SECRET_API_KEY

@app.route('/api/edit', methods=['POST'])
def edit_image_vps():
    if not check_api_key(): return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    image_url = data.get('image_url')
    prompt = data.get('prompt')
    if not image_url or not prompt: return jsonify({"status": "error", "message": "Data incomplete"}), 400
    headers = {'Authorization': f'Bearer {SENSENOVA_API_KEY}', 'Content-Type': 'application/json'}
    payload = {"model": "sensenova-u1.5-lite", "images": [{"image_url": image_url}], "prompt": prompt, "n": 1, "size": "864x1536", "response_format": "url", "watermark": False, "prompt_extend": True}
    try:
        response = requests.post(SENSENOVA_URL, json=payload, headers=headers, timeout=300)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/render-kimo', methods=['POST'])
def render_kimo():
    if not check_api_key(): return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    video_id = data.get('video_id', str(uuid.uuid4()))
    downloads = data.get('downloads', {})
    commands = data.get('mcp_commands', [])
    srt_content = data.get('srt_content')

    if not commands or 'intro' not in downloads:
        return jsonify({"status": "error", "message": "Payload incomplete: commands atau intro hilang"}), 400

    local_paths = {}
    try:
        if srt_content:
            srt_path = os.path.join(WORKSPACE_DIR, f"{video_id}.srt")
            with open(srt_path, 'w', encoding='utf-8') as f: f.write(srt_content)
            local_paths['srt'] = srt_path
            print(f"[KIMO] File SRT disimpan di {srt_path}")

        for key, url in downloads.items():
            if not url: continue
            ext = '.jpg' if 'intro' in key or 'wm' in key else '.mp4'
            local_path = os.path.join(WORKSPACE_DIR, f"{video_id}_{key}{ext}")
            print(f"[KIMO] Mendownload {key} dari {url}")
            r = requests.get(url, stream=True)
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            local_paths[key] = local_path

        print(f"[KIMO] Memulai Kimo MCP untuk {video_id}")
        kimo_bin = '/usr/local/bin/kimo-mcp'
        process = subprocess.Popen([kimo_bin], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

        responses = {}
        for cmd in commands:
            cmd_id = cmd.get('id')
            cmd_str = json.dumps(cmd)
            for key, path in local_paths.items():
                cmd_str = cmd_str.replace(f'"$file:{key}"', f'"{path}"')
            refs = re.findall(r'"\$ref:(\d+)\.(\w+)"', cmd_str)
            for ref_id, ref_field in refs:
                if int(ref_id) in responses and ref_field in responses[int(ref_id)]:
                    val = responses[int(ref_id)][ref_field]
                    cmd_str = cmd_str.replace(f'"$ref:{ref_id}.{ref_field}"', f'"{val}"')
                else:
                    raise Exception(f"GAGAL MENGISI REF: $ref:{ref_id}.{ref_field} tidak ditemukan.")

            process.stdin.write(cmd_str + '\n')
            process.stdin.flush()
            output_line = process.stdout.readline()
            if not output_line: raise Exception("Kimo MCP mati mendadak.")
            resp_data = json.loads(output_line)
            if 'error' in resp_data: raise Exception(f"Kimo Error: {resp_data['error']}")
            if 'result' in resp_data:
                try: responses[cmd_id] = json.loads(resp_data['result']['content'][0]['text'])
                except Exception: responses[cmd_id] = resp_data['result']

        output_file = os.path.join(WORKSPACE_DIR, f"{video_id}.mp4")
        wait_time = 0
        while not os.path.exists(output_file) and wait_time < 60:
            time.sleep(1)
            wait_time += 1
        if not os.path.exists(output_file):
            raise Exception("File hasil render tidak ditemukan di VPS setelah 60 detik.")

        return jsonify({"status": "success", "video_id": video_id, "message": "Render selesai"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "traceback": traceback.format_exc()}), 500
    finally:
        if 'process' in locals() and process.poll() is None: process.kill()

@app.route('/api/download/<video_id>', methods=['GET'])
def download_video(video_id):
    if not check_api_key(): return jsonify({"status": "error", "message": "Unauthorized"}), 401
    video_path = os.path.join(WORKSPACE_DIR, f"{video_id}.mp4")
    if os.path.exists(video_path):
        return send_file(video_path, mimetype='video/mp4', as_attachment=True)
    return jsonify({"status": "error", "message": "File tidak ditemukan"}), 404

@app.route('/api/cleanup/<video_id>', methods=['DELETE'])
def cleanup_video(video_id):
    if not check_api_key(): return jsonify({"status": "error", "message": "Unauthorized"}), 401
    for filename in os.listdir(WORKSPACE_DIR):
        if filename.startswith(video_id):
            filepath = os.path.join(WORKSPACE_DIR, filename)
            try: os.remove(filepath)
            except Exception as e: print(f"[CLEANUP ERROR] {e}")
    return jsonify({"status": "success", "message": "Cleanup berhasil"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
