#!/usr/bin/env python3
"""
Zotero Web API v3 Synchronization & Export Engine for BiblioOstéo (Cochin Radio B)
----------------------------------------------------------------------------------
- Automatically discovers Zotero userID from the API Key via GET /keys/{key}
- Creates collection "BiblioOstéo — RI & Imagerie Ostéo-Articulaire (Cochin)"
- Pushes journalArticle entries with:
  * Full bibliographic metadata (Title, Authors, Journal, Year, Volume, Issue, Pages, DOI, PMID)
  * Combined French Structured Summary + Original Abstract in abstractNote
  * Dedicated HTML Child Note with the Cochin Clinical Synthesis
  * Local PDF attachment upload (with automatic fallback to linked_url if Zotero cloud storage quota is exceeded)
- Also generates local 1-click import files:
  * exports/biblioosteo_zotero.ris
  * exports/biblioosteo_zotero.bib
  * exports/biblioosteo_csl.json
"""

import hashlib
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARTICLES_JSON = BASE_DIR / "data" / "articles.json"
EXPORTS_DIR = BASE_DIR / "exports"
PDFS_DIR = BASE_DIR / "pdfs"
ZOTERO_STATE_FILE = BASE_DIR / "data" / "zotero_sync_state.json"

ZOTERO_API_BASE = "https://api.zotero.org"
COLLECTION_NAME = "BiblioOstéo — RI & Ostéo-Articulaire (Cochin)"


