"""Serve the blind listening page on 127.0.0.1 (reach it through the SSH tunnel) and save the ratings.

    python experiments/voices/v2/listening/serve.py [--port 8610]

GET  /           ecoute.html, tasks.json, clips/*.wav
POST /save       the listener's ratings → ratings/<listener>_<time>.json
"""

import argparse
import functools
import http.server
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).parent


PUBLIC = re.compile(r"^/(ecoute\.html|tasks\.json|clips/x[0-9a-f]{6}\.wav)?$")  # never design.json (the key)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.path = "/ecoute.html"
        elif not PUBLIC.match(path):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        data = json.loads(body)
        who = re.sub(r"[^\w-]", "_", str(data.get("listener") or "anonyme"))[:40]
        out = HERE / "ratings"
        out.mkdir(exist_ok=True)
        path = out / f"{who}_{time.strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"saved": path.name}).encode())

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8610)
    args = ap.parse_args()
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(Handler, directory=str(HERE))) as s:
        print(f"Écoute à l'aveugle : http://127.0.0.1:{args.port}/ecoute.html")
        s.serve_forever()


if __name__ == "__main__":
    main()
