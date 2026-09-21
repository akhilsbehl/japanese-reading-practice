"""server.py — serve lessons + save memory. No deps.
Run: python tools/server.py [--port 8000]
POST /api/save {lesson,picked{},score,comments,peeks,furigana,seconds}
 -> memory/lesson-<id>.md + patch memory/global.md (no sentence/writing field)
"""
import argparse, json, os, datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)
    def do_POST(self):
        if urlparse(self.path).path != "/api/save":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or b"{}")
        lid = re.sub(r"[^0-9A-Za-z\-_]", "", data.get("lesson", datetime.date.today().isoformat())) or datetime.date.today().isoformat()
        mem = os.path.join(ROOT, "memory", f"lesson-{lid}.md")
        body = f"# lesson {lid}\ndate: {datetime.date.today().isoformat()}\nscore: {data.get('score','')}\npicked: {json.dumps(data.get('picked',{}), ensure_ascii=False)}\npeeks: {', '.join(data.get('peeks',[]))}\nfurigana: {data.get('furigana','')}\nseconds: {data.get('seconds','')}\n\ncomments: {data.get('comments','')}\n"
        os.makedirs(os.path.join(ROOT, "memory"), exist_ok=True)
        with open(mem, "w", encoding="utf-8") as f: f.write(body)
        # append weak to global (crude, agent refines later)
        gpath = os.path.join(ROOT, "memory", "global.md")
        with open(gpath, "a", encoding="utf-8") as f:
            f.write(f"\n- {lid}: score {data.get('score','')} picked {json.dumps(data.get('picked',{}), ensure_ascii=False)} peeks {data.get('peeks',[])}")
        out = json.dumps({"ok": True, "file": mem}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers()
        self.wfile.write(out)
    def log_message(self, *a): pass

import re
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    print(f"serving {ROOT} on http://localhost:{args.port}")
    HTTPServer(("127.0.0.1", args.port), H).serve_forever()
