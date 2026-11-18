#!/usr/bin/env python3
"""Gestion de la catégorie « 🎓 Recommandé pour les internes ».

Source éditable : data/internes.json (ordre = ordre d'affichage).
Ce script régénère aussi data/internes.js (window.BIBLIO_INTERNES) pour le mode hors-ligne.

Usage :
  python3 scripts/internes.py list
  python3 scripts/internes.py add <PMID> --type diag|ri --pourquoi "Pourquoi le présenter au staff"
  python3 scripts/internes.py remove <PMID>
  python3 scripts/internes.py build          # régénère seulement data/internes.js
"""
import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SRC = DATA_DIR / "internes.json"
JS = DATA_DIR / "internes.js"
ANNEE_MIN = 2024  # règle de Thomas : aucun article recommandé antérieur à 2024


def load():
    return json.loads(SRC.read_text(encoding="utf-8")) if SRC.exists() else []


def articles_by_pmid():
    return {a["pmid"]: a for a in json.loads((DATA_DIR / "articles.json").read_text(encoding="utf-8"))}


def save(items):
    SRC.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    JS.write_text(f"window.BIBLIO_INTERNES = {json.dumps(items, ensure_ascii=False)};\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("build")
    a = sub.add_parser("add")
    a.add_argument("pmid")
    a.add_argument("--type", choices=["diag", "ri"], required=True)
    a.add_argument("--pourquoi", required=True)
    r = sub.add_parser("remove")
    r.add_argument("pmid")
    args = p.parse_args()

    items = load()
    arts = articles_by_pmid()

    missing = [i["pmid"] for i in items if i["pmid"] not in arts]
    if missing:
        print(f"⚠️  PMID absents de la base (ignorés à l'affichage) : {', '.join(missing)}")

    old = [i["pmid"] for i in items if i["pmid"] in arts and (arts[i["pmid"]].get("year") or 0) < ANNEE_MIN]
    if old:
        print(f"⚠️  Articles antérieurs à {ANNEE_MIN} dans la liste : {', '.join(old)}")

    if args.cmd == "list":
        for n, i in enumerate(items, 1):
            t = arts.get(i["pmid"], {}).get("title_fr", "??")[:90]
            print(f"{n:2}. [{i['type']}] {i['pmid']}  {t}")
        print(f"\n{len(items)} article(s) recommandé(s).")
        return
    if args.cmd == "add":
        if args.pmid not in arts:
            sys.exit(f"❌ PMID {args.pmid} introuvable dans data/articles.json (l'ajouter d'abord avec add_article.py).")
        if (arts[args.pmid].get("year") or 0) < ANNEE_MIN:
            sys.exit(f"❌ Article de {arts[args.pmid].get('year')} : seuls les articles publiés à partir de {ANNEE_MIN} sont recommandés.")
        items = [i for i in items if i["pmid"] != args.pmid]
        items.append({"pmid": args.pmid, "type": args.type, "pourquoi": args.pourquoi})
        print(f"✅ Ajouté : {arts[args.pmid]['title_fr'][:90]}")
    elif args.cmd == "remove":
        before = len(items)
        items = [i for i in items if i["pmid"] != args.pmid]
        if len(items) == before:
            sys.exit(f"❌ PMID {args.pmid} n'est pas dans la liste.")
        print(f"🗑️  Retiré : {args.pmid}")
    save(items)
    print(f"→ {len(items)} article(s) dans data/internes.json + data/internes.js")


if __name__ == "__main__":
    main()
