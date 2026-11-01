<img src="assets/icon.svg" width="64" height="64" alt="BiblioOstéo">

# BiblioOstéo — Radiologie Interventionnelle & Imagerie Ostéo-Articulaire (Hôpital Cochin • Radiologie B)

🌐 **Portail Web GitHub Pages :** **[https://mrthomaslef.github.io/biblioosteo/](https://mrthomaslef.github.io/biblioosteo/)**

Portail de veille bibliographique, de résumés cliniques structurés en français (avec abstracts originaux PubMed), de stockage de PDF intégraux et de synchronisation automatique vers **Zotero**, conçu sur mesure autour des activités du **Service de Radiologie B de l'Hôpital Cochin** (Pavillon Achard -1 / Pavillon Ollier) et de votre **Agenda Interventionnel**.

---

## 🎯 Thématiques couvertes (calquées sur l'Agenda Interventionnel Cochin)

1. **Ablation Thermique des Tumeurs Osseuses Bénignes (RF & Cryoablation)**
   - Ostéome ostéoïde (tibia proximal, coude, hanche, astragale/talus en technique *no-touch*, IRM dynamique).
   - Chondroblastome épiphysaire (genou, respect de la lame sous-chondrale, gestion des récidives).
2. **Cryoablation des Tumeurs Desmoïdes & des Parties Molles**
   - Essai français *CRYODESMO-01*, tumeurs desmoïdes extra-abdominales (creux sus-claviculaire / proximité du plexus brachial, hydrodissection), nodules paravertébraux et du trapèze.
3. **Électrochimiothérapie (ECT - Bléomycine) & Métastases Osseuses**
   - Électrochimiothérapie osseuse sous bléomycine IV (fenêtre 8–40 min, générateur IGEA), combinaison **Cryoablation + ECT** (métastases du pied, rachis), cryoablation pariétale thoracique antalgique.
4. **Consolidation Osseuse Percutanée : Vissage du Bassin & Cimentoplastie Cervicale**
   - Ostéosynthèse percutanée par vissage du bassin sous scanner post-radiothérapie (et combinaison *Cryo + Vissage*), cimentoplastie cervicale sous AG (voie antéro-latérale, gestion péri-procédurale des anticoagulants *Eliquis + Plavix*).
5. **Sclérothérapie / Alcoolisation des Kystes Osseux**
   - Kyste osseux anévrismal (KOA humérus, réarrangement *USP6*, suivi TDM à 1 an) et kyste osseux essentiel (KOE aile iliaque, alcoolisation +/- cimentoplastie).
6. **Radiologie Interventionnelle de la Douleur & Cryoneurolyse**
   - Cryoneurolyse sous anesthésie locale du **névrome de Morton** (3e espace inter-métatarsien).
   - Bloc test anesthésique sous échographie et radiofréquence des **nerfs géniculés** (gonarthrose).
   - Cryoneurolyse des **nerfs intercostaux** (douleurs post-zona) et des douleurs neuropathiques post-amputation.
7. **Biopsies Ostéo-Articulaires, Synoviales & Sarcomes (Scanner / Échographie)**
   - Biopsies de masses des parties molles sous échographie (respect strict du fascia et des compartiments en concertation avec les chirurgiens orthopédistes de Cochin), biopsies synoviales (genou, chondromatose / SVN) et biopsies osseuses sous scanner (récidive de lymphome B, masse pré-sacrée / sacrum).
8. **Imagerie Ostéo-Articulaire Diagnostique & Suivi Post-Thérapeutique**
   - Sémiologie des tumeurs solitaires du rachis et du sacrum (équipe Cochin), IRM dynamique de l'ostéome ostéoïde, suivi IRM des tumeurs ténosynoviales à cellules géantes (**TTCG / SVN**) et contrôles IRM post-cryoablation.

---

## 📚 Stockage des PDF & Intégration Zotero

- **PDFs originaux dans [`pdfs/`](pdfs/) :**
  - `pdfs/PMID_<pmid>.pdf` : **Uniquement les vrais PDF éditeur / Open-Access intégraux** (aucun PDF synthétique n'est généré).
  - Si le PDF intégral n'est pas en accès libre direct, l'application et Zotero fournissent directement le **lien officiel de l'article** (`DOI` / `PMC` / `PubMed`).
- **Synchronisation Zotero directe (API Web Zotero v3) :**
  - Depuis l'interface web (bouton **📚 Synchroniser Zotero**) ou en ligne de commande :
    ```bash
    ZOTERO_API_KEY="votre_cle_zotero" python3 scripts/zotero_sync.py
    ```
  - Crée automatiquement la collection **`BiblioOstéo — RI & Ostéo-Articulaire (Cochin)`**, ajoute les entrées complètes (`journalArticle`), attache la fiche de résumé en français en note enfant, l'abstract original et le vrai PDF (s'il est disponible) ou le lien direct vers l'article.
- **Exports Zotero 1-clic dans [`exports/`](exports/) :**
  - [`exports/biblioosteo_zotero.ris`](exports/biblioosteo_zotero.ris) (format RIS avec résumé FR + abstract EN + lien PDF)
  - [`exports/biblioosteo_zotero.bib`](exports/biblioosteo_zotero.bib) (format BibTeX)
  - [`exports/biblioosteo_csl.json`](exports/biblioosteo_csl.json) (format CSL-JSON)

---

## 🛠️ Commandes utiles (Ajout d'articles & Mise à jour)

```bash
# Régénérer toute la base, les PDFs et les exports Zotero
python3 scripts/build_biblio_database.py
python3 scripts/add_article.py

# Ajouter un nouvel article PubMed par son PMID ou par requête
python3 scripts/add_article.py 38438685
python3 scripts/add_article.py "cryoablation chondroblastoma knee"

# Synchroniser avec votre compte Zotero
ZOTERO_API_KEY="votre_cle" python3 scripts/zotero_sync.py
```
