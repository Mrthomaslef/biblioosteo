#!/usr/bin/env python3
"""
Add a new PubMed / Europe PMC article to BiblioOstéo by PMID or search query,
download its genuine Open-Access PDF if available (never generates synthetic PDFs;
falls back to direct DOI / PubMed / PMC links),
update exports (.ris, .bib, .json) and data/embedded_data.js, and optionally push to Zotero.

Usage:
  python3 scripts/add_article.py 38438685
  python3 scripts/add_article.py "cryoablation osteoid osteoma talus"
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from build_biblio_database import (
    CATEGORIES,
    extract_pub_month_and_date,
    get_journal_info_and_if,
    is_real_pdf,
    try_download_real_pdf,
)
from zotero_sync import generate_static_exports, sync_to_zotero

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = BASE_DIR / "pdfs"


def update_embedded_js():
    articles = json.loads((DATA_DIR / "articles.json").read_text(encoding="utf-8"))
    categories = json.loads((DATA_DIR / "categories.json").read_text(encoding="utf-8"))
    js_content = (
        f"window.BIBLIO_ARTICLES = {json.dumps(articles, ensure_ascii=False)};\n"
        f"window.BIBLIO_CATEGORIES = {json.dumps(categories, ensure_ascii=False)};\n"
        + (f"window.BIBLIO_SYNTHESES = {(DATA_DIR / 'syntheses.json').read_text(encoding='utf-8')};\n" if (DATA_DIR / "syntheses.json").exists() else "")
    )
    (DATA_DIR / "embedded_data.js").write_text(js_content, encoding="utf-8")
    print(f"[Embedded JS] Updated data/embedded_data.js ({len(articles)} articles)")


def infer_category_and_modality(title: str, abstract: str) -> tuple:
    txt = f"{title} {abstract}".lower()
    if "electrochemotherapy" in txt or "bleomycin" in txt:
        cat_id = "ect_mets"
        interv = "Électrochimiothérapie (ECT)"
    elif "desmoid" in txt or "fibromatosis" in txt:
        cat_id = "desmoid_soft_tissue"
        interv = "Cryoablation"
    elif "pudendal" in txt or "alcock" in txt:
        cat_id = "pudendal_cryoneurolysis"
        interv = "Cryoneurolyse du Nerf Pudendal"
    elif "morton" in txt or "genicular" in txt or "cryoneurolysis" in txt or "intercostal" in txt:
        cat_id = "pain_cryoneurolysis"
        interv = "Cryoneurolyse / RF Nerveuse"
    elif "aneurysmal bone cyst" in txt or "unicameral" in txt or "sclerotherapy" in txt:
        cat_id = "cyst_sclerotherapy"
        interv = "Sclérothérapie / Alcoolisation"
    elif "screw" in txt or "osteosynthesis" in txt or "cementoplasty" in txt or "vertebroplasty" in txt:
        cat_id = "consolidation_screw_cement"
        interv = "Cimentoplastie / Vissage"
    elif "biopsy" in txt:
        cat_id = "msk_biopsy"
        interv = "Biopsie percutanée"
    elif "osteoid osteoma" in txt or "chondroblastoma" in txt:
        cat_id = "ablation_benign"
        interv = "Ablation Thermique (RF / Cryo)"
    elif "ablation" in txt or "cryoablation" in txt or "radiofrequency" in txt or "microwave" in txt or "endometriosis" in txt:
        cat_id = "percutaneous_ablation_general"
        interv = "Ablation Percutanée Tumorale"
    else:
        cat_id = "msk_imaging"
        interv = "Imagerie Ostéo-Articulaire"

    if "ultrasound" in txt or "sonograph" in txt:
        mod = "Échographie"
    elif "magnetic resonance" in txt or "mri" in txt:
        mod = "IRM"
    else:
        mod = "Scanner TDM"

    return cat_id, mod, interv


def add_from_query_or_pmid(query_str: str):
    q = f"EXT_ID:{query_str}" if query_str.isdigit() else query_str
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": q,
        "format": "json",
        "pageSize": 1,
        "resultType": "core",
    })
    req = urllib.request.Request(url, headers={"User-Agent": "BiblioOsteo-Cochin/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        res = json.loads(resp.read().decode("utf-8")).get("resultList", {}).get("result", [])

    if not res:
        print(f"Aucun article trouvé sur PubMed / Europe PMC pour : {query_str}")
        return

    r = res[0]
    pmid = str(r.get("pmid") or r.get("id"))
    articles = json.loads((DATA_DIR / "articles.json").read_text(encoding="utf-8"))
    if any(str(a.get("pmid")) == pmid for a in articles):
        print(f"L'article PMID {pmid} est déjà présent dans data/articles.json.")
        update_embedded_js()
        return

    title = r.get("title", "").rstrip(".")
    journal_info = r.get("journalInfo", {})
    journal = journal_info.get("journal", {}).get("title", "")
    year = str(r.get("pubYear", "2025"))
    month_num, month_fr, pub_date_fr = extract_pub_month_and_date(r, year)
    impact_factor, journal_short = get_journal_info_and_if(journal)
    doi = str(r.get("doi", ""))
    pmcid = str(r.get("pmcid", ""))
    abstract_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.get("abstractText", ""))).strip()

    authors_list = [
        a.get("fullName") or f"{a.get('lastName', '')} {a.get('initials', '')}".strip()
        for a in r.get("authorList", {}).get("author", [])
        if a.get("fullName") or a.get("lastName")
    ]
    authors_short = f"{authors_list[0]}, {authors_list[1]} et al." if len(authors_list) > 3 else ", ".join(authors_list)

    cat_id, modality, interv = infer_category_and_modality(title, abstract_clean)
    cat = CATEGORIES[cat_id]
    rel_pdf = f"pdfs/PMID_{pmid}.pdf"
    pdf_path = BASE_DIR / rel_pdf
    has_real_pdf = is_real_pdf(pdf_path) or try_download_real_pdf(pmid, doi, pdf_path)

    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    doi_url = f"https://doi.org/{doi}" if doi else pubmed_url
    pmc_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else ""
    article_url = pmc_url or doi_url or pubmed_url

    new_art = {
        "id": f"pmid-{pmid}",
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": doi,
        "title": title,
        "title_fr": f"[Veille PubMed] {title}",
        "authors_list": authors_list,
        "authors_short": authors_short,
        "journal": journal,
        "journal_short": journal_short,
        "impact_factor": impact_factor,
        "year": int(year) if year.isdigit() else 2025,
        "month_num": month_num,
        "month_fr": month_fr,
        "pub_date_fr": pub_date_fr,
        "volume": str(journal_info.get("volume", "")),
        "issue": str(journal_info.get("issue", "")),
        "pages": str(r.get("pageInfo", "")),
        "category_id": cat_id,
        "category_label": cat["label"],
        "category_short": cat["short_label"],
        "category_color": cat["color"],
        "modality": modality,
        "intervention_type": interv,
        "cochin_link": f"Sélectionné via la veille BiblioOstéo dans le pôle « {cat['short_label']} » (Service de Radiologie B — Hôpital Cochin).",
        "summary_fr_short": f"Article publié dans {journal} ({year}) par {authors_short} portant sur : {title}.",
        "summary_fr_detailed": abstract_clean[:900] + ("..." if len(abstract_clean) > 900 else ""),
        "protocol_fr": f"Modalité principale : {modality} • Type d'acte : {interv}. Voir l'abstract et l'article original pour les paramètres détaillés.",
        "key_points_fr": [
            f"Publication de référence ({journal}, {year}) indexée sous PMID {pmid}.",
            f"Thématique Cochin : {cat['label']}.",
        ],
        "abstract_en": abstract_clean,
        "tags": [cat["short_label"], modality, interv],
        "pdf_file": rel_pdf if has_real_pdf else None,
        "pdf_source": "publisher_oa_pdf" if has_real_pdf else "external_link",
        "pdf_size_kb": round(pdf_path.stat().st_size / 1024) if has_real_pdf else None,
        "pubmed_url": pubmed_url,
        "doi_url": doi_url,
        "pmc_url": pmc_url,
        "article_url": article_url,
    }

    articles.insert(0, new_art)
    (DATA_DIR / "articles.json").write_text(json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8")
    update_embedded_js()
    generate_static_exports(articles)
    print(f"[Add Article] Added PMID {pmid}: {title} (real PDF: {has_real_pdf})")

    api_key = os.environ.get("ZOTERO_API_KEY", "").strip()
    if api_key:
        sync_to_zotero(api_key)


if __name__ == "__main__":
    update_embedded_js()
    if len(sys.argv) > 1:
        add_from_query_or_pmid(" ".join(sys.argv[1:]))
