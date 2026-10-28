#!/usr/bin/env python3
"""
Outil de l'agenda des publications (contenu chiffré).

Tout le contenu (textes + visuels) est chiffré en AES-256-GCM avec une clé
dérivée du mot de passe (PBKDF2-SHA256, 310 000 itérations). Le dépôt peut
donc être public : sans le mot de passe, on ne voit rien.

Mot de passe : variable d'environnement AGENDA_PASSWORD (sinon demandé).

Commandes :
  python3 tools/agenda.py list
  python3 tools/agenda.py add-project --id btt --name "Beyond The Track" --color "#E8970E"
  python3 tools/agenda.py add post.json [post2.json ...]   # ajoute ou remplace (même id)
  python3 tools/agenda.py remove <post_id>
  python3 tools/agenda.py add-story --project btt --date 2026-10-30 --text "Sondage…"
  python3 tools/agenda.py export > agenda.json              # déchiffre tout (ne pas committer)

Format d'un post (JSON) — les chemins "media" pointent vers des fichiers locaux :
{
  "id": "btt-2026-10-29-inscriptions",          # unique, stable
  "project": "btt",
  "date": "2026-10-29", "time": "19:00",
  "network": "Instagram",                        # Instagram, Facebook, LinkedIn, Strava, TikTok…
  "format": "post",                              # post | carrousel | reel | story
  "title": "Inscriptions ouvertes",
  "why": "Objectif du post en une phrase",
  "caption": "Légende complète prête à publier",
  "captionLabel": "Légende",                     # facultatif ("Mode d'emploi" pour une story)
  "media": ["chemin/slide1.png", "chemin/slide2.png"],   # images, ou une vidéo .mp4
  "thumb": "chemin/vignette.jpg",                # facultatif (sinon 1re image)
  "zipName": "BB27_inscriptions.zip",            # facultatif, nom du zip de téléchargement
  "canva": false                                 # true = visuel fait dans Canva (pas de téléchargement)
}
"""
import argparse, base64, getpass, hashlib, io, json, mimetypes, os, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 310000

def _salt():
    p = os.path.join(ROOT, "salt.json")
    if not os.path.exists(p):
        json.dump({"salt": base64.b64encode(os.urandom(16)).decode(), "iterations": ITER}, open(p, "w"))
    j = json.load(open(p))
    return base64.b64decode(j["salt"]), j.get("iterations", ITER)

_KEY = None
def key():
    global _KEY
    if _KEY is None:
        pw = os.environ.get("AGENDA_PASSWORD") or getpass.getpass("Mot de passe de l'agenda : ")
        salt, it = _salt()
        _KEY = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(pw.encode())
    return _KEY

def enc(b: bytes) -> bytes:
    iv = os.urandom(12); return iv + AESGCM(key()).encrypt(iv, b, None)

def dec(b: bytes) -> bytes:
    return AESGCM(key()).decrypt(b[:12], b[12:], None)

DATA = os.path.join(ROOT, "data.enc")
def load():
    if not os.path.exists(DATA):
        return {"version": 1, "projects": [], "posts": [], "stories": []}
    try:
        return json.loads(dec(open(DATA, "rb").read()))
    except Exception:
        sys.exit("Mot de passe incorrect (impossible de déchiffrer data.enc).")

def save(d):
    d["posts"].sort(key=lambda p: (p["date"], p.get("time", "")))
    d["stories"].sort(key=lambda s: s["date"])
    open(DATA, "wb").write(enc(json.dumps(d, ensure_ascii=False).encode()))

def put_media(path, name=None):
    raw = open(path, "rb").read()
    h = hashlib.sha256(raw + key()).hexdigest()[:20]       # nom opaque, stable pour un même fichier
    os.makedirs(os.path.join(ROOT, "media"), exist_ok=True)
    out = os.path.join("media", h + ".bin")
    if not os.path.exists(os.path.join(ROOT, out)):
        open(os.path.join(ROOT, out), "wb").write(enc(raw))
    mt = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return {"file": out, "name": name or os.path.basename(path), "type": mt}