def generate_static_exports(articles: list, github_pages_url: str = "https://mrthomaslef.github.io/biblioosteo"):
    """Generate .ris, .bib, and CSL-JSON files for 1-click Zotero import."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. RIS Export
    ris_lines = []
    for art in articles:
        ris_lines.append("TY  - JOUR")
        ris_lines.append(f"TI  - {art['title']}")
        for author in art.get("authors_list", []):
            ris_lines.append(f"AU  - {author}")
        ris_lines.append(f"JO  - {art.get('journal', '')}")
        ris_lines.append(f"PY  - {art.get('year', '')}")
        if art.get("volume"):
            ris_lines.append(f"VL  - {art['volume']}")
        if art.get("issue"):
            ris_lines.append(f"IS  - {art['issue']}")
        if art.get("pages"):
            ris_lines.append(f"SP  - {art['pages']}")
        if art.get("doi"):
            ris_lines.append(f"DO  - {art['doi']}")
        pmid = art.get("pmid", "")
        pmcid = art.get("pmcid", "")
        combined_ab = (
            f"[RÉSUMÉ CLINique COCHIN - FR] {art.get('summary_fr_short', '')} "
            f"| Points clés : {' ; '.join(art.get('key_points_fr', []))} "
            f"| Pratique Cochin : {art.get('cochin_link', '')} "
            f"|| [ABSTRACT ORIGINAL - EN] {art.get('abstract_en', '')}"
        )
        ris_lines.append(f"AB  - {combined_ab}")
        ris_lines.append(f"N1  - PMID: {pmid} | PMCID: {pmcid} | Catégorie: {art.get('category_label', '')}")
        if art.get("pdf_file"):
            ris_lines.append(f"L1  - {github_pages_url}/{art['pdf_file']}")
        ris_lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        for tag in art.get("tags", []):
            ris_lines.append(f"KW  - {tag}")
        ris_lines.append("ER  - ")
        ris_lines.append("")

    (EXPORTS_DIR / "biblioosteo_zotero.ris").write_text("\n".join(ris_lines), encoding="utf-8")

    # 2. BibTeX Export
    bib_lines = []
    for art in articles:
        pmid = art.get("pmid", "unknown")
        first_author_last = (art.get("authors_list", ["Author"])[0].split(",")[0].split()[0]).lower()
        first_author_last = "".join(c for c in first_author_last if c.isalnum())
        cite_key = f"{first_author_last}{art.get('year', '')}_{pmid}"
        bib_lines.append(f"@article{{{cite_key},")
        bib_lines.append(f"  title = {{{art['title']}}},")
        bib_lines.append(f"  author = {{{' and '.join(art.get('authors_list', []))}}},")
        bib_lines.append(f"  journal = {{{art.get('journal', '')}}},")
        bib_lines.append(f"  year = {{{art.get('year', '')}}},")
        if art.get("volume"):
            bib_lines.append(f"  volume = {{{art['volume']}}},")
        if art.get("issue"):
            bib_lines.append(f"  number = {{{art['issue']}}},")
        if art.get("pages"):
            bib_lines.append(f"  pages = {{{art['pages']}}},")
        if art.get("doi"):
            bib_lines.append(f"  doi = {{{art['doi']}}},")
        bib_lines.append(f"  pmid = {{{pmid}}},")
        bib_lines.append(f"  url = {{https://pubmed.ncbi.nlm.nih.gov/{pmid}/}},")
        if art.get("pdf_file"):
            bib_lines.append(f"  file = {{Full Text PDF:{github_pages_url}/{art['pdf_file']}:application/pdf}},")
        clean_ab = art.get("summary_fr_short", "").replace("{", "").replace("}", "")
        bib_lines.append(f"  abstract = {{{clean_ab}}}")
        bib_lines.append("}\n")

    (EXPORTS_DIR / "biblioosteo_zotero.bib").write_text("\n".join(bib_lines), encoding="utf-8")

    # 3. CSL-JSON Export
    csl_items = []
    for art in articles:
        pmid = art.get("pmid", "")
        authors_csl = []
        for a in art.get("authors_list", []):
            parts = a.rsplit(" ", 1)
            if len(parts) == 2:
                authors_csl.append({"family": parts[0], "given": parts[1]})
            else:
                authors_csl.append({"family": a})
        csl_items.append({
            "id": f"pmid-{pmid}",
            "type": "article-journal",
            "title": art["title"],
            "container-title": art.get("journal", ""),
            "volume": art.get("volume", ""),
            "issue": art.get("issue", ""),
            "page": art.get("pages", ""),
            "DOI": art.get("doi", ""),
            "PMID": pmid,
            "PMCID": art.get("pmcid", ""),
            "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "author": authors_csl,
            "issued": {"date-parts": [[int(art.get("year", 2025))]]},
            "abstract": (
                f"[SYNTHÈSE FR] {art.get('summary_fr_short', '')}\n\n"
                f"[ABSTRACT EN] {art.get('abstract_en', '')}"
            ),
        })
    (EXPORTS_DIR / "biblioosteo_csl.json").write_text(
        json.dumps(csl_items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[Exports] Generated RIS, BibTeX, and CSL-JSON for {len(articles)} articles in {EXPORTS_DIR}")


def zotero_request(path: str, api_key: str, method: str = "GET", data: bytes = None, extra_headers: dict = None):
    url = f"{ZOTERO_API_BASE}{path}"
    headers = {
        "Zotero-API-Version": "3",
        "Zotero-API-Key": api_key,
        "User-Agent": "BiblioOsteo-Cochin/1.0",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return resp.status, dict(resp.headers), json.loads(body.decode("utf-8")) if body else None


def get_user_info(api_key: str) -> dict:
    _, _, info = zotero_request(f"/keys/{api_key}", api_key)
    if not info or "userID" not in info:
        raise ValueError("Invalid Zotero API Key or unable to resolve userID.")
    return info


def get_or_create_collection(user_id: int, api_key: str, name: str) -> str:
    _, _, cols = zotero_request(f"/users/{user_id}/collections?limit=100", api_key)
    for c in cols or []:
        if c.get("data", {}).get("name") == name:
            return c["key"]
    payload = json.dumps([{"name": name}]).encode("utf-8")
    _, _, res = zotero_request(
        f"/users/{user_id}/collections",
        api_key,
        method="POST",
        data=payload,
        extra_headers={"Content-Type": "application/json"},
    )
    successful = (res or {}).get("successful", {})
    if "0" in successful:
        return successful["0"]["key"]
    raise RuntimeError(f"Failed to create Zotero collection: {res}")


def get_existing_pmids(user_id: int, api_key: str, collection_key: str) -> set:
    existing = set()
    try:
        _, _, items = zotero_request(
            f"/users/{user_id}/collections/{collection_key}/items/top?limit=100", api_key
        )
        for it in items or []:
            extra = it.get("data", {}).get("extra", "")
            for line in extra.splitlines():
                if line.upper().startswith("PMID:"):
                    existing.add(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return existing


def format_child_note_html(art: dict, github_pages_url: str) -> str:
    kp_html = "".join(f"<li>{html.escape(p)}</li>" for p in art.get("key_points_fr", []))
    pmid = html.escape(str(art.get("pmid", "")))
    title = html.escape(art.get("title", ""))
    title_fr = html.escape(art.get("title_fr", ""))
    summary_fr = html.escape(art.get("summary_fr_detailed", art.get("summary_fr_short", "")))
    protocol_fr = html.escape(art.get("protocol_fr", ""))
    cochin_link = html.escape(art.get("cochin_link", ""))
    abstract_en = html.escape(art.get("abstract_en", ""))
    pdf_url = f"{github_pages_url}/{art.get('pdf_file', '')}"

    return (
        f"<h2>🇫🇷 Fiche de Synthèse BiblioOstéo — {title_fr}</h2>"
        f"<p><strong>Titre original :</strong> {title}</p>"
        f"<p><strong>Catégorie :</strong> {html.escape(art.get('category_label', ''))} | "
        f"<strong>PMID :</strong> <a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/'>{pmid}</a> | "
        f"<strong>PDF :</strong> <a href='{pdf_url}'>Ouvrir le PDF complet</a></p>"
        f"<h3>🎯 Pertinence Agenda Interventionnel (Hôpital Cochin - Radio B)</h3>"
        f"<p>{cochin_link}</p>"
        f"<h3>📋 Résumé Clinique Structuré</h3>"
        f"<p>{summary_fr}</p>"
        f"<h3>🔬 Technique & Protocole Interventionnel / Imagerie</h3>"
        f"<p>{protocol_fr}</p>"
        f"<h3>💡 Points Clés à Retenir</h3>"
        f"<ul>{kp_html}</ul>"
        f"<hr/>"
        f"<h3>🇬🇧 Original PubMed Abstract</h3>"
        f"<p>{abstract_en}</p>"
    )


def upload_pdf_attachment(user_id: int, api_key: str, parent_key: str, pdf_path: Path, github_pages_url: str, rel_pdf: str):
    """
    Create a PDF attachment on the parent Zotero item.
    Attempts native Zotero cloud file storage upload first; if storage quota is full or restricted,
    automatically attaches a linked_url PDF pointing to the GitHub Pages hosted PDF.
    """
    if not pdf_path.exists():
        return False, "missing_local_pdf"

    # 1. Try creating an imported_file attachment item
    filename = pdf_path.name
    att_template = [{
        "itemType": "attachment",
        "parentItem": parent_key,
        "linkMode": "imported_file",
        "title": f"PDF - {filename}",
        "contentType": "application/pdf",
        "filename": filename,
        "tags": [{"tag": "PDF Complet"}, {"tag": "BiblioOstéo"}]
    }]
    try:
        _, _, res = zotero_request(
            f"/users/{user_id}/items",
            api_key,
            method="POST",
            data=json.dumps(att_template).encode("utf-8"),
            extra_headers={"Content-Type": "application/json"},
        )
        att_key = res["successful"]["0"]["key"]

        # Compute MD5, size, mtime for Zotero upload authorization
        pdf_bytes = pdf_path.read_bytes()
        md5_hex = hashlib.md5(pdf_bytes).hexdigest()
        filesize = len(pdf_bytes)
        mtime_ms = int(pdf_path.stat().st_mtime * 1000)

        auth_params = urllib.parse.urlencode({
            "md5": md5_hex,
            "filename": filename,
            "filesize": filesize,
            "mtime": mtime_ms,
        }).encode("utf-8")

        _, _, auth_res = zotero_request(
            f"/users/{user_id}/items/{att_key}/file",
            api_key,
            method="POST",
            data=auth_params,
            extra_headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
            },
        )
        if auth_res and auth_res.get("exists") == 1:
            return True, "uploaded_cached"

        if auth_res and "url" in auth_res:
            prefix = auth_res.get("prefix", "").encode("utf-8")
            suffix = auth_res.get("suffix", "").encode("utf-8")
            ct = auth_res.get("contentType", "multipart/form-data")
            body = prefix + pdf_bytes + suffix
            s3_req = urllib.request.Request(
                auth_res["url"],
                data=body,
                headers={"Content-Type": ct},
                method="POST",
            )
            with urllib.request.urlopen(s3_req, timeout=60) as _:
                pass

            upload_key = auth_res["uploadKey"]
            reg_data = urllib.parse.urlencode({"upload": upload_key}).encode("utf-8")
            zotero_request(
                f"/users/{user_id}/items/{att_key}/file",
                api_key,
                method="POST",
                data=reg_data,
                extra_headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "If-None-Match": "*",
                },
            )
            return True, "uploaded_binary"
    except Exception as e:
        # Fallback: attach linked_url PDF pointing to the hosted PDF on GitHub Pages
        pass

    linked_template = [{
        "itemType": "attachment",
        "parentItem": parent_key,
        "linkMode": "linked_url",
        "title": f"PDF Intégral (BiblioOstéo) — {filename}",
        "contentType": "application/pdf",
        "url": f"{github_pages_url}/{rel_pdf}",
        "tags": [{"tag": "PDF Complet"}, {"tag": "BiblioOstéo"}]
    }]
    try:
        zotero_request(
            f"/users/{user_id}/items",
            api_key,
            method="POST",
            data=json.dumps(linked_template).encode("utf-8"),
            extra_headers={"Content-Type": "application/json"},
        )
        return True, "linked_url_pdf"
    except Exception as e:
        return False, str(e)


def sync_to_zotero(api_key: str, github_pages_url: str = "https://mrthomaslef.github.io/biblioosteo"):
    articles = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    user_info = get_user_info(api_key)
    user_id = user_info["userID"]
    username = user_info.get("username", str(user_id))
    print(f"[Zotero] Authenticated as {username} (userID: {user_id})")

    collection_key = get_or_create_collection(user_id, api_key, COLLECTION_NAME)
    print(f"[Zotero] Target collection '{COLLECTION_NAME}' -> key={collection_key}")

    existing_pmids = get_existing_pmids(user_id, api_key, collection_key)
    print(f"[Zotero] Already in collection: {len(existing_pmids)} items")

    synced_count = 0
    pdf_count = 0
    for art in articles:
        pmid = str(art.get("pmid", ""))
        if pmid in existing_pmids:
            print(f"  - Skipping PMID {pmid} (already present)")
            continue

        creators = []
        for a in art.get("authors_list", []):
            parts = a.rsplit(" ", 1)
            if len(parts) == 2:
                creators.append({"creatorType": "author", "lastName": parts[0], "firstName": parts[1]})
            else:
                creators.append({"creatorType": "author", "name": a})

        tags = [{"tag": t} for t in art.get("tags", [])]
        tags.append({"tag": "BiblioOstéo Cochin"})
        tags.append({"tag": art.get("category_label", "Ostéo-Articulaire")})

        combined_abstract = (
            f"🇫🇷 RÉSUMÉ CLINIQUE (COCHIN) :\n{art.get('summary_fr_short', '')}\n\n"
            f"🎯 LIEN AGENDA INTERVENTIONNEL :\n{art.get('cochin_link', '')}\n\n"
            f"🇬🇧 ORIGINAL ABSTRACT :\n{art.get('abstract_en', '')}"
        )

        extra_lines = [f"PMID: {pmid}"]
        if art.get("pmcid"):
            extra_lines.append(f"PMCID: {art['pmcid']}")

        item_payload = [{
            "itemType": "journalArticle",
            "title": art["title"],
            "creators": creators,
            "publicationTitle": art.get("journal", ""),
            "date": str(art.get("year", "")),
            "volume": str(art.get("volume", "")),
            "issue": str(art.get("issue", "")),
            "pages": str(art.get("pages", "")),
            "DOI": art.get("doi", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "abstractNote": combined_abstract,
            "extra": "\n".join(extra_lines),
            "collections": [collection_key],
            "tags": tags,
        }]

        _, _, res = zotero_request(
            f"/users/{user_id}/items",
            api_key,
            method="POST",
            data=json.dumps(item_payload).encode("utf-8"),
            extra_headers={"Content-Type": "application/json"},
        )
        successful = (res or {}).get("successful", {})
        if "0" not in successful:
            print(f"  ! Error creating item PMID {pmid}: {res}")
            continue

        item_key = successful["0"]["key"]
        synced_count += 1

        # Create child note with structured French clinical summary + Original abstract
        note_payload = [{
            "itemType": "note",
            "parentItem": item_key,
            "note": format_child_note_html(art, github_pages_url),
            "tags": [{"tag": "Fiche Résumé FR"}],
        }]
        try:
            zotero_request(
                f"/users/{user_id}/items",
                api_key,
                method="POST",
                data=json.dumps(note_payload).encode("utf-8"),
                extra_headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            print(f"  ! Note warning for PMID {pmid}: {e}")

        # Upload or attach PDF
        rel_pdf = art.get("pdf_file", f"pdfs/PMID_{pmid}.pdf")
        pdf_path = BASE_DIR / rel_pdf
        ok, mode = upload_pdf_attachment(user_id, api_key, item_key, pdf_path, github_pages_url, rel_pdf)
        if ok:
            pdf_count += 1
        print(f"  + Synced PMID {pmid} -> Zotero key={item_key} (PDF: {mode})")
        time.sleep(0.25)

    state = {
        "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_id": user_id,
        "username": username,
        "collection_key": collection_key,
        "collection_name": COLLECTION_NAME,
        "total_articles": len(articles),
        "newly_synced": synced_count,
        "pdfs_attached": pdf_count,
    }
    ZOTERO_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Zotero] Sync complete: {synced_count} new items added, {pdf_count} PDFs attached.")
    return state


def get_local_zotero_existing_pmids() -> set:
    """Read ~/Zotero/zotero.sqlite (via a safe temp snapshot) to find already imported PMIDs."""
    import shutil
    import sqlite3

    zot_db = Path.home() / "Zotero" / "zotero.sqlite"
    if not zot_db.exists():
        return set()
    tmp_db = Path("/tmp/biblioosteo_zot_check.sqlite")
    for ext in ["", "-wal", "-shm"]:
        src = Path(f"{zot_db}{ext}")
        dst = Path(f"{tmp_db}{ext}")
        if src.exists():
            shutil.copy(src, dst)
        elif dst.exists():
            dst.unlink()

    existing = set()
    try:
        con = sqlite3.connect(str(tmp_db))
        cur = con.cursor()
        rows = cur.execute("""
            SELECT iv.value FROM items i
            JOIN itemData id ON i.itemID = id.itemID
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemDataValues iv ON id.valueID = iv.valueID
            WHERE f.fieldName IN ('PMID', 'extra')
              AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
        """).fetchall()
        for (val,) in rows:
            val_s = str(val).strip()
            if val_s.isdigit():
                existing.add(val_s)
            for line in val_s.splitlines():
                if line.upper().startswith("PMID:"):
                    existing.add(line.split(":", 1)[1].strip())
        con.close()
    except Exception:
        pass
    return existing


def sync_to_local_zotero_desktop(github_pages_url: str = "https://mrthomaslef.github.io/biblioosteo") -> dict:
    """
    Push all articles + French clinical notes + full PDF files directly into the local Zotero.app
    running on the Mac mini via its local Connector Server (http://127.0.0.1:23119).
    Automatically launches /Applications/Zotero.app if it is not running yet.
    """
    import subprocess

    ping_url = "http://127.0.0.1:23119/connector/ping"
    zotero_running = False
    try:
        with urllib.request.urlopen(ping_url, timeout=2) as r:
            zotero_running = r.status == 200
    except Exception:
        pass

    if not zotero_running and Path("/Applications/Zotero.app").exists():
        print("[Zotero Local] Launching /Applications/Zotero.app...")
        subprocess.run(["open", "-g", "-a", "/Applications/Zotero.app"], check=False)
        for _ in range(15):
            time.sleep(1)
            try:
                with urllib.request.urlopen(ping_url, timeout=2) as r:
                    if r.status == 200:
                        zotero_running = True
                        break
            except Exception:
                pass

    if not zotero_running:
        print("[Zotero Local] Zotero Desktop is not running on port 23119.")
        return {"synced": 0, "pdfs": 0}

    articles = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    existing_pmids = get_local_zotero_existing_pmids()
    print(f"[Zotero Local] Connected to Mac mini Zotero.app ({len(existing_pmids)} PMIDs already present)")

    synced_count = 0
    pdf_count = 0
    for idx, art in enumerate(articles):
        pmid = str(art.get("pmid", ""))
        if pmid in existing_pmids:
            continue

        session_id = f"biblioosteo-{int(time.time())}-{idx}"
        item_id = f"item-{pmid}"
        creators = []
        for a in art.get("authors_list", []):
            parts = a.rsplit(" ", 1)
            if len(parts) == 2:
                creators.append({"creatorType": "author", "lastName": parts[0], "firstName": parts[1]})
            else:
                creators.append({"creatorType": "author", "lastName": a, "firstName": ""})

        tags = [{"tag": t} for t in art.get("tags", [])]
        tags.append({"tag": "BiblioOstéo Cochin"})
        tags.append({"tag": art.get("category_short", "Ostéo-Articulaire")})

        combined_abstract = (
            f"🇫🇷 RÉSUMÉ CLINIQUE (COCHIN) :\n{art.get('summary_fr_short', '')}\n\n"
            f"🎯 LIEN AGENDA INTERVENTIONNEL :\n{art.get('cochin_link', '')}\n\n"
            f"🇬🇧 ORIGINAL ABSTRACT :\n{art.get('abstract_en', '')}"
        )

        payload = {
            "sessionID": session_id,
            "uri": f"{github_pages_url}/",
            "items": [{
                "id": item_id,
                "itemType": "journalArticle",
                "title": art["title"],
                "creators": creators,
                "publicationTitle": art.get("journal", ""),
                "date": art.get("pub_date_fr", str(art.get("year", ""))),
                "volume": str(art.get("volume", "")),
                "issue": str(art.get("issue", "")),
                "pages": str(art.get("pages", "")),
                "DOI": art.get("doi", ""),
                "url": art.get("pubmed_url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
                "abstractNote": combined_abstract,
                "extra": f"PMID: {pmid}\nImpact Factor: {art.get('impact_factor', '')}",
                "tags": tags,
                "notes": [{
                    "note": format_child_note_html(art, github_pages_url)
                }]
            }]
        }

        try:
            req = urllib.request.Request(
                "http://127.0.0.1:23119/connector/saveItems",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Zotero-Connector-API-Version": "3",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as _:
                synced_count += 1

            # Attach main PDF binary directly into ~/Zotero/storage
            rel_pdf = art.get("pdf_file", f"pdfs/PMID_{pmid}.pdf")
            pdf_path = BASE_DIR / rel_pdf
            if pdf_path.exists():
                pdf_bytes = pdf_path.read_bytes()
                att_meta = {
                    "sessionID": session_id,
                    "parentItemID": item_id,
                    "title": f"PDF Intégral — PMID {pmid} ({art.get('journal_short', '')} {art.get('year', '')}).pdf",
                    "url": f"{github_pages_url}/{rel_pdf}",
                }
                req_att = urllib.request.Request(
                    f"http://127.0.0.1:23119/connector/saveAttachment?sessionID={session_id}",
                    data=pdf_bytes,
                    headers={
                        "Content-Type": "application/pdf",
                        "X-Zotero-Connector-API-Version": "3",
                        "X-Metadata": json.dumps(att_meta),
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req_att, timeout=30) as _:
                    pdf_count += 1

            # Also attach the French Clinical Synthesis PDF if distinct from the publisher PDF
            rel_synth = art.get("synth_pdf_file", f"pdfs/SYNTHESE_PMID_{pmid}.pdf")
            synth_path = BASE_DIR / rel_synth
            if art.get("pdf_source") == "publisher_oa_pdf" and synth_path.exists():
                synth_bytes = synth_path.read_bytes()
                synth_meta = {
                    "sessionID": session_id,
                    "parentItemID": item_id,
                    "title": f"Fiche Synthèse FR — PMID {pmid}.pdf",
                    "url": f"{github_pages_url}/{rel_synth}",
                }
                req_s = urllib.request.Request(
                    f"http://127.0.0.1:23119/connector/saveAttachment?sessionID={session_id}",
                    data=synth_bytes,
                    headers={
                        "Content-Type": "application/pdf",
                        "X-Zotero-Connector-API-Version": "3",
                        "X-Metadata": json.dumps(synth_meta),
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req_s, timeout=20) as _:
                    pass

            print(f"  + [Zotero Local] Imported PMID {pmid} + Note FR + PDF ({art.get('journal_short')} {art.get('pub_date_fr')})")
        except Exception as e:
            print(f"  ! [Zotero Local] Error on PMID {pmid}: {e}")

    print(f"[Zotero Local] Done: {synced_count} new articles imported, {pdf_count} PDFs stored in ~/Zotero/storage.")
    return {"synced": synced_count, "pdfs": pdf_count}


if __name__ == "__main__":
    if ARTICLES_JSON.exists():
        arts = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
        generate_static_exports(arts)
    # Always sync to local Zotero Desktop on the Mac mini if installed
    sync_to_local_zotero_desktop()
    api_key = os.environ.get("ZOTERO_API_KEY", "").strip()
    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1].strip()
    if api_key:
        sync_to_zotero(api_key)