def make_thumb(path):
    from PIL import Image
    im = Image.open(path).convert("RGB"); w = 420
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=82)
    tmp = os.path.join(ROOT, ".thumb_tmp.jpg"); open(tmp, "wb").write(buf.getvalue())
    m = put_media(tmp, "vignette.jpg"); os.remove(tmp); return m

def video_thumb(path):
    import subprocess, tempfile
    t = tempfile.mktemp(suffix=".jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "8", "-i", path, "-frames:v", "1", t], check=True)
    m = make_thumb(t); os.remove(t); return m

def cmd_add(files):
    d = load()
    for f in files:
        base = os.path.dirname(os.path.abspath(f))
        p = json.load(open(f))
        rel = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
        for k in ("id", "project", "date", "format", "title"):
            if not p.get(k): sys.exit(f"{f} : champ obligatoire manquant « {k} »")
        if p["project"] not in {x["id"] for x in d["projects"]}:
            sys.exit(f"Projet « {p['project']} » inconnu : ajoute-le avec add-project.")
        media = [put_media(rel(m)) for m in p.get("media", [])]
        thumb_src = p.get("thumb") or next((m for m in p.get("media", []) if not m.lower().endswith((".mp4", ".mov", ".webm"))), None)
        if thumb_src: thumb = make_thumb(rel(thumb_src))
        elif p.get("media"): thumb = video_thumb(rel(p["media"][0]))
        else: thumb = None
        post = {k: p.get(k) for k in ("id", "project", "date", "time", "network", "format", "title", "why", "caption", "captionLabel", "zipName", "canva") if p.get(k) is not None}
        post["media"], post["thumb"] = media, thumb
        d["posts"] = [x for x in d["posts"] if x["id"] != post["id"]] + [post]
        print("✓", post["date"], post.get("time", ""), post["title"])
    save(d)

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="c", required=True)
    sp.add_parser("list"); sp.add_parser("export")
    a = sp.add_parser("add"); a.add_argument("files", nargs="+")
    r = sp.add_parser("remove"); r.add_argument("id")
    pr = sp.add_parser("add-project"); pr.add_argument("--id", required=True); pr.add_argument("--name", required=True); pr.add_argument("--color", required=True)
    st = sp.add_parser("add-story"); st.add_argument("--project", required=True); st.add_argument("--date", required=True); st.add_argument("--text", required=True)
    o = ap.parse_args()
    if o.c == "add": cmd_add(o.files)
    elif o.c == "list":
        d = load()
        print("Projets :", ", ".join(f"{p['id']} ({p['name']})" for p in d["projects"]) or "aucun")
        for p in d["posts"]: print(f"{p['date']} {p.get('time',''):>5}  [{p['project']}] {p['format']:<9} {p['title']}  ({p['id']})")
        print(f"{len(d['stories'])} stories")
    elif o.c == "export": print(json.dumps(load(), ensure_ascii=False, indent=2))
    elif o.c == "remove":
        d = load(); n = len(d["posts"]); d["posts"] = [p for p in d["posts"] if p["id"] != o.id]; save(d)
        print("supprimé" if len(d["posts"]) < n else "id introuvable")
    elif o.c == "add-project":
        d = load(); d["projects"] = [p for p in d["projects"] if p["id"] != o.id] + [{"id": o.id, "name": o.name, "color": o.color}]; save(d); print("✓ projet", o.name)
    elif o.c == "add-story":
        d = load(); d["stories"] = [s for s in d["stories"] if not (s["project"] == o.project and s["date"] == o.date and s["text"] == o.text)] + [{"project": o.project, "date": o.date, "text": o.text}]; save(d); print("✓ story", o.date)

if __name__ == "__main__":
    main()
