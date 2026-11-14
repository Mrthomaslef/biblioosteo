#!/usr/bin/env python3
"""
Builds the BiblioOstéo dataset (data/articles.json), downloads genuine Open-Access Publisher PDFs
when available (never generates synthetic PDFs; falls back to direct publisher/DOI/PubMed links),
and generates Zotero export files (.ris, .bib, .json).
"""

import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = BASE_DIR / "pdfs"

CATEGORIES = {
    "ablation_benign": {
        "id": "ablation_benign",
        "label": "Ablation Thermique des Tumeurs Osseuses Bénignes",
        "short_label": "RF & Cryo (OO / Chondroblastome / TCG)",
        "icon": "flame",
        "color": "#f97316",
        "agenda_examples": [
            "RF ostéome ostéoïde coude, tibia proximal, hanche & C6",
            "RF / Cryothérapie ostéome ostéoïde de l'astragale (no-touch)",
            "RF & Cryoablation de chondroblastome et récidive de TCG du genou"
        ]
    },
    "desmoid_soft_tissue": {
        "id": "desmoid_soft_tissue",
        "label": "Cryoablation des Tumeurs Desmoïdes & Parties Molles",
        "short_label": "Cryo Desmoïdes & Tissus Mous",
        "icon": "snowflake",
        "color": "#06b6d4",
        "agenda_examples": [
            "Cryothérapie tumeur desmoïde creux sus-claviculaire & flanc gauche",
            "Cryothérapie nodules paravertébraux et du trapèze"
        ]
    },
    "ect_mets": {
        "id": "ect_mets",
        "label": "Électrochimiothérapie (ECT) & Métastases Osseuses",
        "short_label": "ECT (Bléomycine) & Métastases",
        "icon": "zap",
        "color": "#eab308",
        "agenda_examples": [
            "Électrochimiothérapie (ECT - Bléomycine 30 mg IV) au scanner Achard -1",
            "Traitement combiné Cryoablation + ECT (métastase osseuse du pied - cancer rénal)",
            "Cryoablation pariétale thoracique à visée antalgique"
        ]
    },
    "consolidation_screw_cement": {
        "id": "consolidation_screw_cement",
        "label": "Cimentoplastie & Vissage Percutané du Bassin",
        "short_label": "Cimentoplastie & Vissage Bassin",
        "icon": "shield",
        "color": "#8b5cf6",
        "agenda_examples": [
            "Vissage percutané du bassin post-radiothérapie en HDJ Radio B",
            "Combinaison cryoablation de debulking + vissage du bassin",
            "Cimentoplastie cervicale et thoraco-lombaire (T12, L4) sous AG / AL"
        ]
    },
    "cyst_sclerotherapy": {
        "id": "cyst_sclerotherapy",
        "label": "Alcoolisation & Sclérothérapie des Kystes Osseux",
        "short_label": "Alcoolisation KOA / KOE",
        "icon": "droplet",
        "color": "#10b981",
        "agenda_examples": [
            "Alcoolisation (+/- cimentoplastie) de kyste osseux essentiel de l'aile iliaque",
            "Alcoolisation percutanée de kyste osseux anévrismal (KOA) de l'humérus droit"
        ]
    },
    "pain_cryoneurolysis": {
        "id": "pain_cryoneurolysis",
        "label": "Douleur & Neurolyse : Morton, Géniculés, Intercostaux & Clunéal",
        "short_label": "Cryoneurolyse & RF Nerveuse",
        "icon": "activity",
        "color": "#ec4899",
        "agenda_examples": [
            "Cryothérapie sous AL au scanner de névrome de Morton (2e et 3e espaces)",
            "Test anesthésique sous écho + Radiofréquence des nerfs géniculés (gonarthrose)",
            "Cryoneurolyse percutanée du nerf clunéal et du nerf intercostal sous scanner"
        ]
    },
    "pudendal_cryoneurolysis": {
        "id": "pudendal_cryoneurolysis",
        "label": "Cryoneurolyse du Nerf Pudendal & Névralgie Pelvi-Périnéale",
        "short_label": "Cryoneurolyse Nerf Pudendal",
        "icon": "snowflake",
        "color": "#0ea5e9",
        "agenda_examples": [
            "Cryoneurolyse percutanée du nerf pudendal sous scanner (épine ischiatique / canal d'Alcock)",
            "Bloc test anesthésique scanoguidé du nerf pudendal (critères de Nantes)",
            "Cryoneurolyse pudendale bilatérale antalgique (douleurs pelvi-périnéales réfractaires et oncologiques)"
        ]
    },
    "msk_biopsy": {
        "id": "msk_biopsy",
        "label": "Biopsies Ostéo-Articulaires, Synoviales & Sarcomes",
        "short_label": "Biopsies TDM & Écho",
        "icon": "crosshair",
        "color": "#3b82f6",
        "agenda_examples": [
            "Biopsie synoviale du genou sous scanner (suspicion chondromatose / SVN)",
            "Biopsie osseuse sous scanner (crête iliaque, sacrum) & biopsie couplée à la cryoablation",
            "Biopsie de masse des parties molles et tumeur lipomateuse profonde sous écho/TDM (MDM2)"
        ]
    },
    "msk_imaging": {
        "id": "msk_imaging",
        "label": "Imagerie Ostéo-Articulaire Diagnostique & Suivi Post-Geste",
        "short_label": "IRM / TDM Diagnostique & Suivi",
        "icon": "eye",
        "color": "#6366f1",
        "agenda_examples": [
            "IRM dynamique protocole ostéome ostéoïde avant RF",
            "IRM rachis lombaire et cervicale de contrôle post-cryothérapie (à 6 semaines et 3 mois)",
            "IRM de suivi de TTCG / synovite villonodulaire sous thérapie ciblée & arthroscanner"
        ]
    },
    "percutaneous_ablation_general": {
        "id": "percutaneous_ablation_general",
        "label": "Ablation Percutanée Tumorale : Standards, Endométriome & Oncologie",
        "short_label": "Ablation Percutanée (Standards & Onco)",
        "icon": "target",
        "color": "#e11d48",
        "agenda_examples": [
            "Standards CIRSE d'ablation thermique osseuse (RF, cryoablation, micro-ondes)",
            "Cryoablation percutanée d'endométriome pariétal abdominal et parties molles",
            "Ablation thermique à visée curative et palliative des tumeurs osseuses malignes"
        ]
    }
}


CURATED_DATA = {
    "42489686": {
        "category_id": "ablation_benign",
        "title_fr": "Radiofréquence guidée par scanner d'un ostéome ostéoïde tibial : sécurité, dosimétrie et gestion péri-procédurale",
        "modality": "Scanner TDM",
        "intervention_type": "Radiofréquence (RF)",
        "cochin_link": "En lien direct avec les radiofréquences d'ostéome ostéoïde du tibia proximal gauche, du coude et de la hanche programmées en HDJ Radio B (Pavillon Achard -1).",
        "summary_fr_short": "Démonstration de la faisabilité et de la sécurité d'une ablation par radiofréquence (RF) sous guidage TDM basse dose d'un ostéome ostéoïde cortical tibial. L'optimisation du collimatage, la réduction du kilovoltage et l'utilisation d'une sonde monopolaire permettent une éradication complète du nidus avec sédation/anesthésie adaptée et disparition immédiate des douleurs nocturnes.",
        "summary_fr_detailed": "L'ablation thermique par radiofréquence (RF) sous guidage tomodensitométrique constitue le gold standard thérapeutique de l'ostéome ostéoïde. Cet article détaille les stratégies d'optimisation technique et de radioprotection extrême lors du ciblage d'un nidus tibial cortical : acquisition hélicoïdale ultra-focalisée, abord trans-cortical à la tréphine osseuse et thermocoagulation contrôlée à 90 °C pendant 6 minutes. La résolution complète des douleurs inflammatoires nocturnes est obtenue dès 24–48 h sans récidive clinique au suivi.",
        "protocol_fr": "Repérage TDM millimétrique basse dose centré sur le nidus • Forage cortical coaxial (11G–14G) • Électrode RF à extrémité active 5 à 7 mm • Palier thermique à 90 °C pendant 6 minutes • Contrôle de l'intégrité cutanée si localisation superficielle (crête tibiale / astragale).",
        "key_points_fr": [
            "Taux de succès clinique primaire de la RF d'ostéome ostéoïde > 92–95 % dès la première séance.",
            "L'optimisation du protocole TDM (collimation serrée, bas kVp) réduit drastiquement la dose efficace délivrée aux patients jeunes.",
            "Attention particulière aux localisations superficielles (tibia antérieur, astragale, coude) pour prévenir les brûlures cutanées ou cartilagineuses.",
            "L'IRM dynamique injectée (séquence T1 gadolinium précoce) permet de confirmer le nidus en amont afin de limiter les acquisitions TDM diagnostiques."
        ],
        "tags": ["Ostéome ostéoïde", "Radiofréquence", "Tibia", "Scanner", "Radioprotection", "HDJ Radio B"]
    },
    "33839926": {
        "category_id": "ablation_benign",
        "title_fr": "Ostéome ostéoïde : quelle est la meilleure option mini-invasive ? Comparaison Radiofréquence, Cryoablation, Micro-ondes et Laser",
        "modality": "Scanner TDM",
        "intervention_type": "RF vs Cryoablation",
        "cochin_link": "Éclaire directement le choix entre Radiofréquence et Cryoablation (technique 'no-touch') pour les ostéomes ostéoïdes superficiels ou intra-articulaires comme celui de l'astragale pris en charge à Cochin.",
        "summary_fr_short": "Revue comparative des techniques percutanées d'ablation thermique de l'ostéome ostéoïde (RF, cryoablation, laser, micro-ondes). Alors que la RF reste la référence historique pour les lésions corticales classiques, la cryoablation offre un avantage majeur grâce à la visualisation directe du glaçon ('iceball') au scanner et à la possibilité d'une approche 'no-touch' extra-osseuse.",
        "summary_fr_detailed": "Cette étude synthétise les performances cliniques et les profils de sécurité des modalités d'ablation percutanée de l'ostéome ostéoïde. L'efficacité globale dépasse 90 % quelle que soit la technique thermique, avec un taux de complications mineures inférieur à 3 %. La cryoablation se distingue par la possibilité de positionner la cryosonde au contact du cortex péri-lésionnel sans forer le nidus ('no-touch'), réduisant le traumatisme mécanique sur les petits os (talus/astragale, carpe) ou à proximité immédiate du cartilage et des nerfs.",
        "protocol_fr": "RF : canulation directe du nidus, 90 °C (4–6 min). Cryoablation : 1 sonde 17G en position juxta-corticale ('no-touch') ou intra-lésionnelle, cycle Congélation (8–10 min) – Décongélation passive/active (5 min) – Congélation (8–10 min) avec suivi TDM de l'isotherme 0 °C.",
        "key_points_fr": [
            "Efficacité équivalente entre RF et Cryoablation (> 93 % de guérison clinique durable).",
            "La technique 'no-touch' en cryoablation évite le forage du nidus dans les os du tarse (astragale) et les lésions superficielles.",
            "Visualisation en temps réel de la zone d'ablation hypodense (iceball) sous scanner en cryoablation.",
            "Moins de douleurs post-procédurales immédiates après cryoablation grâce à l'effet analgésique intrinsèque du froid sur le périoste."
        ],
        "tags": ["Ostéome ostéoïde", "Cryoablation", "Radiofréquence", "No-touch", "Astragale", "Talus"]
    },
    "19304917": {
        "category_id": "ablation_benign",
        "title_fr": "Chondroblastome : l'ablation par radiofréquence comme alternative curative à la résection chirurgicale",
        "modality": "Scanner TDM",
        "intervention_type": "Radiofréquence (RF)",
        "cochin_link": "Référence fondamentale pour les radiofréquences et cryoablations de chondroblastome du genou (à distance de la lame sous-chondrale) et la gestion des récidives locales en Radiologie B.",
        "summary_fr_short": "Étude princeps démontrant que l'ablation thermique par radiofréquence sous scanner est une alternative sûre et efficace au curetage chirurgical pour les chondroblastomes épiphysaires sélectionnés. Elle permet une sédation rapide des douleurs et une préservation articulaire, sous réserve d'une maîtrise stricte de la marge thermique vis-à-vis du cartilage hyalin sous-chondral.",
        "summary_fr_detailed": "Le chondroblastome est une tumeur cartilagineuse bénigne mais localement agressive touchant électivement les épiphyses (genou, tête fémorale, tête humérale). Le curetage chirurgical expose au risque de lésion du cartilage articulaire ou du cartilage de croissance et présente un taux de récidive de 10 à 35 %. Dans cette série de *Radiology*, l'ablation par radiofréquence guidée par scanner obtient une disparition complète des douleurs et une récupération fonctionnelle rapide. Le point critique est le respect d'une distance de sécurité par rapport à la lame osseuse sous-chondrale pour éviter toute chondrolyse secondaire ou effondrement articulaire.",
        "protocol_fr": "Bilan pré-thérapeutique par TDM fin + IRM pour mesurer l'épaisseur de la lame sous-chondrale • Abord extra-articulaire strict • Multi-positionnement de l'électrode RF (ou cryosonde) si la lésion dépasse 15–20 mm • Refroidissement intra-articulaire au sérum physiologique si proximité cartilagineuse.",
        "key_points_fr": [
            "Alternative mini-invasive majeure au curetage chirurgical pour les chondroblastomes épiphysaires de taille petite à modérée (< 2,5 cm).",
            "Préservation de la lame osseuse sous-chondrale indispensable : risque d'effondrement ostéochondral si l'ablation touche directement l'os sous-chondral porteur.",
            "En cas de lésion résiduelle sur les berges d'une cavité déjà traitée, une séance complémentaire ciblée (RF ou cryoablation) permet le contrôle local.",
            "Suivi IRM et TDM indispensable à 3, 6 et 12 mois pour évaluer la réossification progressive de la loge d'ablation."
        ],
        "tags": ["Chondroblastome", "Radiofréquence", "Genou", "Épiphyse", "Lame sous-chondrale", "Radiology"]
    },
    "24838839": {
        "category_id": "ablation_benign",
        "title_fr": "Ablation percutanée guidée par l'image des tumeurs osseuses et des parties molles : revue des modalités et indications",
        "modality": "Multimodal (TDM / IRM / Écho)",
        "intervention_type": "Ablation Thermique (RF / Cryo / MW)",
        "cochin_link": "Socle méthodologique pour l'ensemble du plateau d'ablation thermique ostéo-articulaire (Achard -1) : choix de l'énergie selon le caractère ostéolytique, ostéocondensant ou tissulaire.",
        "summary_fr_short": "Synthèse exhaustive d'*Insights into Imaging* comparant les principes physiques, indications et limites de la radiofréquence, de la cryoablation, des micro-ondes et du laser dans les tumeurs musculosquelettiques bénignes et malignes, avec un focus sur les techniques de thermoprotection des structures nobles.",
        "summary_fr_detailed": "Cet article de référence détaille la physique de propagation thermique dans l'os cortical et spongieux. Alors que l'os cortical agit comme un isolant électrique limitant la diffusion de la radiofréquence, le froid en cryoablation franchit aisément l'os condensant et permet de traiter des lésions ostéoblastiques ou volumineuses en associant plusieurs cryosondes synergiques. L'article systématise également les manœuvres de protection thermique (carbodissection, hydrodissection au glucosé ou sérum salé, thermométrie par thermocouple et électrostimulation nerveuse).",
        "protocol_fr": "Sélection de l'énergie : RF monopolaire/bipolaire pour petites lésions intra-osseuses (< 1,5 cm) ; Cryoablation multi-sondes pour lésions > 2 cm, ostéocondensantes ou des parties molles • Protection nerveuse si distance < 10 mm de l'iceball.",
        "key_points_fr": [
            "L'os cortical freine le courant RF (haute impédance) mais laisse diffuser le froid en cryoablation.",
            "Seuil de neurotoxicité thermique : < 10 °C et > 45 °C pour les troncs nerveux périphériques et radiculaires.",
            "Association systématique d'une consolidation (cimentoplastie ou vissage) après ablation en zone portante (cotyle, col fémoral, corps vertébral).",
            "L'hydrodissection et la carbodissection (CO2) permettent d'écarter la peau, le tube digestif ou les plexus nerveux."
        ],
        "tags": ["Ablation thermique", "Cryoablation", "Radiofréquence", "Thermoprotection", "Hydrodissection"]
    },
    "33290994": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Étude prospective multicentrique CRYODESMO-01 (Phase II) : cryoablation des tumeurs desmoïdes extra-abdominales en progression",
        "modality": "Scanner TDM / IRM",
        "intervention_type": "Cryoablation",
        "cochin_link": "Essai prospectif français de référence pour les cryoablations de tumeurs desmoïdes réalisées à Cochin (ex: tumeur desmoïde du creux sus-claviculaire à proximité du plexus brachial).",
        "summary_fr_short": "Essai prospectif multicentrique français de phase II (Kurtz, Buy, Deschamps et al.) évaluant la cryoablation percutanée chez 50 patients porteurs de tumeurs desmoïdes extra-abdominales progressives après traitement médical. À 12 mois, 85,6 % des patients n'ont aucune progression tumorale, avec une réduction marquée des douleurs et une amélioration fonctionnelle significative.",
        "summary_fr_detailed": "Les tumeurs desmoïdes (fibromatoses agressives) présentent un taux élevé de récidive locale après chirurgie mutilante. L'essai français CRYODESMO-01 a évalué de manière prospective la cryoablation percutanée sous guidage TDM/IRM chez 50 patients en échec d'au moins une ligne systémique. Le critère principal de non-progression à 12 mois (selon mRECIST sur le tissu viable rehaussé) atteint 85,6 % (réponse complète 28,6 %, réponse partielle 26,2 %, maladie stable 31,0 %). Le score moyen de douleur diminue dès le premier mois, confirmant la cryoablation comme traitement local de référence.",
        "protocol_fr": "Planification IRM T1 Gado et T2 FS • Sous AG, implantation de cryosondes 17G espacées de 1,5 à 2 cm pour couvrir l'ensemble du volume tumoral avec marges de 5 mm • Double cycle Congélation (10 min) / Décongélation (10 min) • Neuromonitoring et hydrodissection continue si proximité d'un tronc nerveux (ex: plexus brachial, nerf sciatique).",
        "key_points_fr": [
            "Taux de contrôle local (non-progression à 12 mois) de 85,6 % dans l'essai prospectif français CRYODESMO-01.",
            "L'évaluation de la réponse repose sur les critères mRECIST en IRM (mesure du volume tumoral viable prenant le contraste, et non de la taille globale incluant la nécrose).",
            "Le volume tumoral initial et la proximité immédiate des troncs nerveux imposent une planification multi-sondes rigoureuse et une hydrodissection protectrice.",
            "Alternative mini-invasive de premier plan évitant la chirurgie délabrante après surveillance active ou traitement systémique."
        ],
        "tags": ["Tumeur desmoïde", "CRYODESMO-01", "Cryoablation", "Plexus brachial", "Parties molles", "mRECIST"]
    },
    "39556172": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Cryoablation percutanée dans la prise en charge des tumeurs des parties molles : revue pédagogique et technique",
        "modality": "Scanner TDM / Échographie",
        "intervention_type": "Cryoablation",
        "cochin_link": "Guide pratique pour la cryoablation des masses des parties molles (tumeurs desmoïdes, nodules métastatiques paravertébraux ou du trapèze, schwannomes, malformations vasculaires) en HDJ Radio B.",
        "summary_fr_short": "Revue didactique (*Insights into Imaging*, 2024) détaillant la sélection des patients, la balistique des cryosondes, la synergie thermique et la prévention des complications lors de la cryoablation des tumeurs bénignes et malignes des parties molles (desmoïdes, endométriomes pariétaux, métastases musculaires et sous-cutanées).",
        "summary_fr_detailed": "Cet article passe en revue l'ensemble des indications de la cryoablation des tissus mous en radiologie interventionnelle oncologique et fonctionnelle. Il détaille l'effet cytotoxique biphasique (formation de cristaux de glace intracellulaires à -40 °C, apoptose périphérique et thrombose microvasculaire), ainsi que la gestion des localisations superficielles ou juxta-nerveuses. Pour les nodules métastatiques musculaires (trapèze, loge paravertébrale) ou les tumeurs desmoïdes, la cryoablation procure un contrôle local durable et une sédation rapide de la douleur par dénervation locale.",
        "protocol_fr": "Guidage mixte Échographie (insertion des sondes et contrôle Doppler) + Scanner (cartographie 3D de l'iceball) • Gant chaud ou hydrodissection sous-cutanée au sérum physiologique tiède pour protéger le derme • Suivi IRM à 3 mois avec soustraction dynamique.",
        "key_points_fr": [
            "L'isotherme létal (-20 °C à -40 °C) se situe à environ 3 à 5 mm en dedans de la limite visible du glaçon (0 °C) au scanner.",
            "Pour les nodules superficiels (trapèze, paroi thoracique), une hydrodissection sous-cutanée continue prévient efficacement la nécrose cutanée.",
            "Efficacité remarquable sur les localisations oligométastatiques des parties molles (mélanome, cancer du rein, sein, sarcomes).",
            "Possibilité de réaliser le geste sous anesthésie locale + sédation consciente pour les lésions de petite taille à distance des troncs moteurs."
        ],
        "tags": ["Cryoablation", "Parties molles", "Nodule paravertébral", "Trapèze", "Hydrodissection", "Insights into Imaging"]
    },
    "42631901": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Prise en charge percutanée des tumeurs desmoïdes : actualisation 2026 des indications et thérapies ablatives",
        "modality": "Scanner TDM / IRM",
        "intervention_type": "Cryoablation / Ablation",
        "cochin_link": "Mise à jour 2026 intégrée aux discussions de RCP Sarcomes / Tumeurs des parties molles (Cochin) pour positionner la cryoablation face aux inhibiteurs de gamma-sécrétase et de tyrosine kinase.",
        "summary_fr_short": "Revue récente (*Current Oncology Reports*, 2026) précisant la place de la radiologie interventionnelle (cryoablation, micro-ondes, HIFU, embolisation transartérielle) dans l'algorithme moderne des tumeurs desmoïdes aux côtés de la surveillance active et des nouvelles thérapies ciblées (nirogacestat, sorafénib).",
        "summary_fr_detailed": "Avec l'évolution des recommandations internationales du Desmoid Tumor Working Group (DTWG), la chirurgie d'exérèse a laissé place à une approche conservatrice. Cet article de 2026 analyse les résultats à long terme de la cryoablation percutanée en première ou deuxième ligne pour les desmoïdes extra-abdominaux symptomatiques ou progressifs (ceinture scapulaire, creux sus-claviculaire, paroi thoracique, membres). La cryoablation permet d'éviter la toxicité chronique des traitements systémiques au long cours tout en préservant l'option d'un retraitement focal en cas de reliquat évolutif.",
        "protocol_fr": "Discussion systématique en RCP Sarcomes • Ablation complète (A0) visée lorsque l'anatomie le permet ; cryoablation de réduction volumétrique ('debulking' antalgique) avec épargne nerveuse lorsque la tumeur engaine le plexus brachial ou sciatique.",
        "key_points_fr": [
            "Taux de réponse objective de 55 à 80 % et contrôle symptomatique > 85 % après cryoablation des tumeurs desmoïdes.",
            "En cas de contiguïté avec le plexus brachial (creux sus-claviculaire), une cryoablation subtotale planifiée soulage les douleurs sans déficit moteur.",
            "Faible morbidité comparée à la chirurgie et absence de toxicité systémique prolongée (contrairement aux ITK ou inhibiteurs de gamma-sécrétase).",
            "Possibilité de séances itératives de cryoablation sur un bourgeon résiduel détecté sur l'IRM de suivi."
        ],
        "tags": ["Tumeur desmoïde", "Cryoablation", "RCP Sarcome", "Creux sus-claviculaire", "2026"]
    },
    "37834793": {
        "category_id": "ect_mets",
        "title_fr": "L'électrochimiothérapie (ECT) dans le traitement des métastases osseuses : revue systématique de la littérature",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Électrochimiothérapie (ECT)",
        "cochin_link": "Correspond directement aux séances d'Électrochimiothérapie (ECT sous Bléomycine 30 mg IV avec générateur IGEA) réalisées au scanner Achard -1 à Cochin, seules ou combinées à la cryoablation.",
        "summary_fr_short": "Revue systématique évaluant l'efficacité et la sécurité de l'électrochimiothérapie (ECT à la bléomycine) dans les métastases osseuses appendiculaires, pelviennes et rachidiennes. L'ECT associe l'injection intraveineuse de bléomycine à des impulsions électriques réversibles qui perméabilisent la membrane des cellules tumorales sans détruire la trame osseuse ni les structures nerveuses adjacentes.",
        "summary_fr_detailed": "Contrairement aux ablations thermiques (RF, cryoablation, micro-ondes), l'électrochimiothérapie (ECT) est une modalité non thermique basée sur l'électroporation réversible : des impulsions électriques de haut voltage ouvrent temporairement des nanopores membranaires, multipliant par plus de 1000 la pénétration intracellulaire de la bléomycine. Cette revue systématique démontre un contrôle antalgique majeur chez plus de 75–85 % des patients et une préservation unique de la résistance mécanique des travées osseuses, du cartilage articulaire et des gaines nerveuses, permettant de traiter des localisations complexes (pied, rachis, péri-articulaire).",
        "protocol_fr": "Positionnement parallèle des électrodes aiguilles sous guidage TDM selon la géométrie tumorale (espacement 1,5 à 2,5 cm) • Bolus IV de Bléomycine (15 000 UI/m² soit ~25–30 mg) • Fenêtre thérapeutique d'électroporation entre 8 min et 40 min post-injection (8 impulsions de 100 µs à 1000 V/cm par paire d'électrodes) sous AG avec curarisation.",
        "key_points_fr": [
            "Respect absolu de la fenêtre pharmacocinétique : délivrance des impulsions électriques entre 8 et 40 minutes après le bolus IV de bléomycine.",
            "Absence d'effet thermique délétère : préserve la matrice extracellulaire osseuse, l'os sous-chondral, les vaisseaux et les nerfs périphériques.",
            "Indication de choix pour les métastases osseuses distales (pied, main), juxta-articulaires ou radiorésistantes (cancer du rein, mélanome).",
            "Synergie remarquable avec la cryoablation ('Cryo + ECT') ou la cimentoplastie pour les lésions volumineuses ostéolytiques."
        ],
        "tags": ["Électrochimiothérapie", "ECT", "Bléomycine", "Métastases osseuses", "Pied", "IGEA"]
    },
    "38732352": {
        "category_id": "ect_mets",
        "title_fr": "Électrochimiothérapie des métastases rachidiennes et osseuses complexes : aspects techniques, balistique et sécurité neurologique",
        "modality": "Scanner TDM",
        "intervention_type": "Électrochimiothérapie (ECT)",
        "cochin_link": "Fournit les abaques techniques de placement des électrodes et de sécurité neurologique lors des procédures d'ECT réalisées en Radiologie B en collaboration avec l'HEGP.",
        "summary_fr_short": "Étude technique détaillant la mise en œuvre de l'électrochimiothérapie (ECT) pour les métastases osseuses à haut risque neurologique ou mécanique. Grâce à son mécanisme non thermique, l'ECT permet de traiter des lésions au contact direct d'éléments nerveux ou articulaires là où la radiofréquence et la cryoablation seules exposeraient à des complications.",
        "summary_fr_detailed": "Cet article analyse les paramètres pratiques d'implantation des électrodes d'électroporation dans l'os pathologique, la vérification de la couverture du champ électrique et les résultats cliniques sur la douleur (échelle EVA) et le contrôle tumoral local en imagerie. L'étude souligne l'importance de la synchronisation anesthésique (curarisation profonde au moment des impulsions électriques et limitation de la FiO2 sous bléomycine) et confirme l'absence de nécrose thermique des tissus sains environnants.",
        "protocol_fr": "Planification TDM de la géométrie des aiguilles • Curarisation per-procédurale pour limiter les secousses musculaires lors des impulsions • FiO2 < 30 % pendant l'anesthésie générale (prévention de la toxicité pulmonaire de la bléomycine) • Contrôle IRM à 6–12 semaines.",
        "key_points_fr": [
            "Précaution anesthésique essentielle : maintenir une FiO2 minimale (< 30 %) lors de l'AG après administration de bléomycine.",
            "Permet une destruction tumorale sélective au contact immédiat des structures nerveuses ou cutanées (pied, cheville, épidure).",
            "Diminution rapide et durable de l'EVA douleur et réduction de la consommation d'opioïdes dès le premier mois.",
            "Peut être associée dans le même temps opératoire à une cryoablation centrale (debulking) avec couronne périphérique d'ECT."
        ],
        "tags": ["Électrochimiothérapie", "ECT", "Bléomycine", "Sécurité neurologique", "Métastases", "Scanner"]
    },
    "37504355": {
        "category_id": "ect_mets",
        "title_fr": "Le rôle de la cryoablation percutanée dans les métastases osseuses : contrôle local, debulking et antalgie",
        "modality": "Scanner TDM",
        "intervention_type": "Cryoablation",
        "cochin_link": "Directement applicable aux cryoablations de métastases osseuses et pariétales (paroi thoracique, bassin, pied, trapèze) programmées en HDJ Radio B.",
        "summary_fr_short": "Revue complète sur la cryoablation percutanée des métastases osseuses à visée palliative (antalgique / debulking) ou curative (maladie oligométastatique). Analyse des résultats cliniques, du couplage avec les thérapies systémiques (anti-angiogéniques comme le lenvatinib, immunothérapie) et des techniques de consolidation associées.",
        "summary_fr_detailed": "La cryoablation s'est imposée comme la technique de choix pour les métastases osseuses douloureuses ou oligométastatiques, notamment celles comportant une extension dans les parties molles. La visualisation directe du glaçon au scanner permet de traiter des volumes complexes tout en protégeant la peau, la plèvre ou les nerfs adjacents. L'article discute également la gestion péri-procédurale des thérapies ciblées anti-angiogéniques (tels que le lenvatinib ou le cabozantinib dans le cancer du rein métastatique) afin d'optimiser la cicatrisation cutanée et d'éviter les complications hémorragiques.",
        "protocol_fr": "Suspension temporaire concertée avec l'oncologue des ITK anti-angiogéniques (ex: Lenvatinib 48–72h avant/après selon demi-vie et risque cutané) • Double cycle de congélation 10 min • Consolidation par cimentoplastie ou vissage si atteinte d'une zone de contrainte mécanique.",
        "key_points_fr": [
            "Soulagement antalgique significatif chez > 80 % des patients rebelles aux morphiniques ou après échec de la radiothérapie externe.",
            "Taux de contrôle local à 1 an de 85 à 92 % dans les indications oligométastatiques (marges d'ablation ≥ 5 mm).",
            "Dans les localisations distales (pied, main) ou sous anti-angiogéniques (Lenvatinib), vigilance accrue sur la protection cutanée.",
            "Pour les douleurs pariétales thoraciques oncologiques, la cryoablation associe destruction tumorale et cryoneurolyse intercostale."
        ],
        "tags": ["Cryoablation", "Métastases osseuses", "Paroi thoracique", "Lenvatinib", "Cancer du rein", "Debulking"]
    },
    "26318372": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Ostéosynthèse percutanée par vissage du bassin chez les patients oncologiques : technique sous scanner et résultats",
        "modality": "Scanner TDM / Cone-Beam CT",
        "intervention_type": "Vissage Percutané du Bassin",
        "cochin_link": "Référence directe pour les vissages percutanés du bassin (post-radiothérapie ou combinés à une cryoablation de debulking) réalisés au scanner Achard -1 à Cochin.",
        "summary_fr_short": "Série princeps de Deschamps, de Baère et Tselikas (*European Radiology*) démontrant l'efficacité et la fiabilité du vissage percutané guidé par scanner (seul ou associé à une cimentoplastie/ablation) pour stabiliser les fractures pathologiques ou post-radiques de l'anneau pelvien et du cotyle chez les patients atteints de cancer.",
        "summary_fr_detailed": "Les lésions ostéolytiques ou les fractures post-radiothérapie du bassin (aileron sacré, articulation sacro-iliaque, toit du cotyle, branches pubiennes) entraînent une impotence fonctionnelle sévère que la cimentoplastie seule ne suffit pas toujours à stabiliser en raison des contraintes de cisaillement et de traction. Cette étude montre que le vissage percutané canulé sous guidage scanner permet une remise en charge rapide, une réduction majeure des douleurs et un faible taux de complications. Il détaille également la conduite à tenir devant une migration secondaire de vis (reprise ou vissage complémentaire par voie antérieure ou postérieure).",
        "protocol_fr": "Sous AG et asepsie chirurgicale au scanner • Mise en place de broches-guides Kirschner selon les corridors osseux pelviens (trans-sacro-iliaque S1/S2, supra-acétabulaire antéro-postérieur ou rétrograde, colonne antérieure) • Vis canulées titane 6,5 à 8,0 mm +/- cimentoplastie d'ancrage ('screw-cementoplasty').",
        "key_points_fr": [
            "Restaure la stabilité mécanique en cisaillement et en compression de l'anneau pelvien là où le ciment seul est insuffisant.",
            "L'ancrage des vis par injection de ciment PMMA ('augmented osteosynthesis') prévient le démontage ou la migration de vis dans l'os irradié ou ostéoporotique.",
            "Permet une reprise précoce de l'appui dès J1 et une sortie rapide en hospitalisation de jour ou court séjour.",
            "En cas de migration tardive de vis sur os remanié post-radique, une reprise percutanée par voie antérieure ou un scellement au ciment permet de restaurer la stabilité."
        ],
        "tags": ["Vissage du bassin", "Ostéosynthèse percutanée", "Post-radiothérapie", "Cimentoplastie", "Deschamps", "European Radiology"]
    },
    "20848245": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Vertébroplastie / Cimentoplastie percutanée des métastases du rachis cervical : voies d'abord, sécurité et efficacité antalgique",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Cimentoplastie Cervicale",
        "cochin_link": "Correspond exactement aux cimentoplasties cervicales sous AG post-radiothérapie programmées au scanner Achard -1 (avec gestion péri-opératoire des anticoagulants Eliquis + Plavix).",
        "summary_fr_short": "Étude évaluant la cimentoplastie percutanée des fractures et lésions ostéolytiques métastatiques du rachis cervical (C2 à C7). Sous guidage scanner haute résolution, l'injection contrôlée de PMMA procure une stabilisation rachidienne immédiate et une réduction drastique des cervicalgies mécaniques rebelles.",
        "summary_fr_detailed": "La cimentoplastie cervicale est un geste de haute technicité en raison de la proximité de l'axe jugulo-carotidien, de l'artère vertébrale, du pharynx/œsophage et de la moelle cervicale. Cet article démontre que le guidage scanner (ou biplan/TDM combiné) par voie antéro-latérale pré-vasculaire (C3–C7) ou trans-orale/antéro-latérale haute (C2) permet un positionnement millimétrique du trocart 13G–15G. Chez les patients sous double traitement antithrombotique (ex: AOD type apixaban/Eliquis + clopidogrel/Plavix), une fenêtre d'arrêt coordonnée avec l'anesthésiste et le cardiologue est indispensable pour prévenir tout hématome pré-vertébral ou épidural.",
        "protocol_fr": "Sous AG • Voie antéro-latérale cervicale sous TDM en réclinant manuellement le paquet jugulo-carotidien en dehors et l'axe viscéral (trachée/œsophage) en dedans • Trocart biseauté 13G ou 15G • Injection fractionnée de ciment PMMA radio-opaque de haute viscosité (1,5 à 2,5 mL) sous contrôle TDM séquentiel • Gestion stricte des anticoagulants (arrêt Eliquis J-3, relais/arrêt Plavix selon protocole anesthésie).",
        "key_points_fr": [
            "Réduction rapide et durable des douleurs cervicales (> 80 % des patients) et prévention du collapsus vertébral secondaire.",
            "Voie antéro-latérale sous TDM (entre la gaine carotidienne latéralement et l'œsophage médialement) : voie de choix pour C3–C7.",
            "Geste classé à haut risque hémorragique (espace rétropharyngé et canal rachidien cervical) : arrêt impératif des AOD (Eliquis J-3) et gestion des antiagrégants (Plavix) validés en consultation d'anesthésie.",
            "Faible volume de ciment nécessaire (1,5 à 2,5 mL) pour restaurer la résistance mécanique d'un corps vertébral cervical."
        ],
        "tags": ["Cimentoplastie cervicale", "Vertébroplastie", "Rachis cervical", "Anticoagulants", "Eliquis", "Scanner"]
    },
    "38544877": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "De la cimentoplastie à la cryoablation et à l'ostéosynthèse percutanée : état de l'art en radiologie interventionnelle osseuse",
        "modality": "Scanner TDM / Cone-Beam CT",
        "intervention_type": "Consolidation & Ablation Combinées",
        "cochin_link": "Synthétise la stratégie multimodale appliquée à Cochin : associer destruction tumorale (cryoablation/RF) et consolidation mécanique (cimentoplastie / vissage) en une seule séance.",
        "summary_fr_short": "Revue générale (*BJR Open*, 2024) détaillant l'évolution des gestes percutanés osseux : critères de sélection entre cimentoplastie seule, ostéosynthèse par vis canulées et association ablation thermique + consolidation selon la classification de Mirels et le score SINS.",
        "summary_fr_detailed": "Cet article propose un algorithme décisionnel complet pour le radiologue interventionnel ostéo-articulaire. Il précise les propriétés biomécaniques du ciment PMMA (excellente résistance aux forces de compression au rachis et au toit du cotyle, mais résistance limitée aux forces de torsion et de traction sur le bassin postérieur et les os longs, justifiant l'association au vissage percutané). Il détaille également la chronologie optimale lors des gestes combinés : réaliser la cryoablation suivie d'un réchauffement complet de la loge avant d'injecter le ciment PMMA afin de ne pas altérer sa polymérisation.",
        "protocol_fr": "Évaluation biomécanique pré-opératoire (score SINS au rachis, localisation en zone portante au bassin) • En cas de geste combiné Cryo + Cimentoplastie : attendre la décongélation complète du glaçon avant d'injecter le PMMA.",
        "key_points_fr": [
            "Le ciment PMMA résiste parfaitement à la compression (corps vertébral, toit du cotyle) mais nécessite des vis canulées en zone de cisaillement (anneau pelvien, col fémoral).",
            "Toujours attendre la fonte du glaçon après cryoablation avant d'injecter le ciment pour éviter une polymérisation retardée ou des fuites.",
            "La cryoablation préalable réduit la pression intra-tumorale et diminue le risque de fuite veineuse ou épidurale de ciment.",
            "L'évaluation multidisciplinaire (radiologue interventionnel, orthopédiste, oncologue, anesthésiste) optimise le calendrier vis-à-vis de la radiothérapie."
        ],
        "tags": ["Cimentoplastie", "Cryoablation", "Ostéosynthèse", "PMMA", "Biomécanique", "BJR Open"]
    },
    "35941207": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Mise au point sur le kyste osseux anévrismal (KOA) : physiopathologie, imagerie et sclérothérapie percutanée",
        "modality": "Scanner TDM / Fluoroscopie / Écho",
        "intervention_type": "Sclérothérapie / Alcoolisation",
        "cochin_link": "Directement lié au suivi TDM à 1 an des kystes osseux anévrismaux (KOA de l'humérus) et aux alcoolisations de kystes osseux en HDJ Radio B.",
        "summary_fr_short": "Mise au point de référence (*Pediatric Radiology*, 2022) sur le kyste osseux anévrismal (KOA) primaire (réarrangement du gène *USP6*) : sémiologie IRM/TDM, diagnostic différentiel avec l'ostéosarcome télangiectasique et protocoles de sclérothérapie percutanée (éthanol absolu, polidocanol, doxycycline).",
        "summary_fr_detailed": "La découverte de la translocation du gène *USP6* a confirmé la nature néoplasique bénigne du KOA primaire, distinct des formes secondaires réactionnelles à un chondroblastome ou une tumeur à cellules géantes. Sur le plan thérapeutique, la sclérothérapie percutanée (alcoolisation à l'éthanol absolu gélifié ou liquide, polidocanol, doxycycline) a largement remplacé le curetage chirurgical, avec d'excellents taux d'ossification progressive et moins de morbidité fonctionnelle. Le suivi repose sur la tomodensitométrie et la radiographie à 6 et 12 mois pour objectiver l'épaississement cortical et la trabéculation des logettes.",
        "protocol_fr": "Biopsie préalable systématique si atypie clinique ou radiologique (recherche réarrangement USP6, exclusion ostéosarcome télangiectasique) • Ponction des logettes sous TDM/ampli avec kystographie iodée pour exclure un drainage veineux rapide • Injection de l'agent sclérosant (éthanol 96 % / éthylcellulose ou polidocanol) • Contrôle TDM à 6–12 mois.",
        "key_points_fr": [
            "Toute lésion kystique multiloculée à niveaux liquide-liquide atypique doit bénéficier d'une confirmation histologique/moléculaire (USP6) avant sclérothérapie.",
            "La kystographie préalable au produit de contraste iodé est indispensable avant alcoolisation pour éliminer une fuite veineuse directe ou un passage articulaire.",
            "La guérison radiologique au scanner se traduit par un épaississement cortical progressif, une disparition de l'effet soufflant et une ossification centripète sur 6 à 24 mois.",
            "Une ossification partielle asymptomatique avec corticale solide au scanner à 1 an ne nécessite pas de nouveau geste."
        ],
        "tags": ["Kyste osseux anévrismal", "KOA", "Alcoolisation", "Sclérothérapie", "USP6", "Humérus"]
    },
    "34367902": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Stratégies actuelles de traitement des kystes osseux essentiels (solitaires) et anévrismaux : alcoolisation et comblement",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Alcoolisation +/- Cimentoplastie",
        "cochin_link": "Correspond à l'avis et à la prise en charge en HDJ pour alcoolisation (+/- cimentoplastie) d'un volumineux kyste osseux essentiel de l'aile iliaque ou de l'humérus proximal.",
        "summary_fr_short": "Revue comparant les techniques mini-invasives de traitement du kyste osseux essentiel (KOE / unicameral bone cyst) et du kyste osseux anévrismal : alcoolisation percutanée à l'éthanol, injection de corticoïdes, décompression et adjonction d'un substitut osseux ou d'une cimentoplastie dans les kystes volumineux à risque fracturaire.",
        "summary_fr_detailed": "Le kyste osseux essentiel (KOE) touche principalement la métaphyse proximale de l'humérus et du fémur ainsi que l'aile iliaque chez l'adolescent et le jeune adulte. Sa paroi tapissée d'une membrane fibreuse sécrétant des prostaglandines et des enzymes ostéolytiques peut être détruite efficacement par alcoolisation percutanée après évacuation du liquide citrin et kystographie. Pour les kystes volumineux du bassin (aile iliaque) ou des zones portantes, l'alcoolisation de la membrane kystique peut être complétée par un comblement (substitut phosphocalcique ou cimentoplastie) afin d'assurer une consolidation mécanique immédiate.",
        "protocol_fr": "Double ponction (technique à deux aiguilles pour lavage-drainage sans hyperpression) • Kystographie de sécurité • Instillation d'éthanol à 96 % pendant 10–15 minutes puis aspiration complète et rinçage au sérum physiologique • Comblement optionnel si volumineuse cavité fragilisante (aile iliaque).",
        "key_points_fr": [
            "Technique à double trocart recommandée dans les grands kystes essentiels (aile iliaque, humérus) pour éviter toute surpression lors de l'injection.",
            "L'alcoolisation détruit la membrane endokystique sécrétante et induit une ostéogenèse réparatrice dans 80 à 90 % des cas en 1 à 2 séances.",
            "Dans les volumineux kystes de l'aile iliaque, l'association alcoolisation + comblement/cimentoplastie prévient les fractures pathologiques lors de la reprise sportive.",
            "Suivi radiographique ou TDM à 6 et 12 mois selon la classification de Neer / Capanna."
        ],
        "tags": ["Kyste osseux essentiel", "KOE", "Alcoolisation", "Aile iliaque", "Cimentoplastie", "Kystographie"]
    },
    "38438685": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Sécurité et efficacité de la cryoneurolyse percutanée du névrome de Morton sous anesthésie locale",
        "modality": "Échographie / Scanner TDM",
        "intervention_type": "Cryoneurolyse (Morton)",
        "cochin_link": "Référence centrale pour les cryothérapies de névrome de Morton (3e espace inter-métatarsien) réalisées sous anesthésie locale au scanner à Cochin par le Dr Thomas Lefèvre.",
        "summary_fr_short": "Étude de *CardioVascular and Interventional Radiology (CVIR)* (2024) évaluant la cryoneurolyse percutanée du névrome de Morton réfractaire au traitement conservateur. Réalisée en ambulatoire sous anesthésie locale, la cryoablation induit une dégénérescence wallérienne réversible (axonotmésis) sans formation de névrome d'amputation, avec un succès clinique supérieur à 80 %.",
        "summary_fr_detailed": "Le névrome de Morton correspond à une fibrose périneurale du nerf digital plantaire commun (le plus souvent au 3e espace inter-métatarsien). La chirurgie d'exérèse (neurectomie) expose au risque redouté de névrome de moignon douloureux ('stump neuroma') et de cicatrice plantaire. La cryoneurolyse percutanée par voie dorsale ou dans l'axe de l'espace inter-métatarsien détruit les axones tout en préservant l'architecture de l'endonèvre et du périnèvre. Cette série de 2024 confirme une réduction majeure de l'EVA douleur, une reprise immédiate de la marche et une tolérance remarquable sous simple anesthésie locale.",
        "protocol_fr": "Sous anesthésie locale stricte (lidocaïne à proximité du nerf en amont) • Abord dorsal ou commissural dans l'axe du 3e espace inter-métatarsien sous guidage TDM et/ou échographique • Cryosonde fine (17G ou aiguille de cryoneurolyse) centrée sur le névrome • 2 cycles de congélation de 2 à 3 minutes séparés d'une décongélation de 1 minute • Vérification de la distance à la peau plantaire et dorsale (> 5 mm ou hydrodissection).",
        "key_points_fr": [
            "Réalisable en ambulatoire strict sous anesthésie locale (AL) avec reprise immédiate de l'appui à la sortie du scanner.",
            "Contrairement à la chirurgie ou à l'alcoolisation, la cryoneurolyse respecte la gaine conjonctive nerveuse (axonotmésis de type II de Sunderland) et ne crée jamais de névrome d'amputation.",
            "Taux de satisfaction et de réduction significative des douleurs > 80–85 % à 6 et 12 mois.",
            "Protection cutanée essentielle dans l'espace inter-métatarsien étroit : contrôle de l'extension du glaçon au scanner/écho et hydrodissection sous-cutanée dorsale si nécessaire."
        ],
        "tags": ["Névrome de Morton", "Cryoneurolyse", "Cryoablation", "Anesthésie locale", "Avant-pied", "CVIR 2024"]
    },
    "42602563": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Nerfs géniculés : écho-anatomie détaillée, techniques de repérage échographique et implications pour le bloc test et la radiofréquence",
        "modality": "Échographie",
        "intervention_type": "Bloc Test & RF Nerfs Géniculés",
        "cochin_link": "Guide anatomique et échographique exact pour les tests anesthésiques du genou sous échographie (Pavillon Ollier) avant radiofréquence / neurolyse des nerfs géniculés.",
        "summary_fr_short": "Article de référence (2026) détaillant l'anatomie échographique haute résolution des nerfs géniculés (supéro-latéral SLGN, supéro-médial SMGN, inféro-médial IMGN, nerf récurrent fibulaire et nerf du vaste intermédiaire). Précise les repères vasculaires et périostés permettant un bloc test diagnostique ultra-sélectif avant radiofréquence.",
        "summary_fr_detailed": "La réussite de la radiofréquence ou de la cryoneurolyse des nerfs géniculés dans la gonarthrose ou les douleurs persistantes du genou dépend directement de la précision du repérage anatomique et de la positivité du bloc test anesthésique préalable. Cet article illustre les repères échographiques constants à la jonction diaphyso-métaphysaire fémorale et tibiale, au contact des artères géniculées en Doppler couleur/puissance. Il souligne comment l'utilisation d'un faible volume d'anesthésique local (0,5 à 1 mL par cible) lors du test écho-guidé évite les faux positifs par diffusion articulaire.",
        "protocol_fr": "Sonde linéaire haute fréquence (12–18 MHz) • Ciblage des 3 troncs classiques : SMGN (jonction diaphyse-épicondyle médial fémoral), SLGN (jonction diaphyse-épicondyle latéral fémoral), IMGN (jonction diaphyse-épicondyle médial tibial sous le LCM) • Épargne systématique du nerf géniculé inféro-latéral (proximité du nerf fibulaire commun) • Bloc test avec 0,5 à 1 mL de lidocaïne/ropivacaïne par nerf (positif si baisse EVA ≥ 50 %).",
        "key_points_fr": [
            "Le bloc test anesthésique sous échographie avec faible volume (0,5–1 mL par nerf) est le meilleur prédicteur d'efficacité de la radiofréquence.",
            "Le Doppler couleur/micro-flux permet de visualiser les artères géniculées accompagnant les rameaux nerveux au contact du périoste.",
            "Ne jamais cibler le nerf géniculé inféro-latéral (ILGN) en raison du risque de lésion motrice du nerf fibulaire commun (steppage).",
            "L'extension du protocole à 4 ou 5 cibles (incluant le nerf supra-patellaire / vaste médial et intermédiaire) améliore le taux de répondeurs."
        ],
        "tags": ["Nerfs géniculés", "Échographie", "Bloc test anesthésique", "Radiofréquence", "Gonarthrose"]
    },
    "28431129": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Radiofréquence des nerfs géniculés et cryoneurolyse des nerfs périphériques (intercostaux / post-amputation) : efficacité à long terme",
        "modality": "Échographie / Scanner TDM",
        "intervention_type": "RF Géniculés & Cryoneurolyse Périphérique",
        "cochin_link": "Couvre à la fois les radiofréquences des nerfs géniculés après bloc test positif et les cryoneurolyses du nerf intercostal (post-zona) ou des névromes post-amputation suivis à Cochin.",
        "summary_fr_short": "Étude de référence sur la dénervation thermique par radiofréquence des nerfs géniculés et la neurolyse percutanée des douleurs neuropathiques chroniques. Montre une réduction significative de la douleur (≥ 50 % chez 74 % des patients), une amélioration du score fonctionnel WOMAC et une diminution durable de la consommation d'antalgiques.",
        "summary_fr_detailed": "Cet essai clinique démontre la supériorité et la durabilité de l'ablation par radiofréquence des nerfs géniculés chez les patients souffrant de gonalgies chroniques après sélection par bloc pronostique. Les mêmes principes de sélection par bloc test positif s'appliquent aux cryoneurolyses des nerfs intercostaux (douleurs neuropathiques post-zostériennes ou post-thoracotomie) et des nerfs de moignon d'amputation trans-tibiale (nerf tibial / fibulaire / saphène) : le bloc anesthésique préalable valide la cible somatotopique avant de réaliser une neurolyse thermique (RF à 80 °C ou cryoneurolyse à -60 °C sous AL).",
        "protocol_fr": "Nerfs géniculés : RF conventionnelle (80 °C, 90 s) ou refroidie (60 °C, 150 s) après test moteur négatif à 2 Hz. Nerf intercostal (post-zona) / Névrome post-amputation : repérage TDM ou écho au bord inférieur de la côte (espace subcostal), hydrodissection pleurale de sécurité, puis cryoneurolyse sous AL (2 cycles de 2 min).",
        "key_points_fr": [
            "Plus de 70 % des patients sélectionnés par un bloc test positif maintiennent une réduction de douleur ≥ 50 % à 6–12 mois.",
            "Toujours réaliser un test de stimulation motrice (2 Hz jusqu'à 1–2 V) avant thermocoagulation RF pour exclure toute proximité de fibres motrices.",
            "Pour la cryoneurolyse intercostale (douleur post-zona ou oncologique), le guidage TDM au bord inférieur costal évite tout risque de pneumothorax.",
            "Dans les douleurs neuropathiques post-amputation trans-tibiale, la cryoneurolyse ciblée du névrome terminal ou du tronc nerveux d'amont soulage les décharges électriques et douleurs fantômes."
        ],
        "tags": ["Radiofréquence", "Nerfs géniculés", "Cryoneurolyse", "Nerf intercostal", "Post-zona", "Post-amputation"]
    },
    "34497298": {
        "category_id": "msk_biopsy",
        "title_fr": "Précision diagnostique et sécurité des biopsies percutanées écho-guidées des tumeurs des parties molles et sarcomes : respect des fascias et compartiments",
        "modality": "Échographie",
        "intervention_type": "Biopsie sous Échographie",
        "cochin_link": "Correspond exactement aux biopsies de masses des parties molles (cuisse, bras apposée sur le fascia sans traverser le fascia) demandées par l'orthopédie Cochin (Pr Anract, Pr Biau, Dr Dumaine).",
        "summary_fr_short": "Étude démontrant que la microbiopsie percutanée au trocart automatique (14G–16G) sous guidage échographique atteint une précision diagnostique de 95 à 97 % pour différencier lésion bénigne/maligne et grader les sarcomes des tissus mous, tout en réduisant drastiquement les complications par rapport à la biopsie chirurgicale incisionnelle.",
        "summary_fr_detailed": "Dans les centres de référence sarcomes (réseau NetSarc / Cochin), toute masse des parties molles profonde, > 5 cm ou évolutive doit être biopsiée par voie percutanée radioguidée après IRM. Cet article confirme que la biopsie écho-guidée permet de cibler en temps réel les portions charnues hypervasculaires en évitant les plages nécrotiques, tout en contrôlant millimétriquement la profondeur de tir pour ne jamais franchir un fascia profond sain ni contaminer un compartiment anatomique adjacent ou un pédicule vasculo-nerveux.",
        "protocol_fr": "Validation préalable de la voie d'abord avec le chirurgien orthopédiste référent (trajet de biopsie excisable lors de la chirurgie finale) • Abord tangentiel strict si masse superficielle apposée sur le fascia afin de ne pas traverser l'aponévrose • Trocart coaxial 14G ou 16G : au moins 4 à 6 carottes dirigées vers les zones viables en Doppler • Hémostase compressive.",
        "key_points_fr": [
            "Règle d'or carcinologique : ne jamais traverser un compartiment anatomique sain ni franchir le fascia profond lors de la biopsie d'une lésion superficielle sus-aponévrotique.",
            "Le trajet de ponction doit toujours être situé sur la future ligne d'incision chirurgicale définie avec les chirurgiens (Pr Anract / Pr Biau / Dr Dumaine).",
            "Précision diagnostique > 95 % pour la malignité et > 88 % pour le sous-type histologique et le grade FNCLCC.",
            "En cas d'antécédent oncologique (ex: mélanome), les prélèvements multiples permettent l'immunohistochimie et le profilage moléculaire complet."
        ],
        "tags": ["Biopsie écho-guidée", "Sarcome", "Parties molles", "Fascia", "Compartiment", "NetSarc Cochin"]
    },
    "41838307": {
        "category_id": "msk_biopsy",
        "title_fr": "Biopsie osseuse guidée par scanner à comptage photonique et cartographie de l'œdème médullaire : ciblage des lésions occultes et lymphomes",
        "modality": "Scanner TDM",
        "intervention_type": "Biopsie Osseuse sous Scanner",
        "cochin_link": "Illustre le ciblage TDM de haute précision pour les biopsies osseuses (suspicion de récidive de lymphome B au genou, biopsie sacrée/pré-sacrée) et synoviales en HDJ Radio B.",
        "summary_fr_short": "Article de *European Radiology Experimental* (2026) montrant l'apport de l'imagerie spectrale / comptage photonique et de la corrélation IRM-TDM lors des biopsies osseuses sous scanner pour cibler les zones d'infiltration médullaire active (lymphome osseux, métastases médullaires) même en l'absence d'ostéolyse corticale franche.",
        "summary_fr_detailed": "Les biopsies osseuses pour suspicion de récidive de lymphome B, d'infiltration hématologique ou de lésions sacrées/pré-sacrées présentent un défi particulier lorsque la trame trabéculaire paraît subnormale au scanner conventionnel ou remaniée par des traitements antérieurs. Cet article montre comment la fusion cognitive avec l'IRM (diffusion / T1 Gado) et l'analyse de densité médullaire permettent de diriger le trocart osseux exactement dans le foyer cellulaire actif, maximisant le rendement histologique et moléculaire tout en sécurisant les gestes sous anticoagulants.",
        "protocol_fr": "Corrélation précise avec les images clés PACS (IRM T1, STIR, Diffusion) • Pour les patients sous AOD (ex: Eliquis 2,5 mg ou 5 mg), arrêt à J-3, contrôle du bilan d'hémostase 48h avant et reprise > 6h après le geste • Trocart de biopsie osseuse coaxial 11G–13G : prélèvement de 3 à 4 carottes non fragmentées pour histologie et cytogénétique/FISH (lymphome).",
        "key_points_fr": [
            "Dans les suspicions de récidive de lymphome osseux, cibler la zone d'hypersignal diffusion / rehaussement IRM et éviter l'écrasement mécanique des carottes.",
            "Pour les biopsies synoviales sous scanner (genou, suspicion de chondromatose synoviale ou SVN), utiliser un système coaxial 14G ciblant directement le nodule synovial du récessus.",
            "Pour les masses pré-sacrées / sacrées (ex: suspicion de myélolipome ou chordome), l'abord trans-sacré ou para-sacré postérieur sous TDM évite toute effraction rectale ou plexique.",
            "Protocole anticoagulants (Eliquis) pour biopsie osseuse profonde : arrêt J-3 et reprise > 6h post-procédure en l'absence de saignement."
        ],
        "tags": ["Biopsie osseuse", "Scanner", "Lymphome osseux", "Sacrum", "Biopsie synoviale", "Eliquis"]
    },
    "41204964": {
        "category_id": "msk_biopsy",
        "title_fr": "Facteurs prédictifs de biopsie osseuse non contributive sous scanner : étude multicentrique et stratégies d'optimisation",
        "modality": "Scanner TDM",
        "intervention_type": "Biopsie Osseuse sous Scanner",
        "cochin_link": "Permet d'optimiser le rendement diagnostique des biopsies osseuses et synoviales réalisées sous scanner au Pavillon Achard -1.",
        "summary_fr_short": "Étude multicentrique publiée dans *European Radiology* (2026) analysant les causes de biopsies osseuses non diagnostiques sous scanner et définissant les critères techniques permettant d'atteindre un rendement supérieur à 90 % (calibre du trocart, nombre de carottes, ciblage de la composante tissulaire non nécrotique).",
        "summary_fr_detailed": "Malgré la précision du guidage tomodensitométrique, 8 à 15 % des biopsies osseuses peuvent s'avérer non contributives, notamment dans les lésions kystiques remaniées, les tumeurs très sclérosantes ou les lésions inflammatoires chroniques. Cette étude multicentrique démontre que le prélèvement simultané de la composante intra-osseuse et de la composante tissulaire périphérique (ou synoviale), l'utilisation d'aiguilles de calibre ≥ 13G pour l'os et ≥ 14G pour les parties molles, et l'aspiration du sang médullaire comme bloc cellulaire réduisent significativement le taux d'échec.",
        "protocol_fr": "Prélèvement combiné : carottes osseuses (11G–13G) + carottes des parties molles/synoviale (14G) + envoi du caillot médullaire aspiré au laboratoire d'anatomopathologie • En cas de doute infectieux différentiel, toujours adresser un fragment en bactériologie/mycobactériologie à frais.",
        "key_points_fr": [
            "Envoyer systématiquement le sang/caillot médullaire aspiré dans la seringue en anatomopathologie (technique du 'cell block') : augmente le rendement diagnostique de 7 %.",
            "Cibler la berge ostéolytique active ou le nodule synovial charnu plutôt que le centre nécrotique ou kystique.",
            "Un minimum de 3 carottes de longueur ≥ 10 mm est recommandé pour permettre les analyses immunohistochimiques et moléculaires.",
            "Discussion préalable des images clés PACS avec le radiologue référent et l'anatomopathologiste spécialisé en pathologie osseuse."
        ],
        "tags": ["Biopsie osseuse", "European Radiology", "Rendement diagnostique", "Anatomopathologie", "Scanner"]
    },
    "18635627": {
        "category_id": "msk_imaging",
        "title_fr": "Imagerie diagnostique des tumeurs solitaires du rachis et du bassin : sémiologie, algorithme et conduite à tenir (Équipe Cochin)",
        "modality": "IRM / Scanner TDM",
        "intervention_type": "Imagerie Diagnostique & Bilan pré-biopsie",
        "cochin_link": "Article de référence de l'équipe de l'Hôpital Cochin (Rodallec, Feydy, Larousserie, Anract, Campagna, Drapé — Services de Radiologie B, Anatomopathologie et Orthopédie).",
        "summary_fr_short": "Publication majeure de l'équipe de Cochin dans *RadioGraphics* détaillant la démarche diagnostique complète devant une lésion tumorale solitaire du rachis ou du sacrum : sémiologie TDM et IRM selon l'âge et la topographie (corps vertébral vs arc postérieur), pièges diagnostiques (myélolipome, hémangiome agressif, kyste anévrismal) et planification de la biopsie radioguidée.",
        "summary_fr_detailed": "Rédigé par les équipes de Radiologie B, d'Orthopédie et d'Anatomopathologie de l'Hôpital Cochin, cet article de référence structure l'analyse radiologique des tumeurs rachidiennes et sacrées : tumeurs bénignes de l'arc postérieur chez le sujet jeune (ostéome ostéoïde, ostéoblastome, kyste osseux anévrismal), tumeurs malignes ou localement agressives du corps vertébral et du sacrum chez l'adulte (métastase solitaire, plasmocytome, lymphome, chordome, chondrosarcome), et pseudo-tumeurs ou lésions rares à composante graisseuse/hématopoïétique (hémangiome agressif, myélolipome pré-sacré). Il précise ce que le radiologue doit impérativement mentionner dans son compte rendu et comment planifier la voie de biopsie.",
        "protocol_fr": "Association systématique TDM en coupes fines (analyse de la matrice minéralisée, des corticales et du nidus) + IRM (T1 sans injection pour la moelle osseuse et le contingent graisseux microscopique/macroscopique, T2/STIR, T1 FS Gadolinium).",
        "key_points_fr": [
            "Toute lésion de l'arc postérieur avec scoliose douloureuse raide chez un sujet jeune doit faire rechercher un ostéome ostéoïde ou un ostéoblastome.",
            "Devant une masse pré-sacrée ou sacrée contenant des îlots graisseux en hypersignal T1 qui s'effacent en saturation de graisse, évoquer un myélolipome pré-sacré (diagnostic différentiel du liposarcome et du chordome).",
            "La biopsie percutanée sous scanner d'une lésion rachidienne ou sacrée suspecte de sarcome/chordome doit emprunter une voie postérieure strictement concertée avec le chirurgien.",
            "Référence historique illustrant la synergie Radio B – Orthopédie – Anatomopathologie à l'Hôpital Cochin."
        ],
        "tags": ["Hôpital Cochin", "Radiologie B", "Tumeurs du rachis", "Sacrum", "Myélolipome", "RadioGraphics"]
    },
    "12773675": {
        "category_id": "msk_imaging",
        "title_fr": "Imagerie de l'ostéome ostéoïde par IRM dynamique après injection de gadolinium (DCE-MRI) : détection du nidus et suivi post-RF",
        "modality": "IRM",
        "intervention_type": "IRM Dynamique (Protocole OO)",
        "cochin_link": "Correspond exactement aux examens d'IRM 'protocole OO avec injection dynamique' programmés au Pavillon Achard -1 avant consultation et radiofréquence d'ostéome ostéoïde.",
        "summary_fr_short": "Étude princeps de *Radiology* démontrant que l'IRM dynamique injectée au temps artériel réalise une détection du nidus de l'ostéome ostéoïde bien supérieure à l'IRM conventionnelle et égale au scanner fin. Le nidus hypervasculaire présente un rehaussement artériel précoce intense suivi d'un lavage ('wash-out'), tandis que l'œdème réactionnel péri-lésionnel se rehausse tardivement.",
        "summary_fr_detailed": "Sur les séquences IRM morphologiques standard (T1, T2 FS), le petit nidus de l'ostéome ostéoïde (particulièrement dans les formes intra-articulaires du col fémoral, du coude ou de l'astragale) est fréquemment masqué par l'intense œdème médullaire et synovial réactionnel. L'acquisition dynamique 3D T1 écho de gradient avec saturation de graisse toutes les 10 à 15 secondes après bolus de gadolinium met en évidence un pic de rehaussement artériel précoce du nidus dès la phase artérielle (82 % des cas), permettant à la fois d'affirmer le diagnostic en pré-opératoire et de vérifier la nécrose complète du nidus après radiofréquence ou cryoablation.",
        "protocol_fr": "Protocole IRM Ostéome Ostéoïde (Cochin Achard -1) : Séquences T1, T2 DIXON/STIR dans 2 plans + Séquence 3D T1 FS dynamique (résolution temporelle 10–15 s pendant 2 minutes dès l'injection de Gadolinium) avec courbes de perfusion ROI sur le nidus et soustraction • Même protocole utilisé en suivi post-RF/Cryo en cas de doute sur un reliquat actif.",
        "key_points_fr": [
            "L'IRM sans séquence dynamique méconnaît jusqu'à 35 % des nidus d'ostéome ostéoïde noyés dans l'œdème médullaire.",
            "Signature hémodynamique pathognomonique du nidus : rehaussement intense au temps artériel précoce (< 30 s) avec wash-out veineux.",
            "Indispensable pour les ostéomes ostéoïdes intra-articulaires (hanche, coude, astragale) où l'ostéosclérose périphérique est absente ou minime.",
            "En suivi post-ablation thermique (RF ou cryoablation), la disparition complète du rehaussement artériel précoce signe l'éradication du nidus."
        ],
        "tags": ["IRM dynamique", "Ostéome ostéoïde", "Nidus", "Gadolinium", "Suivi post-ablation", "Radiology"]
    },
    "31601938": {
        "category_id": "msk_imaging",
        "title_fr": "Tumeur ténosynoviale à cellules géantes (TTCG / Synovite villonodulaire) : évaluation IRM et efficacité à long terme des thérapies ciblées",
        "modality": "IRM",
        "intervention_type": "IRM de Suivi (TTCG / SVN)",
        "cochin_link": "En lien direct avec les IRM de contrôle de cheville/genou pour TTCG / synovite villonodulaire (SVN) sous traitement médical et les suivis post-cryothérapie à Cochin.",
        "summary_fr_short": "Étude multicentrique évaluant la réponse clinique et radiologique (RECIST et score volumétrique TVS en IRM) des tumeurs ténosynoviales à cellules géantes (TTCG / synovite villonodulaire pigmentée diffuse) traitées médicalement lorsqu'une synovectomie chirurgicale complète est impossible ou morbide.",
        "summary_fr_detailed": "Les formes diffuses de tumeur ténosynoviale à cellules géantes (TTCG, anciennement synovite villonodulaire pigmentée - SVN) de la cheville, du genou ou de la hanche présentent un taux élevé de récidive locale après chirurgie. L'IRM est l'examen clé pour le diagnostic (effet de susceptibilité magnétique 'blooming' lié aux dépôts d'hémosidérine en écho de gradient T2*) et pour le suivi longitudinal sous thérapies médicales (inhibiteurs de CSF1R tels que pexidartinib/vimseltinib, imatinib ou biothérapies). L'évaluation IRM doit combiner la mesure volumétrique synoviale, le degré de rehaussement et l'état chondral articulaire.",
        "protocol_fr": "Protocole IRM TTCG / SVN et suivi post-thérapeutique : T1, T2 FS/DIXON 3 plans, séquence Écho de Gradient T2* (détection du blooming d'hémosidérine) et 3D T1 FS Gadolinium • Comparaison volumétrique à 6 mois avant consultation multidisciplinaire rhumato-orthopédique.",
        "key_points_fr": [
            "Signe IRM caractéristique de la TTCG/SVN : hyposignal T1/T2 avec artefact de susceptibilité ('blooming') sur la séquence T2* lié à l'hémosidérine.",
            "Le suivi IRM à 6 mois sous traitement médical évalue la réduction du volume synovial charnu rehaussé (souvent > 30 % dès 3–6 mois) et la stabilisation des érosions osseuses.",
            "En cas de masse nodulaire intra-articulaire atypique non hémosidérinique (diagnostic différentiel : chondromatose synoviale, lipome arborescent, sarcome synovial), la biopsie synoviale sous scanner/écho s'impose.",
            "Pour les contrôles IRM post-cryothérapie (rachis lombaire, cervical, membres à 6 semaines et 3 mois), les séquences T1 FS Gado avec soustraction distinguent le halo inflammatoire périphérique bénin d'un nodule résiduel."
        ],
        "tags": ["TTCG", "Synovite villonodulaire", "SVN", "IRM", "Cheville", "Genou", "Suivi thérapeutique"]
    },
    "42931896": {
        "category_id": "ablation_benign",
        "title_fr": "Ostéome ostéoïde intra-articulaire de la hanche (cotyle) traité par radiofréquence guidée par scanner : supériorité sur l'arthroscopie",
        "modality": "Scanner TDM",
        "intervention_type": "Radiofréquence (RF Hanche)",
        "cochin_link": "En lien direct avec la prise en charge à Cochin (IRM dynamique + RF sous AG) des ostéomes ostéoïdes intra-articulaires de hanche chez l'adolescent et l'adulte jeune.",
        "summary_fr_short": "Publication d'octobre 2026 (*Skeletal Radiology*) illustrant le traitement curatif par radiofréquence sous scanner d'un ostéome ostéoïde intra-articulaire de la fosse acétabulaire après échec d'une résection arthroscopique, avec disparition complète de la synovite réactionnelle et des douleurs.",
        "summary_fr_detailed": "Les ostéomes ostéoïdes intra-articulaires de la hanche (cotyle, col fémoral) provoquent une synovite inflammatoire sévère, un épanchement articulaire et un remodelage arthrosique précoce mimant une coxite. L'abord arthroscopique est souvent mis en échec dans les localisations médiales profondes de la fosse acétabulaire. Le guidage scanner permet une trajectoire trans-osseuse extra-capsulaire millimétrique jusqu'au nidus avec thermocoagulation RF complète et préservation du cartilage articulaire.",
        "protocol_fr": "Repérage TDM en coupes fines • Abord trans-iliaque ou rétro-acétabulaire extra-articulaire évitant le cartilage hyalin • Sonde RF monopolaire 90 °C pendant 6 minutes • Contrôle IRM montrant la régression de la synovite et de l'œdème médullaire.",
        "key_points_fr": [
            "Les ostéomes ostéoïdes intra-articulaires de hanche s'accompagnent d'une synovite réactionnelle floride et d'une absence d'ostéosclérose périphérique.",
            "La RF sous scanner offre un accès direct aux nidus profonds du cotyle inaccessibles en arthroscopie.",
            "Privilégier une voie trans-osseuse extra-articulaire pour protéger le cartilage acétabulaire et le nerf sciatique.",
            "Résolution rapide de l'épanchement articulaire et des douleurs nocturnes dès la première semaine."
        ],
        "tags": ["Ostéome ostéoïde", "Hanche", "Cotyle", "Intra-articulaire", "Radiofréquence", "Skeletal Radiology 2026"]
    },
    "42618654": {
        "category_id": "ect_mets",
        "title_fr": "Cryoablation à visée curative des métastases osseuses : protocole de l'étude prospective multicentrique européenne BOREALIS (CIRSE)",
        "modality": "Scanner TDM / IRM",
        "intervention_type": "Cryoablation Curative (A0)",
        "cochin_link": "Essai multicentrique de référence (Cazzato, Buy, Deschamps, Palussière, Gangi — *CVIR* août 2026) cadrant les cryoablations de métastases osseuses à visée de contrôle local complet réalisées à Cochin.",
        "summary_fr_short": "Présentation du registre prospectif multicentrique BOREALIS (*CVIR*, août 2026) évaluant la cryoablation percutanée à visée curative (éradication tumorale complète avec marges de sécurité) chez les patients oligométastatiques osseux.",
        "summary_fr_detailed": "Portée par les principaux centres européens et français de radiologie interventionnelle oncologique (Strasbourg, Bordeaux, Gustave Roussy), l'étude BOREALIS standardise les critères techniques de la cryoablation osseuse à visée curative : sélection des patients oligométastatiques (1 à 3 lésions osseuses ≤ 4 cm), couverture tridimensionnelle complète de la tumeur par l'isotherme létal (-20 °C / -40 °C) avec marges d'au moins 5 mm au-delà des limites IRM, et suivi systématique par IRM/TEP-TDM sur 24 mois.",
        "protocol_fr": "Bilan pré-thérapeutique IRM + TDM • Multi-cryosondes 17G pour obtenir une marge d'iceball ≥ 5–8 mm autour de la lésion • Double cycle de congélation (10 min) séparé d'un dégel passif/actif • Consolidation associée (cimentoplastie ou vissage) si risque fracturaire • Suivi IRM à 3, 6, 12 et 24 mois.",
        "key_points_fr": [
            "Passage d'une indication purement palliative antalgique à une ablation curative (A0) dans la maladie oligométastatique osseuse.",
            "Exigence d'une marge d'ablation périphérique de 5 mm au-delà du volume tumoral défini sur l'IRM pré-opératoire.",
            "Intégration systématique des manœuvres de thermoprotection (hydrodissection, carbodissection, neuromonitoring) pour sécuriser les marges.",
            "Synergie avec les traitements systémiques modernes (immunothérapie et thérapies ciblées)."
        ],
        "tags": ["BOREALIS", "Cryoablation", "Métastases osseuses", "Oligométastatique", "CVIR 2026", "Gangi"]
    },
    "42173356": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Combinaison percutanée Cryoablation + Vissage + Cimentoplastie pour les métastases osseuses pelviennes douloureuses",
        "modality": "Scanner TDM",
        "intervention_type": "Trithérapie : Cryo + Vissage + Ciment",
        "cochin_link": "Correspond exactement aux suivis post « cryo de debulking + vissage du bassin » programmés dans l'Agenda Interventionnel du Dr Thomas Lefèvre à Cochin.",
        "summary_fr_short": "Étude française (*JVIR*, mai 2026 — Grange, Pelage, Gorelik et al.) démontrant la faisabilité, la sécurité et le bénéfice fonctionnel majeur d'un geste combiné associant en une seule séance cryoablation tumorale, vissage percutané et cimentoplastie pour les métastases pelviennes.",
        "summary_fr_detailed": "Les métastases ostéolytiques du bassin (toit du cotyle, aile iliaque, sacrum) combinent douleur tumorale inflammatoire et instabilité mécanique sévère. Cette étude française évalue la stratégie 'tout-en-un' sous guidage scanner : cryoablation première pour détruire le contingent tumoral et réduire l'hypervascularisation, suivie de la mise en place de vis canulées trans-osseuses scellées par cimentoplastie PMMA. Le succès technique atteint 100 %, avec une baisse rapide de l'EVA douleur, une reprise de la marche et une amélioration significative de la qualité de vie.",
        "protocol_fr": "1) Cryoablation percutanée (2 cycles de congélation) pour réduction tumorale ('debulking') • 2) Décongélation complète de la loge • 3) Mise en place des broches et vis canulées dans les corridors pelviens sous TDM • 4) Injection de ciment PMMA autour des vis et dans la cavité d'ostéolyse.",
        "key_points_fr": [
            "Synergie optimale : la cryoablation assure le contrôle tumoral local tandis que le couple vis + ciment restaure immédiatement la résistance mécanique du bassin.",
            "Attendre le réchauffement complet de la zone cryoablatée avant d'injecter le ciment PMMA.",
            "Le scellement des vis par le ciment ('cement-augmented screw fixation') limite fortement le risque de migration secondaire des vis dans l'os pathologique.",
            "Amélioration rapide de l'autonomie à la marche et réduction de la consommation d'opioïdes dès le premier mois."
        ],
        "tags": ["Cryoablation", "Vissage du bassin", "Cimentoplastie", "Métastases pelviennes", "JVIR 2026"]
    },
    "42803442": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Cartographie anatomique des terminaisons des nerfs géniculés sur genou natif vs prothétique : optimisation du bloc test et de la radiofréquence",
        "modality": "Échographie / Fluoroscopie",
        "intervention_type": "Bloc & RF Nerfs Géniculés",
        "cochin_link": "Précise les zones cibles capsulaires optimales pour les tests anesthésiques du genou sous échographie (Pavillon Ollier) et les radiofréquences des nerfs géniculés.",
        "summary_fr_short": "Étude anatomique et histologique (*Pain Medicine*, septembre 2026 — Fonkoué et al.) cartographiant la densité des terminaisons nociceptives des nerfs géniculés dans la capsule du genou natif et prothétique afin d'affiner le positionnement des aiguilles de bloc et de radiofréquence.",
        "summary_fr_detailed": "Cet article compare l'innervation nociceptive intracapsulaire et la densité vasculaire des différents quadrants du genou natif arthrosique et du genou douloureux post-prothèse totale (PTG). L'étude confirme une prédominance majeure des fibres nociceptives dans les quadrants supéro-médial, supéro-latéral et inféro-médial, au contact étroit des artères géniculées périostées, justifiant le repérage écho-Doppler lors du bloc pronostique et un ciblage élargi lors de la thermocoagulation RF ou de la cryoneurolyse.",
        "protocol_fr": "Repérage écho-Doppler des pédicules vasculaires géniculés au contact de la corticale métaphyso-épiphysaire • Bloc test diagnostique faible volume (0,5–1 mL) sur SMGN, SLGN et IMGN • En cas de gonalgie persistante post-PTG ou post-geste cartilagineux, ciblage identique des troncs afférents extra-capsulaires.",
        "key_points_fr": [
            "Forte corrélation anatomique entre les pédicules artériels géniculés (visibles en Doppler) et la densité des terminaisons nerveuses nociceptives.",
            "Applicable aussi bien à la gonarthrose sur genou natif qu'aux douleurs chroniques persistantes après chirurgie ou geste articulaire du genou.",
            "Confirme l'intérêt d'un ciblage précis contre le périoste fémoral et tibial pour capter les rameaux articulaires avant leur arborisation capsulaire."
        ],
        "tags": ["Nerfs géniculés", "Radiofréquence", "Bloc test", "Échographie", "Pain Medicine 2026"]
    },
    "34812672": {
        "category_id": "ablation_benign",
        "title_fr": "Ostéome ostéoïde de l'adulte : la cryoablation percutanée sous scanner (approche 'no-touch' extra-osseuse) est sûre, efficace et durable",
        "modality": "Scanner TDM",
        "intervention_type": "Cryoablation (No-Touch)",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » — Référence majeure (*Radiology*, 2022) validant la cryoablation extra-osseuse 'no-touch' sous sédation consciente, appliquée à Cochin notamment pour les ostéomes ostéoïdes superficiels ou de l'astragale.",
        "summary_fr_short": "Étude de référence (*Radiology*, févr. 2022) sur 50 patients adultes traités par cryoablation TDM d'un ostéome ostéoïde : taux de succès clinique global de 96 % (48/50), réalisé dans 60 % des cas sous anesthésie locale et sédation consciente en positionnant la cryosonde en extra-osseux ('no-touch') sans forer le nidus.",
        "summary_fr_detailed": "Cette série rétrospective de 50 patients (âge médian 24 ans) démontre que la cryoablation percutanée sous scanner permet d'éradiquer durablement l'ostéome ostéoïde chez l'adolescent et l'adulte avec une chute de l'EVA médiane de 8/10 à 0/10 à 6 semaines et à long terme (18–90 mois). L'innovation majeure réside dans l'approche extra-osseuse : dans 60 % des cas, la cryosonde est simplement apposée contre le cortex en regard du nidus sans forage trans-cortical, ce qui évite la douleur per-procédurale du forage et autorise une prise en charge sous anesthésie locale + sédation consciente sans complication majeure.",
        "protocol_fr": "Sous AL + sédation consciente (ou AG) • Positionnement de la cryosonde au contact direct de la corticale ('no-touch' extra-osseux) ou intra-osseux • Couverture complète du nidus par l'iceball visible au scanner • 2 cycles de congélation-décongélation • Surveillance de la peau et des nerfs adjacents.",
        "key_points_fr": [
            "Taux de succès clinique global de 96 % (48/50) avec disparition durable des douleurs (EVA 8 -> 0).",
            "Dans 60 % des cas, réalisation sous anesthésie locale et sédation consciente grâce à la position extra-osseuse de la cryosonde sans forage du nidus.",
            "Visualisation directe de la sphère de glace (iceball) englobant le nidus à travers l'os cortical.",
            "Aucune complication majeure rapportée (seulement 6 % de complications mineures transitoires)."
        ],
        "tags": ["Ostéome ostéoïde", "Cryoablation", "No-touch", "Radiology", "Ablation percutanée", "Zotero"]
    },
    "39576446": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Cryoablation percutanée de l'endométriose pariétale abdominale : revue systématique sur 10 ans de la sécurité et de l'efficacité",
        "modality": "Échographie / Scanner TDM",
        "intervention_type": "Cryoablation Pariétale",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (Bodard et al., *Insights into Imaging*, nov. 2024) — Référence clé pour l'ablation percutanée des nodules d'endométriome de la paroi abdominale et des masses pariétales des parties molles.",
        "summary_fr_short": "Revue systématique sur 10 ans (8 études, *Insights into Imaging*, nov. 2024) démontrant que la cryoablation percutanée des endométriomes de la paroi abdominale (AWE) réduit la douleur médiane de 8/10 à 1/10 (p < 0,0001), avec 80 à 100 % de réponse antalgique complète et moins de 2 % de complications majeures.",
        "summary_fr_detailed": "L'endométriose pariétale abdominale (souvent sur cicatrice de césarienne ou laparoscopie) entraîne des douleurs cycliques invalidantes. La chirurgie d'exérèse large expose à un risque de défect aponévrotique et d'éventration. Cette revue systématique (2014–2024) confirme que la cryoablation guidée par échographie et/ou scanner offre une réponse antalgique complète dans 80 à 100 % des séries et une survie sans douleur locale médiane de 76,8 % au dernier suivi, sans aucun cas d'aggravation douloureuse post-procédurale et avec un profil de sécurité remarquable en ambulatoire.",
        "protocol_fr": "Planification IRM pelvienne/pariétale • Guidage échographique + contrôle TDM de l'iceball • Hydrodissection sous-cutanée (protection cutanée) et rétro-aponévrotique/pré-péritonéale si proximité digestive • 2 cycles de congélation couvrant le nodule fibreux avec marges.",
        "key_points_fr": [
            "Diminution spectaculaire de l'EVA douleur de 8/10 (IQR 7–9) à 1/10 (IQR 0–2) au suivi à long terme (p < 0,0001).",
            "Taux médian de réponse complète sur la douleur locale compris entre 80 % et 100 %.",
            "Préserve l'intégrité musculo-aponévrotique de la sangle abdominale (aucun recours à un filet prothétique).",
            "Hydrodissection indispensable pour protéger le derme superficiel en avant et le péritoine/anses digestives en profondeur."
        ],
        "tags": ["Endométriome pariétal", "Cryoablation", "Paroi abdominale", "Ablation percutanée", "Insights into Imaging", "Zotero"]
    },
    "37030078": {
        "category_id": "ect_mets",
        "title_fr": "Électrochimiothérapie (ECT) des compressions médullaires épidurales métastatiques réfractaires à la radiothérapie",
        "modality": "Scanner TDM",
        "intervention_type": "Électrochimiothérapie (ECT Rachis)",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (Deschamps, Tselikas et al., *Eur J Cancer*, juin 2023) — Étude majeure justifiant le recours à l'ECT (Bléomycine IV) pour les lésions vertébrales et épidurales radio-résistantes sans recours chirurgical possible.",
        "summary_fr_short": "Série princeps (*European Journal of Cancer*, juin 2023) chez 40 patients présentant une compression médullaire épidurale métastatique (MESCC) réfractaire à la radiothérapie : l'électrochimiothérapie percutanée à la bléomycine réduit l'EVA médiane de 7/10 à 1/10 à 1 mois (p < 0,001), améliore le statut neurologique chez 56 % des patients et obtient 77 % de réponse objective épidurale en IRM.",
        "summary_fr_detailed": "Lorsque la compression médullaire ou radiculaire épidurale récidive après radiothérapie chez des patients non opérables, l'ablation thermique (RF, cryoablation) est contre-indiquée au contact direct du cordon médullaire en raison de la neurotoxicité thermique irréversible. L'électrochimiothérapie (ECT) détruit sélectivement les cellules tumorales en division par électroporation réversible + bléomycine tout en respectant la trame conjonctive et les structures nerveuses adjacentes. Sur 40 patients consécutifs, l'IRM à 1 mois montre 46 % de réponse complète et 31 % de réponse partielle selon le score de Bilsky (ESCCS), démontrant que l'ECT peut sauver des compressions médullaires en impasse thérapeutique.",
        "protocol_fr": "Sous AG • Mise en place transpédiculaire ou paravertébrale d'électrodes aiguilles encadrant la coulée épidurale sous TDM • Bolus IV de Bléomycine (15 000 UI/m² ou dose fixe adaptée) • Délivrance des impulsions électriques entre 8 et 28 min post-injection • Contrôle IRM à 1 et 3 mois (score ESCCS).",
        "key_points_fr": [
            "Chute majeure de la douleur médiane de 7/10 à 1/10 à 1 mois et 2/10 à 3 mois (p < 0,001).",
            "Amélioration neurologique marquée ou modérée chez 56 % des patients à 1 mois (et stabilisation chez 38 %).",
            "Réponse radiologique objective sur le contingent épidural en IRM (score ESCCS) chez 77 % des patients à 1 mois (46 % complète, 31 % partielle).",
            "Seule technique ablative percutanée utilisable au contact immédiat du fourreau dural et de la moelle épinière après échec de la radiothérapie."
        ],
        "tags": ["Électrochimiothérapie", "Compression médullaire", "Épidurite", "Bléomycine", "Rachis", "Eur J Cancer", "Zotero"]
    },
    "41720112": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Cryoablation percutanée pour la prise en charge des tumeurs osseuses et des parties molles : état de l'art 2026",
        "modality": "Scanner TDM / IRM / Écho",
        "intervention_type": "Cryoablation Musculosquelettique",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (*Seminars in Musculoskeletal Radiology*, févr. 2026) — Synthèse de référence couvrant l'ensemble du spectre d'ablation percutanée pratiqué à Cochin (ostéome ostéoïde, desmoïdes, métastases, endométriomes, récidives de sarcomes).",
        "summary_fr_short": "Revue d'état de l'art (*Semin Musculoskelet Radiol*, févr. 2026) détaillant les indications établies (ostéome ostéoïde, palliation antalgique et contrôle oligométastatique osseux) et émergentes (chondroblastome, tumeurs desmoïdes, anomalies vasculaires, endométriose pariétale, récidives locales de sarcomes) de la cryoablation percutanée.",
        "summary_fr_detailed": "Cet article de synthèse 2026 fait le point sur la maturité technologique et clinique de la cryoablation guidée par l'image en pathologie musculosquelettique. Il détaille la planification multi-sondes pour sculpter l'iceball aux géométries tumorales complexes, les stratégies de prévention des complications (hydrodissection, carbodissection, réchauffement cutané, monitoring neurophysiologique et consolidation mécanique préventive) ainsi que l'expansion des indications vers les tumeurs bénignes agressives et le rattrapage local des sarcomes osseux et des parties molles.",
        "protocol_fr": "Choix du calibre et de la longueur d'extrémité active des cryosondes (règle d'espacement 1,5–2 cm, distance < 1 cm de la berge tumorale) • Double cycle Congélation-Décongélation • Thermoprotection active si structure noble < 10 mm • Cimentoplastie/ostéosynthèse combinée sur os porteur.",
        "key_points_fr": [
            "Panorama complet 2026 des indications validées et émergentes de la cryoablation osseuse et des parties molles.",
            "Détaille les techniques d'optimisation de la géométrie de l'iceball par synergie multi-sondes.",
            "Systématise les protocoles de neuroprotection et de protection cutanée/cartilagineuse.",
            "Souligne la place croissante de la cryoablation dans les récidives locales de sarcomes et les lésions des tissus mous (desmoïdes, malformations vasculaires, endométriomes)."
        ],
        "tags": ["Cryoablation", "Tumeurs osseuses", "Parties molles", "État de l'art 2026", "Ablation percutanée", "Zotero"]
    },
    "24859596": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Techniques d'ablation thermique (RF / Cryoablation) : un traitement curatif des métastases osseuses chez des patients sélectionnés ?",
        "modality": "Scanner TDM",
        "intervention_type": "Ablation Thermique Curative (RF / Cryo)",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (Deschamps, Farouil, Ternes et al., *European Radiology*, août 2014) — Étude fondatrice définissant les critères pronostiques de guérison locale complète des métastases osseuses par ablation thermique.",
        "summary_fr_short": "Série fondatrice (*European Radiology*, août 2014) portant sur 89 patients (122 métastases osseuses) traités par radiofréquence ou cryoablation à visée curative : taux de contrôle local complet de 67 % à 1 an, atteignant > 85 % pour les lésions oligométastatiques métachrones < 2 cm sans rupture corticale.",
        "summary_fr_detailed": "Cette étude rétrospective de Gustave Roussy a établi le changement de paradigme entre ablation palliative antalgique et ablation thermique à visée curative dans les métastases osseuses. Sur 122 métastases traitées avec intention d'éradication complète (suivi médian 22,8 mois), l'analyse multivariée identifie 5 facteurs pronostiques indépendants de succès local complet : le statut oligométastatique (p = 0,02), le caractère métachrone (p = 0,004), une taille tumorale < 2 cm (p = 0,001), l'absence d'érosion corticale (p = 0,01) et l'absence de structure neurologique au contact immédiat (p = 0,002).",
        "protocol_fr": "Sélection en RCP des patients oligométastatiques (1–3 lésions) • Ablation thermique par RF ou Cryoablation visant des marges de sécurité circonférentielles d'au moins 5 mm • Consolidation par cimentoplastie associée si localisation portante • Suivi longitudinal par IRM et TEP-TDM.",
        "key_points_fr": [
            "Taux de contrôle local complet à 1 an de 67 % en intention de traiter sur 122 métastases osseuses.",
            "Cinq facteurs prédictifs majeurs de succès curatif : maladie oligométastatique, lésion métachrone, taille < 2 cm, corticale intacte et distance aux nerfs.",
            "Pose les bases historiques des essais prospectifs modernes d'ablation curative osseuse (comme BOREALIS).",
            "La cryoablation est privilégiée dès que la lésion dépasse 2 cm ou présente une composante ostéocondensante/extra-osseuse."
        ],
        "tags": ["Ablation curative", "Métastases osseuses", "Oligométastatique", "Radiofréquence", "Cryoablation", "Eur Radiol", "Zotero"]
    },
    "37742284": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Prise en charge interventionnelle des tumeurs osseuses malignes : le paradigme palliatif-curatif",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Ablation + Consolidation Osseuse",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (*J Med Imaging Radiat Oncol*, déc. 2023) — Synthèse décisionnelle structurant l'association ablation (cryo, RF, ECT) et consolidation (cimentoplastie, vissage) en oncologie osseuse.",
        "summary_fr_short": "Revue clinique (*JMIRO*, déc. 2023) structurant la radiologie interventionnelle des tumeurs osseuses malignes autour du paradigme « palliatif–curatif », articulant techniques d'ablation (cryoablation, RF, micro-ondes, électrochimiothérapie) et techniques de consolidation (cimentoplastie, ostéosynthèse percutanée).",
        "summary_fr_detailed": "Cet article propose un cadre décisionnel pragmatique pour le radiologue interventionnel face aux métastases osseuses et tumeurs malignes primitives. Il distingue l'approche palliative (soulagement rapide de la douleur et prévention fracturaire par cimentoplastie/vissage +/- ablation de debulking) de l'approche curative (destruction A0 avec marges de sécurité chez le patient oligométastatique). Il compare les avantages respectifs de la cryoablation, de la radiofréquence, des micro-ondes et de l'électrochimiothérapie selon la topographie (rachis vs bassin vs os longs) et la proximité nerveuse.",
        "protocol_fr": "Évaluation multidisciplinaire (score SINS au rachis, Mirels sur os longs, Harrington au cotyle) • Choix de la modalité ablative selon la taille et la matrice osseuse • Consolidation systématique par ciment PMMA et/ou vis canulées en zone de contrainte mécanique.",
        "key_points_fr": [
            "Articulation claire du paradigme « palliatif vs curatif » en radiologie interventionnelle oncologique osseuse.",
            "Complémentarité systématique entre destruction tumorale (cryoablation / RF / ECT) et stabilisation mécanique (cimentoplastie / vissage).",
            "Intégration des scores d'instabilité mécanique (SINS, Mirels) dans l'arbre décisionnel interventionnel.",
            "Place spécifique de l'électrochimiothérapie et de la cryoablation sous neuromonitoring pour les lésions péri-nerveuses."
        ],
        "tags": ["Tumeurs osseuses malignes", "Paradigme palliatif-curatif", "Ablation thermique", "Consolidation", "Zotero"]
    },
    "35348870": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Recommandations et Standards de Pratique du CIRSE sur l'ablation thermique des tumeurs osseuses",
        "modality": "Scanner TDM / IRM / Fluoroscopie",
        "intervention_type": "Standards CIRSE (RF / Cryo / MW / Laser)",
        "cochin_link": "Issu de votre collection Zotero « Ablation percutanée » (Ryan, Tsoumakidou, Buy, Gangi et al., *CVIR*, mai 2022) — Référentiel européen officiel encadrant les standards techniques, la thermoprotection et les indications d'ablation osseuse à Cochin.",
        "summary_fr_short": "Consensus officiel du CIRSE (*CardioVascular and Interventional Radiology*, mai 2022) définissant les standards de bonne pratique pour l'ablation thermique percutanée des tumeurs osseuses bénignes et malignes : indications curatives et palliatives, choix de l'énergie, monitorage thermique et gestes adjuvants (embolisation, consolidation).",
        "summary_fr_detailed": "Rédigé par le comité des Standards de Pratique du CIRSE, ce document de référence établit les recommandations européennes pour la réalisation sécurisée des ablations thermiques osseuses (radiofréquence, cryoablation, micro-ondes, laser). Il précise le bilan pré-thérapeutique, les seuils de sécurité thermique pour la moelle épinière et les nerfs périphériques, les techniques de protection active (hydrodissection, carbodissection, thermocouples, potentiels évoqués moteurs/sensitifs) et le timing optimal de l'embolisation pré-opératoire (tumeurs hypervasculaires : rein, thyroïde) et de la cimentoplastie.",
        "protocol_fr": "Validation préalable en RCP • Bilan d'imagerie en coupes (< 1 mois) • Antibioprophylaxie ciblée (céphalosporine 1re/2e génération, surtout si cimentoplastie associée) • Thermométrie par thermocouple + dissection isolante dès qu'une structure nerveuse est à < 10 mm • Consolidation PMMA immédiate en zone portante.",
        "key_points_fr": [
            "Référentiel européen officiel du CIRSE pour les ablations thermiques osseuses bénignes (ostéome ostéoïde, chondroblastome) et malignes (métastases).",
            "Recommandations précises sur le choix entre RF, Cryoablation et Micro-ondes selon le caractère ostéolytique ou ostéocondensant et la taille tumorale.",
            "Standardisation de la thermoprotection active (CO2, sérum glucosé/salé, contrôle par thermocouple avec seuils stricts < 10 °C et > 45 °C).",
            "Indication d'embolisation transartérielle préalable pour les volumineuses métastases hypervasculaires afin de réduire le saignement et l'effet 'heat-sink'."
        ],
        "tags": ["Standards CIRSE", "Ablation thermique", "Tumeurs osseuses", "Thermoprotection", "CVIR 2022", "Zotero"]
    },
    "42471112": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Variabilité de hauteur des corridors intrasacrés S1 et S2 lors du vissage pelvien percutané guidé par CBCT (115 patients)",
        "modality": "Cone-Beam CT (CBCT) / Scanner TDM",
        "intervention_type": "Vissage Percutané Sacro-Iliaque S1/S2",
        "cochin_link": "Directement lié aux vissages percutanés du bassin (fractures de fragilité ou post-radiothérapie) programmés en HDJ Radio B à Cochin.",
        "summary_fr_short": "Étude rétrospective monocentrique (*JVIR*, juil. 2026, 115 patients, 169 vis) analysant la variabilité anatomique de la hauteur des corridors intrasacrés S1 et S2 lors du vissage pelvien percutané guidé par Cone-Beam CT (CBCT).",
        "summary_fr_detailed": "Sur 115 patients consécutifs (âge médian 67 ans) traités par ostéosynthèse pelvienne percutanée guidée par CBCT pour fractures traumatiques ou par insuffisance osseuse, la hauteur médiane du corridor intrasacré mesurée en reconstruction 'true outlet' était de 23 mm (IQR 21–26 mm, extrêmes 10 à 32 mm). Malgré cette variabilité anatomique majeure, aucune corrélation significative n'a été retrouvée avec le temps opératoire (médiane 47 min, p = 0,65) ni avec l'exposition radique (DAP médian 78,8 Gy·cm², p = 0,55), avec un taux d'événement indésirable très faible (0,6 %). La planification 3D CBCT permet de sécuriser le vissage trans-sacré même dans les corridors étroits (< 12 mm).",
        "protocol_fr": "Planification 3D sur CBCT ou TDM en reconstructions multiplanaires vraies (Inlet, Outlet vrai, profil sacré strict) • Mesure pré-opératoire de la hauteur des corridors S1 et S2 • Guidage 3D fluoroscopique/CBCT avec contrôle du couloir osseux au-dessus du foramen S1 et en avant du canal sacré.",
        "key_points_fr": [
            "Forte variabilité interindividuelle de la hauteur des corridors intrasacrés S1/S2 (10 à 32 mm, médiane 23 mm).",
            "Temps opératoire médian rapide (47 minutes) et dose d'irradiation maîtrisée (DAP 78,8 Gy·cm²) grâce au guidage 3D.",
            "L'étroitesse du couloir sacré n'allonge ni la durée du geste ni la dose radique lorsque la planification 3D multiplanaires est standardisée.",
            "Sécurité élevée (0,6 % de complication) validant le vissage percutané S1/S2 en routine interventionnelle."
        ],
        "tags": ["Vissage bassin", "Corridors S1 S2", "CBCT", "Fracture sacrum", "Ostéosynthèse percutanée", "JVIR 2026"]
    },
    "41867110": {
        "category_id": "ablation_benign",
        "title_fr": "Score de risque IRM dynamique (DCE-MRI 3T) prédictif de récidive douloureuse après radiofréquence d'ostéome ostéoïde",
        "modality": "IRM Dynamique 3T (DCE-MRI) + Scanner TDM",
        "intervention_type": "Ablation par Radiofréquence (RFA)",
        "cochin_link": "Correspond exactement au couple « IRM dynamique protocole ostéome ostéoïde » + « Thermocoagulation par radiofréquence sous TDM » pratiqué à Cochin.",
        "summary_fr_short": "Étude rétrospective sur 122 patients (*Int J Hyperthermia*, mars 2026) démontrant que les paramètres quantitatifs de l'IRM dynamique injectée 3T (DCE-MRI) pré-opératoire et la topographie extracorticale du nidus prédisent le risque de récidive douloureuse après radiofréquence d'ostéome ostéoïde.",
        "summary_fr_detailed": "Sur 122 patients (âge médian 19 ans) ayant bénéficié d'une IRM dynamique 3T (DCE-MRI) avant thermoablation par radiofréquence guidée par scanner, une récidive douloureuse (EVA > 4/10 après > 2 semaines) a été observée chez 22 patients (18 %). Les facteurs prédictifs indépendants de récidive étaient une localisation extracorticale/périostée du nidus (HR 6,5 ; p < 0,001), un temps jusqu'au pic (TTP) allongé > 40 s (HR 6,0 ; p = 0,016), un rehaussement relatif maximal (MRE) < 300 % (HR 0,3 ; p = 0,042) et une pente de wash-in réduite (HR 0,1 ; p = 0,03). Dans le sous-groupe des nidus extracorticaux présentant un TTP > 40 s et un MRE < 300 %, la probabilité de récidive atteignait ≥ 55 %, justifiant d'adapter le protocole d'ablation.",
        "protocol_fr": "IRM pré-thérapeutique 3T avec séquence dynamique T1 injectée (DCE-MRI : mesure du Time-To-Peak [TTP], Maximum Relative Enhancement [MRE] et Wash-in rate) + TDM en coupes fines • Si nidus extracortical avec TTP > 40 s et MRE < 300 % : allonger le temps de radiofréquence ou réaliser deux positions d'électrode chevauchantes.",
        "key_points_fr": [
            "La localisation extracorticale du nidus multiplie par 6,5 le risque de récidive douloureuse après RF standard (p < 0,001).",
            "Un rehaussement lent et moins intense en DCE-MRI 3T (TTP > 40 s et MRE < 300 %) reflète un nidus moins vascularisé ou scléreux plus résistant à la conduction thermique.",
            "En présence d'un nidus extracortical avec TTP > 40 s et MRE < 300 %, le risque de récidive dépasse 55 %.",
            "Permet de personnaliser le geste à Cochin dès l'IRM dynamique pré-RF (durée d'ablation prolongée, température accrue ou cryoablation)."
        ],
        "tags": ["Ostéome ostéoïde", "IRM dynamique DCE-MRI", "Radiofréquence", "Facteurs prédictifs", "Récidive"]
    },
    "42955498": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Options d'ablation guidée par l'image pour les fibromatoses desmoïdes : preuves contemporaines et intégration aux recommandations",
        "modality": "Scanner TDM / IRM / Échographie",
        "intervention_type": "Cryoablation / HIFU / Ablation Thermique",
        "cochin_link": "En lien direct avec les cryoablations de tumeurs desmoïdes (creux sus-claviculaire, paroi thoracique, paravertébral) et le suivi IRM en Radio B.",
        "summary_fr_short": "Mise au point de référence (*Curr Treat Options Oncol*, oct. 2026) détaillant l'intégration de la cryoablation percutanée dans l'algorithme multidisciplinaire des tumeurs desmoïdes symptomatiques ou progressives, incluant les stratégies d'ablation subtotale délibérée à proximité des nerfs critiques.",
        "summary_fr_detailed": "Après surveillance active initiale, le traitement ablatif est indiqué en cas de douleur réfractaire, gêne fonctionnelle, progression soutenue ou menace sur les structures nobles. La cryoablation percutanée est la modalité de référence grâce à la visualisation directe de la boule de glace, la synergie multi-sondes pour sculpter la zone d'ablation et la possibilité de traitements séquentiels. L'article formalise le concept d'ablation subtotale délibérée ('deliberate subtotal ablation') lorsque l'objectif principal est l'antalgie et que l'obtention d'une marge circonférentielle complète menacerait un plexus nerveux, la peau ou le tube digestif. L'association séquentielle ou combinée aux traitements systémiques (inhibiteurs de gamma-sécrétase, TKIs) pour traiter un foyer dominant symptomatique est également détaillée.",
        "protocol_fr": "Discussion en RCP Sarcomes/Desmoïdes • Planification IRM T2/DWI/T1 injecté • Cryoablation multi-sondes sous TDM/IRM avec hydrodissection, réchauffement cutané actif et neuromonitoring • Visée complète (A0) si marges sûres, ou debulking subtotal délibéré au contact des troncs nerveux.",
        "key_points_fr": [
            "La cryoablation percutanée est la modalité ablative de choix dans les tumeurs desmoïdes grâce au contrôle visuel de la boule de glace.",
            "Validation du concept d'ablation subtotale délibérée à visée antalgique/fonctionnelle lorsque la tumeur jouxte un plexus nerveux majeur.",
            "Complémentarité entre thérapie systémique et cryoablation focale sur un contingent résiduel douloureux ou progressif ('oligoprogression').",
            "Rôle essentiel de l'hydrodissection, du réchauffement cutané et de la protection nerveuse active."
        ],
        "tags": ["Tumeur desmoïde", "Cryoablation", "Ablation subtotale", "Thermoprotection", "Recommandations 2026"]
    },
    "42439173": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Cimentoplastie des os thoraciques extra-rachidiens (sternum, côtes, clavicule, scapula) : faisabilité, sécurité et résultats antalgiques",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Cimentoplastie Thoracique Extra-Rachidienne",
        "cochin_link": "Correspond aux cimentoplasties et traitements combinés (cryoablation + cimentoplastie) des lésions osseuses thoraciques et ceinture scapulaire à Cochin.",
        "summary_fr_short": "Série clinique rétrospective (*Acta Radiol*, juil. 2026, 43 patients, 59 os thoraciques traités) démontrant une efficacité antalgique de 88 % et une stabilisation fracturaire de 87 % après cimentoplastie percutanée du sternum, des côtes, de la clavicule et de la scapula.",
        "summary_fr_detailed": "Cette étude a évalué 59 lésions osseuses thoraciques extra-rachidiennes (métastases et myélome multiple principalement) traitées au cours de 51 procédures chez 43 patients (âge médian 60 ans). Un remplissage en ciment PMMA supérieur à 60 % du volume lésionnel a été obtenu dans 89 % des lésions focales, permettant une stabilisation fracturaire efficace dans 87 % des cas (20/23). À 3 mois, 88 % des patients évaluables (29/33) présentaient une amélioration nette ou une disparition complète des douleurs. Les fuites majeures de ciment (9 %, 5/56) sont restées strictement asymptomatiques, avec un seul événement infectieux local.",
        "protocol_fr": "Guidage TDM (ou CBCT) sous anesthésie locale renforcée ou générale • Abord tangentiel sécurisé (attention à la plèvre, au péricarde et aux vaisseaux sous-claviers) • Injection fractionnée de ciment PMMA haute viscosité visant un remplissage ≥ 60 % de la lésion ostéolytique.",
        "key_points_fr": [
            "Taux de succès antalgique élevé (88 % d'amélioration ou résolution complète des douleurs à 3 mois).",
            "Excellente consolidation mécanique des fractures pathologiques du sternum, des côtes, de la clavicule et de la scapula (87 %).",
            "Remplissage lésionnel > 60 % obtenu dans 89 % des cas sous guidage scanner.",
            "Fuites de ciment peu fréquentes (9 %) et toutes asymptomatiques grâce au contrôle tomodensitométrique."
        ],
        "tags": ["Cimentoplastie", "Sternum", "Côtes", "Scapula", "Clavicule", "Métastases osseuses"]
    },
    "42363976": {
        "category_id": "msk_biopsy",
        "title_fr": "Biopsie percutanée disco-vertébrale modifiée couplée au séquençage ARN 16S pour le diagnostic précoce des spondylodiscites à pyogènes",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Biopsie Disco-Vertébrale Transpédiculaire",
        "cochin_link": "Directement applicable aux biopsies disco-vertébrales sous scanner réalisées en urgence ou en programmé à Cochin pour suspicion de spondylodiscite.",
        "summary_fr_short": "Étude de cohorte rétrospective (*Eur Spine J*, juin 2026, 66 patients) démontrant qu'une technique de biopsie percutanée combinant prélèvement du plateau vertébral sous-chondral et du disque intervertébral par voie transpédiculaire modifiée, associée au séquençage génétique 16S rRNA, porte le rendement microbiologique de 51,6 % à 85,7 %.",
        "summary_fr_detailed": "Dans les spondylodiscites à pyogènes débutantes, la biopsie discale ou trans-pédiculaire standard souffre d'un taux élevé de faux négatifs. Cette étude a comparé 31 patients ayant eu une biopsie transpédiculaire classique + PCR 16S (Groupe A) à 35 patients ayant bénéficié d'une biopsie transpédiculaire modifiée prélevant simultanément l'os sous-chondral vertébral inflammatoire et le disque intervertébral + séquençage génétique (Groupe B). Le taux d'identification du pathogène (dominé par Staphylococcus aureus) a bondi de 51,6 % (16/31) à 85,7 % (30/35, p < 0,01), sans aucune complication grave dans les deux groupes.",
        "protocol_fr": "Guidage TDM/fluoroscopique par abord transpédiculaire oblique descendant • Prélèvement combiné : carottes osseuses du plateau vertébral sous-chondral œdématié (en IRM STIR/T1 Gado) + tissu discal adjacent • Envoi systématique en bactériologie standard prolongée, anatomopathologie et biologie moléculaire (PCR ARN 16S / NGS).",
        "key_points_fr": [
            "Augmentation majeure de la rentabilité microbiologique : 85,7 % contre 51,6 % avec la biopsie transpédiculaire classique (p < 0,01).",
            "Intérêt majeur de cibler simultanément l'os sous-chondral du plateau vertébral (riche en germes au stade précoce) et le disque.",
            "Synergie diagnostique avec le séquençage ARN 16S, particulièrement utile en cas d'antibiothérapie préalable ou de germe lent.",
            "Aucune complication grave rapportée sur les 66 procédures."
        ],
        "tags": ["Biopsie disco-vertébrale", "Spondylodiscite", "ARN 16S", "Voie transpédiculaire", "Rendement diagnostique"]
    },
    "41063397": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Efficacité et sécurité des techniques d'ablation des nerfs géniculés dans la gonarthrose : revue systématique et méta-analyse des essais randomisés contrôlés versus sham",
        "modality": "Échographie + Fluoroscopie / TDM",
        "intervention_type": "Radiofréquence & Cryoneurolyse des Nerfs Géniculés",
        "cochin_link": "Correspond directement aux séances de test anesthésique sous écho + radiofréquence/cryoneurolyse des nerfs géniculés pour gonarthrose à Cochin.",
        "summary_fr_short": "Méta-analyse d'essais randomisés contrôlés contre procédure fictive (*Pain Medicine*, avr. 2026, 8 ECR, 627 patients) confirmant l'efficacité antalgique à 12 semaines et fonctionnelle (WOMAC) à 24 semaines de la neurolyse des nerfs géniculés (radiofréquence et cryoneurolyse) dans la gonarthrose réfractaire.",
        "summary_fr_detailed": "Cette revue systématique avec analyse séquentielle des essais (TSA) a inclus exclusivement les essais randomisés contrôlés contre procédure sham (8 ECR, n = 627 patients) évaluant la radiofréquence (monopolaire conventionnelle, refroidie ou bipolaire) et la cryoneurolyse des nerfs géniculés chez des adultes souffrant de gonarthrose symptomatique inéligibles à la prothèse. Par rapport au groupe sham, les techniques ablatives réduisent significativement la douleur à 12 semaines (différence moyenne MD -1,65 ; IC 95 % [-2,57 ; -0,74]) et améliorent le score fonctionnel WOMAC (MD -11,37 ; IC 95 % [-18,83 ; -3,91]). L'analyse séquentielle (TSA) confirme le caractère concluant du bénéfice antalgique à 3 mois et fonctionnel à 6 mois, sans aucun événement indésirable grave rapporté.",
        "protocol_fr": "Repérage combiné échographique et fluoroscopique/TDM des artères et nerfs géniculés supéro-médial (SMGN), supéro-latéral (SLGN) et inféro-médial (IMGN) • Test de stimulation sensitive/motrice • Thermocoagulation par radiofréquence conventionnelle (80 °C, 90 s) ou refroidie, ou cryoneurolyse percutanée.",
        "key_points_fr": [
            "Haut niveau de preuve (méta-analyse de 8 essais randomisés contrôlés contre sham, 627 patients) validé par Trial Sequential Analysis (TSA).",
            "Réduction significative de l'EVA douloureuse à 12 semaines (MD -1,65 point) et amélioration fonctionnelle WOMAC durable jusqu'à 24 semaines (MD -11,37 points).",
            "Excellent profil de sécurité : aucun événement indésirable grave rapporté sur les 627 patients.",
            "La radiofréquence monopolaire conventionnelle affiche le rapport efficacité/coût le plus robuste en analyse de sous-groupe."
        ],
        "tags": ["Nerfs géniculés", "Gonarthrose", "Radiofréquence", "Cryoneurolyse", "Méta-analyse ECR sham"]
    },
    "42527616": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Procédures osseuses percutanées guidées par scanner avec assistance robotique (Epione®) : étude pilote multicentrique prospective",
        "modality": "Scanner TDM + Navigation Robotique (Epione®)",
        "intervention_type": "Consolidation & Ablation Osseuse Robot-Assistée",
        "cochin_link": "Directement lié aux gestes complexes de consolidation et d'ablation osseuse rachidienne et pelvienne sous guidage TDM avancé réalisés à Cochin.",
        "summary_fr_short": "Étude prospective multicentrique pilote (*CVIR*, juil. 2026, 34 patients, 90 insertions d'aiguilles) démontrant une faisabilité de 98,9 % et une précision balistique de 2,0 ± 1,4 mm pour les procédures osseuses percutanées du rachis et du bassin assistées par le robot Epione®.",
        "summary_fr_detailed": "Cette étude prospective menée dans trois centres hospitalo-universitaires a évalué l'insertion robot-assistée sous scanner de trocarts osseux chez 34 patients (90 trajectoires : 66 au rachis thoraco-lombaire [73,3 %] et 24 au bassin [26,7 %], pour consolidation [97 %] ou thermoablation tumorale [3 %]). Le placement robotique a réussi sans conversion manuelle dans 89/90 insertions (98,9 %). L'écart latéral moyen à la pointe de l'aiguille était de 2,0 ± 1,4 mm et la déviation angulaire de 3,1° ± 2,7°, sans aucun événement indésirable lié au dispositif ni à la procédure.",
        "protocol_fr": "Acquisition TDM de planification • Définition sur console 3D du point d'entrée cutané et de la cible intra-osseuse (pédicule vertébral ou couloir pelvien) • Positionnement automatique du bras robotique Epione® • Insertion du trocart osseux sous apnée contrôlée et contrôle TDM de vérification.",
        "key_points_fr": [
            "Taux de succès technique de 98,9 % (89/90 trocarts) sans conversion manuelle sur des cibles rachidiennes et pelviennes.",
            "Précision millimétrique (déviation latérale moyenne à la pointe : 2,0 ± 1,4 mm ; déviation angulaire : 3,1°).",
            "Aucune complication imputable au guidage robotique sur les 90 ponctions osseuses.",
            "Sécurise les abords obliques complexes ou multi-aiguilles en oncologie interventionnelle ostéo-articulaire."
        ],
        "tags": ["Robotique interventionnelle", "Epione", "Consolidation osseuse", "Ablation tumorale", "Rachis", "Bassin", "CVIR 2026"]
    },
    "41876692": {
        "category_id": "ablation_benign",
        "title_fr": "Dose d'irradiation, résultats cliniques et tendances de l'ablation d'ostéome ostéoïde pédiatrique guidée par scanner : analyse du registre DeGIR (166 patients)",
        "modality": "Scanner TDM (Protocole Basse Dose Pédiatrique)",
        "intervention_type": "Radiofréquence (RFA) / Micro-ondes (MWA) / Cryoablation",
        "cochin_link": "Fournit les niveaux de référence diagnostiques et interventionnels (DLP) pour les thermoablations d'ostéomes ostéoïdes chez l'adolescent et le jeune adulte à Cochin.",
        "summary_fr_short": "Analyse multicentrique du registre allemand DeGIR (*CVIR*, mars 2026, 166 patients ≤ 18 ans) établissant les valeurs de référence de dose d'irradiation (DLP médian 132 mGy·cm) et confirmant un succès technique de 99,4 % pour l'ablation TDM d'ostéome ostéoïde.",
        "summary_fr_detailed": "Sur 166 patients pédiatriques (âge moyen 13,5 ans) traités par ablation percutanée sous scanner entre 2019 et 2024, la radiofréquence représentait 71,1 % des gestes, les micro-ondes 26,5 % et la cryoablation 1,8 %. Le Produit Dose-Longueur (DLP) médian global était de 132 mGy·cm (IQR 53–314), avec une médiane de 124 mGy·cm (IQR 51–297) pour le squelette appendiculaire et de 222 mGy·cm (IQR 64,5–485) pour le squelette axial. Le taux de succès technique atteignait 99,4 % avec un taux de complications mineures de seulement 1,81 %.",
        "protocol_fr": "Hélice de repérage ultra-basse dose centrée sur le nidus (collimation réduite, bas kilovoltage 80–100 kVp, itération dédiée) • Guidage séquentiel ('step-and-shoot') limité à quelques coupes millimétriques • Objectif dosimétrique : DLP < 150 mGy·cm sur les membres et < 250 mGy·cm sur le rachis/bassin.",
        "key_points_fr": [
            "Établit les premiers repères dosimétriques multicentriques (benchmarks DLP Q1–Q3) pour l'ablation TDM d'ostéome ostéoïde.",
            "DLP médian très contenu : 124 mGy·cm sur les membres et 222 mGy·cm sur le squelette axial.",
            "Succès technique de 99,4 % et taux de complication très bas (1,81 %), confirmant la RFA comme gold standard (71 % des procédures).",
            "Référentiel directement utilisable pour l'audit dosimétrique et l'optimisation ALARA au scanner interventionnel."
        ],
        "tags": ["Ostéome ostéoïde", "Radioprotection", "DLP", "Radiofréquence", "Registre DeGIR", "CVIR 2026"]
    },
    "40906057": {
        "category_id": "ect_mets",
        "title_fr": "Électrochimiothérapie (ECT) des métastases vertébrales par voie transpédiculaire : étude préclinique de sécurité médullaire sous neuromonitoring",
        "modality": "Scanner TDM + Fluoroscopie + Neuromonitoring (PEM/PES)",
        "intervention_type": "Électrochimiothérapie (ECT) Vertébrale Transpédiculaire",
        "cochin_link": "Directement lié aux séances d'électrochimiothérapie (Bléomycine IV) des métastases rachidiennes et épidurales réalisées au scanner Achard -1 à Cochin.",
        "summary_fr_short": "Étude de sécurité préclinique (*Eur Radiol Exp*, sept. 2025, 12 sujets, 36 niveaux thoraco-lombaires T11–L1) démontrant que l'électrochimiothérapie vertébrale par voie transpédiculaire ne provoque aucune lésion histologique médullaire ni déficit neurologique permanent.",
        "summary_fr_detailed": "L'électrochimiothérapie (ECT) est une alternative majeure pour les métastases vertébrales radiorésistantes ou proches du cordon médullaire, mais le champ électrique pulsé pourrait théoriquement léser la moelle épinière. Dans cette étude évaluant l'ECT sur 3 niveaux consécutifs (T11, T12, L1) par abord transpédiculaire bilatéral avec neuromonitoring per-opératoire, une sidération transitoire des potentiels évoqués moteurs (PEM) des membres inférieurs a été observée chez 5/6 sujets mais avec récupération complète systématique en moins de 30 minutes. L'examen clinique à J3 et J30 était strictement normal (marche normale, absence de trouble sphinctérien) et l'analyse histopathologique médullaire n'a révélé ni apoptose neuronale, ni thrombose vasculaire, ni foyer hémorragique.",
        "protocol_fr": "Insertion d'électrodes-aiguilles par voie transpédiculaire bilatérale sous guidage TDM • Perfusion IV de Bléomycine • Délivrance des impulsions d'électroporation synchronisées à l'ECG sous surveillance continue des Potentiels Évoqués Moteurs (PEM) • Savoir qu'une chute immédiate des PEM récupère habituellement en < 30 min sans lésion anatomique médullaire.",
        "key_points_fr": [
            "Démonstration histologique de l'innocuité médullaire de l'ECT vertébrale par voie transpédiculaire (aucune apoptose ni ischémie médullaire).",
            "Observation importante pour le radiologue interventionnel : les Potentiels Évoqués Moteurs (PEM) peuvent chuter transitoirement après l'impulsion électrique mais récupèrent intégralement en moins de 30 minutes.",
            "Aucun déficit moteur ni trouble vésico-sphinctérien observé au cours du suivi.",
            "Confirme la sécurité du positionnement transpédiculaire des électrodes pour traiter les métastases rachidiennes complexes."
        ],
        "tags": ["Électrochimiothérapie", "Métastases vertébrales", "Voie transpédiculaire", "Neuromonitoring", "Sécurité médullaire", "Eur Radiol Exp"]
    },
    "42663695": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Éviter les pièges du vissage percutané des colonnes acétabulaires grâce aux incidences fluoroscopiques de contrôle combinées (COOHO, Outlet et Profil strict)",
        "modality": "Fluoroscopie / Cone-Beam CT / Scanner TDM",
        "intervention_type": "Vissage Percutané des Colonnes Antérieure et Postérieure du Cotyle",
        "cochin_link": "Directement applicable aux vissages percutanés du bassin et du cotyle (colonnes antérieure et postérieure, montage tripode) pratiqués à Cochin.",
        "summary_fr_short": "Note technique et série clinique (*Eur J Orthop Surg Traumatol*, août 2026) décrivant trois incidences fluoroscopiques spécifiques — dont la vue combinée 'Obturator Oblique Hyper-Outlet' (COOHO) — pour démasquer les effractions corticales 'in-out-in' lors du vissage percutané des colonnes acétabulaires.",
        "summary_fr_detailed": "Les incidences fluoroscopiques orthogonales standard (alarme/iliaque et obturatrice) peuvent masquer une brèche corticale extra-osseuse ('in-out-in') lors du vissage rétrograde ou antérograde des colonnes du cotyle. Cet article valide sur modèle pelvien et série clinique l'utilisation de l'incidence COOHO (Combined Obturator Oblique Hyper-Outlet) pour la colonne antérieure : elle profile tangentiellement le récessus pectiné et la gouttière ilio-psoas, détectant immédiatement toute sortie corticale antéro-supérieure. Pour la colonne postérieure, l'ajout systématique des vues Outlet et Profil strict (True Lateral) permet de visualiser l'étendue verticale de la ligne ilio-ischiatique et de prévenir toute effraction médiale dans la lame quadrilatère ou postérieure dans la petite échancrure sciatique.",
        "protocol_fr": "Colonne antérieure (AC) : contrôler systématiquement la broche-guide en incidence COOHO (obturatrice + hyper-outlet) pour éliminer un trajet 'in-out-in' dans la gouttière du psoas • Colonne postérieure (PC) : compléter les vues iliaque/obturatrice par un Outlet et un Profil sacré strict (True Lateral) pour sécuriser la lame quadrilatère et l'échancrure sciatique.",
        "key_points_fr": [
            "Les vues fluoroscopiques classiques peuvent donner une fausse impression de trajet intra-osseux dans les couloirs acétabulaires étroits.",
            "L'incidence COOHO (Combined Obturator Oblique Hyper-Outlet) profile tangentiellement la gouttière ilio-psoas et le récessus pectiné pour sécuriser la vis de colonne antérieure.",
            "Le couple Outlet + Profil strict (True Lateral) sécurise la colonne postérieure en regard de la petite échancrure sciatique et de la lame quadrilatère.",
            "Repères fluoroscopiques rapides directement intégrables au bloc interventionnel (arceau 3D / TDM)."
        ],
        "tags": ["Vissage cotyle", "Colonne antérieure", "Colonne postérieure", "Incidence COOHO", "Fluoroscopie", "Bassin"]
    },
    "41999357": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Évaluation de la cryoneurolyse du nerf pudendal guidée par scanner dans le traitement des douleurs pelviennes réfractaires (oncologiques et non oncologiques)",
        "modality": "Scanner TDM",
        "intervention_type": "Cryoneurolyse Percutanée du Nerf Pudendal",
        "cochin_link": "Complète l'arsenal de cryoneurolyse percutanée sous scanner (Morton, nerfs intercostaux, douleurs pelviennes et périnéales oncologiques) réalisé à Cochin.",
        "summary_fr_short": "Étude clinique rétrospective (*Am J Hosp Palliat Care*, avr. 2026, 30 patients) démontrant une réduction hautement significative de l'EVA douloureuse (jusqu'à 6 mois, p < 0,001) et de la consommation d'opioïdes après cryoneurolyse TDM du nerf pudendal, sans aucune complication.",
        "summary_fr_detailed": "Sur 30 patients consécutifs souffrant de névralgie pudendale ou de douleur pelvienne réfractaire d'origine tumorale ou bénigne, la cryoneurolyse guidée par scanner du nerf pudendal (au niveau de l'épine sciatique / canal d'Alcock) a permis une amélioration significative du score EVA à 1 semaine (3,9 ± 2,1, p < 0,001), 1 mois (4,6 ± 2,3, p < 0,001), 3 mois (3,9 ± 2,2, p < 0,001) et 6 mois (p < 0,001). La consommation quotidienne d'équivalents morphiniques (ME) a significativement diminué dès la 1re semaine et à 1 mois (de 30 mg à 17,5 mg, p = 0,032). L'efficacité antalgique était comparable entre les cohortes oncologique et non oncologique, avec 0 % d'effet indésirable.",
        "protocol_fr": "Patient en procubitus au scanner • Repérage TDM du ligament sacro-épineux, du ligament sacro-tubéral et du canal d'Alcock (épine ischiatique) • Positionnement d'une cryosonde fine au contact du tronc du nerf pudendal • Double cycle de congélation (2 × 2 min avec décongélation intermédiaire) sous anesthésie locale.",
        "key_points_fr": [
            "Soulagement antalgique rapide dès J7 et durable jusqu'à 6 mois (p < 0,001) chez 30 patients atteints de douleurs pelviennes réfractaires.",
            "Épargne morphinique significative à 1 semaine et 1 mois post-procédure (p = 0,032).",
            "Efficacité identique dans les douleurs pelviennes oncologiques (envahissement sacré/pelvien) et les névralgies pudendales non malignes.",
            "Sécurité remarquable sous guidage scanner (aucun événement indésirable rapporté)."
        ],
        "tags": ["Cryoneurolyse", "Nerf pudendal", "Douleur pelvienne", "Soins palliatifs", "Guidage scanner"]
    },
    "42182575": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Résultats thérapeutiques dans les neuropathies clunéales (nerfs clunéaux supérieur et moyen) : revue systématique et méta-analyse (628 patients)",
        "modality": "Scanner TDM / Échographie / Fluoroscopie",
        "intervention_type": "Neurolyse (Radiofréquence / Cryoneurolyse) & Infiltration du Nerf Clunéal",
        "cochin_link": "Directement lié aux nouvelles procédures de « cryoneurolyse percutanée du nerf clunéal » inscrites dans l'Agenda Interventionnel de Cochin.",
        "summary_fr_short": "Revue systématique et méta-analyse (*Brain & Spine*, avr. 2026, 26 bras thérapeutiques, 628 patients) démontrant un taux global de répondeurs (réduction douloureuse ≥ 50 %) de 78,3 % à ≥ 3 mois et de 82,9 % à ≥ 6 mois après traitement ciblé des névralgies clunéales supérieure et moyenne.",
        "summary_fr_detailed": "L'entrapment des nerfs clunéaux supérieur (franchissant la crête iliaque à travers l'orifice ostéo-aponévrotique thoraco-lombaire, 6 à 8 cm de la ligne médiane) ou moyen (en regard du ligament sacro-iliaque postérieur long) est une cause fréquente mais sous-diagnostiquée de lombalgie basse et de fessalgie pseudo-radiculaire. Sur 628 patients inclus, le taux poolé de succès clinique (baisse de l'EVA ≥ 50 %) atteint 75,1 % (IC 95 % : 62,1–84,7 %) pour l'ablation percutanée par radiofréquence/neurolyse, 72,4 % (IC 95 % : 65,9–78,1 %) pour les infiltrations ciblées, 80,1 % pour la neurostimulation périphérique et 93,1 % pour la décompression chirurgicale.",
        "protocol_fr": "Repérage TDM ou échographique de la crête iliaque postérieure à 6–8 cm de la ligne médiane (incisure clunéale / tunnel ostéo-fibreux du fascia thoraco-lombaire pour le nerf clunéal supérieur ; gouttière sacro-iliaque postérieure entre EIPS et S3 pour le nerf clunéal moyen) • Bloc test anesthésique diagnostique préalable (> 50 % de soulagement) • Cryoneurolyse percutanée (2 cycles de congélation) ou radiofréquence sous AL.",
        "key_points_fr": [
            "Taux global de répondeurs élevé dans les névralgies clunéales : 78,3 % à ≥ 3 mois et 82,9 % à ≥ 6 mois (628 patients).",
            "L'ablation percutanée (RFA / neurolyse thermique) obtient 75,1 % de succès durable après bloc diagnostique positif.",
            "Cible anatomique précise : franchissement de la crête iliaque postéro-supérieure (6–8 cm de la ligne médiane) pour le nerf clunéal supérieur.",
            "Justifie pleinement l'intégration du bloc test et de la cryoneurolyse du nerf clunéal dans les lombalgies/fessalgies réfractaires à Cochin."
        ],
        "tags": ["Nerf clunéal", "Cryoneurolyse", "Radiofréquence", "Lombalgie", "Fessalgie", "Méta-analyse 2026"]
    },
    "42667387": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Faisabilité, sécurité et efficacité à court terme de la radiofréquence guidée par échographie pour l'endométriose pariétale abdominale",
        "modality": "Échographie (technique 'Moving-Shot') + IRM",
        "intervention_type": "Ablation par Radiofréquence (RFA) d'Endométriome Pariétal",
        "cochin_link": "Complète directement votre thématique d'ablation percutanée des nodules d'endométriose pariétale abdominale (cicatrice de césarienne) à Cochin.",
        "summary_fr_short": "Étude clinique monocentrique (*Abdominal Radiology*, août 2026, 19 patientes, 29 lésions) évaluant l'ablation par radiofréquence sous échographie (technique 'moving-shot') des endométriomes de la paroi abdominale : chute de l'EVA de 7,37 à 1,72 et réduction volumétrique de 77,5 % dès 3 mois.",
        "summary_fr_detailed": "Sur 19 patientes (âge moyen 35,5 ans) présentant 29 nodules d'endométriose pariétale abdominale (douleur cyclique dans 73,7 % des cas, masse palpable dans 89,5 %), la thermoablation par radiofréquence a été réalisée sous guidage échographique avec une électrode 18G selon la technique 'moving-shot' sous anesthésie locale et sédation IV. À 3 mois, le diamètre maximal moyen a diminué de 25,1 ± 17,5 mm à 13,4 ± 10,6 mm (p < 0,01), le volume lésionnel moyen a chuté de 5,65 mL à 1,27 mL (-77,5 %, p < 0,01) et l'EVA douloureuse moyenne est passée de 7,37/10 à 1,72/10 (p < 0,01), sans aucune complication majeure (classification SIR).",
        "protocol_fr": "Bilan IRM pelvi-pariétal pré-thérapeutique • Anesthésie locale tumescente / hydrodissection sous-cutanée et pré-aponévrotique sous échographie • Électrode de radiofréquence monopolaire 18G manipulée selon la technique 'moving-shot' pour couvrir l'ensemble du nodule fibreux d'endométriose • Alternative directe à la cryoablation en ambulatoire.",
        "key_points_fr": [
            "Réduction spectaculaire de la douleur cyclique pariétale : EVA moyenne passant de 7,37/10 à 1,72/10 dès 3 mois (p < 0,01).",
            "Réduction volumétrique moyenne de 77,5 % à 3 mois (de 5,65 mL à 1,27 mL, p < 0,01).",
            "Excellente tolérance en ambulatoire sous anesthésie locale + analgésie IV (aucune complication majeure SIR).",
            "Confirme la place de la thermoablation percutanée (cryoablation ou RFA moving-shot) en première intention face à la chirurgie pariétale délabrante."
        ],
        "tags": ["Endométriose pariétale", "Radiofréquence", "Moving-shot", "Échographie interventionnelle", "Abdominal Radiology 2026"]
    },
    "42780331": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Complications de la cimentoplastie vertébrale dans les fractures rachidiennes métastatiques : revue systématique de 76 études (3 234 patients, 5 737 vertèbres)",
        "modality": "Scanner TDM / Fluoroscopie",
        "intervention_type": "Vertébroplastie & Kyphoplastie Oncologique",
        "cochin_link": "Référentiel majeur de sécurité pour les cimentoplasties vertébrales (cervicales, thoraciques et lombaires) post-radiothérapie ou combinées aux ablations à Cochin.",
        "summary_fr_short": "Revue systématique d'envergure (*Journal of Bone Oncology*, sept. 2026, 76 études, 3 234 patients, ≥ 5 737 vertèbres traitées) quantifiant précisément le taux de complications symptomatiques (3,41 %) et de fuites de ciment (20,7 %, majoritairement asymptomatiques) lors de la cimentoplastie des métastases rachidiennes.",
        "summary_fr_detailed": "Sur 5 737 niveaux vertébraux métastatiques traités par vertébroplastie ou kyphoplastie, le taux pondéré d'événements indésirables globaux (incluant les fuites radiologiques asymptomatiques) est de 25,5 %, mais le taux de complications réellement symptomatiques n'est que de 3,41 %. L'incidence pondérée des fuites de ciment est de 20,7 % (détectées plus fréquemment sur le contrôle TDM post-opératoire que sur la fluoroscopie seule : 28,6 % vs 11,9 %, p = 0,004). Les complications cliniques comprennent les douleurs transitoires post-procédure (1,77 %), l'embolie pulmonaire de ciment (1,08 %) et les fractures des vertèbres adjacentes (0,79 %).",
        "protocol_fr": "Analyse TDM pré-opératoire rigoureuse du mur postérieur et des veines basivertébrales/épidurales • Utilisation de ciment PMMA haute viscosité injecté lentement sous contrôle fluoroscopique/TDM continu • Arrêt immédiat de l'injection dès la moindre fuite veineuse pré-vertébrale ou épidurale.",
        "key_points_fr": [
            "Plus vaste synthèse publiée à ce jour en oncologie rachidienne : 3 234 patients et plus de 5 737 vertèbres métastatiques cimentées.",
            "Taux de complications symptomatiques très contenu (3,41 %), confirmant la haute sécurité du geste palliatif.",
            "Faible incidence d'embolie pulmonaire de ciment (1,08 %) et de fracture adjacente précoce (0,79 %).",
            "Le contrôle par scanner détecte 2,4 fois plus de micro-fuites asymptomatiques que la radioscopie standard (28,6 % vs 11,9 %)."
        ],
        "tags": ["Cimentoplastie vertébrale", "Métastases rachidiennes", "Sécurité", "Fuite de ciment", "J Bone Oncol 2026"]
    },
    "40911195": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Résultats à très long terme (> 5 ans) après vertébroplastie ou cimentoplastie osseuse chez les patients atteints de myélome multiple",
        "modality": "Scanner TDM / IRM de suivi à long terme",
        "intervention_type": "Vertébroplastie & Cimentoplastie Pelvienne (Myélome)",
        "cochin_link": "Directement lié aux cimentoplasties rachidiennes et du bassin chez les patients suivis au long cours pour myélome multiple à Cochin.",
        "summary_fr_short": "Étude rétrospective avec suivi imagerie ≥ 5 ans (*Neuroradiology*, sept. 2025, 142 sites cimentés) démontrant la pérennité mécanique remarquable de la cimentoplastie dans le myélome multiple (1,4 % de refracture locale) et identifiant la fuite discale comme facteur majeur de fracture vertébrale adjacente (31 % vs 8,8 %).",
        "summary_fr_detailed": "Sur 47 patients atteints de myélome multiple survivant à plus de 5 ans avec imagerie de contrôle (74 procédures, 142 sites cimentés : 129 vertèbres, 11 cimentoplasties pelviennes), seules 2 refractures de l'os cimenté (1,4 %) sont survenues, prouvant la durabilité biomécanique à long terme du PMMA. En revanche, 14 % des vertèbres adjacentes non cimentées ont présenté une fracture secondaire au cours du suivi : la présence d'une fuite de ciment dans le disque intervertébral multipliait par 3,5 ce risque (31 % vs 8,8 %, p = 0,022). Les fractures à distance étaient associées à une plasmocytose médullaire initiale élevée (23 % vs 13 %, p = 0,014).",
        "protocol_fr": "Cimentoplastie vertébrale ou pelvienne guidée par TDM/fluoroscopie • Viser un remplissage spongieux trabéculaire homogène d'un plateau à l'autre tout en évitant strictement le franchissement du plateau vertébral et la fuite discale • Discuter une cimentoplastie prophylactique d'une vertèbre adjacente prise en sandwich ou en cas de fuite discale.",
        "key_points_fr": [
            "Stabilité mécanique exceptionnelle à plus de 5 ans : seulement 1,4 % de récidive fracturaire sur les 142 os cimentés.",
            "Règle technique essentielle : la fuite de ciment intradiscale fait passer le risque de fracture de la vertèbre adjacente de 8,8 % à 31 % (p = 0,022).",
            "Aucune complication grave liée à la procédure sur 129 vertèbres et 11 bassins cimentés.",
            "Ouvre la discussion d'une cimentoplastie préventive des niveaux adjacents à haut risque dans le myélome."
        ],
        "tags": ["Myélome multiple", "Cimentoplastie", "Vertébroplastie", "Fuite discale", "Fracture adjacente", "Neuroradiology"]
    },
    "41473339": {
        "category_id": "msk_imaging",
        "title_fr": "Évaluation par imagerie (TDM et IRM) des tumeurs osseuses du rachis cervical : revue complète diagnostique et pré-thérapeutique",
        "modality": "IRM + Scanner TDM / Angio-TDM",
        "intervention_type": "Bilan Pré-Thérapeutique & Suivi du Rachis Cervical",
        "cochin_link": "En lien direct avec les gestes cervicaux récemment programmés dans l'Agenda Cochin (« RF d'ostéome ostéoïde de C6 » et « cimentoplastie cervicale sous AG »).",
        "summary_fr_short": "Revue clinique et iconographique complète (*Int J Gen Med*, déc. 2025) détaillant la sémiologie IRM et TDM des tumeurs osseuses bénignes (ostéome ostéoïde, ostéoblastome, KOA) et malignes (métastases, chordome, myélome) du rachis cervical ainsi que les repères anatomiques critiques avant geste percutané.",
        "summary_fr_detailed": "Le rachis cervical présente des défis diagnostiques et interventionnels uniques en raison de l'étroitesse des pédicules, de la proximité immédiate des artères vertébrales dans les foramens transversaires (C1–C6), du cordon médullaire et des racines nerveuses. Cet article synthétise les critères de caractérisation TDM et IRM permettant de différencier les lésions bénignes de l'arc postérieur (ostéome ostéoïde, ostéoblastome, kyste osseux anévrismal) des lésions malignes prédominant sur le corps vertébral (métastases ostéolytiques, myélome, chordome), et précise le bilan pré-thérapeutique indispensable avant biopsie, thermoablation ou cimentoplastie cervicale.",
        "protocol_fr": "Bilan pré-interventionnel cervical : TDM en coupes infra-millimétriques + Angio-TDM des troncs supra-aortiques (cartographie de l'artère vertébrale V2 dans le foramen transversaire par rapport au nidus ou au trajet de trocart) + IRM cervicale T1, STIR, Diffusion et T1 injecté • Abord antéro-latéral (entre axe jugulo-carotidien et axe aéro-digestif) pour le corps vertébral ou postéro-latéral pour l'arc postérieur.",
        "key_points_fr": [
            "Cartographie indispensable des rapports avec l'artère vertébrale (segment V2) et le foramen intervertébral avant toute RF d'ostéome ostéoïde cervical (ex. C6).",
            "Topographie préférentielle sur l'arc postérieur pour l'ostéome ostéoïde, l'ostéoblastome et le KOA, contre le corps vertébral pour les métastases et le chordome.",
            "Complémentarité systématique du scanner en coupes fines (matrice minérale, corticale) et de l'IRM (extension épidurale, œdème réactionnel).",
            "Guide le choix sécurisé de la voie d'abord cervicale (antéro-latérale vs postéro-latérale) au scanner interventionnel."
        ],
        "tags": ["Rachis cervical", "Ostéome ostéoïde cervical", "Métastases cervicales", "IRM", "Scanner TDM", "Artère vertébrale"]
    },
    "42384128": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Évaluation de la réponse radiologique (M-RECIST vs RECIST 1.1) chez les patients atteints de fibromatose desmoïde traitée par cryoablation percutanée",
        "modality": "IRM Multiparamétrique (T2, Diffusion, T1 Gado) + TDM",
        "intervention_type": "Cryoablation Percutanée & Suivi IRM M-RECIST",
        "cochin_link": "Directement lié aux cryoablations de tumeurs desmoïdes (flanc gauche, creux sus-claviculaire, paravertébral) et à leurs IRM de contrôle à 6 semaines et 3 mois à Cochin.",
        "summary_fr_short": "Étude rétrospective (*Eur Radiol Exp*, juil. 2026, 34 patients, 37 cryoablations) démontrant que les critères IRM adaptés à la viabilité tissulaire (M-RECIST) détectent 79,4 % de réponse objective (dont 44,1 % de réponse complète) contre seulement 28,6 % avec les critères dimensionnels RECIST 1.1.",
        "summary_fr_detailed": "La cryoablation percutanée induit une nécrose de coagulation et une hyalinisation collagénique qui précèdent de plusieurs mois la rétraction volumétrique, rendant le score RECIST 1.1 classique peu sensible. Sur 37 cryoablations de tumeurs desmoïdes extra-abdominales suivies en médiane 16 mois, le taux de non-progression est de 91,2 %. Alors que RECIST 1.1 classe 62,9 % des lésions en maladie stable (SD) et seulement 28,6 % en réponse partielle (ORR 28,6 %), l'évaluation M-RECIST (fondée sur le volume tumoral viable résiduel en pondération T2, diffusion et soustraction T1 injectée) identifie 44,1 % de réponses complètes (CR) et 35,3 % de réponses partielles (ORR 79,4 %).",
        "protocol_fr": "IRM de réévaluation post-cryoablation (à 6 semaines, 3 mois, 6 mois et 12 mois) incluant séquences T2, Diffusion (ADC) et T1 Fat-Sat sans et avec injection de gadolinium (soustraction) • Appliquer systématiquement les critères M-RECIST (mesure du contingent viable rehaussé et en hypersignal T2) plutôt que le diamètre global RECIST 1.1.",
        "key_points_fr": [
            "Taux de contrôle local (non-progression) de 91,2 % à 16 mois après cryoablation percutanée de tumeur desmoïde.",
            "Supériorité majeure du score M-RECIST (ORR 79,4 %, dont 44,1 % de réponse complète) sur RECIST 1.1 (ORR 28,6 %).",
            "Une cicatrice fibreuse post-cryoablation non rehaussée peut conserver la même taille globale tout en étant en rémission complète histologique et fonctionnelle.",
            "Standardise le compte-rendu IRM de suivi post-cryoablation des tumeurs desmoïdes en Radiologie B."
        ],
        "tags": ["Tumeur desmoïde", "Cryoablation", "M-RECIST", "IRM de suivi", "Eur Radiol Exp 2026"]
    },
    "41357250": {
        "category_id": "msk_imaging",
        "title_fr": "Sémiologie IRM post-cryoablation des tumeurs desmoïdes : atlas iconographique et pièges d'interprétation (6 à 30 mois de suivi)",
        "modality": "IRM Multiparamétrique de Suivi Post-Cryoablation",
        "intervention_type": "Suivi IRM Post-Cryoablation (Desmoïdes & Parties Molles)",
        "cochin_link": "Outil pratique quotidien pour l'interprétation des IRM de contrôle post-cryoablation (distinction entre réaction inflammatoire périphérique normale et récidive locale) à Cochin.",
        "summary_fr_short": "Atlas didactique (*Diagn Interv Radiol*, déc. 2025) illustrant l'évolution temporelle en IRM (de 6 à 30 mois) des tumeurs desmoïdes traitées par cryoablation percutanée afin d'éviter de confondre les remaniements post-thérapeutiques attendus avec une récidive.",
        "summary_fr_detailed": "Cet article iconographique détaille les aspects IRM pré-thérapeutiques, per-procédure et post-cryoablation (suivi de 6 à 30 mois) des fibromatoses desmoïdes. Il décrit la couronne inflammatoire périphérique précoce (fine prise de contraste annulaire régulière de tissu de granulation entourant la nécrose centrale avasculaire en hyposignal T1/T2 ou hypersignal T1 hémorragique), l'involution progressive en hyposignal T2 franc fibreux mature, et les signes formels de récidive focale viable (nodule asymétrique en hypersignal T2 franc, restriction en diffusion et rehaussement précoce nodulaire sur la berge d'ablation, souvent au contact d'une structure neuro-vasculaire thermoprotégée).",
        "protocol_fr": "Protocole IRM de suivi post-cryoablation : T1 sans injection (repérage de la nécrose hémorragique de coagulation), T2 Fat-Sat / STIR, Diffusion b800 avec cartographie ADC, et T1 Fat-Sat injecté avec soustraction dynamique • Comparaison systématique au contour initial de la boule de glace per-procédure.",
        "key_points_fr": [
            "Une fine prise de contraste périphérique circonférentielle et régulière dans les 3 à 6 premiers mois correspond à une réaction granulomateuse cicatricielle normale.",
            "La nécrose centrale post-cryoablation présente souvent un hypersignal T1 spontané (remaniements hémorragiques) rendant indispensable la séquence de soustraction après gadolinium.",
            "Le passage progressif en hyposignal T2 franc et l'absence de rehaussement signent la réponse complète durable.",
            "La récidive vraie se traduit par un bourgeon nodulaire focal en hypersignal T2 et rehaussement intense, typiquement situé sur une marge ayant nécessité une hydrodissection protectrice."
        ],
        "tags": ["IRM post-cryoablation", "Tumeur desmoïde", "Sémiologie IRM", "Soustraction T1", "Récidive vs cicatrice"]
    },
    "41568883": {
        "category_id": "ablation_benign",
        "title_fr": "Nouveautés dans la prise en charge des tumeurs à cellules géantes de l'os (TCG) : place de la thermoablation percutanée des récidives locales",
        "modality": "Scanner TDM + IRM",
        "intervention_type": "Cryoablation & Radiofréquence sur Récidive de TCG",
        "cochin_link": "Correspond directement au nouveau geste de l'Agenda Interventionnel Cochin : « cryothérapie percutanée sur récidive de TCG du genou ».",
        "summary_fr_short": "Mise au point (*SICOT-J*, janv. 2026) synthétisant les avancées thérapeutiques dans les tumeurs à cellules géantes de l'os (TCG / GCTB) des membres, mettant en avant l'efficacité de l'ablation thermique percutanée (radiofréquence et cryoablation) pour traiter les récidives locales de petite taille sans reprise chirurgicale lourde.",
        "summary_fr_detailed": "Alors que le curetage intra-lésionnel conservateur des tumeurs à cellules géantes de l'os (TCG) expose à un risque significatif de récidive locale épiphyso-métaphysaire (notamment autour du genou), cet article souligne les résultats favorables de la thermoablation percutanée guidée par scanner (radiofréquence ou cryoablation seule ou combinée à une cimentoplastie de comblement) pour éradiquer les récidives locales focales tout en préservant l'articulation native et le cartilage sous-chondral. L'article aborde également le suivi biologique par la phosphatase acide résistante au tartrate 5b (TRACP-5b) et les biomatériaux de comblement.",
        "protocol_fr": "Dépistage précoce de la récidive locale de TCG sur le suivi TDM/IRM post-curetage • Ciblage TDM de la logette d'ostéolyse récidivante • Thermoablation percutanée (cryoablation ou radiofréquence) avec thermoprotection cartilagineuse (injection intra-articulaire de sérum/CO2 si < 5 mm de la lame sous-chondrale) +/- cimentoplastie PMMA de soutien sous-chondral.",
        "key_points_fr": [
            "Valide l'ablation thermique percutanée (cryoablation / RFA) comme alternative mini-invasive de choix pour les récidives locales focales de TCG après curetage.",
            "Permet d'éviter un second curetage chirurgical itératif ou une résection prothétique tout en préservant la fonction articulaire du genou.",
            "Intérêt de combiner la destruction thermique à un comblement cimenté (PMMA) lorsque la récidive fragilise la corticale ou l'os sous-chondral.",
            "Nécessité d'une surveillance IRM/TDM rapprochée de l'interface os-ciment après traitement initial d'une TCG."
        ],
        "tags": ["Tumeur à cellules géantes", "TCG", "Récidive locale", "Genou", "Cryoablation", "Radiofréquence", "SICOT-J 2026"]
    },
    "41857607": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Avancées dans la prise en charge mini-invasive et chirurgicale des kystes osseux anévrismaux (KOA) et des kystes osseux essentiels (KOE)",
        "modality": "Scanner TDM / Fluoroscopie / Échographie",
        "intervention_type": "Sclérothérapie Percutanée (Alcool / Polidocanol / Doxycycline) & Embolisation",
        "cochin_link": "Directement lié aux séances d'« alcoolisation percutanée du kyste osseux anévrismal de l'humérus droit » et de « kyste essentiel de l'aile iliaque (+/- cimentoplastie) » programmées à Cochin.",
        "summary_fr_short": "Revue de synthèse (*J Orthop Surg Res*, mars 2026) comparant l'efficacité, le taux de récidive et la sécurité des approches mini-invasives (sclérothérapie percutanée, embolisation artérielle sélective, ablation guidée par l'image) face au curetage chirurgical dans les KOA et KOE.",
        "summary_fr_detailed": "Cette mise au point analyse l'évolution du paradigme thérapeutique des kystes osseux anévrismaux (KOA) et essentiels (KOE). Dans les KOA, les modalités mini-invasives — au premier rang desquelles la sclérothérapie percutanée répétée (éthanol absolu, polidocanol, mousse de doxycycline), l'embolisation artérielle sélective et la cryoablation/radiofréquence — obtiennent des taux élevés d'ossification corticale, de soulagement douloureux et de récupération fonctionnelle, avec une morbidité nettement inférieure au curetage chirurgical ou à la résection en bloc. Dans les KOE symptomatiques ou à risque fracturaire, l'injection percutanée sclérosante associée si besoin à une stabilisation ou un comblement permet une consolidation fiable.",
        "protocol_fr": "Ponction-aspiration sous guidage TDM et contrôle fluoroscopique avec kystographie préalable (éliminer un drainage veineux rapide avant injection d'éthanol) • Sclérothérapie percutanée à l'alcool absolu (ou polidocanol/doxycycline) avec temps de contact contrôlé puis réaspiration/rinçage • Cimentoplastie ou embrochage associé si risque fracturaire mécanique élevé.",
        "key_points_fr": [
            "La sclérothérapie percutanée est désormais établie comme traitement de première intention de nombreux KOA et KOE grâce à son faible taux de complications.",
            "Taux élevés de ré-ossification progressive et de contrôle douloureux sans les séquelles fonctionnelles du curetage ouvert.",
            "Rôle complémentaire de la cryoablation et de l'embolisation sélective pour les KOA volumineux, axiaux ou récidivants.",
            "Suivi TDM séquentiel à 3, 6 et 12 mois évaluant l'épaississement cortical et la trabéculation intrakystique (critères de Capanna)."
        ],
        "tags": ["Kyste osseux anévrismal", "Kyste osseux essentiel", "Sclérothérapie", "Alcoolisation", "Humérus", "J Orthop Surg Res 2026"]
    },
    "42129022": {
        "category_id": "msk_biopsy",
        "title_fr": "Évolution clinique, dédifférenciation et concordance IRM-histologie des tumeurs lipomateuses atypiques (ALT / liposarcomes bien différenciés)",
        "modality": "IRM + Biopsie Percutanée Échoguidée / Scanoguidée (MDM2)",
        "intervention_type": "Biopsie Percutanée de Masse Lipomateuse Profonde",
        "cochin_link": "En lien direct avec les « biopsies percutanées de formation lipomateuse glutéale ou de masse de la cuisse sous échographie/scanner » réalisées à Cochin.",
        "summary_fr_short": "Étude de cohorte (*Annals of Surgical Oncology*, mai 2026, 183 patients : 36 en surveillance active et 147 opérés) analysant le risque de dédifférenciation (8 % en surveillance, 20 % des récidives locales) et démontrant le caractère indispensable de la biopsie percutanée ciblée dès que l'IRM montre des signes atypiques.",
        "summary_fr_detailed": "Les tumeurs lipomateuses atypiques (ALT / liposarcomes bien différenciés des membres et de la région glutéale, caractérisées par l'amplification de MDM2) posent le dilemme entre surveillance IRM et chirurgie d'exérèse. Sur 36 patients suivis en médiane 26 mois, 61 % ont présenté une progression dimensionnelle et 3 patients (8 %) ont développé une dédifférenciation sarcomateuse (dont 2 n'avaient eu qu'un diagnostic IRM initial sans biopsie préalable). Parmi les 147 patients opérés d'emblée, 10 % ont récidivé localement (dont 20 % sous forme de liposarcome dédifférencié). L'étude souligne que la confirmation histologique et moléculaire par biopsie percutanée ciblée sur les septas épais ou nodules non graisseux visibles en IRM est indispensable.",
        "protocol_fr": "Analyse IRM préalable (T1, T2 Fat-Sat, T1 Gado : recherche de septas épais > 2 mm, nodules non adipeux rehaussés, localisation profonde sous-fasciale > 5 cm) • Biopsie percutanée au trocart 14G–16G sous échographie ou scanner sans franchir un compartiment sain, en ciblant électivement les septas épaissis ou tout contingent nodulaire non graisseux • Recherche systématique d'amplification MDM2 en FISH.",
        "key_points_fr": [
            "Toute masse lipomateuse profonde (> 5 cm, sous-fasciale, cuisse ou fesse) présentant des septas épais ou un nodule non graisseux en IRM impose une microbiopsie dirigée avec recherche d'amplification MDM2.",
            "Le ciblage biopsique doit impérativement porter sur la zone non graisseuse ou septale la plus vascularisée pour ne pas méconnaître un contingent dédifférencié.",
            "Risque de dédifférenciation de 8 % sous surveillance active (médiane 26 mois) et de 2 % au total après chirurgie initiale.",
            "Sécurise la décision en RCP Sarcome entre surveillance IRM active et exérèse chirurgicale."
        ],
        "tags": ["Tumeur lipomateuse atypique", "Liposarcome bien différencié", "MDM2", "Biopsie parties molles", "IRM", "Ann Surg Oncol 2026"]
    },
    "42970180": {
        "category_id": "msk_imaging",
        "title_fr": "Corrélation imagerie-anatomopathologie quantitative dans la fasciite nodulaire et discrimination diagnostique face aux sarcomes des tissus mous (IRM 3T)",
        "modality": "IRM 3T Multiparamétrique (Diffusion ADC + Séquences Anatomiques)",
        "intervention_type": "Caractérisation IRM & Concordance Radio-Histologique Pré-Biopsique",
        "cochin_link": "En lien direct avec les bilans IRM et « biopsies percutanées de masses des parties molles (diagnostic différentiel fasciite nodulaire vs sarcome) » en RCP Sarcome à Cochin.",
        "summary_fr_short": "Étude rétrospective sur 261 patients (*Insights into Imaging*, nov. 2026 : 128 fasciites nodulaires et 133 sarcomes des tissus mous en IRM 3T) démontrant que l'ADC moyen et le signe de la queue fasciale combinés aux biomarqueurs histopathologiques distinguent fasciite nodulaire et sarcome avec une AUC de 0,96.",
        "summary_fr_detailed": "La fasciite nodulaire (FN) est une prolifération myofibroblastique bénigne à croissance rapide simulant fréquemment un sarcome des tissus mous (STS) en IRM et en microbiopsie. Sur 128 FN et 133 STS explorés en IRM 3T préopératoire, l'hétérogénéité T2 corrèle positivement avec la dégénérescence myxoïde (ρ = 0,52, p < 0,001) et négativement avec la teneur en collagène (ρ = -0,28), tandis que l'ADC moyen corrèle inversement avec la densité cellulaire (ρ = -0,63, p < 0,001) et s'avère significativement plus élevé dans la FN que dans les sarcomes (p < 0,001). Le modèle intégrant sémiologie IRM (signe de la queue fasciale, ADC moyen/minimum, œdème périlésionnel) et biomarqueurs histologiques atteint une AUC de 0,96 (contre 0,89 pour l'IRM seule), sécurisant l'évaluation de concordance radio-pathologique après microbiopsie.",
        "protocol_fr": "IRM 3T pré-biopsique incluant séquences T1, T2 Fat-Sat (évaluation du fascial tail sign, du score d'hétérogénéité T2 et de l'œdème périlésionnel), diffusion DWI avec cartographie ADC (mesure de l'ADC moyen et minimal hors nécrose) et T1 Gadolinium • Confrontation systématique de l'ADC et de l'architecture stromale avec le résultat de la microbiopsie percutanée (recherche de réarrangement USP6).",
        "key_points_fr": [
            "Un ADC moyen significativement plus élevé associé au « fascial tail sign » oriente fortement vers une fasciite nodulaire face à un sarcome des parties molles.",
            "L'ADC moyen corrèle inversement avec la cellularité tumorale (ρ = -0,63) et l'hétérogénéité T2 reflète la composante myxoïde (ρ = 0,52).",
            "La combinaison IRM 3T + histologie quantitative porte la performance diagnostique à une AUC de 0,96 (IC 95 % : 0,938–0,978).",
            "Évite les exérèses délabrantes inutiles en sécurisant la concordance radio-histologique lors des biopsies de masses superficielles ou sous-fasciales."
        ],
        "tags": ["Fasciite nodulaire", "Sarcome des tissus mous", "IRM 3T", "Diffusion ADC", "Concordance radio-histologique", "Insights Imaging 2026"]
    },
    "42942556": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Monitorage neurophysiologique per-procédure lors de l'ablation par radiofréquence continue du névrome de Morton : confirmation d'ablation complète",
        "modality": "Échographie + Stimulation / Monitorage Neurophysiologique (SNAP)",
        "intervention_type": "Neurolyse par Radiofréquence Continue du Névrome de Morton",
        "cochin_link": "Complète directement les « neurolyses percutanées de névrome de Morton rebelle des 2e et 3e espaces interdigitaux (cryothérapie / radiofréquence) » de l'Agenda Cochin.",
        "summary_fr_short": "Série prospective de 22 patients / 30 névromes de Morton (*Medicina*, oct. 2026) traités par radiofréquence continue échoguidée sous monitorage en temps réel des potentiels d'action nerveux sensitifs (SNAP), obtenant 86,7 % de succès global (96,3 % hors métatarsalgie mécanique) et 100 % de succès en rattrapage après échec d'une RF antérieure.",
        "summary_fr_detailed": "Bien que la radiofréquence (RF) et la cryoneurolyse percutanées du névrome de Morton affichent 80 à 85 % de succès clinique, les échecs résultent soit d'une destruction neuronale incomplète, soit d'une métatarsalgie mécanique intriquée. Cette étude prospective a enregistré les potentiels d'action nerveux sensitifs (SNAP) avant, pendant et après chaque cycle de RF continue échoguidée jusqu'à abolition complète de la conduction sensitive sur 30 névromes. À 12 mois, l'EVA douleur chute de 8,67 à 1,67 avec 86,7 % de résultats satisfaisants (score de Giannini ≥ 60), et 96,3 % après exclusion des métatarsalgies mécaniques. Fait majeur : les 7 névromes en échec d'une première RF conventionnelle ont tous répondu favorablement (7/7) grâce au monitorage per-opératoire confirmant l'ablation neuronale complète.",
        "protocol_fr": "Repérage échographique longitudinal et transversal de l'espace intermétatarsien (2e ou 3e espace) • Positionnement de la sonde à l'extrémité proximale du névrome • Enregistrement des potentiels sensitifs (SNAP) du nerf digital plantaire commun et cycles de thermo-ablation RF continue jusqu'à disparition complète du signal de conduction • Test préalable de suppression anesthésique pour éliminer une métatarsalgie mécanique pure.",
        "key_points_fr": [
            "Diminution majeure de l'EVA douleur de 8,67 en pré-procédure à 1,67 à 12 mois (taux de succès ajusté de 96,3 %).",
            "100 % de succès clinique (7/7) chez les patients en récidive ou échec d'une première radiofréquence conventionnelle.",
            "Le test anesthésique diagnostique préalable est déterminant pour écarter une métatarsalgie mécanique statique associée.",
            "Valide l'intérêt du contrôle électrophysiologique et d'un ciblage nerveux proximal précis dans les névromes de Morton rebelles traités à Cochin."
        ],
        "tags": ["Névrome de Morton", "Radiofréquence", "Neurolyse percutanée", "Monitorage neurophysiologique", "Échoguidage", "Medicina 2026"]
    },
    "42977533": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Résultats cliniques et IRM (MOAKS) après ablation par radiofréquence refroidie (CRFA) échoguidée des nerfs géniculés dans la gonarthrose sévère",
        "modality": "Échographie + Contrôle IRM (Score MOAKS)",
        "intervention_type": "Radiofréquence Refroidie (Cooled RF) des Nerfs Géniculés",
        "cochin_link": "Directement lié aux séances de « test anesthésique sous écho + radiofréquence des nerfs géniculés pour gonarthrose » programmées à l'Hôpital Cochin.",
        "summary_fr_short": "Étude de cohorte (*Pain Management*, nov. 2026, 31 patients / 35 genoux, 91 % de gonarthrose sévère Kellgren-Lawrence 3–4) démontrant une baisse significative des douleurs (marche, repos, nuit) et une diminution de la synovite en IRM (Hoffa-synovitis / effusion-synovitis) sans aggravation des lésions osseuses sous-chondrales (BML) ni de l'arthrose à 3 mois.",
        "summary_fr_detailed": "Une préoccupation classique concernant la dénervation par radiofréquence refroidie (CRFA) des nerfs géniculés dans la gonarthrose sévère (KL 3–4) est le risque théorique d'arthropathie destructrice rapide ou d'aggravation des lésions médullaires osseuses sous-chondrales (BML) par perte du rétrocontrôle douloureux. Cette étude évalue 35 genoux (âge moyen 73,6 ans, 91 % KL 3–4) par scores cliniques (EVA, KOOS) et IRM quantitative (score MOAKS) avant et 3 mois après CRFA échoguidée. L'EVA à la marche diminue de 24 points (réduction ≥ 30 % chez 65,7 % et ≥ 50 % chez 42,9 % des genoux) et le score KOOS Douleur progresse de +12,8 points (p < 0,001). Surtout, l'IRM de contrôle démontre l'absence totale d'aggravation des BML, du grade KL ou de l'axe mécanique, et objective même une réduction des scores de synovite de Hoffa et d'épanchement-synovite.",
        "protocol_fr": "Repérage échographique des artères et nerfs géniculés supéro-médial (SMGN), supéro-latéral (SLGN) et inféro-médial (IMGN) au contact des corticales fémorales et tibiale • Test de stimulation sensitive et motrice de sécurité • Ablation par radiofréquence refroidie (Cooled RF, 60°C intra-électrode / ~80°C tissulaire pendant 150 s par cible) • Évaluation clinique (EVA, KOOS) et IRM (MOAKS : BML, synovite de Hoffa, épanchement).",
        "key_points_fr": [
            "Efficacité antalgique rapide dans les gonarthroses sévères KL 3–4 non opérables ou en attente de PTG (-24 points d'EVA à la marche, p < 0,05).",
            "Sécurité articulaire démontrée en IRM : aucune aggravation des œdèmes osseux sous-chondraux (BML), de l'interligne (KL) ni de l'alignement mécanique.",
            "Réduction concomitante des scores IRM de synovite de Hoffa et d'épanchement articulaire grâce à la reprise de la mobilité.",
            "Aucune complication grave observée sous guidage échographique strict."
        ],
        "tags": ["Nerfs géniculés", "Radiofréquence refroidie", "Gonarthrose", "IRM MOAKS", "Échoguidage", "Pain Manag 2026"]
    },
    "42731622": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Cryoablation percutanée des tumeurs desmoïdes extra-abdominales : résultats cliniques, survie sans progression et concordance volumétrique / mRECIST",
        "modality": "Scanner / IRM Interventionnelle",
        "intervention_type": "Cryoablation Percutanée de Tumeurs Desmoïdes Extra-Abdominales",
        "cochin_link": "Au cœur de l'activité de « cryothérapie percutanée de tumeur desmoïde (creux sus-claviculaire, flanc, paroi, membres) » du Service de Radiologie B à Cochin.",
        "summary_fr_short": "Étude de cohorte sur 92 séances de cryoablation chez 44 patients (*JVIR*, sept. 2026, taille médiane 6,9 cm, suivi médian 28,9 mois) rapportant 81,1 % de succès clinique, 78,4 % de réponse objective (24,3 % RC, 54,1 % RP), une concordance quasi parfaite entre volumétrie 3D et mRECIST (κ = 0,895), et seulement 5,3 % de complications majeures.",
        "summary_fr_detailed": "Sur une cohorte institutionnelle de 208 tumeurs desmoïdes extra-abdominales prises en charge entre 2020 et 2024, 44 patients (20,7 %) ont bénéficié de 92 procédures de cryoablation percutanée guidée par l'image pour des lésions volumineuses (taille médiane 6,9 cm, IQR 5,5–9,2 cm). Après un suivi médian de 28,9 mois, le taux de succès clinique composite (absence de progression, amélioration symptomatique et absence de traitement systémique/chirurgical) atteint 81,1 %. En imagerie, on observe 24,3 % de réponses complètes, 54,1 % de réponses partielles, 16,2 % de stabilisations et seulement 5,4 % de progressions. L'évaluation volumétrique 3D du tissu viable montre un accord quasi parfait avec la classification mRECIST (κ = 0,895). Les taux de survie sans progression à 1 an et 2 ans sont de 76,5 % et 67,4 %, avec une seconde séance de cryoablation efficace dans 26,3 % des cas.",
        "protocol_fr": "Planification IRM T1 Gado et T2 pour cartographier le volume charnu viable et les rapports vasculo-nerveux • Insertion multi-cryosondes sous guidage TDM/IRM avec marges de sécurité • Double cycle de congélation-décongélation sous contrôle continu de la boule de glace et neuroprotection/hydrodissection • Suivi IRM par critères mRECIST et volumétrie 3D du résidu rehaussé.",
        "key_points_fr": [
            "Taux de succès clinique de 81,1 % et contrôle de la maladie (RC + RP + stabilité) de 94,6 % sur des desmoïdes volumineuses (médiane 6,9 cm).",
            "Concordance quasi parfaite (κ = 0,895) entre les critères mRECIST et la volumétrie 3D sur l'IRM de suivi post-cryoablation.",
            "Possibilité de retraitement itératif par cryoablation (26,3 % des patients) en cas de reliquat ou récidive focale, évitant les chimiothérapies au long cours.",
            "Profil de sécurité très favorable avec seulement 5,3 % d'événements indésirables de grade SIR ≥ 3."
        ],
        "tags": ["Tumeur desmoïde", "Cryoablation", "mRECIST", "Volumétrie IRM", "Parties molles", "JVIR 2026"]
    },
    "42477120": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Traitement mini-invasif des kystes osseux anévrismaux (KOA) par technique Sclerograft modifiée en une séance (sclérothérapie doxycycline ± cryoablation + greffe régénérative)",
        "modality": "Fluoroscopie + Scanner Interventionnel",
        "intervention_type": "Sclérothérapie Doxycycline + Greffe Osseuse Percutanée (Sclerograft) ± Cryoablation",
        "cochin_link": "Complète directement les procédures d'« alcoolisation / sclérothérapie et comblement percutané de kyste osseux anévrismal (KOA) ou essentiel (KOE) » de l'Agenda Cochin.",
        "summary_fr_short": "Étude clinique du *CardioVascular and Interventional Radiology* (*CVIR*, juil. 2026, 27 patients, suivi médian 1,88 an) évaluant le protocole « Modified Sclerograft » (disruption mécanique des cloisons + sclérothérapie à la doxycycline ± cryoablation adjuvante + injection de substitut osseux régénératif), permettant une guérison en une seule séance chez 74,1 % des patients.",
        "summary_fr_detailed": "Le traitement percutané classique des kystes osseux anévrismaux (KOA) par sclérothérapie séquentielle (alcool, polidocanol ou doxycycline) nécessite habituellement 3 à 5 séances sous anesthésie générale. Cette étude évalue sur 27 KOA primitifs du squelette appendiculaire confirmés en IRM et biopsie une approche en séance unique (« Modified Sclerograft ») combinant : 1) disruption mécanique percutanée des logettes intrakystiques, 2) sclérothérapie chimique par mousse de doxycycline (± cryoablation adjuvante pour les formes agressives), et 3) comblement par substitut osseux régénératif injectable. Le nombre médian de procédures n'est que de 1 (moyenne 1,33), avec 74,1 % des patients guéris sans aucune réintervention (score de Neer modifié 1–2) et une ossification rapide permettant un suivi radiographique simple dans 92,6 % des cas.",
        "protocol_fr": "Abord percutané bi-trocart sous guidage fluoroscopique et TDM • Kystographie avec exclusion d'un drainage veineux rapide • Disruption mécanique endokystique des septas fibreux • Sclérothérapie chimique à la mousse de doxycycline (± cycle de cryoablation sur les parois charnues) • Comblement en fin de séance par greffon osseux régénératif injectable favorisant l'ostéoconduction.",
        "key_points_fr": [
            "Réduit drastiquement le nombre de séances d'anesthésie générale : médiane de 1 seule procédure (74,1 % de succès définitif après une unique séance).",
            "L'association disruption mécanique + sclérosant + substitut osseux ostéoconducteur accélère le remodelage cortical (Neer modifié grades 1–2).",
            "Possibilité d'associer une cryoablation percutanée ciblée sur les composantes charnues des KOA volumineux ou récidivants.",
            "Alternative mini-invasive très pertinente aux séances multiples d'alcoolisation ou au curetage chirurgical."
        ],
        "tags": ["Kyste osseux anévrismal", "Sclérothérapie", "Doxycycline", "Substitut osseux", "Cryoablation", "CVIR 2026"]
    },
    "42909541": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Cryoablation percutanée des tumeurs musculo-squelettiques : résultats cliniques, complications (classification CIRSE) et diminution de densité (UH) sur 48 patients",
        "modality": "Scanner Interventionnel",
        "intervention_type": "Cryoablation Percutanée de Tumeurs Osseuses, Cartilagineuses & Métastases",
        "cochin_link": "Au cœur de l'activité de « cryoablation percutanée sous scanner de tumeurs osseuses, cartilagineuses et de métastases » du Service de Radiologie B à Cochin.",
        "summary_fr_short": "Série monocentrique de référence (*Skeletal Radiology*, oct. 2026, équipe de R. Botchu, 48 patients) évaluant la cryoablation percutanée des tumeurs musculo-squelettiques (métastases, tumeurs cartilagineuses et tumeurs osseuses primitives/bénignes), avec 73 % de réponse clinique (58 % complète/bonne, 15 % partielle), une baisse de densité TDM (UH) dans 94 % des cas et aucune complication majeure CIRSE.",
        "summary_fr_detailed": "Cette étude rétrospective menée dans un centre tertiaire d'oncologie musculo-squelettique (Royal Orthopaedic Hospital, Birmingham) analyse 48 procédures consécutives de cryoablation percutanée réalisées par un radiologue interventionnel senior pour des métastases osseuses, des tumeurs cartilagineuses et des tumeurs osseuses bénignes ou primitives. Une réponse clinique complète ou bonne est obtenue chez 58 % des patients et une réponse partielle chez 15 % (soit 73 % d'efficacité globale). Sur le plan scannographique, une diminution de la densité en unités Hounsfield (UH) au sein de la zone traitée est observée chez 45 des 48 patients (94 %), traduisant la nécrose de liquéfaction cryogénique. Le taux global de complications (classification CIRSE) est faible (6,3 %, 3/48), sans aucune complication majeure ni séquelle permanente.",
        "protocol_fr": "Planification TDM/IRM pré-procédure • Insertion d'une ou plusieurs cryosondes sous guidage scanographique avec contrôle tridimensionnel de la boule de glace (« iceball ») englobant les marges tumorales • Double cycle de congélation-décongélation active/passive avec thermoprotection des structures nobles • Mesure comparative de l'atténuation TDM (UH) pré- et post-ablation et gradation des complications selon le référentiel CIRSE.",
        "key_points_fr": [
            "73 % de réponse clinique favorable (58 % complète/bonne, 15 % partielle) sur un large spectre de tumeurs osseuses, cartilagineuses et métastatiques.",
            "Chute de l'atténuation scannographique (UH) post-cryoablation constatée dans 94 % des lésions (45/48), marqueur quantitatif simple de nécrose.",
            "Excellent profil de sécurité avec 0 % de complication majeure selon la classification CIRSE (6,3 % de complications mineures transitoires).",
            "Confirme la reproductibilité et la sûreté de la cryoablation osseuse et des parties molles pratiquée quotidiennement au scanner à Cochin."
        ],
        "tags": ["Cryoablation", "Tumeurs musculo-squelettiques", "Métastases osseuses", "Unités Hounsfield", "Classification CIRSE", "Skeletal Radiol 2026"]
    },
    "42804145": {
        "category_id": "ect_mets",
        "title_fr": "Électrodes aiguilles bipolaires mono-aiguille pour l'électroporation et l'électrochimiothérapie (ECT) des tissus mous et osseux : conception et mise en œuvre guidée par l'image",
        "modality": "Scanner / Échographie Interventionnelle",
        "intervention_type": "Électrochimiothérapie (ECT) Osseuse & des Parties Molles par Aiguille Bipolaire",
        "cochin_link": "Directement lié aux procédures d'« électrochimiothérapie (ECT - Bléomycine IV) osseuse et épidurale sous guidage scanographique » réalisées au scanner Achard à Cochin.",
        "summary_fr_short": "Note technique multicentrique (*La Radiologia Medica*, sept. 2026, IF 8,9) détaillant l'architecture du champ électrique et l'implantation guidée par l'image d'électrodes aiguilles bipolaires mono-aiguille pour l'électrochimiothérapie (ECT) des tumeurs osseuses et des tissus mous, permettant de réduire le nombre d'insertions tout en confinant le champ électrique à distance des structures nerveuses.",
        "summary_fr_detailed": "L'électrochimiothérapie (ECT) osseuse et vertébrale conventionnelle requiert l'insertion rigoureusement parallèle de multiples aiguilles monopolaires pour couvrir le volume tumoral, ce qui est parfois complexe dans les corridors osseux étroits (pédicule, épidure, toit acétabulaire) ou les régions multi-opérées. Ce travail multicentrique présente les simulations de distribution de champ électrique, les validations précliniques et les applications cliniques guidées par l'image d'une électrode aiguille bipolaire unique (conception coaxiale à deux pôles sur le même axe). Cette géométrie mono-aiguille génère un champ électrique prévisible et spatialement confiné sans effet de dissipation thermique, évitant les insertions multiples et limitant la diffusion du courant aux structures neuro-vasculaires adjacentes.",
        "protocol_fr": "Guidage TDM ou échographique pour le positionnement d'une électrode aiguille bipolaire coaxiale au centre de la lésion cible (os ou parties molles) • Perfusion intraveineuse de bléomycine (15 000 UI/m²) • Délivrance des impulsions électriques calibrées entre le pôle distal et le pôle proximal de la même aiguille (fenêtre de perméabilisation 8 à 40 min post-injection) • Contrôle de couverture volumétrique par repositionnement axial si nécessaire.",
        "key_points_fr": [
            "L'architecture bipolaire mono-aiguille supprime la contrainte de parallélisme strict entre plusieurs électrodes monopolaires dans l'os.",
            "Confinement spatial optimal du champ électrique d'électroporation, idéal à proximité du fourreau dural, des racines nerveuses ou des gros vaisseaux.",
            "Mécanisme non thermique préservant la trame minérale osseuse et compatible avec une cimentoplastie ou un vissage consolidateur dans le même temps.",
            "Ouvre la voie à des procédures d'ECT mini-invasives simplifiées pour les métastases vertébrales, pelviennes et les récidives profondes."
        ],
        "tags": ["Électrochimiothérapie", "Électrode bipolaire", "Électroporation", "Métastases osseuses", "Bléomycine", "Radiol Med 2026"]
    },
    "42891691": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Prise en charge des fractures sacrées par insuffisance osseuse avec dissociation spino-pelvienne (types U et Rommens IVb) : place du vissage percutané",
        "modality": "Scanner Interventionnel / Fluoroscopie 3D (Scopie Allura)",
        "intervention_type": "Vissage Percutané Sacro-Iliaque / Trans-Sacré & Sacroplastie",
        "cochin_link": "En lien direct avec les « vissages percutanés du bassin et sacroplasties (Scanner / Scopie Allura) » pour fractures sacrées par insuffisance ou post-radiques à Cochin.",
        "summary_fr_short": "Revue systématique PRISMA-ScR (*Eur J Orthop Surg Traumatol*, oct. 2026, 8 études / 235 patients) consacrée aux fractures bilatérales postérieures du sacrum par insuffisance osseuse (fractures en H/U et Rommens IVb), confirmant que le vissage percutané est la technique de référence après échec du traitement médical pour restaurer la mobilité et soulager la douleur.",
        "summary_fr_detailed": "Les fractures par fragilité ou insuffisance osseuse du sacrum (ostéoporose sévère, antécédent de radiothérapie pelvienne) évoluent fréquemment vers une fracture bilatérale en U ou en H (Rommens type IVb) réalisant une dissociation spino-pelvienne très douloureuse et invalidante. Cette revue PRISMA-ScR portant sur 235 patients compare l'approche conservatrice et la fixation chirurgicale/interventionnelle. Le vissage percutané ilio-sacré ou trans-sacré (éventuellement cimenté) constitue la modalité technique la plus utilisée, généralement proposée devant l'échec de la verticalisation sous traitement antalgique. La fixation percutanée précoce permet une amélioration rapide de l'EVA douleur, une reprise précoce de l'appui et une réduction des complications de décubitus chez des patients âgés ou oncologiques fragiles.",
        "protocol_fr": "Analyse TDM multi-planaire des corridors sacrés S1 et S2 (recherche d'un dysmorphisme sacré et du trait transversal en U/H) • Sous guidage scanographique ou fluoroscopique (vues inlet, outlet et profil sacré strict), mise en place percutanée de vis canulées ilio-sacrées ou trans-sacrées S1 ± S2 • Cimentoplastie/sacroplastie d'augmentation autour des spires en os porotique ou post-radique.",
        "key_points_fr": [
            "Les fractures sacrées bilatérales par insuffisance (Rommens IVb / en U) entraînent une instabilité spino-pelvienne souvent rebelle au repos médical.",
            "Le vissage percutané ilio-sacré / trans-sacré est la technique mini-invasive de référence pour rétablir la continuité mécanique spino-pelvienne.",
            "Une intervention précoce en cas d'impossibilité de mise en charge accélère la récupération fonctionnelle et l'autonomie.",
            "En os très déminéralisé ou irradié, l'augmentation cimentée (vissage cimenté au scanner ou sous scopie Allura) prévient le desserrement mécanique."
        ],
        "tags": ["Fracture du sacrum", "Dissociation spino-pelvienne", "Vissage percutané", "Sacroplastie", "Insuffisance osseuse", "Eur J Orthop Surg Traumatol 2026"]
    },
    "42874309": {
        "category_id": "msk_biopsy",
        "title_fr": "Précision diagnostique de la biopsie percutanée au trocart (CNB) pour déterminer le grade histologique définitif des tumeurs cartilagineuses malignes (chondrosarcomes)",
        "modality": "Scanner Interventionnel",
        "intervention_type": "Biopsie Osseuse Percutanée Scanoguidée de Tumeur Chondroïde",
        "cochin_link": "Directement applicable aux « biopsies osseuses percutanées sous scanner de lésions cartilagineuses (bassin, fémur, humérus, scapula) » discutées en RCP Sarcome à Cochin.",
        "summary_fr_short": "Étude rétrospective sur 111 chondrosarcomes opérés (*European Journal of Surgical Oncology*, oct. 2026) évaluant la concordance de grade entre la biopsie percutanée préopératoire au trocart (CNB) et la pièce de résection : concordance parfaite (100 %) pour les chondrosarcomes dédifférenciés, mais risque élevé de sous-évaluation dans les grades G1–G2 (concordance globale 48 %), imposant un ciblage biopsique guidé par l'IRM sur les zones d'ostéolyse ou d'envahissement des parties molles.",
        "summary_fr_detailed": "La fiabilité de la biopsie osseuse au trocart (Core Needle Biopsy, CNB) pour grader les tumeurs cartilagineuses malignes est un enjeu majeur en RCP Sarcome en raison de l'hétérogénéité spatiale intratumorale. Sur 111 patients opérés d'un chondrosarcome après biopsie percutanée lue par des pathologistes spécialisés, la concordance exacte du grade histologique entre biopsie et pièce opératoire est de 48 % (53/111), avec 100 % de concordance (10/10) pour les chondrosarcomes dédifférenciés, contre 46 % pour les G1 et 41,4 % pour les G2. La concordance varie également selon le site anatomique (scapula κ = 0,60, fémur distal κ = 0,50, bassin κ = 0,30, fémur proximal κ = 0,10, humérus proximal κ = 0). L'étude démontre que le risque principal est la sous-estimation du grade (undergrading) dans les lésions périphériques ou G1–G2, d'où la nécessité absolue de cibler sous scanner la zone la moins minéralisée, d'encoche endostée active ou d'extension extra-osseuse identifiée sur l'IRM.",
        "protocol_fr": "Relecture conjointe TDM + IRM multiparamétrique avant biopsie pour repérer le contingent non calcifié, myxoïde, hypervasculaire ou de rupture corticale • Biopsie osseuse scanoguidée au trocart de gros calibre (8G–11G) sur le trajet de la voie d'abord chirurgicale validée avec l'orthopédiste • Prélèvements multiples échantillonnant à la fois le contingent cartilagineux hyalin et toute zone ostéolytique ou charnue suspecte de haut grade / dédifférenciation.",
        "key_points_fr": [
            "Excellente sensibilité (100 %, 10/10) de la biopsie percutanée lorsque le prélèvement cible le contingent non cartilagineux d'un chondrosarcome dédifférencié.",
            "Risque significatif de sous-estimation du grade (undergrading) entre ACT/G1 et chondrosarcome G2–G3 en raison de l'hétérogénéité tumorale (concordance de 48 %).",
            "La décision thérapeutique (curetage vs résection carcinologique) ne doit jamais reposer sur la seule biopsie G1 sans confrontation radio-clinique et IRM.",
            "Dans le bassin, le fémur proximal et l'humérus proximal, réaliser des carottes multiples ciblant les zones d'ostéolyse endostée et de prise de contraste précoce."
        ],
        "tags": ["Chondrosarcome", "Tumeur cartilagineuse", "Biopsie osseuse", "Grade histologique", "RCP Sarcome", "Eur J Surg Oncol 2026"]
    },
    "42742682": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Sélection et protocole des anesthésiques locaux lors de l'ablation par radiofréquence (RFA) rachidienne et des grandes articulations : guide pratique pour le radiologue ostéo-articulaire",
        "modality": "Scanner / Fluoroscopie / Échographie Interventionnelle",
        "intervention_type": "Radiofréquence Nerveuse Articulaire (Géniculés, Hanche, SI) & Rachidienne",
        "cochin_link": "Guide directement le protocole pharmacologique des « tests anesthésiques et radiofréquences des nerfs géniculés, articulaires postérieurs et sacro-iliaques » à Cochin.",
        "summary_fr_short": "Mise au point pratique (*Skeletal Radiology*, sept. 2026) définissant le choix, la concentration et le séquençage des anesthésiques locaux lors des procédures de radiofréquence (RFA) rachidienne (branches médiales), sacro-iliaque et des grandes articulations périphériques (genou, hanche, épaule) afin de préserver la fiabilité des tests de stimulation motrice/sensitive et d'optimiser l'analgésie.",
        "summary_fr_detailed": "Lors des procédures de neurolyse par radiofréquence (nerfs géniculés du genou, branches articulaires de hanche, rameaux médiaux rachidiens et branches latérales sacro-iliaques), l'administration d'anesthésique local (AL) sur le trajet de ponction puis en périneural conditionne à la fois le confort du patient et la validité du test de stimulation neurophysiologique. Cette revue de *Skeletal Radiology* établit que : 1) la lidocaïne à 1 % est le standard pour l'anesthésie cutanée et du trajet superficiel ; 2) il faut éviter d'injecter de la lidocaïne à 2 % au contact immédiat du nerf cible avant les tests de stimulation sensitive et motrice pour ne pas abolir la réponse d'alerte motrice ; 3) avant le cycle de thermo-ablation, la bupivacaïne 0,25 % ou la ropivacaïne 0,2 % (préférable en cas de procédure multi-étagée ou de trouble conductif cardiaque) offre la meilleure analgésie post-procédure, sans aucun bénéfice démontré au mélange lidocaïne + bupivacaïne.",
        "protocol_fr": "Anesthésie cutanée et du trajet superficiel à la lidocaïne 1 % en restant à distance du nerf cible • Positionnement de la canule de radiofréquence sous guidage écho/scopie/TDM • Réalisation des tests de stimulation sensitive (50 Hz) et motrice (2 Hz) avant toute infiltration périneurale profonde • Injection périneurale pré-lésionnelle de 0,5 à 1 mL de ropivacaïne 0,2 % (ou bupivacaïne 0,25 %) 60 à 90 secondes avant le cycle thermique.",
        "key_points_fr": [
            "Ne jamais infiltrer le nerf cible (surtout à la lidocaïne 2 %) avant d'avoir effectué les tests de stimulation sensitive (50 Hz) et motrice (2 Hz).",
            "Le mélange empirique lidocaïne + bupivacaïne n'accélère pas le délai d'action par rapport à l'anesthésique seul et réduit la durée d'analgésie prolongée.",
            "Privilégier la ropivacaïne 0,2 % (profil cardiotoxique plus sûr) lors des dénervations multi-sites (3 nerfs géniculés ou branches sacro-iliaques).",
            "Fournit un algorithme structuré de substitution en cas d'allergie documentée aux amino-amides."
        ],
        "tags": ["Radiofréquence nerveuse", "Anesthésiques locaux", "Ropivacaïne", "Nerfs géniculés", "Stimulation motrice", "Skeletal Radiol 2026"]
    },
    "42947096": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Analyse de l'activité d'une RCP Métastases Osseuses en CHU (AP-HP Pitié-Salpêtrière) sur 630 patients : profils cliniques, facteurs pronostiques et place centrale de la cimentoplastie",
        "modality": "Scanner / Fluoroscopie Interventionnelle & Concertation Pluridisciplinaire (RCP)",
        "intervention_type": "Cimentoplastie Vertébrale / Pelvienne & Stratégie Pluridisciplinaire Osseuse",
        "cochin_link": "Miroir direct de l'activité parisienne AP-HP de « cimentoplastie vertébrale/pelvienne et vissage percutané discutés en RCP Métastases Osseuses » à l'Hôpital Cochin.",
        "summary_fr_short": "Étude rétrospective de l'équipe AP-HP Pitié-Salpêtrière (*World Journal of Surgical Oncology*, août 2026, 992 dossiers / 630 patients) analysant l'activité d'une RCP Métastases Osseuses universitaire : atteinte rachidienne dans 85 % et pelvienne dans 51 % des cas, avec recours à la cimentoplastie percutanée chez 39 % des patients (contre 22 % de chirurgie).",
        "summary_fr_detailed": "Cette série française de l'AP-HP analyse 992 présentations consécutives en Réunion de Concertation Pluridisciplinaire (RCP) dédiée aux métastases osseuses chez 630 patients. Les primitifs les plus fréquents sont bronchopulmonaires, mammaires, myélomateux, prostatiques et thyroïdiens, avec 85 % de localisations rachidiennes et 51 % de localisations pelviennes. Les décisions thérapeutiques illustrent le virage mini-invasif contemporain : radiothérapie dans 49 % des cas, cimentoplastie percutanée dans 39 % des cas et chirurgie ouverte dans seulement 22 % des cas. Alors que 37 % des patients opérés décèdent dans les 6 mois post-opératoires (survie globale médiane de 17 mois), la cimentoplastie offre une consolidation antalgique immédiate sans retarder les traitements systémiques.",
        "protocol_fr": "Évaluation systématique en RCP Métastases Osseuses (score SINS rachidien, classification de Harrington/mirels pelvienne, pronostic oncologique selon le primitif) • Cimentoplastie percutanée vertébrale ou acétabulaire/sacrée sous guidage TDM et fluoroscopique seule ou couplée à la radiothérapie stéréotaxique/antalgique • Réservation de la chirurgie lourde aux compressions médullaires aiguës ou instabilités non accessibles au vissage/cimentoplastie.",
        "key_points_fr": [
            "La cimentoplastie percutanée est indiquée chez 39 % des patients présentés en RCP Métastases Osseuses en CHU (contre 22 % pour la chirurgie).",
            "85 % des patients présentent une atteinte rachidienne et 51 % une atteinte du bassin, cibles privilégiées de la radiologie interventionnelle ostéo-articulaire.",
            "37 % des patients opérés décédant dans les 6 mois, l'approche percutanée (cimentoplastie ± vissage) évite une morbidité chirurgicale disproportionnée.",
            "Données françaises AP-HP directement transposables au flux de patients oncologiques pris en charge en HDJ et au scanner à Cochin."
        ],
        "tags": ["Métastases osseuses", "Cimentoplastie", "RCP", "Rachis", "Bassin", "World J Surg Oncol 2026"]
    },
    "42785703": {
        "category_id": "ect_mets",
        "title_fr": "Oncologie interventionnelle rachidienne : revue illustrée des techniques mini-invasives (électrochimiothérapie épidurale, cimentoplastie cervicale, vissage odontoidien/sacré et thermo-ablation)",
        "modality": "Scanner Interventionnel / Angiographie Biplan / Cône-Beam CT",
        "intervention_type": "Électrochimiothérapie (ECT) Épidurale, Thermo-Ablation, Cimentoplastie Cervicale & Vissage",
        "cochin_link": "En lien direct avec les procédures complexes d'« électrochimiothérapie (ECT) rachidienne/épidurale, cimentoplastie cervicale et vissage pelvi-sacré » réalisées à Cochin.",
        "summary_fr_short": "Mise au point illustrée française (*Neurochirurgie*, sept. 2026, équipes Pitié-Salpêtrière & Rouen) synthétisant l'arsenal d'oncologie interventionnelle rachidienne : biopsie radioguidée, cimentoplastie des étages complexes (rachis cervical), fixation percutanée (odontoïde, sacrum, bassin), embolisation préopératoire, ablation thermique et électrochimiothérapie (ECT) en présence d'une épidurite.",
        "summary_fr_detailed": "Rédigée par des équipes françaises de radiologie interventionnelle ostéo-articulaire et neuroradiologique, cette revue détaille l'intégration complémentaire des gestes percutanés dans les métastases et tumeurs primitives du rachis. Au-delà de la vertébroplastie thoraco-lombaire standard, l'article précise les règles techniques et de sécurité pour les localisations à haut risque : cimentoplastie cervicale (abord antéro-latéral ou trans-oral), vissage percutané de l'odontoïde et des fractures-lyses sacro-pelviennes, thermo-ablation (RF/cryoablation sous thermoprotection épidurale et monitorage radiculaire) et électrochimiothérapie (ECT) à la bléomycine qui permet de traiter les extensions épidurales au contact du cordon médullaire sans risque de lésion thermique.",
        "protocol_fr": "Bilan pré-thérapeutique IRM + TDM (bilan de la corticale postérieure, de l'extension épidurale Bilsky et repérage de l'artère d'Adamkiewicz si nécessaire) • Choix personnalisé : thermo-ablation (RF/cryo) + cimentoplastie pour les lésions intracorporelles, ou électrochimiothérapie (ECT) non thermique en cas d'envahissement épidural ou radiculaire • Combinaison au vissage percutané en cas d'instabilité mécanique (SINS ≥ 7).",
        "key_points_fr": [
            "L'électrochimiothérapie (ECT) constitue l'alternative de choix à l'ablation thermique lorsqu'une coulée tumorale épidurale jouxte la moelle ou les racines.",
            "Détaille les corridors de sécurité pour la cimentoplastie cervicale, le vissage de l'odontoïde et la fixation spino-pelvienne percutanée.",
            "Insiste sur les stratégies de neuroprotection (dissection épidurale au CO2/sérum glucosé, thermométrie et monitorage neurophysiologique).",
            "Synthèse française de référence alignée sur l'intégralité du plateau technique interventionnel ostéo-articulaire de l'Hôpital Cochin."
        ],
        "tags": ["Oncologie interventionnelle rachidienne", "Électrochimiothérapie", "Cimentoplastie cervicale", "Vissage percutané", "Épidurite métastatique", "Neurochirurgie 2026"]
    },
    "42955458": {
        "category_id": "msk_imaging",
        "title_fr": "Rôle actuel de la radiomique IRM dans la prise en charge des sarcomes des tissus mous : diagnostic de grade, prédiction et évaluation de la réponse thérapeutique",
        "modality": "IRM Multiparamétrique & Analyse Radiomique Quantitative",
        "intervention_type": "Caractérisation IRM Pré-Biopsique & Évaluation de Réponse des Sarcomes",
        "cochin_link": "Complète les bilans d'« IRM diagnostique, ciblage biopsique et suivi post-thérapeutique des sarcomes des parties molles » en centre de référence Sarcome à Cochin.",
        "summary_fr_short": "Revue de synthèse (*Current Treatment Options in Oncology*, oct. 2026, IF 4,1) faisant le point sur l'apport des biomarqueurs radiomiques extraits de l'IRM conventionnelle dans les sarcomes des tissus mous : discrimination bas grade vs haut grade avant biopsie, prédiction précoce de la nécrose post-traitement néoadjuvant et stratification pronostique du risque métastatique.",
        "summary_fr_detailed": "Les sarcomes des tissus mous (STS) présentent une forte hétérogénéité spatiale qui limite parfois l'analyse sémantique visuelle de l'IRM et expose au risque d'échantillonnage incomplet lors de la biopsie percutanée. Cette revue synthétise les performances cliniques des modèles radiomiques IRM (séquences T1, T2 Fat-Sat, DWI/ADC et T1 injecté) pour : 1) différencier les lésions bénignes (lipomes, fasciites, schwannomes) des sarcomes et distinguer les grades FNCLCC G1 vs G2/G3 ; 2) cartographier les sous-régions intratumorales (« habitats ») les plus agressives afin de guider la microbiopsie percutanée ; et 3) prédire la réponse histopathologique (nécrose > 90 %) aux traitements néoadjuvants mieux que les seuls critères dimensionnels RECIST.",
        "protocol_fr": "Acquisition IRM multiparamétrique standardisée (T1, T2 FS/STIR, diffusion multi-b avec ADC et perfusion/T1 Gado) • Analyse de l'hétérogénéité de texture intratumorale et de la zone périlésionnelle pour identifier le contingent de plus haut grade • Ciblage de la biopsie percutanée sur l'habitat hypercellulaire/hypervasculaire et suivi longitudinal post-thérapeutique multiparamétrique.",
        "key_points_fr": [
            "L'analyse quantitative de l'hétérogénéité IRM distingue avec une haute précision les sarcomes de haut grade (FNCLCC G2–G3) des tumeurs de bas grade.",
            "Permet d'orienter la biopsie percutanée vers le sous-volume tumoral (« habitat ») biologiquement le plus agressif.",
            "Surpasse les critères morphologiques RECIST 1.1 pour évaluer la nécrose tumorale réelle après traitement néoadjuvant ou ablation.",
            "Renforce la valeur ajoutée de l'expertise IRM ostéo-articulaire de Cochin au sein de la RCP Sarcome."
        ],
        "tags": ["Sarcome des tissus mous", "IRM multiparamétrique", "Radiomique", "Réponse thérapeutique", "Grade FNCLCC", "Curr Treat Options Oncol 2026"]
    },
    "42234093": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Mesure in vivo de la pression intra-osseuse des lésions kystiques osseuses (KOA / KOE) sous guidage scanographique et comparaison à la moelle normale",
        "modality": "Scanner Interventionnel + Manométrie Intra-Osseuse",
        "intervention_type": "Sclérothérapie Percutanée Scanoguidée de Kyste Osseux (KOA / KOE)",
        "cochin_link": "Directement lié aux procédures d'« alcoolisation / sclérothérapie percutanée sous scanner de kyste osseux anévrismal (KOA) et essentiel (KOE) » réalisées à Cochin.",
        "summary_fr_short": "Étude prospective du Massachusetts General Hospital (*Skeletal Radiology*, juin/oct. 2026, équipe de C.Y. Chang) mesurant in vivo la pression intra-osseuse par le trocart de ponction lors des sclérothérapies scanoguidées de kystes osseux : mise en évidence d'une hyperpression systolique intrakystique significative (90 ± 18 mmHg vs 67 ± 23 mmHg dans la moelle normale, p = 0,01) indépendante de la pression artérielle systémique.",
        "summary_fr_detailed": "La physiopathologie de l'expansion corticale et du risque d'extravasation lors de la sclérothérapie des kystes osseux anévrismaux (KOA) et essentiels (KOE) repose sur un régime d'hyperpression intralésionnelle jusqu'ici peu quantifié chez l'adulte et l'adolescent. Dans cette étude prospective portant sur 52 patients (lésions kystiques osseuses adressées pour sclérothérapie TDM vs moelle osseuse normale), la pression intra-osseuse a été enregistrée pendant 5 minutes via un capteur artériel fermé connecté au trocart osseux. La pression systolique intrakystique est significativement plus élevée dans les kystes osseux que dans la moelle normale (90 ± 18 mmHg contre 67 ± 23 mmHg, p = 0,01), alors même que la pression artérielle systémique moyenne des patients jeunes porteurs de kystes est plus basse (80 vs 93 mmHg), confirmant l'autonomie hémodynamique du compartiment kystique.",
        "protocol_fr": "Mise en place sous guidage TDM d'un trocart osseux dans la cavité kystique • Mesure/décompression initiale de l'hyperpression intrakystique (systolique moyenne ~90 mmHg) et réalisation systématique d'une technique à double aiguille (une aiguille d'injection et une aiguille de décompression/ventilation) lors de l'injection du produit de contraste et de l'agent sclérosant (alcool absolu, polidocanol ou doxycycline) pour prévenir toute surpression et fuite veineuse.",
        "key_points_fr": [
            "Démontre in vivo une hyperpression systolique élevée (90 ± 18 mmHg) au sein des lésions kystiques osseuses par rapport à la moelle normale (67 mmHg).",
            "La pression intrakystique est indépendante de la pression artérielle systémique (p > 0,35), traduisant un mécanisme hémodynamique local propre.",
            "Justifie physiologiquement le recours au montage à double trocart (décompression/drainage) lors des alcoolisations et sclérothérapies à Cochin.",
            "Réduit le risque d'extravasation veineuse ou péri-osseuse de l'agent sclérosant en évitant toute surpression lors de l'injection."
        ],
        "tags": ["Kyste osseux anévrismal", "Kyste osseux essentiel", "Pression intra-osseuse", "Sclérothérapie", "Scanner interventionnel", "Skeletal Radiol 2026"]
    },
    "42671500": {
        "category_id": "ablation_benign",
        "title_fr": "Ciblage assisté par robotique pour le traitement percutané de l'ostéome ostéoïde : revue systématique sur 440 procédures",
        "modality": "Scanner Interventionnel / Guidage Robotique & Navigation 3D",
        "intervention_type": "Thermo-Ablation Percutanée (RF / Cryoablation) d'Ostéome Ostéoïde",
        "cochin_link": "Complète la réflexion technique sur le « guidage TDM de haute précision pour radiofréquence et cryoablation d'ostéome ostéoïde (rachis, col fémoral, talus) » à Cochin.",
        "summary_fr_short": "Revue systématique (*Journal of Robotic Surgery*, août 2026, 12 études / 440 procédures dont 232 assistées par robot) évaluant l'apport du positionnement robotique lors du forage et de l'ablation thermique des ostéomes ostéoïdes : réduction du nombre de repositionnements de broche et fenêtres osseuses plus économiques, avec une efficacité clinique et une sécurité équivalentes au guidage TDM expert à main levée.",
        "summary_fr_detailed": "L'accès millimétrique au nidus de l'ostéome ostéoïde (notamment dans les localisations profondes, péri-articulaires ou rachidiennes proches des structures nerveuses) conditionne le succès de la radiofréquence ou de la cryoablation. Cette revue systématique analyse 440 cas traités (dont 232 avec assistance robotique contraignant la trajectoire du trocart). Le guidage robotique réduit le nombre de corrections d'angle de la broche de Kirschner et raccourcit le temps de ciblage balistique initial. En revanche, à modalité d'ablation thermique constante (RFA ou cryoablation), les taux de succès clinique définitif, de récidive et de complications ne diffèrent pas significativement d'un guidage scanographique conventionnel réalisé par un opérateur entraîné.",
        "protocol_fr": "Acquisition TDM en coupes fines millimétriques centrée sur le nidus calcifié ou hypodense • Planification 3D de la trajectoire trans-corticale optimale évitant les pédicules vasculo-nerveux et le cartilage articulaire • Forage coaxial (11G–14G) jusqu'au centre du nidus (avec approche no-touch en cryoablation pour les localisations superficielles ou juxta-articulaires) • Thermo-ablation RF (90°C pendant 6 min) ou cryoablation.",
        "key_points_fr": [
            "Sur 440 procédures analysées, le facteur déterminant du succès reste l'ablation thermique complète du nidus plutôt que le recours à un bras robotique.",
            "L'assistance balistique diminue le nombre de réorientations d'aiguille dans les trajectoires obliques complexes (bassin, rachis, col fémoral).",
            "Les taux de guérison clinique (> 90–95 %) et de complications demeurent identiques au guidage TDM à main levée pratiqué en centre expert.",
            "Confirme l'excellence du standard actuel par thermo-ablation scanoguidée directe (RF ou cryoablation no-touch) réalisé à Cochin."
        ],
        "tags": ["Ostéome ostéoïde", "Radiofréquence", "Guidage scanographique", "Robotique interventionnelle", "Nidus", "J Robot Surg 2026"]
    },
    "42995280": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Évolution du rôle de la cryoablation tumorale et de la cryoneurolyse périphérique dans la prise en charge interventionnelle de la douleur (oncologique et non oncologique)",
        "modality": "Scanner / Échographie / IRM Interventionnelle",
        "intervention_type": "Cryoneurolyse Périphérique & Cryoablation Antalgique / Curative",
        "cochin_link": "Synthèse européenne de référence (*European Radiology*, D. Filippiadis et al.) couvrant les « cryoneurolyses (Morton, intercostal, clunéal) et cryoablations osseuses/parties molles » de l'Agenda Cochin.",
        "summary_fr_short": "Mise au point de référence publiée dans *European Radiology* (nov. 2026, IF 4,7, équipe de D. Filippiadis) structurant les indications, le mécanisme d'axonotmésis réversible (classification de Sunderland II) et les protocoles de cryoablation tumorale (ostéome ostéoïde, métastases osseuses, tumeurs des parties molles) et de cryoneurolyse périphérique (nerfs intercostaux, clunéaux, géniculés, névrome de Morton).",
        "summary_fr_detailed": "Rédigée par les experts européens du comité CIRSE (D.M. Düx, D. Filippiadis, F. Wacker, K.I. Ringe), cette revue distingue et articule les deux piliers de la cryothérapie interventionnelle : 1) la cryoablation tissulaire (destruction tumorale par cycles de congélation-décongélation à -40°C des tumeurs osseuses bénignes comme l'ostéome ostéoïde, des métastases osseuses et des tumeurs des parties molles à visée curative ou palliative) ; et 2) la cryoneurolyse sélective des nerfs périphériques ou sympathiques (températures de -20°C à -60°C induisant une dégénérescence wallérienne réversible avec préservation de l'endonèvre et du périnèvre, évitant tout névrome de désafférentation). Chez le patient non oncologique, l'indication de cryoneurolyse repose sur la positivité préalable d'un bloc nerveux diagnostique ciblé.",
        "protocol_fr": "En pathologie tumorale : cryoablation directe sous TDM/IRM avec visualisation temps réel de l'iceball couvrant l'interface os-tumeur et thermoprotection (hydro/carbodissection) • En douleur neuropathique ou articulaire non oncologique : bloc test anesthésique diagnostique préalable sous écho/scanner, puis cryoneurolyse ciblée (2 cycles de congélation de 2 à 3 min séparés par une décongélation passive) au contact du nerf responsable.",
        "key_points_fr": [
            "Clarifie l'algorithme décisionnel entre cryoablation de la lésion cible (tumeur osseuse ou des parties molles accessible) et cryoneurolyse du nerf afférent.",
            "La cryoneurolyse induit une axonotmésis (Sunderland II) préservant la gaine conjonctive endoneurale, permettant une régénération axonale sans névrome secondaire.",
            "Valide le prérequis d'un bloc diagnostique positif avant cryoneurolyse dans les douleurs non oncologiques (nerfs géniculés, clunéaux, intercostaux, inguinaux).",
            "Souligne l'avantage décisif de la visualisation directe de la boule de glace au scanner ou en IRM par rapport aux techniques thermiques par le chaud."
        ],
        "tags": ["Cryoneurolyse", "Cryoablation", "Douleur interventionnelle", "Filippiadis", "Métastases osseuses", "Eur Radiol 2026"]
    },
    "42997935": {
        "category_id": "msk_imaging",
        "title_fr": "IRM de perfusion dynamique (DCE-MRI) et diffusion IVIM à 3T pour caractériser l'angiogenèse des sarcomes des tissus mous : étude de co-alignement radio-histologique",
        "modality": "IRM 3T Multiparamétrique (DCE-MRI Perfusion + Diffusion IVIM)",
        "intervention_type": "Cartographie IRM de l'Angiogenèse & Ciblage Biopsique des Sarcomes",
        "cochin_link": "Directement applicable aux « bilans IRM 3T pré-biopsiques et au ciblage des zones hypervasculaires viables des sarcomes des parties molles » en RCP Sarcome à Cochin.",
        "summary_fr_short": "Étude prospective sur 70 sarcomes des tissus mous en IRM 3T (*Quantitative Imaging in Medicine and Surgery*, nov. 2026) avec co-alignement spatial coupe-à-coupe IRM/anatomopathologie, démontrant que les paramètres Ktrans (DCE-MRI) et D* (IVIM) corrèlent fortement avec l'expression de VEGF et la densité microvasculaire (MVD) avec une AUC de 0,86.",
        "summary_fr_detailed": "L'évaluation non invasive de la néo-angiogenèse tumorale au sein des sarcomes des tissus mous (STS) est cruciale pour guider la biopsie percutanée hors des zones nécrotiques et évaluer la réponse aux thérapies ciblées ou anti-angiogéniques. Sur 70 patients explorés en IRM 3T (séquences de perfusion dynamique T1 DCE-MRI et diffusion bi-exponentielle IVIM) avec protocole de recalage spatial strict entre coupes IRM et lames histologiques, les paramètres de transfert vasculaire Ktrans (r = 0,673), Kep (r = 0,573), le coefficient de pseudo-diffusion D* (r = 0,692) et la fraction de perfusion f corrèlent significativement avec l'expression immunohistochimique du VEGF et la densité microvasculaire (MVD). Ktrans (AUC = 0,861) et D* (AUC = 0,860) constituent deux biomarqueurs indépendants majeurs de l'hypervascularisation sarcomateuse.",
        "protocol_fr": "IRM 3T pré-biopsique combinant : 1) séquence de diffusion IVIM multi-b (séparation de la diffusion moléculaire pure D et de la micro-perfusion capillaire D* et f sans injection) ; 2) séquence de perfusion dynamique T1 après injection de gadolinium (calcul des cartes paramétriques Ktrans, Kep et Ve) • Ciblage de la microbiopsie percutanée sur le « hot-spot » présentant le Ktrans et le D* les plus élevés.",
        "key_points_fr": [
            "Corrélation radio-histologique coupe-à-coupe démontrant que Ktrans (DCE-MRI) et D* (IVIM) reflètent fidèlement l'expression de VEGF et la densité microvasculaire.",
            "Excellente performance diagnostique de Ktrans (AUC 0,861) et D* (AUC 0,860) pour identifier les contingents sarcomateux fortement angiogéniques.",
            "La séquence IVIM permet d'estimer la fraction de perfusion microvasculaire (D*, f) même chez les patients insuffisants rénaux ne pouvant recevoir de gadolinium.",
            "Optimise le rendement de la microbiopsie percutanée à Cochin en guidant le trocart vers le foyer tumoral biologiquement le plus actif."
        ],
        "tags": ["Sarcome des tissus mous", "DCE-MRI", "Diffusion IVIM", "Angiogenèse", "Concordance IRM-histologie", "Quant Imaging Med Surg 2026"]
    },
    "42997475": {
        "category_id": "msk_biopsy",
        "title_fr": "Imagerie multimodale, intelligence artificielle et limites de la biopsie au trocart (CNB) dans le diagnostic des tumeurs osseuses : analyse critique de la concordance biopsie-résection",
        "modality": "Scanner / IRM / TEP-TDM & Biopsie Osseuse Percutanée",
        "intervention_type": "Biopsie Osseuse Percutanée & Concordance Radio-Pathologique (RCP Sarcome)",
        "cochin_link": "Éclaire directement l'interprétation des « biopsies osseuses percutanées sous scanner (notamment du bassin et des os longs) » discutées en RCP Sarcome à Cochin.",
        "summary_fr_short": "Revue critique publiée dans le *Journal of Bone Oncology* (oct./déc. 2026, IF 3,4) démontrant que la limite principale des modèles diagnostiques en oncologie osseuse réside dans la variabilité du standard histologique : la concordance de grade entre biopsie au trocart (CNB) et pièce opératoire dans les chondrosarcomes centraux chute de κ = 0,63 sur les os longs à κ = 0,12 dans le bassin.",
        "summary_fr_detailed": "Cette mise au point du *Journal of Bone Oncology* analyse l'intégration de l'imagerie multimodale (radiographie, TDM pour l'analyse corticale et matricielle, IRM pour l'extension médullaire et des parties molles, TEP-TDM pour le métabolisme) et de la biopsie osseuse au trocart (Core Needle Biopsy). Les auteurs démontrent chiffres à l'appui que la biopsie percutanée isolée ne peut constituer un gold standard absolu sans confrontation à l'imagerie en raison de quatre facteurs : 1) l'erreur d'échantillonnage spatial sur les tumeurs volumineuses (dans les chondrosarcomes centraux, la concordance pondérée κ entre biopsie et résection tombe de 0,63 dans les os longs à seulement 0,12 dans le bassin) ; 2) la variabilité inter-observateur entre pathologistes experts (κ = 0,44) et radiologues (κ = 0,35) ; 3) l'évolution des critères moléculaires OMS ; et 4) la dissociation possible entre aspect histologique focal et agressivité clinique.",
        "protocol_fr": "Synthèse pré-biopsique obligatoire TDM + IRM (+ TEP-TDM si lésion pelvienne volumineuse) pour cibler le secteur le plus suspect • Dans les tumeurs osseuses du bassin (où la concordance d'un prélèvement unique tombe à κ = 0,12), réalisation de prélèvements multi-sites divergents au trocart osseux 8G–11G sous guidage TDM • Décision thérapeutique fondée sur un standard composite (radio-histo-moléculaire et évolutif) en RCP Sarcome.",
        "key_points_fr": [
            "Dans les tumeurs cartilagineuses centrales du bassin, la concordance de grade entre biopsie au trocart et résection chute à κ = 0,12 (contre κ = 0,63 sur les os longs).",
            "Une biopsie osseuse rassurante (bas grade) sur une lésion pelvienne lytique ou agressivement rehaussée en IRM ne doit jamais faire récuser un haut grade sans relecture.",
            "Justifie la réalisation de carottes multiples dans des cadrans distincts lors des biopsies osseuses scanoguidées du bassin à Cochin.",
            "Plaide pour l'adoption systématique d'un gold standard composite associant imagerie multimodale, histologie et biologie moléculaire en RCP."
        ],
        "tags": ["Tumeurs osseuses", "Biopsie osseuse", "Chondrosarcome du bassin", "Imagerie multimodale", "RCP Sarcome", "J Bone Oncol 2026"]
    },
    "42782915": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Ablation thermique percutanée (radiofréquence et cryoablation) des chordomes rachidiens et sacrés : revue systématique sur 34 lésions et protocole pré-spondylectomie combiné à la vertébroplastie",
        "modality": "Scanner Interventionnel + Fluoroscopie",
        "intervention_type": "Radiofréquence / Cryoablation & Cimentoplastie de Chordome Rachidien / Sacré",
        "cochin_link": "En lien direct avec les procédures d'« ablation thermique percutanée (cryoablation / RF) et cimentoplastie des tumeurs rachidiennes et sacrées » réalisées à Cochin.",
        "summary_fr_short": "Revue systématique (*Current Oncology*, sept. 2026, 13 études / 33 patients / 34 sites de chordomes rachidiens ou sacrés traités par cryoablation [n=21] ou radiofréquence [n=11]) et cas illustratif de chordome L4 traité par RFA + vertébroplastie scanoguidée avant spondylectomie en bloc, sans déficit neurologique ni récidive à 18 mois.",
        "summary_fr_detailed": "Les chordomes du rachis mobile et du sacrum sont des tumeurs malignes localement agressives et radio-résistantes dont la résection chirurgicale en bloc expose à une lourde morbidité fonctionnelle et à un risque de dissémination lors de l'ostéotomie. Cette revue systématique synthétise 34 procédures d'ablation thermique guidée par l'image (21 par cryoablation, 11 par radiofréquence, 1 par LITT) réalisées soit en néoadjuvant avant résection en bloc, soit à visée curative/palliative pour les récidives locales inopérables. Les auteurs rapportent également un protocole séquentiel associant RFA bipolaire scanoguidée et vertébroplastie consolidatrice d'un chordome L4 avant spondylectomie en bloc, permettant une nécrose tumorale centrale, une réduction du saignement peropératoire et une survie sans récidive à 18 mois sans complication neurologique.",
        "protocol_fr": "Repérage TDM/IRM précis des rapports avec le fourreau dural et les racines lombaires/sacrées • Thermoprotection épidurale et foraminale (hydrodissection / carbodissection + thermocouples) et monitorage neurophysiologique • Cryoablation multi-sondes (visualisation de l'iceball sur les chordomes sacrés) ou RFA + vertébroplastie acrylique sur le corps vertébral du rachis mobile.",
        "key_points_fr": [
            "Sur 34 chordomes rachidiens/sacrés traités par ablation percutanée, la cryoablation (62 %) et la RFA (32 %) assurent un contrôle antalgique et local avec peu de complications.",
            "En situation néoadjuvante pré-spondylectomie, le couplage RFA + vertébroplastie stérilise le contingent corporéal et limite le risque d'essaimage peropératoire.",
            "Dans les récidives locales sacrées inopérables ou post-radiques, la cryoablation scanoguidée constitue une option de rattrapage mini-invasive précieuse.",
            "Illustre la complémentarité entre radiologie interventionnelle ostéo-articulaire et chirurgie rachidienne oncologique."
        ],
        "tags": ["Chordome", "Rachis", "Sacrum", "Radiofréquence", "Cryoablation", "Vertébroplastie", "Curr Oncol 2026"]
    },
    "42483265": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Sclérothérapie percutanée au polidocanol combinée à l'injection adjuvante de moelle osseuse autologue pour le traitement des kystes osseux anévrismaux (KOA) : étude prospective",
        "modality": "Fluoroscopie / Scanner Interventionnel",
        "intervention_type": "Sclérothérapie au Polidocanol + Injection de Moelle Osseuse Autologue (KOA)",
        "cochin_link": "Complète directement les protocoles de « sclérothérapie / alcoolisation percutanée des kystes osseux anévrismaux (KOA) et essentiels (KOE) » de l'Agenda Cochin.",
        "summary_fr_short": "Étude prospective sur 20 patients suivis 30 mois (*Indian Journal of Orthopaedics*, janv./juil. 2026) évaluant l'association d'une sclérothérapie percutanée au polidocanol et d'une injection adjuvante de moelle osseuse autologue dans les kystes osseux anévrismaux : chute de l'EVA douleur de 6,2 à 0,3, réduction du volume kystique de 79,9 mL à 2,0 mL (p < 0,001) et seulement 5 % de récidive.",
        "summary_fr_detailed": "Afin d'accélérer l'ostéogenèse réparatrice après destruction chimique de la membrane endokystique des kystes osseux anévrismaux (KOA), cette étude prospective a traité 20 patients consécutifs par sclérothérapie percutanée au polidocanol suivie de l'instillation intrakystique de moelle osseuse autologue (prélevée sur la crête iliaque au cours de la même séance). Au terme d'un suivi complet de 30 mois après la dernière séance, le score EVA douleur diminue de 6,2 ± 1,4 à 0,3 ± 0,5 (p < 0,001) et le volume résiduel du kyste passe de 79,9 ± 26,3 mL à 2,0 ± 2,1 mL (p < 0,001), avec une ré-ossification corticale complète dans 95 % des cas et un taux de récidive limité à 5 % (1/20), sans complication majeure.",
        "protocol_fr": "Ponction percutanée du KOA sous guidage radiologique/TDM et aspiration du contenu hématique • Sclérothérapie chimique par injection de polidocanol (Aetoxisclerol) • Aspiration de moelle osseuse rouge autologue à la crête iliaque dans le même temps opératoire et réinjection intrakystique pour apporter des cellules souches mésenchymateuses ostéoprogénitrices • Suivi radiographique jusqu'à 30 mois.",
        "key_points_fr": [
            "Réduction volumétrique spectaculaire des KOA de 79,9 mL à 2,0 mL (p < 0,001) et disparition quasi complète des douleurs (EVA 6,2 → 0,3).",
            "Taux de guérison sans récidive de 95 % à 30 mois de recul (seulement 5 % de récidive locale).",
            "L'apport de moelle osseuse autologue iliaque stimule l'ostéogenèse intrakystique après l'action sclérosante du polidocanol sur l'endothélium.",
            "Technique simple, autologue et peu coûteuse facilement combinable aux procédures de sclérothérapie de KOA/KOE réalisées à Cochin."
        ],
        "tags": ["Kyste osseux anévrismal", "Polidocanol", "Moelle osseuse autologue", "Sclérothérapie", "Ostéogenèse", "Indian J Orthop 2026"]
    },
    "42999001": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Névralgie pudendale en centre tertiaire de la douleur (224 patients) : bloc diagnostique du nerf pudendal, radiofréquence pulsée et facteurs prédictifs de neuromodulation",
        "modality": "Scanner / Échographie / Fluoroscopie Interventionnelle",
        "intervention_type": "Infiltration Diagnostique & Radiofréquence Pulsée / Cryoneurolyse du Nerf Pudendal",
        "cochin_link": "Directement lié aux « infiltrations scanoguidées, radiofréquences pulsées et cryoneurolyses des nerfs pudendal et clunéal » programmées à l'Hôpital Cochin.",
        "summary_fr_short": "Étude de cohorte sur 224 adultes (*Pain and Therapy*, nov. 2026, IF 3,8) évaluant le parcours interventionnel de la névralgie pudendale : bloc pudendal diagnostique réalisé chez 59,4 % des patients et radiofréquence pulsée (PRF) chez 28,6 %, avec identification d'un bloc diagnostique positif (OR ajusté = 4,88) et d'une étiologie post-chirurgicale confirmée (OR = 2,83) comme facteurs prédictifs majeurs de réponse aux thérapies de neuromodulation.",
        "summary_fr_detailed": "La névralgie pudendale est une douleur neuropathique périnéale chronique invalidante aggravée par la position assise (critères de Nantes). Sur 224 patients consécutifs suivis en centre tertiaire, l'analyse après vérification manuelle des dossiers montre qu'une origine post-chirurgicale vraie n'est confirmée que dans 13,8 % des cas (contre 24,1 % de syndrome canalaire d'Alcock). La prise en charge repose avant tout sur la radiologie interventionnelle : bloc du nerf pudendal (59,4 %) et radiofréquence pulsée (28,6 %), tandis que la chirurgie de décompression (9,4 %) et l'implantation définitive d'un neurostimulateur (8,0 %) restent réservées aux formes réfractaires. Un soulagement significatif après bloc diagnostique pudendal multiplie par près de 5 (OR ajusté = 4,88, IC 95 % : 1,91–12,46) la probabilité d'éligibilité aux techniques de neuromodulation percutanée.",
        "protocol_fr": "Patient en procubitus sous guidage scanographique • Ciblage sélectif du nerf pudendal à l'épine ischiatique (pince ligamentaire sacro-épineuse / sacro-tubérale) et/ou dans le canal d'Alcock • Bloc diagnostique par anesthésique local (lidocaïne / ropivacaïne) ± corticoïde avec évaluation de l'EVA assise avant/après • En cas de bloc positif mais d'effet transitoire : radiofréquence pulsée (PRF, 42°C pendant 120 à 240 s) ou cryoneurolyse prudente.",
        "key_points_fr": [
            "Près de 60 % des patients bénéficient d'un bloc pudendal et près de 30 % d'une radiofréquence pulsée, piliers du parcours mini-invasif.",
            "Un test anesthésique positif du nerf pudendal est le facteur prédictif indépendant le plus puissant (OR = 4,88) pour guider la neuromodulation.",
            "L'implantation chirurgicale lourde n'est finalement nécessaire que chez 8 % des patients grâce à l'efficacité des gestes percutanés.",
            "Conforte l'algorithme de prise en charge graduée (bloc test scanoguidé puis PRF / cryoneurolyse) pratiqué en Radiologie B à Cochin."
        ],
        "tags": ["Névralgie pudendale", "Nerf pudendal", "Radiofréquence pulsée", "Bloc nerveux", "Douleur pelvi-périnéale", "Pain Ther 2026"]
    },
    "42998777": {
        "category_id": "ect_mets",
        "title_fr": "Toxicité pulmonaire induite par la bléomycine intraveineuse : revue systématique et méta-analyse PRISMA sur 7 601 patients (implications pour l'électrochimiothérapie)",
        "modality": "Scanner Thoracique & Électrochimiothérapie (ECT) sous Scanner",
        "intervention_type": "Sécurité Pharmacologique de l'Électrochimiothérapie (Bléomycine IV)",
        "cochin_link": "Référence essentielle de sécurité pour les séances d'« électrochimiothérapie (ECT - Bléomycine 15 000 UI/m² soit ~30 mg IV) osseuse et épidurale » au scanner Achard à Cochin.",
        "summary_fr_short": "Méta-analyse PRISMA 2020 (*Critical Reviews in Oncology/Hematology*, nov. 2026, IF 5,5, équipe de J. Gehl, 65 études / 7 601 patients) évaluant l'incidence et les facteurs de risque de toxicité pulmonaire à la bléomycine IV : contrairement aux cures répétées de chimiothérapie systémique (incidence globale 18 % en oncologie médicale), l'injection unique ou pauciséquentielle d'ECT à faible dose cumulative reste dépourvue de surrisque lié à l'âge ou aux métastases pulmonaires.",
        "summary_fr_detailed": "La bléomycine intraveineuse (15 000 UI/m² en bolus) est l'agent cytotoxique de référence de l'électrochimiothérapie (ECT) osseuse et des parties molles. Coordonnée par Julie Gehl (pionnière européenne de l'ECT), cette méta-analyse de 65 études (7 601 patients traités principalement par cures multiples pour tumeurs germinales ou lymphomes) montre que l'incidence rapportée de pneumopathie interstitielle dépend fortement de la définition utilisée (42 % sur des anomalies TDM asymptomatiques vs 16 % sur des critères cliniques composites). Fait rassurant pour la pratique d'ECT interventionnelle (où une dose unique faible est administrée) : l'analyse méta-régressive ne retrouve pas d'association significative à l'échelle des études avec l'âge, le sexe, le tabagisme ou la présence de métastases pulmonaires, tout en rappelant les précautions anesthésiques standard (limitation de la FiO2 peropératoire ≤ 30 %).",
        "protocol_fr": "Bilan pré-ECT : vérification de la fonction rénale (DFG, adaptation de dose si insuffisance rénale) et de l'absence de fibrose pulmonaire évolutive sur le scanner thoracique • Administration IV en bolus de bléomycine (15 000 UI/m²) sous anesthésie générale avec consigne stricte d'oxygénothérapie à FiO2 minimale nécessaire (idéalement FiO2 ≤ 30 %) • Impulsions d'électroporation entre 8 et 40 minutes post-injection.",
        "key_points_fr": [
            "Travail de référence de l'équipe de J. Gehl précisant le profil de tolérance pulmonaire de la bléomycine intraveineuse sur 7 601 patients.",
            "La présence de métastases pulmonaires ou l'âge avancé ne constituent pas en soi une contre-indication à une séance d'électrochimiothérapie osseuse.",
            "Distingue les anomalies scannographiques asymptomatiques (42 %) des pneumopathies cliniquement symptomatiques (16 % après cures cumulées d'oncologie médicale).",
            "Rappelle l'importance de la coordination avec l'anesthésiste (maintien d'une FiO2 basse per-procédure) lors des ECT réalisées à Cochin."
        ],
        "tags": ["Électrochimiothérapie", "Bléomycine", "Toxicité pulmonaire", "Sécurité anesthésique", "FiO2", "Crit Rev Oncol Hematol 2026"]
    },
    "42641400": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Cryoablation des tumeurs malignes et des lésions bénignes localement agressives (tumeurs desmoïdes, ostéome ostéoïde, chondroblastome) chez l'enfant et le jeune : consensus de la SIR Foundation",
        "modality": "Scanner / IRM / Échographie Interventionnelle",
        "intervention_type": "Cryoablation Percutanée des Tumeurs Desmoïdes & Tumeurs Osseuses Bénignes",
        "cochin_link": "En lien direct avec les « cryothérapies percutanées de tumeurs desmoïdes et de tumeurs osseuses bénignes chez les adolescents et jeunes adultes » prises en charge à Cochin.",
        "summary_fr_short": "Actes officiels du panel de consensus de la Society of Interventional Radiology (*JVIR*, août/nov. 2026) définissant les priorités cliniques et biologiques de la cryoablation chez le sujet jeune : comparaison prospective traitement systémique + cryoablation vs traitement systémique seul dans les tumeurs desmoïdes, et respect du cartilage articulaire et de conjugaison lors de la cryoablation des lésions osseuses bénignes.",
        "summary_fr_detailed": "Réunissant un panel multidisciplinaire d'experts nord-américains sous l'égide de la SIR Foundation, ce consensus synthétise les données d'efficacité et de qualité de vie de la cryoablation percutanée dans les pathologies tumorales musculo-squelettiques de l'enfant, de l'adolescent et du jeune adulte. Le groupe établit trois axes majeurs pour la pratique : 1) dans les tumeurs desmoïdes extra-abdominales, l'intégration précoce de la cryoablation percutanée (seule ou combinée aux traitements systémiques) améliore rapidement la douleur et la fonction ; 2) dans les tumeurs osseuses bénignes (ostéome ostéoïde, ostéoblastome, chondroblastome, KOA), il est essentiel de contrôler la marge de l'iceball au voisinage du cartilage hyalin et des physes ; et 3) dans les sarcomes oligométastatiques, la cryoablation constitue une alternative d'épargne parenchymateuse à la métastasectomie chirurgicale.",
        "protocol_fr": "Planification IRM et TDM haute résolution • Utilisation de cryosondes de petit calibre (17G) permettant de sculpter précisément la géométrie de l'iceball • Surveillance scannographique ou IRM continue de la marge à 0°C et -20°C à distance du cartilage articulaire, des physes et des troncs nerveux • Hydrodissection/carbodissection et réchauffement cutané actif.",
        "key_points_fr": [
            "Consensus officiel de la SIR positionnant la cryoablation au premier plan dans la stratégie multimodale des tumeurs desmoïdes.",
            "Met en avant le gain majeur de qualité de vie et d'épargne fonctionnelle par rapport à la chirurgie ou aux chimiothérapies prolongées.",
            "Précise les règles de prudence thermique au voisinage du cartilage épiphysaire et articulaire dans les tumeurs osseuses bénignes.",
            "Parfaitement aligné avec la prise en charge des jeunes adultes porteurs de tumeurs desmoïdes ou d'ostéomes ostéoïdes/chondroblastomes à Cochin."
        ],
        "tags": ["Cryoablation", "Tumeur desmoïde", "Consensus SIR", "Tumeurs osseuses bénignes", "Cartilage", "JVIR 2026"]
    },
    "42767629": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Vissage percutané ilio-sacré des fractures du sacrum en procubitus : technique modifiée guidée par le pédicule S1 et associée à la sacroplastie",
        "modality": "Fluoroscopie 2D/3D (Scopie Allura) + Contrôle Scanner",
        "intervention_type": "Vissage Percutané Ilio-Sacré en Procubitus & Sacroplastie",
        "cochin_link": "Directement applicable aux « vissages percutanés du bassin et sacroplasties en procubitus (Scanner / Scopie Allura) » réalisés à l'Hôpital Cochin.",
        "summary_fr_short": "Série clinique (*Orthopaedic Surgery*, sept./nov. 2026, PMC Open-Access, 22 patients) décrivant une technique modifiée de vissage ilio-sacré percutané en procubitus guidée par les repères du pédicule de S1 : taux d'excellence de positionnement intra-osseux au scanner de 97 %, absence totale de complication radiculaire et amélioration significative de l'EVA douleur et du score fonctionnel de Majeed.",
        "summary_fr_detailed": "Le positionnement en procubitus (prone position) est la posture de référence en radiologie interventionnelle ostéo-articulaire pour combiner dans le même temps un abord postérieur rachidien/sacré (cimentoplastie, sacroplastie) et un vissage ilio-sacré percutané. Cette étude évalue sur 22 patients une technique standardisée de visée ilio-sacrée en procubitus s'appuyant sur le repérage fluoroscopique du pédicule de S1 (vues inlet, outlet et profil strict). Le scanner de contrôle systématique à 6 mois démontre un taux d'excellence de trajectoire de 97 % sans aucune effraction des foramens sacrés ni lésion nerveuse L5/S1. Les auteurs soulignent l'intérêt majeur du procubitus chez les patients obèses ou présentant des lésions rachidiennes ou sacrées concomitantes nécessitant une sacroplastie associée.",
        "protocol_fr": "Installation en procubitus sur table radiotransparente (Scopie Allura ou table de scanner interventionnel) • Repérage des incidences fluoroscopiques inlet, outlet et profil sacré vrai centrées sur les pédicules S1 • Insertion de la broche-guide à travers l'aile iliaque et l'articulation sacro-iliaque jusque dans le corps de S1 • Mise en place de la vis canulée (7,0–7,3 mm) ± injection de ciment PMMA (sacroplastie/vissage cimenté).",
        "key_points_fr": [
            "Taux de précision intra-osseuse de 97 % au contrôle TDM et 0 % de complication neurologique radiculaire.",
            "L'installation en procubitus facilite l'association dans le même temps d'un vissage ilio-sacré et d'une sacroplastie ou vertébroplastie.",
            "Amélioration rapide et durable de l'EVA douleur et du score fonctionnel pelvien de Majeed.",
            "Correspond exactement à l'installation en procubitus utilisée en salle de scanner et sous scopie Allura à Cochin."
        ],
        "tags": ["Vissage ilio-sacré", "Fracture du sacrum", "Procubitus", "Sacroplastie", "Fluoroscopie", "Orthop Surg 2026"]
    },
    "42645393": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "La radiologie interventionnelle dans le traitement des tumeurs musculo-squelettiques primitives et secondaires : radiofréquence, cryoablation, cimentoplastie et HIFU",
        "modality": "Scanner / IRM / Échographie / Fluoroscopie Interventionnelle",
        "intervention_type": "Ablation Thermique (RF, Cryoablation) & Cimentoplastie des Tumeurs Osseuses et des Parties Molles",
        "cochin_link": "Synthèse transversale couvrant l'ensemble du plateau de « radiofréquence, cryoablation et cimentoplastie des tumeurs osseuses bénignes et malignes » de l'Hôpital Cochin.",
        "summary_fr_short": "Revue clinique du Karolinska Institutet (*Current Oncology*, août 2026, IF 2,8) synthétisant les indications, critères de sélection et résultats de la radiofréquence (RFA), de la cryoablation, de la cimentoplastie et des ultrasons focalisés (HIFU) dans les tumeurs osseuses bénignes (ostéome ostéoïde, chondroblastome), les tumeurs localement agressives (desmoïdes, TCG) et les métastases osseuses et des parties molles.",
        "summary_fr_detailed": "Rédigée par l'équipe d'oncologie musculo-squelettique du Karolinska University Hospital (Stockholm), cette revue propose un arbre décisionnel pragmatique pour le choix de la modalité percutanée : 1) la radiofréquence (RFA) demeure le gold standard des petites lésions intra-osseuses ostéocondensantes ou nidus (ostéome ostéoïde) et se combine idéalement à la cimentoplastie dans les métastases vertébrales ou acétabulaires lytiques ; 2) la cryoablation est privilégiée pour les tumeurs à extension extra-osseuse, les tumeurs cartilagineuses de bas grade ou bénignes (chondroblastome), les récidives de tumeurs à cellules géantes (TCG), les tumeurs desmoïdes et les métastases volumineuses ou ostéoblastiques grâce à la visualisation directe de la boule de glace ; 3) la cimentoplastie assure la stabilisation mécanique immédiate des zones portantes en compression.",
        "protocol_fr": "Sélection personnalisée en RCP selon 5 critères : histologie (bénin vs malin/métastatique), volume et matrice (lytique vs condensante/parties molles), objectif (curatif vs palliatif antalgique), stabilité mécanique (score SINS / Mirels / Harrington) et proximité des structures critiques (< 1 cm de la moelle, d'un tronc nerveux ou du cartilage articulaire).",
        "key_points_fr": [
            "Fournit un algorithme comparatif clair entre RFA (petit nidus intra-osseux, métastase lytique corporéale) et cryoablation (volume > 2–3 cm, extension aux parties molles, matrice sclérotique).",
            "Rappelle la nécessité d'associer une cimentoplastie ou un vissage percutané dès que l'ablation porte sur un segment osseux soumis aux contraintes mécaniques.",
            "Souligne le rôle croissant de la cryoablation dans les tumeurs localement agressives récidivantes (desmoïdes, TCG, chondroblastomes).",
            "Excellente référence pédagogique résumant la philosophie de prise en charge interventionnelle ostéo-articulaire de Cochin."
        ],
        "tags": ["Radiologie interventionnelle", "Tumeurs musculo-squelettiques", "Cryoablation", "Radiofréquence", "Cimentoplastie", "Curr Oncol 2026"]
    },
    "42612110": {
        "category_id": "ect_mets",
        "title_fr": "Simulation patient-spécifique du champ électrique dans l'électrochimiothérapie (ECT) des métastases rachidiennes (workflow 3D Slicer / AI4DEEP)",
        "modality": "Scanner Interventionnel + Fusion IRM / Planification 3D",
        "intervention_type": "Électrochimiothérapie (ECT) des Métastases Vertébrales & Planification Dosimétrique",
        "cochin_link": "Directement applicable aux « Électrochimiothérapies (ECT - Bléomycine 30 mg IV) rachidiennes et épidurales au scanner Achard -1 » réalisées à l'Hôpital Cochin.",
        "summary_fr_short": "Protocole de référence français (Gustave Roussy / AP-HP : Beunon, Bonnet, Tselikas et al., *JoVE*, juil. 2026, IF 1,2) décrivant un workflow reproductible de simulation 3D patient-spécifique du champ électrique (3D Slicer + module éléments finis AI4DEEP) pour l'ECT des métastases vertébrales : validation sur 9 procédures rachidiennes démontrant une concordance maximale avec la nécrose post-ECT en IRM injectée sur l'isodose 160–200 V/cm.",
        "summary_fr_detailed": "L'électrochimiothérapie (ECT) rachidienne permet une décompression épidurale et un contrôle tumoral non thermique au contact de la moelle épinière et des racines nerveuses lorsque la radiothérapie ou la thermoablation sont contre-indiquées. Toutefois, l'hétérogénéité diélectrique entre os cortical, os spongieux, tumeur lytique et espace épidural rend complexe l'anticipation de la couverture réelle du champ électrique. L'équipe française (Gustave Roussy / Hôpitaux Universitaires Paris-Seine-Saint-Denis) détaille un pipeline open-source sous 3D Slicer combinant segmentation multimodale TDM + IRM préopératoire, attribution des conductivités tissulaires (base IT'IS) et résolution par éléments finis via le module dédié AI4DEEP. Validé rétrospectivement sur 9 procédures d'ECT vertébrale avec recalage sur l'IRM injectée de suivi (coefficient de Dice), le modèle montre que le seuil isodose de 160 à 200 V/cm prédit le plus fidèlement le volume tumoral effectivement nécrosé et identifie les zones sous-traitées ou surexposées.",
        "protocol_fr": "Imagerie pré-procédurale multimodale TDM coupes fines + IRM rachidienne gadolinium • Segmentation 3D de la tumeur, des corticales vertébrales, du fourreau dural et des tissus mous sous 3D Slicer • Simulation par éléments finis (module AI4DEEP, conductivités IT'IS) de la géométrie des aiguilles-électrodes transpédiculaires/paravertébrales • Vérification de la couverture tumorale complète au-dessus du seuil réversible/efficace (≥ 160–200 V/cm dans ce modèle linéaire, cible nominale ECT 400 V/cm) tout en limitant le courant traversant le cordon médullaire • Contrôle IRM injecté post-ECT.",
        "key_points_fr": [
            "Premier protocole ouvert et reproductible (3D Slicer + AI4DEEP) de planification patient-spécifique du champ électrique pour l'ECT rachidienne.",
            "Excellente corrélation spatiale (Dice) entre la cartographie simulée (160–200 V/cm en conductivité linéaire constante) et la nécrose observée en IRM de contrôle sur 9 cas cliniques.",
            "Permet d'optimiser le parallélisme, l'espacement et le nombre d'électrodes transpédiculaires avant le geste pour éviter les reliquats épiduraux sous-traités.",
            "Outil directement transposable aux dossiers complexes d'ECT vertébrale discutés en RCP et traités sous scanner à Cochin."
        ],
        "tags": ["Électrochimiothérapie", "ECT rachidienne", "Métastases vertébrales", "Simulation champ électrique", "3D Slicer", "Gustave Roussy", "JoVE 2026"]
    },
    "42964659": {
        "category_id": "msk_biopsy",
        "title_fr": "Performance diagnostique et sécurité de la biopsie osseuse percutanée guidée par scanner en oncologie musculo-squelettique (64 procédures consécutives)",
        "modality": "Scanner Interventionnel (Approche Coaxiale)",
        "intervention_type": "Biopsie Osseuse Percutanée Guidée par TDM (Pelvis, Rachis & Os Longs)",
        "cochin_link": "Reflète directement l'activité quotidienne de « Biopsie osseuse ou disco-vertébrale sous scanner (crête iliaque, sacrum, membres) » de l'Agenda Interventionnel Cochin.",
        "summary_fr_short": "Étude de cohorte monocentrique (*World Journal of Radiology*, oct. 2026, IF 2,5, Open-Access) portant sur 64 biopsies osseuses percutanées consécutives guidées par scanner : rendement diagnostique de 93,75 % (60/64) dès le premier prélèvement, concordance histologique de 100 % parmi les prélèvements contributifs, révision du diagnostic clinique pré-geste dans 9,4 % des cas (6/64) et 0 % de complication majeure SIR.",
        "summary_fr_detailed": "Cette série évalue rigoureusement la rentabilité histopathologique, la concordance diagnostique finale (chirurgie, immunohistochimie et suivi radio-clinique composite) et la morbidité selon la classification SIR de 64 biopsies osseuses percutanées consécutives réalisées sous guidage TDM entre 2023 et 2025 pour suspicion de tumeur osseuse primitive ou secondaire (les localisations pelviennes étant majoritaires). Soixante procédures sur 64 (93,75 % ; IC 95 % : 84,8–98,3 %) ont fourni un diagnostic histologique exploitable sans nécessité de re-biopsie, avec une concordance de 100 % sur les cas contributifs. Fait clinique majeur : dans 6 cas (9,4 %), la biopsie TDM a redressé l'hypothèse diagnostique initiale (ex. lésion bénigne ou infectieuse mimant une métastase ou inversement). Aucune complication majeure SIR n'est survenue (0 %), seuls 2 trajets fistuleux mineurs de grade SIR B (3,1 %) ayant été observés.",
        "protocol_fr": "Revue préalable de l'IRM/TDM/TEP pour cibler la portion charnue non nécrotique ou ostéolytique active et respecter strictement la voie d'abord chirurgicale en cas de suspicion de sarcome primitif • Approche coaxiale sous guidage TDM hélicoïdal ou fluoroscopie-TDM • Carottage multiple au trocart à os (11G–13G) couplé si composante tissulaire à un pistolet semi-automatique (14G–16G) • Bilan d'hémostase et gestion standardisée des antithrombotiques.",
        "key_points_fr": [
            "Rendement diagnostique élevé de 93,75 % dès la première biopsie osseuse sous scanner, dominée par les localisations pelviennes complexes.",
            "Redressement du diagnostic clinique pré-procédural dans près de 1 cas sur 10 (9,4 %), justifiant l'histologie systématique avant ablation ou radiothérapie.",
            "Sécurité optimale : 0 % de complication majeure SIR et seulement 3,1 % d'événements mineurs locaux.",
            "Conforte les standards de biopsie osseuse coaxiale sous scanner pratiqués en Radio B à Cochin."
        ],
        "tags": ["Biopsie osseuse", "Scanner interventionnel", "Rendement diagnostique", "Oncologie musculo-squelettique", "Bassin", "World J Radiol 2026"]
    },
    "42736384": {
        "category_id": "msk_biopsy",
        "title_fr": "Biopsie disco-vertébrale guidée par l'image et antibiothérapie probabiliste préalable dans les suspicions de spondylodiscite (81 procédures)",
        "modality": "Scanner Interventionnel / Fluoroscopie",
        "intervention_type": "Biopsie Disco-Vertébrale Percutanée pour Suspicion de Spondylodiscite",
        "cochin_link": "Répond à une question quotidienne de l'Agenda Cochin lors des demandes urgentes de « Biopsie disco-vertébrale sous scanner pour spondylodiscite » chez des patients déjà mis sous antibiotiques.",
        "summary_fr_short": "Étude rétrospective (*Diagnostic and Interventional Radiology*, sept. 2026, IF 1,9) sur 81 biopsies disco-vertébrales guidées par l'image (62 sous TDM, 19 sous scopie) : rendement microbiologique global de 37,0 % non significativement diminué par une antibiothérapie préalable (36,4 % sous antibiotiques vs 37,8 % sans antibiotiques, p = 0,890), soulignant qu'il ne faut pas retarder l'antibiothérapie probabiliste chez un patient septique et que la biologie moléculaire (ARN 16S / NGS) est indispensable pour compléter la culture.",
        "summary_fr_detailed": "Analysant 81 biopsies percutanées réalisées entre 2014 et 2025 pour suspicion de spondylodiscite infectieuse, cette étude compare le rendement des cultures microbiologiques selon le mode de guidage (TDM : 38,7 % vs fluoroscopie : 31,6 %, p = 0,586), le site prélevé (os transpédiculaire vs disque/aspiration, p > 0,60) et surtout l'exposition préalable aux antibiotiques. De façon notable, la positivité des cultures standard ne diffère pas significativement entre les patients ayant reçu une antibiothérapie avant le geste (36,4 %) et ceux vierges d'antibiotiques (37,8 %, p = 0,890). Hors tuberculose, 97 % des germes isolés étaient couverts par l'association probabiliste vancomycine + ceftriaxone. Les auteurs concluent que la culture isolée a une sensibilité modérée (44,4 %, spécificité 88,9 %) mais reste capitale en cas de suspicion de tuberculose/brucellose/fongique, d'échec clinique ou d'immunodépression.",
        "protocol_fr": "Abord transpédiculaire ou postéro-latéral disco-vertébral sous guidage scanner • Prélèvements multiples combinant carottes osseuses des plateaux vertébraux érodés, tissu discal et aspiration liquidienne éventuelle d'abcès paravertébral/psoas • Envoi systématique en bactériologie standard prolongée, mycobactériologie, anatomopathologie ET biologie moléculaire (PCR universelle ARN 16S) pour pallier la faible sensibilité des cultures seules.",
        "key_points_fr": [
            "Une antibiothérapie probabiliste débutée avant le geste n'annule pas le rendement de la biopsie (36,4 % vs 37,8 %, p = 0,890) et ne doit pas faire récuser d'emblée un prélèvement nécessaire (suspicion de BK, germe atypique ou échec thérapeutique).",
            "Rendement supérieur tendanciel du guidage TDM (38,7 %) par rapport à la fluoroscopie (31,6 %), avec sécurisation des abords thoraciques et paravertébraux.",
            "La sensibilité limitée des cultures conventionnelles (37–44 %) justifie d'associer systématiquement l'anatomopathologie et la PCR ARN 16S sur les carottes disco-vertébrales.",
            "Données pragmatiques très utiles pour arbitrer les demandes de biopsies de spondylodiscite en urgence différée à Cochin."
        ],
        "tags": ["Spondylodiscite", "Biopsie disco-vertébrale", "Antibiothérapie préalable", "Scanner interventionnel", "Microbiologie", "Diagn Interv Radiol 2026"]
    },
    "42804317": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Facteurs prédictifs de succès de la radiofréquence des nerfs intercostaux dans les névralgies intercostales réfractaires : radiofréquence thermique conventionnelle vs pulsée (60 patients)",
        "modality": "Échographie / Scanner Interventionnel",
        "intervention_type": "Radiofréquence Conventionnelle & Pulsée des Nerfs Intercostaux",
        "cochin_link": "Complète directement la prise en charge des douleurs pariétales thoraciques de l'Agenda Cochin (« Neurolyse / Cryoneurolyse et radiofréquence du nerf intercostal »).",
        "summary_fr_short": "Étude comparative rétrospective (*Pain Physician*, sept. 2026, IF 3,1) chez 60 adultes souffrant de névralgie intercostale post-traumatique, post-zostérienne ou idiopathique réfractaire : la radiofréquence thermique conventionnelle (CRF, n = 31) procure une analgésie nettement plus durable à 3 et 6 mois que la radiofréquence pulsée (PRF, n = 29 ; NRS à 6 mois : 2,81 ± 1,93 vs 6,31 ± 2,34, p < 0,001) et constitue le seul facteur prédictif indépendant de réponse clinique IMMPACT (OR = 9,40 ; p = 0,001).",
        "summary_fr_detailed": "Les névralgies intercostales chroniques (post-thoracotomie, post-traumatiques, post-zostériennes) altèrent sévèrement la qualité de vie. Cette cohorte compare deux modalités de neurolyse guidée par l'image des nerfs intercostaux : la radiofréquence thermique conventionnelle ablative (CRF) et la radiofréquence pulsée neuromodulatrice non destructrice (PRF), avec évaluation à 3 et 6 mois selon les critères IMMPACT (réduction ≥ 50 % ou ≥ 4 points du score NRS-11). Alors que les deux techniques soulagent transitoirement la douleur initiale, la CRF maintient un score NRS bas à 3 mois (2,77 vs 5,83, p < 0,001) et à 6 mois (2,81 vs 6,31, p < 0,001). En régression logistique multivariée incluant l'âge, le sexe, l'allodynie et l'intensité douloureuse initiale, le choix d'une modalité ablative vraie (CRF versus PRF) multiplie par 9,4 la probabilité de succès durable à 6 mois.",
        "protocol_fr": "Repérage sous échographie haute fréquence ou scanner du sillon sous-costal au bord inférieur de la côte cible (à distance de la plèvre pariétale et du pédicule vasculaire intercostal) • Stimulation sensitive (50 Hz, reproduction de la topographie douloureuse < 0,5 V) et motrice • Anesthésie locale lidocaïne 1–2 % avant lésion thermique (CRF 80°C pendant 60–90 s, ou alternative par cryoneurolyse -60°C/-70°C à Cochin évitant la névrite de désafférentation).",
        "key_points_fr": [
            "Démontre la supériorité franche d'une neurolyse axonotmétique vraie (RF conventionnelle : NRS 2,8 à 6 mois) sur la simple neuromodulation pulsée (PRF : NRS 6,3 à 6 mois, OR = 9,40).",
            "Ni la présence d'allodynie ni l'âge n'ont empêché la réponse clinique en analyse multivariée.",
            "Confirme que pour les douleurs pariétales thoraciques rebelles, une modalité neurolytique (RF conventionnelle ou cryoneurolyse intercostale sous scanner telle que pratiquée à Cochin) offre un contrôle bien plus durable que la PRF.",
            "Rappelle l'importance du guidage imagerie continu pour prévenir tout risque de pneumothorax ou de brèche vasculaire sous-costale."
        ],
        "tags": ["Nerf intercostal", "Névralgie intercostale", "Radiofréquence", "Douleur thoracique", "Neurolyse", "Pain Physician 2026"]
    },
    "42729247": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Injection percutanée de ciment phosphocalcique pour les kystes osseux essentiels (KOE) : résultats cliniques, remodelage cortical et récidives à moyen et long terme (suivi moyen > 5 ans)",
        "modality": "Fluoroscopie / Scanner Interventionnel",
        "intervention_type": "Injection Percutanée Ostéoconductrice / Cimentoplastie Phosphocalcique de Kyste Osseux Essentiel (KOE)",
        "cochin_link": "En lien direct avec les procédures d'« Alcoolisation (+/- cimentoplastie phosphocalcique) de kyste osseux essentiel (KOE) de l'aile iliaque, de l'humérus ou du fémur proximal » de l'Agenda Cochin.",
        "summary_fr_short": "Série clinique à long terme (*Frontiers in Surgery*, août 2026, IF 1,8, Open-Access, suivi moyen 61,1 mois jusqu'à 12 ans) chez 31 enfants et jeunes adultes porteurs d'un kyste osseux essentiel (dont 14 révélés par fracture pathologique) traités par injection percutanée de ciment phosphocalcique (CPC) : disparition complète des douleurs (EVA médiane à 0), score fonctionnel MSTS médian de 30/30, cicatrisation radiographique Neer I/II dans 100 % des cas finaux et taux de récidive primaire limité à 12,9 % (4/31).",
        "summary_fr_detailed": "Le traitement mini-invasif des kystes osseux essentiels (unicameral bone cysts, KOE) vise à prévenir les fractures itératives tout en stimulant l'ostéogenèse cavitaire sans greffe chirurgicale ouverte. Cette étude analyse avec un recul moyen de plus de 5 ans (61,1 mois, extrêmes 13–149 mois) 31 patients traités par évacuation-lavage percutané suivie du comblement par ciment phosphocalcique injectable (CPC), substitut osseux résorbable et ostéoconducteur offrant une résistance mécanique en compression immédiate. L'EVA douleur chute à 0 et le score fonctionnel MSTS atteint 30/30 (p < 0,001). Quatre récidives cavitaires tardives (12,9 %) sont survenues après la première injection : 3 ont guéri durablement après une seconde injection percutanée de CPC et 1 est restée asymptomatique avec corticale épaissie. Au dernier recul, 100 % des patients présentent un grade de Neer modifié I ou II sans aucune complication grave.",
        "protocol_fr": "Ponction percutanée à deux trocarts sous guidage scopique/TDM (technique à double aiguille pour décompression) • Aspiration du liquide citrin, kystographie de contrôle éliminant un drainage veineux massif, curetage-lavage endokystique mécanique/chimique (alcoolisation préalable possible selon protocole local) • Injection lente sous contrôle fluoroscopique continu du ciment phosphocalcique (CPC) jusqu'au comblement cavitaire complet • Reprise fonctionnelle précoce grâce au renfort mécanique.",
        "key_points_fr": [
            "Recul exceptionnel (> 5 ans de moyenne) confirmant la durabilité du comblement percutané par ciment phosphocalcique dans les KOE (87,1 % de succès en 1 séance, 100 % Neer I/II au recul final).",
            "Épaississement cortical progressif et résorption-substitution osseuse du ciment phosphocalcique contrairement au PMMA non résorbable chez le sujet jeune.",
            "Possibilité de retraiter simplement par nouvelle injection percutanée les rares récidives partielles (3/31) sans chirurgie ouverte.",
            "Valide parfaitement la stratégie combinée sclérothérapie/alcoolisation + comblement phosphocalcique pratiquée à Cochin sur les KOE fragilisants."
        ],
        "tags": ["Kyste osseux essentiel", "KOE", "Ciment phosphocalcique", "Traitement percutané", "Remodelage cortical", "Front Surg 2026"]
    },
    "42938822": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Stabilisation osseuse photodynamique centromédullaire percutanée (IlluminOss®) des fractures pathologiques et menaçantes de l'humérus métastatique : étude bicentrique (52 lésions)",
        "modality": "Fluoroscopie Interventionnelle",
        "intervention_type": "Ostéosynthèse Percutanée Photodynamique & Consolidation des Métastases des Os Longs",
        "cochin_link": "Complète l'arsenal d'« Ostéosynthèse percutanée et consolidation osseuse oncologique » (en complément du vissage cimenté et de la cimentoplastie) discuté en RCP Métastases Osseuses à Cochin.",
        "summary_fr_short": "Étude bicentrique sur données prospectives (*Cancers*, oct. 2026, IF 4,5, Open-Access) portant sur 51 patients métastatiques (52 fractures humérales avérées ou menaçantes Mirels 8–10) traités par ballonnet centromédullaire photopolymérisable mini-invasif (IlluminOss®) : chute rapide de la douleur (NRS de 7,1 à 2,0, p < 0,001), doublement du score fonctionnel MSTS-UE (de 9,5 à 20/30, p < 0,001), implant radiotransparent sans artefact TDM/IRM et faible taux de défaillance mécanique (7,7 %).",
        "summary_fr_detailed": "Contrairement au bassin ou aux vertèbres où le ciment PMMA travaille idéalement en compression, la diaphyse humérale métastatique subit d'importantes contraintes en torsion et flexion qui limitent la cimentoplastie isolée. Cette série bicentrique évalue sur 52 lésions humérales (67,3 % de fractures pathologiques constituées, 32,7 % de lésions lytiques menaçantes Mirels 8–10) le système percutané de stabilisation photodynamique IlluminOss® : un ballonnet en PET souple est introduit par un abord mini-invasif dans le canal médullaire, gonflé d'un monomère liquide épousant la géométrie endostée irrégulière de l'ostéolyse, puis polymérisé in situ en quelques minutes par fibre optique à lumière bleue visible (436 nm). La douleur chute de NRS 7,1 à 2,0 (p < 0,001) et les scores fonctionnels MSTS-UE (9,5 à 20/30) et TESS (36,5 à 61/100) s'améliorent significativement, y compris chez des patients fragiles (25 % ECOG 3–4).",
        "protocol_fr": "Abord percutané proximal ou distal minimal sous guidage fluoroscopique • Alésage léger/cathétérisme du fût huméral à travers la zone ostéolytique • Mise en place du ballonnet PET sur mesure et infusion du monomère liquide sous scopie (zéro fuite extra-osseuse grâce à l'enveloppe étanche du ballonnet) • Photopolymérisation par fibre optique endoluminale (436 nm) créant un tuteur intramédullaire rigide et radiotransparent, compatible avec un vissage transversal complémentaire direct à travers le polymère si fracture complexe.",
        "key_points_fr": [
            "Alternative mini-invasive aux enclouages chirurgicaux lourds pour stabiliser les fractures pathologiques ou menaçantes (Mirels 8–10) de l'humérus chez les patients oncologiques fragiles.",
            "Analgésie rapide et majeure (NRS 7,1 → 2,0) et récupération précoce de la fonction du membre supérieur (MSTS-UE doublé).",
            "Polymère confiné dans un ballonnet étanche (éliminant le risque de fuite de ciment dans les loges vasculo-nerveuses brachiales/radiales) et totalement radiotransparent pour la radiothérapie et le suivi TDM/IRM.",
            "Enrichit les options percutanées de stabilisation des os longs non porteurs soumises aux contraintes de torsion."
        ],
        "tags": ["Stabilisation photodynamique", "IlluminOss", "Humérus métastatique", "Fracture pathologique", "Ostéosynthèse percutanée", "Cancers 2026"]
    },
    "42276242": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Critères cliniques de sélection et résultats à 10 ans de la cryoablation percutanée du nerf pudendal guidée par scanner (362 procédures)",
        "modality": "Scanner Interventionnel (TDM)",
        "intervention_type": "Cryoneurolyse / Cryoablation Percutanée du Nerf Pudendal sous Scanner",
        "cochin_link": "Référence majeure pour la sélection des patients adressés en « Cryoneurolyse percutanée du nerf pudendal sous scanner (épine ischiatique / canal d'Alcock) » à l'Hôpital Cochin.",
        "summary_fr_short": "Plus grande série publiée sur 10 ans (*JVIR*, juin 2026, IF 2,6, 362 cryoablations TDM du nerf pudendal) : les patients réunissant la triade de sélection (facteur déclenchant identifié, douleur périnéale unilatérale systématisée et bloc diagnostique TDM positif) obtiennent 77,4 % de succès clinique (réduction moyenne de la douleur de 88,8 % chez les répondeurs) et un intervalle libre avant réintervention de 31,8 mois, avec 0 % de complication majeure SIR.",
        "summary_fr_detailed": "Cette étude rétrospective académique multicentrique analyse 362 procédures de cryoablation percutanée du nerf pudendal guidées par scanner réalisées entre 2014 et 2024. L'analyse porte sur la valeur prédictive d'une triade clinique prédéfinie : 1) événement causal identifiable (chirurgie, traumatisme, accouchement, compression), 2) topographie douloureuse périnéale unilatérale typique du nerf pudendal, et 3) réponse positive au bloc anesthésique diagnostique sous scanner. Lorsque les 3 critères sont réunis, le taux de réponse clinique (réduction ≥ 50 % du score NRS) atteint 77,4 % contre 36,4 % en l'absence des critères complets (p = 0,002), avec une réduction douloureuse moyenne de 69,1 % (et 88,8 % chez les répondeurs). Chez les patients nécessitant une seconde séance à distance, la durée moyenne d'efficacité avant retraitement est de 31,8 mois (> 2,5 ans), sans aucun événement indésirable majeur (SIR C-F).",
        "protocol_fr": "Sélection pré-procédurale stricte par bloc test scanoguidé du nerf pudendal • Patient en procubitus au scanner • Abord transglutéal postéro-latéral ciblant l'espace inter-ligamentaire (pince entre ligament sacro-épineux et ligament sacro-tubéral à l'épine ischiatique) ou le canal d'Alcock (aponévrose de l'obturateur interne) • Mise en place d'une cryosonde 17G • Double cycle de congélation (ex. 2 × 2 à 3 min séparés par décongélation passive) avec contrôle TDM de l'iceball à distance de la paroi rectale et du nerf sciatique.",
        "key_points_fr": [
            "Série de référence mondiale (362 procédures sur 10 ans dans JVIR) validant l'efficacité durable et la sécurité (0 % complication SIR C-F) de la cryoneurolyse TDM du nerf pudendal.",
            "La triade clinique (événement déclenchant + topographie pudendale unilatérale + bloc test TDM positif) double le taux de succès (77,4 % vs 36,4 %, p = 0,002).",
            "Durabilité remarquable d'une séance : délai moyen de 31,8 mois avant toute réintervention chez les répondeurs.",
            "Guide directement l'indication de cryoneurolyse pudendale après bloc diagnostique positif en Radiologie B à Cochin."
        ],
        "tags": ["Cryoneurolyse", "Cryoablation", "Nerf pudendal", "Névralgie pudendale", "Bloc diagnostique", "Canal d'Alcock", "JVIR 2026"]
    },
    "42527618": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Valeur prédictive du bloc nerveux diagnostique pré-procédural avant cryoneurolyse guidée par scanner des douleurs abdomino-pelviennes réfractaires (95 patients)",
        "modality": "Scanner Interventionnel (TDM)",
        "intervention_type": "Bloc Nerveux Diagnostique & Cryoneurolyse Pelvi-Périnéale sous Scanner",
        "cochin_link": "Éclaire l'organisation du parcours « Bloc test scanoguidé vs Cryoneurolyse d'emblée du nerf pudendal » dans les douleurs pelviennes oncologiques et neuropathiques à Cochin.",
        "summary_fr_short": "Étude comparative (*CardioVascular and Interventional Radiology - CVIR*, juil. 2026, IF 2,8, 95 patients) évaluant l'utilité d'un bloc nerveux diagnostique préalable avant cryoneurolyse TDM abdomino-pelvienne : chute hautement significative de l'EVA (de 8,4 à 3,8 à 1 mois, p < 0,001) avec un taux de succès clinique équivalent avec ou sans bloc préalable (81,1 % vs 69,7 % à 1 mois, p = 0,40), suggérant que la cryoneurolyse directe d'emblée est légitime lorsque l'étiologie anatomique (notamment tumorale) est formellement identifiée.",
        "summary_fr_detailed": "Sur 95 patients traités par cryoneurolyse guidée par scanner pour des douleurs abdomino-pelviennes et périnéales réfractaires (oncologiques et non oncologiques), 52 ont bénéficié d'un bloc anesthésique diagnostique préalable (retardant la cryoneurolyse de 16,1 jours en moyenne) et 43 ont eu une cryoneurolyse directe d'emblée. L'EVA moyenne diminue de 8,4 ± 1,6 avant le geste à 3,9 à 1 semaine, 3,8 à 1 mois et 4,8 à 3 mois (p < 0,001). Les taux de succès clinique (baisse ≥ 3 points d'EVA) ne diffèrent pas significativement entre les groupes avec ou sans bloc à 1 semaine (76,6 % vs 78,4 %) et 1 mois (81,1 % vs 69,7 %), sans aucune complication observée.",
        "protocol_fr": "Stratification selon le contexte clinique : 1) Névralgie pudendale idiopathique ou canalaire (critères de Nantes) : bloc diagnostique TDM préalable recommandé pour confirmer l'imputabilité du nerf pudendal ; 2) Douleur pelvi-périnéale oncologique ou lésionnelle anatomiquement prouvée : cryoneurolyse TDM directe en un seul temps pour éviter tout délai analgésique de 2 semaines.",
        "key_points_fr": [
            "Réduction majeure de l'EVA douleur de 8,4 à 3,8 à 1 mois (p < 0,001) avec 0 % de complication sur 95 patients.",
            "Le bloc test préalable retarde en moyenne la cryoneurolyse de 16 jours : il reste indispensable dans les névralgies fonctionnelles/canalaires mais peut être omis au profit d'une cryoneurolyse d'emblée lorsque la cible tumorale pelvienne est évidente.",
            "Pertinent pour accélérer la prise en charge antalgique des patients d'oncologie pelvienne hospitalisés à Cochin."
        ],
        "tags": ["Cryoneurolyse", "Bloc diagnostique", "Douleur pelvienne", "Nerf pudendal", "Scanner interventionnel", "CVIR 2026"]
    },
    "41440950": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Cryoneurolyse personnalisée dans les douleurs pelviennes sévères : ciblage du nerf pudendal et du ganglion impar (mécanismes, bilan et technique)",
        "modality": "Scanner Interventionnel (TDM) / Fluoroscopie",
        "intervention_type": "Cryoneurolyse Ciblée du Nerf Pudendal & du Ganglion Impar",
        "cochin_link": "Synthèse pratique sur le ciblage combiné « Nerf pudendal + Ganglion de Walther (Impar) » pratiqué sous scanner en Radiologie Interventionnelle à Cochin.",
        "summary_fr_short": "Revue clinique et technique (*Journal of Personalized Medicine*, déc. 2025, IF 3,0, équipe J.D. Prologo) détaillant la neurobiologie de l'axonotmésis par le froid (-20°C à -100°C), la cartographie sémiologique des douleurs pelvi-périnéales et la technique de cryoneurolyse personnalisée du nerf pudendal et du ganglion impar en alternative d'épargne opioïde.",
        "summary_fr_detailed": "Face aux douleurs pelvi-périnéales réfractaires et à la nécessité d'épargne morphinique, cette mise au point détaille l'approche personnalisée par cryoneurolyse guidée par l'image. Contrairement à l'alcoolisation ou à la radiofréquence thermique ablative à haute température qui exposent au névrome de désafférentation, la cryoneurolyse induit une dégénérescence wallérienne réversible (axonotmésis de grade II de Sunderland) en préservant intégralement la trame conjonctive endoneurale, périneurale et épineurale, permettant une repousse axonale physiologique sans névrome. L'article précise les repères TDM pour cibler sélectivement le nerf pudendal (douleur périnéale latéralisée des 2/3 antérieurs, majorée assis) et le ganglion impar pré-coccygien (douleur périnéale médiane, ano-rectale ou coccygienne à composante sympathique).",
        "protocol_fr": "Phénotypage topographique pré-geste : douleur périnéale/génitale dans le territoire S2-S4 → ciblage TDM du nerf pudendal à l'épine ischiatique ou dans le canal d'Alcock ; douleur médiane ano-coccygienne/vulvo-périnéale sympathique → ciblage trans-sacro-coccygien ou latéro-coccygien du ganglion impar dans l'espace rétro-rectal • Cryoneurolyse en zone de transition thermique (-20°C à -70°C) préservant l'endonèvre.",
        "key_points_fr": [
            "Rappelle le fondement histologique clé de la cryoneurolyse : préservation de l'endonèvre et de la lame basale évitant toute névrite ou névrome de désafférentation.",
            "Distingue clairement les indications du nerf pudendal (somatique S2-S4) et du ganglion impar (sympathique médian), souvent complémentaires.",
            "Sécurité sphinctérienne préservée grâce à la précision du guidage TDM et à la réversibilité de la cryo-axonotmésis."
        ],
        "tags": ["Cryoneurolyse", "Nerf pudendal", "Ganglion impar", "Douleur pelvienne", "Axonotmésis", "J Pers Med 2025"]
    },
    "42263315": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "La neurolyse du ganglion impar potentialise l'efficacité de la radiofréquence pulsée du nerf pudendal dans la névralgie pudendale : étude de cohorte comparative (84 patientes)",
        "modality": "Scanner TDM / Fluoroscopie Interventionnelle",
        "intervention_type": "Traitement Combiné Nerf Pudendal + Neurolyse du Ganglion Impar",
        "cochin_link": "Appuie les gestes combinés « Traitement du nerf pudendal + neurolyse du ganglion impar » réalisés pour les douleurs périnéales mixtes somatiques et sympathiques à Cochin.",
        "summary_fr_short": "Étude de cohorte rétrospective comparative (*Pain Physician*, 2026, IF 3,1, 84 patientes) comparant le traitement isolé du nerf pudendal par radiofréquence pulsée (PRF, n = 40) à l'association PRF du nerf pudendal + neurolyse du ganglion impar (PRF + GIN, n = 44) : à 6 mois, le groupe combiné obtient une EVA significativement plus basse (2,09 vs 3,81, p < 0,05), un taux d'amélioration globale supérieur (73,7 % vs 56,1 %, p < 0,05) et une réduction marquée des scores d'anxiété-dépression (HADS) et de catastrophisme (PCS), sans complication.",
        "summary_fr_detailed": "L'efficacité parfois incomplète des gestes ciblant uniquement le tronc du nerf pudendal s'explique par l'intrication fréquente d'une sensibilisation sympathique pelvi-périnéale relayée par le ganglion impar (ganglion de Walther, terminaison impaire de la chaîne sympathique paravertébrale en avant de la jonction sacro-coccygienne). Sur 84 patientes suivies 6 mois, l'adjonction d'une neurolyse du ganglion impar au geste pudendal améliore significativement le contrôle douloureux à 6 mois (EVA moyenne 2,09 ± 1,38 vs 3,81 ± 1,85, p < 0,05 ; amélioration globale de la douleur de 73,7 % vs 56,1 %) ainsi que le retentissement émotionnel (HADS-A : 3,91 vs 6,54 ; PCS : 12,16 vs 19,52, p < 0,05), sans effet indésirable grave.",
        "protocol_fr": "Patient en procubitus • Temps 1 : Ciblage du nerf pudendal à l'épine sciatique / canal d'Alcock (stimulation sensitive 50 Hz < 0,5 V reproduisant la douleur périnéale, puis traitement pudendal par PRF ou cryoneurolyse) • Temps 2 (si composante brûlante périnéale postérieure/médiane ou hyperpathie sympathique) : Abord trans-discale sacro-coccygien ou paracéphalique coccygien du ganglion impar avec opacification rétro-rectale en « virgule » avant neurolyse.",
        "key_points_fr": [
            "Démontre la synergie anatomique et clinique entre le ciblage somatique (nerf pudendal) et sympathique (ganglion impar) dans la névralgie pudendale.",
            "Gain significatif à 6 mois sur l'EVA (2,09 vs 3,81) et sur le taux d'amélioration ressentie (73,7 % vs 56,1 %).",
            "Aucune complication sphinctérienne ou rectale grâce au contrôle d'imagerie en procubitus."
        ],
        "tags": ["Nerf pudendal", "Ganglion impar", "Névralgie pudendale", "Neurolyse combinée", "Radiofréquence pulsée", "Pain Physician 2026"]
    },
    "41594302": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "IRM pelvienne et neurographie par diffusion (DWI) dans la névralgie pudendale chronique : critères diagnostiques et pathologies associées sur 81 patients",
        "modality": "IRM Pelvienne & Neurographie IRM (DWI)",
        "intervention_type": "Bilan IRM Pré-Interventionnel du Nerf Pudendal & du Canal d'Alcock",
        "cochin_link": "Outil de référence pour l'interprétation des « IRM pelviennes et du nerf pudendal pré-infiltration / pré-cryoneurolyse » en Radiologie B à Cochin.",
        "summary_fr_short": "Étude radiologique sur 81 patients atteints de névralgie pudendale chronique (*Diagnostics*, janv. 2026, IF 3,0, Open-Access) évaluant un protocole d'IRM pelvienne incluant une neurographie par séquence de diffusion EPI (valeurs b = 0, 100 et 600 s/mm²) : détection d'anomalies de signal du nerf pudendal chez 51,9 % des patients (42/81, unilatérales dans 78,6 % des cas) et identification d'une cause anatomique compressive ou extrinsèque dans 54,8 % des cas positifs.",
        "summary_fr_detailed": "Bien que le diagnostic de névralgie pudendale repose sur les critères cliniques de Nantes, l'IRM pelvienne est indispensable avant tout geste de cryoneurolyse ou de décompression pour éliminer une lésion tumorale, kystique ou endométriosique et localiser le site exact du conflit canalaire. En intégrant une séquence de diffusion écho-planaire (DWI-EPI avec b = 0, 100 et 600) supprimant le signal vasculaire pour rehausser sélectivement les faisceaux nerveux, les auteurs mettent en évidence une hyperintensité ou un épaississement focal du nerf pudendal chez 42 des 81 patients (33 unilatéraux, 9 bilatéraux), permettant de guider précisément l'étage du bloc et de la cryoneurolyse TDM (pince ligamentaire rétro-sciatique vs canal d'Alcock).",
        "protocol_fr": "IRM pelvienne haute résolution (1,5T ou 3T) : séquences pondérées T2 FSE multiplanaires fines centrées sur la grande échancrure sciatique, l'épine ischiatique, la pince sacro-épineuse/sacro-tubérale et le canal pudendal d'Alcock • Séquence de neurographie par diffusion DWI-EPI (b = 0, 100, 600 s/mm²) permettant de suivre le trajet nerveux et d'identifier les asymétries de calibre/signal avant la cryoneurolyse TDM.",
        "key_points_fr": [
            "La séquence DWI (b = 0, 100, 600) améliore nettement la conspicuité du nerf pudendal et détecte une anomalie focale dans plus de la moitié des névralgies pudendales chroniques.",
            "Identifie une étiologie anatomique ou compressive associée chez plus d'un patient sur deux présentant une anomalie DWI.",
            "Permet de cibler avec précision le site du conflit (pince ligamentaire ischiatique vs canal d'Alcock) lors de la cryoneurolyse sous scanner."
        ],
        "tags": ["IRM pelvienne", "Neurographie IRM", "Diffusion DWI", "Nerf pudendal", "Canal d'Alcock", "Diagnostics 2026"]
    },
    "32602380": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Cryoablation percutanée bilatérale des nerfs pudendaux guidée par scanner pour le traitement palliatif des douleurs pelviennes oncologiques réfractaires",
        "modality": "Scanner Interventionnel (TDM)",
        "intervention_type": "Cryoneurolyse Bilatérale des Nerfs Pudendaux sous Scanner (Oncologie)",
        "cochin_link": "Correspond aux demandes de « Cryoneurolyse pudendale bilatérale antalgique en hospitalisation pour néoplasie pelvienne » prises en charge au scanner de Cochin.",
        "summary_fr_short": "Série clinique (*Am J Hosp Palliat Care*, 2020, IF 1,9, équipe J.D. Prologo) évaluant la cryoablation percutanée bilatérale en un temps des nerfs pudendaux sous scanner chez des patients hospitalisés en crise hyperalgique pour cancer pelvien évolué : succès technique de 100 %, chute moyenne de 5,2 points sur l'échelle de douleur maximale (p = 0,003), sortie d'hospitalisation en 2,3 jours en moyenne et 0 % de complication sphinctérienne ou procédurale.",
        "summary_fr_detailed": "Les tumeurs pelviennes localement avancées (rectum, col utérin, prostate, sarcomes pelviens, métastases sacrées) entraînent fréquemment des douleurs périnéales bilatérales intolérables nécessitant des hospitalisations prolongées sous opioïdes parentéraux à haute dose. Cette étude évalue la faisabilité et la sécurité d'une cryoneurolyse bilatérale simultanée des nerfs pudendaux sous guidage TDM chez 10 patients hospitalisés en impasse antalgique. Toutes les sondes ont été positionnées avec succès dans les canaux d'Alcock droit et gauche, entraînant une réduction immédiate et majeure du score de douleur maximale (-5,2 points sur 10, p = 0,003), autorisant un retour rapide à domicile (délai moyen de sortie : 2,3 jours post-procédure) sans aucune complication urinaire, fécale ou motrice.",
        "protocol_fr": "Patient en procubitus sous sédation consciente ou anesthésie locale au scanner • Ponction bilatérale symétrique par voie transglutéale vers le canal d'Alcock / épine ischiatique • Positionnement d'une cryosonde au contact de chaque nerf pudendal avec contrôle TDM de la distance au rectum • Protocole de congélation bilatérale (2 cycles de congélation séparés par décongélation).",
        "key_points_fr": [
            "Démontre qu'une cryoneurolyse pudendale bilatérale en une seule séance est sûre (0 % d'incontinence ou de complication) et extrêmement efficace (-5,2 points d'EVA, p = 0,003).",
            "Permet une sortie rapide d'hospitalisation (moyenne 2,3 jours) chez des patients oncologiques hyperalgiques alités.",
            "Alternative mini-invasive majeure aux pompes intrathécales chez les patients atteints d'envahissement tumoral pelvi-périnéal."
        ],
        "tags": ["Cryoneurolyse bilatérale", "Nerf pudendal", "Douleur oncologique", "Cancer pelvien", "Soins palliatifs", "Scanner TDM"]
    },
    "25511935": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Étude princeps : cryoablation percutanée du nerf pudendal guidée par scanner dans le traitement de la névralgie pudendale réfractaire (Prologo et al.)",
        "modality": "Scanner Interventionnel (TDM)",
        "intervention_type": "Cryoneurolyse Percutanée du Nerf Pudendal sous Scanner (Protocole Princeps)",
        "cochin_link": "Article fondateur de la technique de « Cryoneurolyse percutanée du nerf pudendal sous scanner » appliquée en Radiologie Interventionnelle à Cochin.",
        "summary_fr_short": "Étude pilote historique (*Skeletal Radiology*, 2015, IF 1,9, Prologo et al.) ayant établi le protocole de cryoablation percutanée TDM du nerf pudendal dans la névralgie pudendale réfractaire : chute spectaculaire de l'EVA douleur de 7,6/10 avant le geste à 2,6 dès 24 h, 3,5 à J45 et 3,1 à 6 mois (p < 0,005), sans aucune complication procédurale.",
        "summary_fr_detailed": "Publication princeps ayant introduit en radiologie interventionnelle musculo-squelettique la cryoneurolyse percutanée sous scanner du nerf pudendal. Onze patients souffrant de névralgie pudendale sévère réfractaire (douleur moyenne 7,6/10 à type de brûlure dans 80 % des cas et de pression insupportable en position assise dans 84,5 % des cas) et répondeurs à un bloc test ont été traités par cryoablation TDM dans le canal d'Alcock / épine ischiatique. Les questionnaires Brief Pain Inventory (BPI) démontrent un effondrement rapide et soutenu de l'intensité douloureuse à 24 h (2,6/10), 45 jours (3,5/10) et 6 mois (3,1/10, p < 0,005) avec amélioration fonctionnelle majeure et 0 % de complication.",
        "protocol_fr": "Patient en procubitus au scanner • Repérage TDM du canal pudendal (Alcock) le long de la paroi latérale de la fosse ischio-rectale au bord médial du muscle obturateur interne • Insertion coaxiale d'une cryosonde 17G • Cycle de congélation en deux temps (8 min de congélation, 4 min de décongélation passive, puis 8 min de congélation dans le protocole princeps, adapté aujourd'hui en cycles de 2 à 3 min selon la sonde) sous contrôle TDM de la boule de glace.",
        "key_points_fr": [
            "Publication fondatrice de J.D. Prologo dans Skeletal Radiology démontrant la faisabilité et la sécurité du ciblage cryoablatif du nerf pudendal sous scanner.",
            "Réduction de plus de 60 % de l'intensité douloureuse dès 24 heures, maintenue à 6 mois (EVA de 7,6 à 3,1, p < 0,005).",
            "Aucune complication sphinctérienne, motrice ou cutanée rapportée."
        ],
        "tags": ["Étude princeps", "Cryoneurolyse", "Nerf pudendal", "Névralgie pudendale", "Prologo", "Skeletal Radiol 2015"]
    },
    "42995340": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Déterminants du nombre d'acquisitions fluoroscopiques et optimisation standardisée du workflow lors du vissage pelvien percutané assisté par robot (601 patients)",
        "modality": "Fluoroscopie 2D/3D & Assistance Robotique / Navigation",
        "intervention_type": "Vissage Percutané des Couloirs Osseux Pelviens (Ilio-Sacré S1/S2 & Colonnes)",
        "cochin_link": "Directement applicable aux « Vissages percutanés du bassin (couloirs ilio-sacrés S1/S2 et colonnes acétabulaires) sous scopie Allura / guidage 3D » réalisés à l'Hôpital Cochin.",
        "summary_fr_short": "Vaste cohorte rétrospective monocentrique (*Journal of Robotic Surgery*, nov. 2026, IF 2,2, 601 patients : 312 avant et 289 après optimisation) identifiant les 4 facteurs indépendants augmentant le recours à la scopie lors du vissage pelvien percutané (surface osseuse oblique au point d'entrée cortical IRR = 1,52, courbe d'apprentissage des 10 premiers cas IRR = 1,48, vissage du couloir S2 IRR = 1,26 et obésité IMC ≥ 30 IRR = 1,19) et démontrant qu'un protocole standardisé réduit de 27 % le nombre de clichés et le temps de scopie (16,2 s vs 21,8 s, p < 0,001) avec 98,7 % de précision intra-osseuse.",
        "summary_fr_detailed": "Même avec une planification 3D ou une assistance robotique, l'exposition radique peropératoire varie fortement lors du vissage percutané des couloirs osseux du bassin. Sur 601 patients consécutifs, la régression binomiale négative multivariée (Partie A) démontre que le dérapage de la broche sur une corticale oblique au point d'entrée (IRR = 1,52, p < 0,001), le vissage du couloir S2 plus étroit (IRR = 1,26, p = 0,001), l'obésité (IRR = 1,19, p = 0,026) et l'expérience initiale de l'opérateur (IRR = 1,48, p < 0,001) sont les principaux déterminants de la surconsommation fluoroscopique. En introduisant un protocole d'optimisation ciblé (ancrage franc anti-dérapage sur corticale oblique, standardisation des incidences inlet/outlet/profil avant insertion), l'équipe réduit de 27 % la fréquence fluoroscopique (9,8 vs 13,5 tirs, p < 0,001) et de 31,5 % dans le sous-groupe à entrée corticale oblique, tout en maintenant un taux d'excellence de trajectoire de 98,7 %.",
        "protocol_fr": "Repérage pré-procédural de l'obliquité de la table externe iliaque au point d'entrée (couloirs S1, S2, rétrograde/antérograde de colonne antérieure) • Utilisation d'une canule biseautée crantée ou d'un pré-forage cortical perpendiculaire pour prévenir le glissement tangentiel de la broche-guide (bénéfice maximal : -31,5 % de scopie) • Acquisition séquentielle standardisée des vues fluoroscopiques de contrôle (inlet, outlet, profil sacré strict / obturateur-iliaque) • Vérification particulière de la sécurité foraminale sur le corridor S2.",
        "key_points_fr": [
            "Plus grande série analysant quantitativement les facteurs de difficulté technique du vissage pelvien percutané (601 patients, 98,7 % de précision).",
            "L'obliquité corticale au point d'entrée (IRR 1,52) et le corridor S2 (IRR 1,26) sont les deux défis anatomiques majeurs majorant le temps de scopie.",
            "Un protocole anti-dérapage au point d'entrée cortical réduit de 31,5 % le nombre de clichés sur les surfaces obliques et abaisse le temps de scopie moyen à 16,2 secondes.",
            "Enseignements techniques directement transposables au vissage pelvien percutané sous scopie/scanner pratiqué à Cochin."
        ],
        "tags": ["Vissage pelvien percutané", "Couloir S1 S2", "Radioprotection", "Fluoroscopie", "Assistance robotique", "J Robot Surg 2026"]
    },
    "42545485": {
        "category_id": "msk_biopsy",
        "title_fr": "Rôle et rentabilité d'une seconde biopsie disco-vertébrale guidée par scanner après un premier prélèvement négatif dans les suspicions de spondylodiscite infectieuse",
        "modality": "Scanner Interventionnel (TDM)",
        "intervention_type": "Biopsie Disco-Vertébrale Percutanée & Re-Biopsie sous Scanner",
        "cochin_link": "Répond directement aux demandes de « Seconde biopsie disco-vertébrale sous scanner après une première biopsie négative » fréquemment discutées avec l'infectiologie et la rhumatologie à Cochin.",
        "summary_fr_short": "Étude observationnelle en centre tertiaire (*Skeletal Radiology*, août/nov. 2026, IF 1,9, 93 biopsies chez 79 patients) évaluant la rentabilité microbiologique d'une seconde biopsie disco-vertébrale sous scanner après un premier prélèvement négatif : rendement initial de 53,2 % (42/79) et positivité de la seconde biopsie dans 35,7 % des cas (5/14), portant le taux d'identification global à 59,5 %, avec la CRP élevée comme principal facteur prédictif (médiane 40 vs 20 mg/L, p = 0,008 ; rendement de 80 % dans les spondylodiscites post-opératoires).",
        "summary_fr_detailed": "Lorsqu'une première biopsie disco-vertébrale sous scanner revient stérile chez un patient présentant une forte suspicion clinique et IRM de spondylodiscite infectieuse, l'utilité d'un second prélèvement percutané est souvent débattue. Sur 79 patients consécutifs (93 biopsies après exclusion des tumeurs et arthropathies microcristallines), la première biopsie TDM identifie le germe dans 53,2 % des cas (IC 95 % : 42,3–63,8 %). Parmi les 14 patients ayant bénéficié d'une seconde biopsie TDM, 5 (35,7 %, p = 0,36 par rapport à la 1re biopsie) ont permis d'isoler l'agent pathogène, élevant le rendement cumulé à 59,5 %. Un taux élevé de CRP au moment du geste est indépendamment associé à la positivité microbiologique (OR ajusté = 1,57 par unité log-CRP, p = 0,043), et le rendement atteint 80 % (4/5) dans les infections rachidiennes post-chirurgicales.",
        "protocol_fr": "Vérification préalable des hémocultures (concordantes dans 85,7 % des cas lorsqu'elles sont positives) et dosage de la CRP • En cas de 1re biopsie négative avec suspicion persistante ou échec probabiliste : re-biopsie sous scanner en modifiant la cible (ciblage controlatéral ou d'une collection épidurale/paravertébrale/psoas nouvellement organisée, carottage sous-chondral des deux plateaux + aspiration discale) • Envoi couplé en bactériologie prolongée, mycobactériologie, anatomopathologie et PCR ARN 16S.",
        "key_points_fr": [
            "Une seconde biopsie disco-vertébrale sous scanner est positive dans plus d'un tiers des cas (35,7 %) après un premier prélèvement négatif, faisant passer le diagnostic microbiologique global de 53,2 % à 59,5 %.",
            "Un syndrome inflammatoire biologique marqué (CRP médiane ≥ 40 mg/L vs 20 mg/L, p = 0,008) et un contexte post-chirurgical (80 % de positivité) prédisent fortement le succès du prélèvement.",
            "Justifie pleinement la réalisation d'une 2e biopsie sous scanner à Cochin en cas de négativité initiale lorsque les hémocultures sont stériles et la suspicion clinique persistante."
        ],
        "tags": ["Spondylodiscite", "Seconde biopsie", "Biopsie disco-vertébrale", "Scanner interventionnel", "CRP", "Skeletal Radiol 2026"]
    },
    "42530616": {
        "category_id": "msk_imaging",
        "title_fr": "Métriques du coefficient de diffusion apparent (ADC) en IRM pour évaluer la réponse histopathologique des sarcomes des parties molles : reproductibilité et valeur pronostique",
        "modality": "IRM Multiparamétrique (1,5T / 3T) & Diffusion (DWI / ADC)",
        "intervention_type": "Bilan IRM de Réponse Thérapeutique & Planification de Biopsie Ciblée des Sarcomes",
        "cochin_link": "Outil clé pour l'interprétation des « IRM de suivi de sarcomes des parties molles sous traitement néoadjuvant et le ciblage des zones de bas ADC (haute cellularité résiduelle) lors des biopsies sous scanner/écho » à Cochin.",
        "summary_fr_short": "Étude radio-histopathologique (*Skeletal Radiology*, juil./nov. 2026, IF 1,9, Open-Access) évaluant à 3 lecteurs indépendants la reproductibilité et la valeur prédictive de l'ADC (b = 200 et 800 s/mm²) dans les sarcomes des parties molles (STS) traités avant chirurgie : excellente reproductibilité inter-observateur de l'ADC tumoral moyen (ICC = 0,91–0,95) et distinction hautement significative des bons répondeurs histologiques (ADC médian post-traitement 2,39 vs 1,50 × 10⁻³ mm²/s chez les non-répondeurs, p = 0,02 ; OR = 20,3 à 33,1), avec corrélation inverse directe au pourcentage de cellules tumorales viables.",
        "summary_fr_detailed": "Dans les sarcomes des parties molles (STS), les critères dimensionnels RECIST sous-estiment fréquemment la réponse histologique en raison de la nécrose hémorragique, de la fibrose ou de la dégénérescence myxoïde induites par la radiothérapie ou les traitements focaux. Trois radiologues ostéo-articulaires indépendants ont mesuré l'ADC tumoral global et sous-régional (zones de haut ADC nécrotiques et zones de bas ADC hypercellulaires) sur l'IRM de diffusion (b = 200, 800 s/mm²) avant et après traitement néoadjuvant, avec corrélation à la pièce d'exérèse chirurgicale. La mesure de l'ADC moyen sur un temps donné présente une reproductibilité quasi parfaite (ICC = 0,91–0,95). Après traitement, un ADC moyen élevé (médiane 2,39 × 10⁻³ mm²/s contre 1,50 × 10⁻³ mm²/s, p = 0,02) est le meilleur facteur prédictif de réponse histopathologique majeure (OR = 20,3 à 33,1, p < 0,05) et corrèle inversement au contingent cellulaire viable résiduel.",
        "protocol_fr": "IRM des parties molles 1,5T ou 3T incluant une séquence de diffusion DWI (valeurs b = 200 et 800 s/mm² permettant d'éliminer l'effet de microperfusion capillaire à bas b) • Cartographie ADC quantitative sur le volume tumoral global (plus reproductible que le delta longitudinal sous-régional, ICC 0,91–0,95) • Repérage des nodules résiduels de bas ADC (< 1,5 × 10⁻³ mm²/s) correspondant aux foyers de cellules sarcomateuses viables pour guider une biopsie percutanée ou un complément d'ablation.",
        "key_points_fr": [
            "Excellente reproductibilité inter-observateur de l'ADC tumoral moyen (ICC = 0,91–0,95) avec le couple de valeurs b = 200 et 800 s/mm².",
            "Seuil discriminant net après traitement : ADC médian de 2,39 × 10⁻³ mm²/s chez les répondeurs histologiques contre 1,50 × 10⁻³ mm²/s chez les non-répondeurs (OR > 20).",
            "Corrélation inverse directe entre la valeur d'ADC et le pourcentage de cellules tumorales viables sur la pièce opératoire.",
            "Indispensable en RCP Sarcomes à Cochin tant pour évaluer la réponse néoadjuvante que pour cibler les zones viables (bas ADC) lors des biopsies."
        ],
        "tags": ["Sarcome des parties molles", "IRM de diffusion", "ADC", "Réponse thérapeutique", "Reproductibilité", "Skeletal Radiol 2026"]
    },
    "42570570": {
        "category_id": "msk_biopsy",
        "title_fr": "Essai randomisé contrôlé comparant le rendement diagnostique et la sécurité des trocarts de biopsie vertébrale transpédiculaire 8G versus 11G dans les spondylodiscites tuberculeuses (50 patients)",
        "modality": "Fluoroscopie / Scanner Interventionnel",
        "intervention_type": "Biopsie Osseuse Vertébrale Transpédiculaire (Choix du Calibre 8G vs 11G)",
        "cochin_link": "Guide directement le choix du matériel (« Trocart osseux 11G vs 8G en biopsie vertébrale transpédiculaire ») au scanner interventionnel de Cochin.",
        "summary_fr_short": "Essai prospectif randomisé contrôlé (*Clinical Radiology*, juil./oct. 2026, IF 2,1, 50 patients randomisés 1:1) comparant les trocarts de biopsie vertébrale transpédiculaire 8G (n = 25) et 11G (n = 25) dans les suspicions de spondylodiscite tuberculeuse : rendement diagnostique global équivalent (52 % vs 48 %, p = 0,62), positivité histologique (40 % vs 36 %, p = 0,88) et microbiologique GeneXpert/PCR/culture liquide (32 % vs 24 %, p > 0,05) non significativement différentes, avec 1 pneumothorax dans le groupe 8G contre 0 complication en 11G.",
        "summary_fr_detailed": "Le choix du calibre du trocart lors d'une biopsie vertébrale transpédiculaire doit concilier la taille de la carotte ostéo-médullaire et le risque traumatique pédiculaire ou pleural. Cet essai randomisé compare deux calibres usuels (8 Gauge de gros calibre versus 11 Gauge intermédiaire) chez 50 patients consécutifs suspects de mal de Pott rachidien, évalués conjointement par histopathologie (granulomes épithélioïdes et giganto-cellulaires avec nécrose caséeuse), test moléculaire rapide GeneXpert MTB/RIF, PCR et culture en milieu liquide. Le taux de prélèvements contributifs ne diffère pas significativement entre 8G et 11G (13/25 vs 12/25 diagnostics formels, p = 0,62 ; échantillons inadéquats : 2/25 vs 4/25), tandis que le seul événement indésirable (pneumothorax) est survenu dans le bras 8G.",
        "protocol_fr": "Abord transpédiculaire sous guidage imagerie • Le trocart 11G offre le meilleur compromis sécurité/rendement (particulièrement à l'étage thoracique ou sur des pédicules étroits), permettant des prélèvements multiples par déflexion angulaire sans sur-risque cortical ou pleural • Association systématique sur les carottes osseuses de l'histopathologie, du test moléculaire rapide (GeneXpert / PCR) et des cultures spécifiques.",
        "key_points_fr": [
            "Premier essai randomisé contrôlé face-à-face démontrant qu'un trocart 11G fait aussi bien qu'un trocart 8G pour le diagnostic histologique et moléculaire des spondylodiscites granulomateuses (p = 0,62).",
            "L'association histologie + biologie moléculaire (GeneXpert/PCR) est indispensable car la microbiologie seule n'est positive que dans 24 à 32 % des formes paucibacillaires.",
            "Conforte l'utilisation préférentielle des systèmes coaxiaux 11G–13G en biopsie rachidienne transpédiculaire sous scanner à Cochin, alliant rendement élevé et sécurité maximale."
        ],
        "tags": ["Biopsie vertébrale", "Abord transpédiculaire", "Calibre 8G vs 11G", "Essai randomisé", "Spondylodiscite tuberculeuse", "Clin Radiol 2026"]
    },
    "42563407": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Traitement ablatif non invasif des tumeurs desmoïdes de la paroi abdominale par ultrasons focalisés de haute intensité (HIFU) : résultats à long terme sur 55 patients",
        "modality": "Ultrasons Focalisés de Haute Intensité (HIFU) / Imagerie de Suivi IRM",
        "intervention_type": "Ablation Thermique Ciblée des Tumeurs Desmoïdes de la Paroi Abdominale",
        "cochin_link": "Complète la discussion de RCP Sarcomes / Tumeurs Desmoïdes à Cochin (« Cryoablation percutanée vs autres modalités d'ablation thermique des tumeurs desmoïdes pariétales abdominales »).",
        "summary_fr_short": "Cohorte de 55 tumeurs desmoïdes de la paroi abdominale (46 primitives, 9 récidivantes après chirurgie) suivies pendant une médiane de 58 mois (*International Journal of Hyperthermia*, août/déc. 2026, IF 3,1) : taux de contrôle local (DCR) de 98 % (54/55) et taux de réponse objective (ORR) de 82 % (87 % chez les patients naïfs de chirurgie contre 56 % sur les récidives post-chirurgicales), confirmant la haute sensibilité des fibromatoses desmoïdes pariétales aux ablations thermiques guidées par l'image.",
        "summary_fr_detailed": "Les tumeurs desmoïdes de la paroi abdominale surviennent fréquemment chez la femme jeune (notamment en post-partum ou sur cicatrice de césarienne) et progressent régulièrement sous surveillance active, tandis que l'exérèse chirurgicale pariétale expose à des récidives locales fréquentes et à des éventrations prothétiques. Sur 55 patientes suivies près de 5 ans (médiane 58 mois), l'ablation thermique par HIFU obtient une nécrose volumique médiane de 61 % dès 1 mois, un taux de réponse objective (ORR) de 82 % (45/55) et un contrôle de la maladie (DCR) de 98 % (54/55). Point stratégique majeur : le taux de réponse objective est nettement supérieur lorsque l'ablation thermique est réalisée en première ligne sur une tumeur naïve (87 %) plutôt qu'en rattrapage sur une récidive post-chirurgicale remaniée par la fibrose cicatricielle (56 %).",
        "protocol_fr": "IRM pariétale abdominale pré-thérapeutique avec séquences T2 (évaluation de l'hypercellularité en hypersignal T2) et T1 gadolinium • Ablation thermique guidée par l'image (à Cochin : cryoablation percutanée sous scanner/échographie avec visualisation directe de l'iceball et hydrodissection péritonéale/cutanée ; ou HIFU selon plateau) • Évaluation IRM à 1, 3, 6 et 12 mois selon les critères mRECIST (volume dévascularisé non rehaussé).",
        "key_points_fr": [
            "Contrôle tumoral durable de 98 % à près de 5 ans de suivi médian (58 mois) sur 55 tumeurs desmoïdes de la paroi abdominale.",
            "Efficacité supérieure en première intention chez les patients naïfs de chirurgie (ORR 87 %) par rapport aux récidives post-opératoires (ORR 56 %), plaidant pour une ablation guidée par l'image précoce dès progression sous surveillance active.",
            "Renforce les arguments en RCP Sarcomes pour proposer une ablation focale (cryoablation percutanée à Cochin) plutôt qu'une chirurgie pariétale délabrante."
        ],
        "tags": ["Tumeur desmoïde", "Paroi abdominale", "Ablation thermique", "HIFU", "Contrôle local à long terme", "Int J Hyperthermia 2026"]
    },
    "42491099": {
        "category_id": "ablation_benign",
        "title_fr": "Efficacité de l'ablation par micro-ondes (MWA) in situ combinée au curetage intralésionnel pour les tumeurs osseuses bénignes localement agressives (TCG, KOA, chondroblastome) : étude comparative sur 284 patients",
        "modality": "Ablation par Micro-Ondes (MWA) / Guidage Imagerie & Chirurgie Conservatrice",
        "intervention_type": "Thermoablation par Micro-Ondes (MWA) des Tumeurs à Cellules Géantes, Chondroblastomes & KOA",
        "cochin_link": "En lien direct avec la prise en charge des « Tumeurs osseuses bénignes localement agressives (chondroblastome, tumeur à cellules géantes TCG, KOA) par thermoablation » à l'Hôpital Cochin.",
        "summary_fr_short": "Importante étude de cohorte comparative (*American Journal of Translational Research*, juin 2026, IF 1,7, Open-Access, 284 patients) comparant l'ablation thermique par micro-ondes (MWA) in situ associée au curetage (n = 156) au curetage seul (n = 128) dans les TCG, chondroblastomes et KOA : division par plus de deux du taux de récidive locale (7,1 % vs 18,0 %, p = 0,008 ; HR multivarié = 0,25, p < 0,001), consolidation osseuse accélérée (4,3 vs 5,0 mois, p < 0,001) et réduction par trois des retards de consolidation (5,8 % vs 18,8 %, p = 0,001).",
        "summary_fr_detailed": "Les tumeurs osseuses bénignes localement agressives (tumeurs à cellules géantes de l'os [TCG], chondroblastomes épiphysaires et kystes osseux anévrismaux [KOA]) présentent un taux élevé de récidive locale après simple curetage mécanique (18 % dans cette série). Sur 284 patients, l'inactivation thermique préalable in situ par antennes micro-ondes (MWA) réduit drastiquement le taux de récidive locale à 7,1 % (contre 18,0 %, p = 0,008 ; survie sans récidive HR = 0,38). En analyse de Cox multivariée, la thermoablation par micro-ondes est un facteur protecteur indépendant majeur contre la récidive (HR = 0,25, p < 0,001), tandis qu'un diamètre > 6 cm, une destruction corticale étendue et un envahissement des parties molles sont les principaux facteurs de risque. Le bénéfice de la thermoablation est particulièrement marqué dans les lésions volumineuses.",
        "protocol_fr": "Insertion d'antennes de micro-ondes (ou sondes de RF/cryoablation en percutané exclusif à Cochin pour les chondroblastomes et récidives de TCG accessibles) au sein de la cavité tumorale • Inactivation thermique contrôlée des berges spongieuses contenant les nids microscopiques de cellules géantes/chondroblastiques tout en protégeant le cartilage sous-chondral par refroidissement continu au sérum physiologique glacé • Comblement cavitaire reconstructeur.",
        "key_points_fr": [
            "Série majeure (284 patients) démontrant que l'adjonction d'une thermoablation (MWA) divise par 4 le risque indépendant de récidive locale (HR = 0,25 ; taux de récidive abaissé de 18,0 % à 7,1 %).",
            "Identifie les 3 facteurs pronostiques de récidive à rechercher sur l'IRM/TDM pré-thérapeutique : diamètre > 6 cm, rupture corticale étendue et extension aux parties molles.",
            "Accélère significativement la consolidation osseuse (4,3 mois vs 5,0 mois) avec un excellent score fonctionnel MSTS."
        ],
        "tags": ["Ablation micro-ondes", "MWA", "Tumeur à cellules géantes", "Chondroblastome", "Kyste osseux anévrismal", "Récidive locale", "2026"]
    },
    "42698683": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Radiofréquence refroidie (Cooled RFA) des nerfs géniculés pour les douleurs chroniques post-chirurgicales persistantes après prothèse totale de genou (PTG) : essai clinique pilote de phase I/IIa",
        "modality": "Échographie / Fluoroscopie Interventionnelle",
        "intervention_type": "Radiofréquence Refroidie (Coolief®) des Nerfs Géniculés sur Genou Prothésé (PTG)",
        "cochin_link": "Correspond directement aux indications de « Test anesthésique sous écho + Radiofréquence / Cryoneurolyse des nerfs géniculés sur genou prothésé douloureux chronique » de l'Agenda Cochin.",
        "summary_fr_short": "Essai clinique prospectif de phase I/IIa enregistré (*Asia-Pacific Journal of Sports Medicine, Arthroscopy, Rehabilitation and Technology*, août/oct. 2026, IF 1,7, Open-Access) évaluant la radiofréquence refroidie (Cooled RFA, système Coolief®) des nerfs géniculés chez des patients souffrant de douleur post-chirurgicale chronique réfractaire (NRS ≥ 5 depuis ≥ 6 mois) après prothèse totale de genou (PTG) et répondeurs à un bloc test géniculé (≥ 50 %) : réduction constante de la douleur et amélioration cliniquement pertinente à 6 mois avec 0 % d'événement indésirable ou d'infection péri-prothétique.",
        "summary_fr_detailed": "Jusqu'à 15 à 20 % des patients opérés d'une prothèse totale de genou (PTG) développent des douleurs chroniques post-chirurgicales (CPSP) sans descellement mécanique ni infection, réfractaires aux antalgiques. Cet essai clinique prospectif de phase I/IIa (jRCTs052230123) évalue de manière rigoureuse la sécurité et l'efficacité à 6 mois de la radiofréquence refroidie (CRFA, Coolief®) ciblant les nerfs géniculés chez des patients présentant un NRS ≥ 5 persistant plus de 6 mois après PTG et ayant répondu positivement (baisse ≥ 50 %) à un bloc diagnostique préalable des nerfs géniculés. L'étude confirme une tolérance parfaite (aucun événement indésirable, aucune complication cutanée ou infectieuse au voisinage des implants prothétiques) et une réduction cliniquement significative de la douleur avec tendance à l'amélioration du Knee Society Score (KSS 2011) à 6 mois.",
        "protocol_fr": "Élimination préalable d'un descellement septique ou mécanique de la PTG • Bloc anesthésique diagnostique sous échographie des nerfs géniculés supéro-médial (SMGN), supéro-latéral (SLGN) et inféro-médial (IMGN) exigeant ≥ 50 % de soulagement • Asepsie chirurgicale stricte (présence de matériel prothétique) • Radiofréquence refroidie (sondes Coolief® 17G à circulation d'eau interne, température de consigne 60°C générant une température tissulaire de ~80°C et une lésion sphérique large couvrant la variabilité anatomique post-chirurgicale des branches géniculées).",
        "key_points_fr": [
            "Valide prospectivement la sécurité absolue (0 % de complication ou d'infection péri-prothétique) de la radiofréquence refroidie des nerfs géniculés sur genou porteur de PTG.",
            "Souligne l'importance d'un bloc diagnostique positif (≥ 50 % de réduction du NRS) pour sélectionner les douleurs neuropathiques/nociceptives capsulaires post-PTG.",
            "La géométrie sphérique élargie de la radiofréquence refroidie (ou de l'iceball en cryoneurolyse) est particulièrement adaptée aux remaniements fibreux péri-prothétiques après PTG."
        ],
        "tags": ["Nerfs géniculés", "Radiofréquence refroidie", "Prothèse totale de genou", "Douleur post-chirurgicale", "Coolief", "2026"]
    },
    "42521887": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Reconstruction percutanée « trépied » (vissage des 3 colonnes + cimentoplastie) combinée à l'ablation thermique par micro-ondes (MWA) pour les métastases péri-acétabulaires : résultats cliniques à long terme (31 patients)",
        "modality": "Scanner TDM / Fluoroscopie Interventionnelle",
        "intervention_type": "Ablation par Micro-Ondes (MWA) + Vissage Percutané Trépied du Cotyle & Cimentoplastie",
        "cochin_link": "En lien direct avec les procédures combinées de « Debulking tumoral par ablation thermique + Vissage percutané du bassin / cotyle et cimentoplastie en un temps » réalisées au scanner interventionnel de Cochin.",
        "summary_fr_short": "Étude de suivi à long terme (*International Orthopaedics*, juil. 2026, IF 2,0, 31 patients) évaluant l'association d'une ablation thermique locale par micro-ondes (MWA) et d'une ostéosynthèse percutanée en « trépied » (vissage des colonnes antérieure, postérieure et trans-iliaque du cotyle avec cimentoplastie) pour les métastases péri-acétabulaires : chute rapide et durable de l'EVA (5,85 en pré-opératoire à 2,48 à 3 mois, 1,22 à 6 mois et 1,59 à 12 mois, p < 0,001), amélioration significative du statut fonctionnel ECOG (2,44 à 1,50), reprise de la marche autonome chez 67,7 % des patients (et 22,6 % avec aide légère), 0 % de démontage mécanique, 0 % d'infection et aucun retard de traitement systémique oncologique.",
        "summary_fr_detailed": "Les métastases lytiques du toit et des colonnes du cotyle (zones II de Harrington) entraînent une impotence fonctionnelle majeure avec risque d'impaction prothétique ou de protrusion acétabulaire, alors que la reconstruction chirurgicale ouverte (prothèse massive de hanche de type Harrington) expose à des pertes sanguines importantes, un taux élevé d'infection et une interruption prolongée des thérapies systémiques. Dans cette cohorte de 31 patients suivis à long terme (survie médiane de 35,0 mois), l'approche combinée 100 % percutanée associe une inactivation tumorale par micro-ondes (MWA) au sein de la lésion acétabulaire et un montage mécanique en « trépied » (vis canulées de gros calibre armant le dôme acétabulaire selon les 3 axes de force ilio-pubien, ilio-ischiatique et supra-acétabulaire, complétées par une acétabuloplastie au ciment PMMA). L'effet antalgique et mécanique se maintient au-delà d'un an (jusqu'à 41 mois) sans aucun échec d'implant ni nécessité de conversion en prothèse totale de hanche.",
        "protocol_fr": "Planification TDM 3D des couloirs osseux péri-acétabulaires (colonne antérieure pubienne, colonne postérieure ischiatique, couloir supra-acétabulaire iliaque) • Sous anesthésie générale, ablation thermique première de la masse tumorale ostéolytique (MWA ou cryoablation de debulking à Cochin) • Mise en place percutanée sur broches guides des 3 vis canulées convergentes au-dessus du toit du cotyle (configuration Tripod) • Injection de ciment PMMA haute viscosité (cimentoplastie d'ancrage) solidarisant les vis et comblant la cavité ablatée • Remise en charge précoce dès J1–J2 sans interrompre la chimiothérapie ou l'immunothérapie.",
        "key_points_fr": [
            "Démontre la durabilité mécanique à long terme (0 % de faillite d'implant, 0 % de conversion en PTH sur un suivi allant jusqu'à 41 mois) du montage percutané « Tripod » couplé à l'ablation thermique.",
            "Réduction rapide et soutenue de la douleur (EVA passant de 5,85 à 1,22 à 6 mois, p < 0,001) permettant une reprise de la marche chez 90,3 % des patients (67,7 % sans aide).",
            "Zéro infection et zéro retard à la reprise du traitement systémique antitumoral, contrairement à la chirurgie ouverte de reconstruction acétabulaire."
        ],
        "tags": ["Métastases péri-acétabulaires", "Vissage trépied", "Cotyle", "Ablation micro-ondes", "Cimentoplastie", "Int Orthop 2026"]
    },
    "42128340": {
        "category_id": "ablation_benign",
        "title_fr": "Cryoablation versus Radiofréquence (RFA) pour le traitement de l'ostéome ostéoïde primitif et récidivant : étude comparative sur 99 procédures (JVIR 2026)",
        "modality": "Scanner TDM Interventionnel",
        "intervention_type": "Cryoablation vs Radiofréquence (RFA) d'Ostéome Ostéoïde",
        "cochin_link": "Référence comparative directe pour l'arbitrage entre « Radiofréquence (RFA) et Cryoablation d'ostéome ostéoïde (notamment localisations atypiques, intra-articulaires ou récidivantes) » en HDJ Radio B à Cochin.",
        "summary_fr_short": "Étude comparative directe (*Journal of Vascular and Interventional Radiology — JVIR*, mai/sept. 2026, IF 2,6) portant sur 99 ablations thermiques consécutives d'ostéome ostéoïde (57 RFA et 42 cryoablations) chez 93 patients : succès technique de 99 % (98/99), succès clinique primaire élevé et comparable entre cryoablation (97 %, 36/37) et RFA (93 %, 51/55 ; p = 0,343), taux de récidive numériquement plus faible après cryoablation (3 % vs 10 % en RFA ; p = 0,202), et taux de guérison définitive sans chirurgie de 97 % (88/92), avec 83 % (5/6) d'efficacité en rattrapage des récidives.",
        "summary_fr_detailed": "Alors que la radiofréquence (RFA) représente le traitement thermique historique de l'ostéome ostéoïde (OO), la cryoablation percutanée est de plus en plus privilégiée pour sa capacité à franchir l'os ostéosclérotique périnidal (approche juxta-corticale « no-touch » sans forage obligatoire du nidus) et la visibilité directe de la boule de glace au scanner. Cette série de 99 procédures compare face-à-face 57 RFA et 42 cryoablations chez 93 patients (âge moyen 17 ans). Le succès clinique primaire atteint 95 % sur la cohorte globale (97 % en cryoablation vs 93 % en RFA, p = 0,343), avec un taux de récidive de 3 % après cryoablation contre 10 % après RFA (p = 0,202). Lorsqu'une seconde ablation thermique est réalisée pour un OO résiduel ou récidivant (n = 6), une guérison complète est obtenue dans 83 % des cas (5/6). Deux événements indésirables (un modéré, un majeur) ont été observés après cryoablation, soulignant l'importance de la protection thermique cutanée et nerveuse.",
        "protocol_fr": "Repérage TDM millimétrique basse dose du nidus • Choix de la modalité : RFA monopolaire (90°C pendant 4 à 6 min après forage cortical coaxial 11G–14G au centre du nidus) ou Cryoablation (sonde 17G positionnée en intra-nidal ou au contact cortical péri-nidal « no-touch », double cycle Gel 8–10 min / Dégel 5 min) • En cryoablation : contrôle TDM de l'extension de l'iceball hypodense et hydrodissection/gant tiède systématique si nidus superficiel (< 10 mm de la peau ou d'un nerf périphérique).",
        "key_points_fr": [
            "Taux de guérison clinique sans chirurgie de 97 % (88/92) pour l'ensemble de la cohorte, confirmant l'équivalence d'efficacité entre cryoablation (97 %) et RFA (93 %).",
            "Tendance à un taux de récidive locale plus bas en cryoablation (3 % vs 10 % en RFA), grâce à la diffusion homogène du froid à travers la sclérose périnidale.",
            "Valide le retraitement percutané par thermoablation des ostéomes ostéoïdes récidivants avec 83 % de guérison définitive.",
            "Rappelle la nécessité d'une thermoprotection rigoureuse (hydrodissection / réchauffement cutané) en cryoablation pour prévenir les complications de voisinage."
        ],
        "tags": ["Ostéome ostéoïde", "Cryoablation", "Radiofréquence", "Étude comparative", "Récidive", "JVIR 2026"]
    },
    "42174179": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Sclérothérapie percutanée à l'éthanol gélifié radio-opaque (RGE / DiscoGel®) des lésions osseuses bénignes (KOA et hémangiomes vertébraux agressifs) : revue systématique (Skeletal Radiology 2026)",
        "modality": "Scanner TDM / Fluoroscopie Interventionnelle",
        "intervention_type": "Sclérothérapie Percutanée à l'Éthanol Gélifié Radio-Opaque (RGE / DiscoGel®)",
        "cochin_link": "Optimise directement les procédures d'« Alcoolisation / Sclérothérapie percutanée de kyste osseux anévrismal (KOA), kyste essentiel et lésions osseuses hypervasculaires » réalisées à Cochin en évitant la fuite veineuse de l'alcool absolu liquide.",
        "summary_fr_short": "Revue systématique (*Skeletal Radiology*, mai/oct. 2026, IF 1,9) analysant 6 études (55 patients, 56 lésions osseuses, 119 procédures ; moyenne de 2,16 séances/patient) traitées par sclérothérapie percutanée à l'éthanol gélifié radio-opaque (RGE, éthanol associé à de l'éthylcellulose et du tungstène) : 80 % de kystes osseux anévrismaux (KOA) et 18 % d'hémangiomes vertébraux agressifs, succès technique de 100 %, disparition complète ou partielle des douleurs dans 96,4 % des cas (64,3 % complète, 32,1 % partielle), réponse radiologique complète (réossification) dans 96 % des lésions suivies, et 0 % de complication majeure CIRSE/CTCAE Grade ≥ 4.",
        "summary_fr_detailed": "L'alcoolisation percutanée classique à l'éthanol absolu liquide (96 %) des kystes osseux anévrismaux (KOA) est efficace mais exposée au risque de fuite rapide dans le drainage veineux péri-lésionnel ou les tissus mous adjacents, d'autant que l'éthanol pur est radiotransparent. L'éthanol gélifié radio-opaque (RGE, DiscoGel®), combinant de l'éthanol à un polymère visqueux hydrophobe (éthylcellulose) et de la poudre de tungstène radio-opaque, forme au contact des fluides intralésionnels un gel cotonneux qui piège le sclérosant in situ tout en permettant un contrôle fluoroscopique/TDM direct. Sur 119 procédures (principalement KOA [80 %] et hémangiomes vertébraux agressifs [18 %]), le succès technique est de 100 %, le taux d'ossification radiologique complète atteint 96 % (avec seulement 3,6 % de recours secondaire à la chirurgie) et aucune complication systémique ou neurologique liée à une fuite d'éthanol n'a été rapportée.",
        "protocol_fr": "Ponction osseuse sous guidage TDM ou biplan fluoroscopique (souvent à double aiguille 14G–18G pour décompression et lavage) • Kystographie préalable aux produits de contraste iodés pour analyser le volume cavitaire et le retour veineux • Injection lente sous contrôle TDM/scopique continu d'éthanol gélifié radio-opaque (RGE / DiscoGel®) qui précipite en matrice visqueuse radio-opaque au sein des logettes du KOA sans lavage secondaire • Répétition éventuelle à 6–8 semaines selon l'ossification corticale et trabéculaire (moyenne ~2 séances).",
        "key_points_fr": [
            "Alternative haute sécurité à l'alcool absolu liquide : la viscosité de l'éthylcellulose et la radio-opacité du tungstène éliminent le risque de fuite veineuse occulte ou de nécrose des parties molles.",
            "Taux de réponse radiologique complète (ossification du KOA) de 96 % et soulagement clinique dans 96,4 % des cas après une moyenne de 2,16 séances.",
            "Particulièrement indiqué pour les KOA rachidiens, sacrés ou juxta-articulaires à haut risque de fuite épidurale ou foraminale."
        ],
        "tags": ["Kyste osseux anévrismal", "KOA", "Éthanol gélifié", "DiscoGel", "Sclérothérapie", "Hémangiome vertébral", "Skeletal Radiol 2026"]
    },
    "42419719": {
        "category_id": "cyst_sclerotherapy",
        "title_fr": "Surveillance active versus injections percutanées (polidocanol vs méthylprednisolone) dans les kystes osseux essentiels (KOE / SBC) de l'enfant : étude comparative sur 160 patients",
        "modality": "Fluoroscopie / Scanner Interventionnel",
        "intervention_type": "Sclérothérapie Percutanée au Polidocanol vs Corticoïdes des Kystes Osseux Essentiels (KOE)",
        "cochin_link": "Éclaire directement la stratégie de « Sclérothérapie / Alcoolisation percutanée des kystes osseux essentiels (KOE) et choix du sclérosant (polidocanol vs corticoïdes) » en radiologie interventionnelle ostéo-articulaire.",
        "summary_fr_short": "Étude de cohorte en risques compétitifs (*Bone & Joint Open*, juil. 2026, IF 2,5, Open-Access, 160 patients, suivi médian 3,4 ans) comparant la surveillance simple (n = 41), l'injection percutanée différée (n = 86) et l'injection percutanée immédiate (n = 33), ainsi que l'efficacité du polidocanol versus méthylprednisolone dans les kystes osseux essentiels (SBC/KOE) : l'intervention percutanée immédiate obtient une incidence cumulée de guérison significativement supérieure à la surveillance ou au traitement différé, et la sclérothérapie au polidocanol surpasse significativement les injections de méthylprednisolone tant sur le taux de consolidation osseuse que sur la prévention des échecs/fractures.",
        "summary_fr_detailed": "La prise en charge des kystes osseux essentiels (simple bone cysts, KOE) oscille entre abstention-surveillance, injections intra-kystiques de corticoïdes (méthylprednisolone) et sclérothérapie chimique (polidocanol, éthanol, doxycycline). Cette étude d'un centre tertiaire d'oncologie musculosquelettique (160 patients consécutifs suivis en médiane 3,4 ans) utilise une modélisation statistique par risques compétitifs et analyse landmark pour comparer ces stratégies. L'abstention initiale expose à un taux élevé d'échec et de fracture pathologique nécessitant secondairement un geste invasif, avec une incidence cumulée de consolidation inférieure à la prise en charge percutanée d'emblée. Surtout, parmi les agents injectés, le sclérosant endothélial (polidocanol) démontre une supériorité statistiquement significative sur l'acétate de méthylprednisolone pour l'obtention de la consolidation osseuse (CI-Healing) et la réduction du taux d'échec (CI-Failure). La localisation au membre inférieur (zones portantes fémorale proximale, calcanéenne ou tibiale) est identifiée comme facteur indépendant de moins bonne consolidation spontanée (HR = 0,38 ; IC 95 % : 0,18–0,82), justifiant d'autant plus un traitement percutané actif précoce.",
        "protocol_fr": "Évaluation TDM/radiographique de l'index kystique et de l'amincissement cortical (en particulier au membre inférieur et au bassin) • Ponction percutanée à double aiguille avec aspiration du liquide séro-citrin et kystographie • Sclérothérapie chimique active (polidocanol ou alcoolisation +/- comblement cavitaire en zone portante à Cochin) privilégiée par rapport aux simples injections de corticoïdes • Suivi radiographique/TDM selon la classification de Neer / Capanna.",
        "key_points_fr": [
            "Sur 160 kystes osseux essentiels, le traitement percutané immédiat offre un taux de consolidation supérieur et réduit la durée d'exposition au risque de fracture par rapport à l'attente vigilante.",
            "La sclérothérapie au polidocanol est significativement plus efficace que les injections intra-kystiques de méthylprednisolone (plus de consolidations, moins d'échecs).",
            "Les localisations du membre inférieur divisent par plus de 2,5 la probabilité de guérison spontanée (HR = 0,38), imposant un traitement interventionnel proactif."
        ],
        "tags": ["Kyste osseux essentiel", "KOE", "Polidocanol", "Méthylprednisolone", "Sclérothérapie", "Bone Jt Open 2026"]
    },
    "42310038": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Facteurs prédictifs du soulagement douloureux après sclérothérapie à la mousse de polidocanol des malformations veineuses douloureuses des parties molles (181 patients, European Radiology 2026)",
        "modality": "Échographie / Fluoroscopie Interventionnelle (Phlébographie Directe)",
        "intervention_type": "Sclérothérapie Percutanée à la Mousse de Polidocanol des Malformations Veineuses",
        "cochin_link": "Directement applicable aux séances de « Sclérothérapie percutanée à la mousse (Aetoxisclérol / Polidocanol) et cryoablation des malformations veineuses douloureuses des parties molles » réalisées à Cochin.",
        "summary_fr_short": "Étude rétrospective de 181 patients traités pour malformation veineuse (MV) périphérique douloureuse par sclérothérapie à la mousse de polidocanol (1 % ou 2 %) publiée dans *European Radiology* (juin/nov. 2026, IF 4,7) : amélioration douloureuse chez 84 % des patients à 2 mois (disparition complète chez 28 %, réduction ≥ 50 % chez 47 %). En analyse multivariée, l'obtention d'une bonne stase intralésionnelle du sclérosant est le seul facteur prédictif indépendant de réponse clinique majeure (OR = 2,44 ; IC 95 % : 1,18–5,18 ; p = 0,016), indépendamment de la concentration de polidocanol (1 % vs 2 % non significatif).",
        "summary_fr_detailed": "La douleur liée aux malformations veineuses (MV) musculaires et sous-cutanées des membres et du tronc (stase veineuse, phlébolithes, thromboses localisées) constitue la première indication de traitement percutané. Sur 240 patients consécutifs traités par sclérothérapie à la mousse de polidocanol entre 2015 et 2025, 181 patients traités spécifiquement pour douleur ont été analysés. Dès 2 mois après une première séance, 84 % présentent une baisse de l'EVA. Si l'analyse univariée associe la réponse favorable à une taille ≤ 5 cm, une morphologie lobulée, des contours bien limités, un faible drainage veineux (types Puig I–II) et une bonne stase de la mousse, la régression logistique multivariée démontre que seule la qualité de la stase intralésionnelle du sclérosant prédit indépendamment le succès antalgique (OR = 2,44, p = 0,016). Fait pratique majeur : augmenter la concentration de polidocanol de 1 % à 2 % n'améliore pas significativement l'efficacité antalgique ; c'est la maîtrise hémodynamique du drainage veineux qui détermine le résultat.",
        "protocol_fr": "Ponction directe sous contrôle échographique de la malformation veineuse (aiguilles 21G–23G) • Phlébographie directe sous scopie soustraite pour classer le drainage veineux (classification de Puig / Dubois) • Stratégie « Stasis-First » : compression manuelle, garrot pneumatique proximal ou occlusion des veines de drainage en cas de type III/IV pour garantir une stase prolongée de la mousse • Préparation de mousse de polidocanol 1 % ou 2 % selon la méthode de Tessari (ratio 1:4 liquide/gaz) et injection sous contrôle échographique/scopique.",
        "key_points_fr": [
            "Sur 181 malformations veineuses douloureuses, une seule séance de mousse de polidocanol diminue la douleur dans 84 % des cas (résolution complète dans 28 % dès la 1re séance).",
            "La qualité de la stase intralésionnelle de la mousse est le seul facteur prédictif indépendant d'efficacité en multivariée (OR = 2,44, p = 0,016), surpassant la taille ou la topographie initiale.",
            "Le polidocanol 1 % est aussi efficace que le 2 % dès lors que la stase hémodynamique est obtenue, permettant de limiter la dose toxique cumulée sur les lésions étendues."
        ],
        "tags": ["Malformation veineuse", "Sclérothérapie", "Mousse de polidocanol", "Aetoxisclérol", "Stase veineuse", "Eur Radiol 2026"]
    },
    "42961054": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Résultats à long terme (suivi médian 5 ans) du vissage pédiculaire percutané augmenté au ciment (PPSF) pour les fractures vertébrales pathologiques oncologiques (240 patients, Neurosurgery 2026)",
        "modality": "Scanner TDM / Fluoroscopie Biplan / Navigation Rachidienne",
        "intervention_type": "Vissage Pédiculaire Percutané Augmenté par Cimentoplastie (Cement-Augmented PPSF)",
        "cochin_link": "Référence majeure pour les « Ostéosynthèses rachidiennes percutanées (vissage pédiculaire cimenté) et cimentoplasties des fractures vertébrales métastatiques » prises en charge à Cochin.",
        "summary_fr_short": "Vaste cohorte oncologique (*Neurosurgery*, oct. 2026, IF 3,9) de 240 patients (241 interventions) traités par vissage pédiculaire percutané augmenté au ciment (cement-augmented PPSF) pour fracture vertébrale par compression pathologique d'origine métastatique, avec un suivi médian de 5,0 ans chez les survivants : taux de défaillance mécanique nécessitant une reprise chirurgicale exceptionnellement bas de 2,1 % (5/240), amélioration significative et durable de la douleur et du statut fonctionnel/neurologique.",
        "summary_fr_detailed": "Grâce aux progrès des thérapies ciblées et de l'immunothérapie, la survie des patients porteurs de métastases rachidiennes s'est considérablement allongée, posant la question de la tenue mécanique à long terme des montages percutanés sans arthrodèse osseuse postéro-latérale ouverte. Cette étude d'un centre de référence en oncologie évalue 240 patients opérés par fixation pédiculaire percutanée avec augmentation cimentée des vis (vis fenêtrées + PMMA) pour fracture vertébrale pathologique. Avec un suivi médian de 5,0 ans chez les patients survivants, l'incidence cumulée de faillite mécanique nécessitant une révision n'est que de 2,1 % (5 patients sur 240). En régression en risques compétitifs (prenant en compte le décès oncologique), seul un âge plus avancé est modestement associé au risque de révision (HR = 1,12 par an, p = 0,046), confirmant que le vissage percutané cimenté offre une stabilité biomécanique pérenne à long terme tout en permettant une reprise quasi immédiate de la radiothérapie et des traitements systémiques.",
        "protocol_fr": "Évaluation pré-opératoire du score SINS (Spinal Instability Neoplastic Score : lésions potentiellement instables ou instables SINS 7–18) • Abord transpédiculaire percutané mini-invasif au-dessus et au-dessous de la vertèbre fracturée • Mise en place de vis pédiculaires canulées et fenêtrées • Injection contrôlée sous scopie de ciment PMMA dans les corps vertébraux adjacents via les vis fenêtrées (augmentation cimentée anti-arrachement) associée à la cimentoplastie du niveau fracturé • Reprise précoce de la radiothérapie stéréotaxique ou conventionnelle sans délai de cicatrisation.",
        "key_points_fr": [
            "Sur 240 patients oncologiques avec un suivi médian de 5 ans chez les survivants, le taux de démontage mécanique nécessitant une reprise n'est que de 2,1 % (5/240).",
            "Démontre qu'une fixation percutanée cimentée sans greffe postéro-latérale ouverte reste mécaniquement fiable même chez les longs survivants sous thérapies ciblées/immunothérapie.",
            "Améliore significativement et durablement les scores de douleur, la force motrice et l'autonomie fonctionnelle."
        ],
        "tags": ["Fracture vertébrale métastatique", "Vissage pédiculaire percutané", "Augmentation cimentée", "Cimentoplastie", "Durabilité à long terme", "Neurosurgery 2026"]
    },
    "42576100": {
        "category_id": "msk_biopsy",
        "title_fr": "Biopsies osseuses techniquement difficiles sous guidage scanner : stratégies pratiques pour les lésions périneurovasculaires, condensantes denses et occultes au scanner (Skeletal Radiology 2026)",
        "modality": "Scanner TDM Interventionnel & Fusion / Repérage Multimodal",
        "intervention_type": "Biopsie Osseuse Percutanée Complexe sous Guidage Scanner (Lésions Condensantes, Occultes TDM & Juxta-Critiques)",
        "cochin_link": "Guide technique quotidien pour les « Biopsies osseuses difficiles sous scanner (lésions ostéocondensantes denses, lésions médullaires occultes au scanner visibles uniquement en IRM/TEP, et abords rachidiens/pelviens proches des axes vasculo-nerveux) » en salle de scanner Achard -1 à Cochin.",
        "summary_fr_short": "Mise au point technique de référence (*Skeletal Radiology*, août 2026, IF 1,9, Open-Access) détaillant les solutions pratiques aux 3 grandes situations difficiles de biopsie osseuse scanoguidée : (1) lésions juxta-vasculaires ou juxta-nerveuses/rachidiennes (voies d'abord obliques sécurisées, hydrodissection protectrice, inclinaison du statif), (2) lésions densément ostéocondensantes (choix de tréphines dentelées motorisées ou manuelles, prélèvement préférentiel de la zone de transition périphérique moins minéralisée), et (3) lésions médullaires occultes en TDM (repérage anatomique millimétrique sur fusion mentale/logicielle IRM ou TEP-FDG).",
        "summary_fr_detailed": "Bien que le scanner soit la modalité de référence pour les biopsies osseuses percutanées, le rendement diagnostique chute et le risque procédural augmente dans trois scénarios fréquents en centre de référence : les localisations anatomiques à haut risque (odontoïde C2, pédicules cervicaux/thoraciques, paroi acétabulaire médiale ou sacrum antérieur au contact des vaisseaux iliaques et du plexus sacral), les lésions fortement ostéosclérotiques (où l'écrasement trabéculaire et la nécrose mécanique réduisent la cellularité exploitable), et les lésions purement intramédullaires occultes au scanner sans ostéolyse corticale ni trabéculaire visible. Cet article illustre par cas cliniques les règles d'or techniques permettant de sécuriser le trajet d'aiguille et de maximiser la rentabilité histologique et moléculaire.",
        "protocol_fr": "1) Lésions ostéocondensantes : cibler la périphérie active de la lésion ou les plages moins denses en T2/diffusion ou hypermétaboliques en TEP plutôt que le centre éburné ; utiliser un système coaxial à couronne tranchante ou motorisé et multiplier les carottes (≥ 3) pour compenser l'artéfact d'écrasement et la décalcification • 2) Lésions occultes au scanner : corrélation millimétrique aux repères osseux fixes sur l'IRM (T1, Dixon, diffusion) ou la TEP-TDM pré-procédurale • 3) Proximité vasculo-nerveuse : injection de sérum physiologique ou lidocaïne diluée (hydrodissection) pour écarter les racines nerveuses, la plèvre ou les vaisseaux iliaques avant passage du trocart osseux.",
        "key_points_fr": [
            "Dans les lésions osseuses condensantes, cibler la zone de transition périphérique ou le foyer de moindre densité au sein de la sclérose améliore nettement le rendement histologique par rapport au cœur éburné.",
            "Pour les lésions intramédullaires occultes au scanner (détectées en IRM ou TEP-TDM), l'alignement strict sur des repères anatomiques osseux constants (foramens, tubérosités, distance au disque/interligne) garantit la précision du prélèvement.",
            "L'hydrodissection et les abords trans-osseux alternatifs (trans-costovertébral, trans-iliaque, trans-pédiculaire oblique) permettent de biopsier en sécurité les lésions rétro-vasculaires ou périradiculaires."
        ],
        "tags": ["Biopsie osseuse difficile", "Lésion ostéocondensante", "Lésion occulte au scanner", "Hydrodissection", "Technique coaxiale", "Skeletal Radiol 2026"]
    },
    "42858634": {
        "category_id": "msk_imaging",
        "title_fr": "IRM Dixon 3T des lésions médullaires rachidiennes : comparaison de la chute de signal (Signal Drop) sur les séquences T2 Dixon versus T1 Dixon post-gadolinium pour différencier bénin et malin (European Journal of Radiology 2026)",
        "modality": "IRM Rachidienne 3T (Séquences Chemical-Shift Dixon T2 et T1 Gado)",
        "intervention_type": "Caractérisation IRM Quantitative (Chute de Signal En-Phase / Hors-Phase Dixon) des Lésions Vertébrales",
        "cochin_link": "Essentiel pour l'interprétation quotidienne des « IRM du rachis pour caractérisation de lésion vertébrale indéterminée avant décision de biopsie osseuse sous scanner » à Cochin.",
        "summary_fr_short": "Étude diagnostique sur 78 patients (*European Journal of Radiology*, oct. 2026, IF 3,2) comparant le pourcentage de chute de signal entre les images en phase et en opposition de phase sur l'IRM 3T T2 Dixon sans injection (`T2 %drop`) versus T1 Dixon après injection de gadolinium (`GdT1 %drop`) dans les lésions médullaires rachidiennes (41 bénignes, 34 malignes) : la chute de signal sur T1 Dixon injecté est significativement plus faible que sur T2 Dixon (21,4 % vs 29,2 %, p < 0,001) et présente une spécificité moitié moindre au seuil garantissant 100 % de sensibilité pour la malignité (spécificité 39,0 % en GdT1 Dixon vs 80,5 % en T2 Dixon, p < 0,001 ; AUC 0,84 vs 0,91).",
        "summary_fr_detailed": "La séquence IRM en déplacement chimique (Dixon In-Phase / Out-of-Phase) est un outil majeur pour distinguer les lésions vertébrales bénignes contenant de la graisse médullaire résiduelle (îlots de moelle rouge, hémangiomes atypiques, fractures bénignes : chute de signal > 20–29 % en opposition de phase) des lésions malignes infiltrantes qui remplacent les adipocytes (chute de signal faible). En pratique clinique, certains protocoles n'acquièrent le Dixon qu'en T2 ou uniquement en T1 après injection de gadolinium. Sur 78 patients explorés à 3T, cette étude démontre que la prise de contraste au gadolinium altère le ratio eau/graisse intravoxel et réduit artificiellement la chute de signal sur le T1 Dixon post-contraste (`GdT1 %drop` médian 21,4 % contre 29,2 % en `T2 %drop`, p < 0,001). Au seuil optimal assurant 100 % de sensibilité pour ne manquer aucune métastase (~28–29 %), la spécificité du T2 Dixon atteint 80,5 % contre seulement 39,0 % pour le T1 Dixon injecté (p < 0,001) : se fier au T1 Dixon post-gadolinium conduit donc à classer à tort de nombreuses lésions bénignes comme suspectes et à indiquer des biopsies vertébrales inutiles.",
        "protocol_fr": "Protocole IRM rachis tumoral / lésion indéterminée à Cochin : réaliser systématiquement la mesure du pourcentage de chute de signal (`[In-Phase - Out-of-Phase] / In-Phase × 100`) sur une séquence Dixon NON injectée (T1 Dixon natif ou T2 Dixon, seuil de bénignité ≥ 29 % pour 100 % de sensibilité maligne et 80,5 % de spécificité) • Ne pas utiliser le T1 Dixon post-gadolinium pour quantifier la chute de signal graisseuse microscopique (risque élevé de faux positifs de malignité) • Réserver le T1 Dixon post-gadolinium uniquement à l'obtention d'une suppression de graisse homogène (image Water-Only).",
        "key_points_fr": [
            "Démonstration méthodologique importante : l'injection de gadolinium diminue significativement le pourcentage de chute de signal en opposition de phase (21,4 % en GdT1 Dixon vs 29,2 % en T2 Dixon, p < 0,001).",
            "Pour une sensibilité de 100 % vis-à-vis des lésions malignes, le T2 Dixon offre une excellente spécificité (80,5 % au seuil de 29,0 %) alors que la spécificité du T1 Dixon injecté s'effondre à 39,0 % (p < 0,001).",
            "Évite des biopsies vertébrales sous scanner inutiles en interprétant le ratio In/Out-of-Phase exclusivement sur les séquences Dixon natives (non injectées)."
        ],
        "tags": ["IRM Dixon", "Chute de signal", "Lésion vertébrale", "Moelle osseuse", "Caractérisation bénin/malin", "Eur J Radiol 2026"]
    },
    "42781084": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Radiofréquence refroidie (Cooled RFA) échoguidée des nerfs géniculés avec ciblage nerveux direct et confirmation physiologique (technique MDNT) dans la gonarthrose : résultats et survie sans retraitement sur 1 025 genoux consécutifs",
        "modality": "Échographie Haute Résolution + Neurostimulation Physiologique",
        "intervention_type": "Radiofréquence Refroidie (CRFA) Échoguidée des Nerfs Géniculés (Technique MDNT)",
        "cochin_link": "Directement en lien avec les séances de « Test anesthésique sous écho + Radiofréquence / Cryoneurolyse des nerfs géniculés pour gonarthrose réfractaire » programmées à l'Hôpital Cochin.",
        "summary_fr_short": "Vaste étude de cohorte rétrospective (*Journal of Pain Research*, sept. 2026, IF 2,5, Open-Access) portant sur 1 025 genoux consécutifs atteints de gonarthrose symptomatique traités par radiofréquence refroidie (CRFA) sous guidage échographique combiné à une électrostimulation sensitive de confirmation (Matsuoka Direct Nerve Targeting, MDNT) : réduction massive et immédiate du NRS moyen de 7,76 ± 1,31 à 2,46 ± 1,93 dès J1 (-5,29 points, p < 0,001) et maintien à 1 an à 2,29 ± 2,06 contre 8,15 en pré-opératoire (n = 246), taux de retraitement de 0,8 % (8/1 025), conversion en PTG de 0,1 %, survie Kaplan-Meier sans retraitement de 99,8 % à 12 mois et 96,9 % à 20 mois, et 0 % de complication majeure.",
        "summary_fr_detailed": "La radiofréquence refroidie (CRFA) des nerfs géniculés guidée uniquement par repères osseux fluoroscopiques classiques souffre d'une variabilité anatomique inter-individuelle des branches articulaires du genou. Cette série de 1 025 genoux évalue la technique MDNT (Matsuoka Direct Nerve Targeting), qui associe l'identification directe sous échographie haute résolution des pédicules vasculo-nerveux géniculés et une confirmation physiologique par neurostimulation sensitive avant thermoablation refroidie. Le soulagement douloureux est rapide dès J1 (NRS passant de 7,76 à 2,46, p < 0,001) et durable à 1 an (NRS 2,29 ± 2,06). Le taux de survie sans seconde procédure CRFA atteint 99,8 % à 12 mois et 96,9 % à 20 mois, sans aucune complication majeure observée.",
        "protocol_fr": "Repérage échographique direct en mode B et Doppler couleur des artères et nerfs géniculés (SMGN, SLGN, IMGN +/- rameaux récurrents et infrapatellaires) • Insertion de la canule de radiofréquence refroidie au contact direct du nerf visualisé • Confirmation physiologique par stimulation sensitive reproduisant la douleur articulaire concordante et absence de réponse motrice • Ablation thermique refroidie après anesthésie locale périneurale.",
        "key_points_fr": [
            "Plus grande cohorte publiée (1 025 genoux consécutifs) de radiofréquence refroidie échoguidée des nerfs géniculés pour gonarthrose.",
            "Le couplage du ciblage échographique direct et de la confirmation électrophysiologique (MDNT) permet une baisse moyenne de plus de 5,3 points d'EVA/NRS maintenue à 1 an.",
            "Survie sans retraitement de 99,8 % à 12 mois et 96,9 % à 20 mois, avec 0 % de complication majeure."
        ],
        "tags": ["Nerfs géniculés", "Radiofréquence refroidie", "Échographie interventionnelle", "Gonarthrose", "Technique MDNT", "J Pain Res 2026"]
    },
    "42128267": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Radiologie interventionnelle des métastases osseuses : concepts actuels, stabilisation hybride (ostéosynthèse + cimentoplastie), cryoablation et effet abscopal (Joint Bone Spine 2026)",
        "modality": "Scanner TDM / Fluoroscopie / Guidage Multimodal",
        "intervention_type": "Ablation Thermique (Cryoablation / RF / MWA) & Stabilisation Hybride (Vissage + Cimentoplastie)",
        "cochin_link": "Synthèse française de référence (*Revue du Rhumatisme / Joint Bone Spine*) correspondant directement au parcours multidisciplinaire « Thermoablation + Vissage percutané / Ostéosynthèse cimentée des métastases osseuses » de l'Hôpital Cochin.",
        "summary_fr_short": "Mise au point de référence (*Joint Bone Spine*, mai 2026, IF 3,8) positionnant la radiologie interventionnelle (RI) comme le « 4e pilier » de l'oncologie osseuse aux côtés de la radiothérapie, de la chirurgie et des traitements systémiques : intégration proactive des biopsies guidées pour profilage moléculaire, de la stabilisation biomécanique hybride (vissage percutané + cimentoplastie) et de l'ablation thermique curative/palliative (cryoablation, RF, micro-ondes), avec analyse de l'effet immunomodulateur « vaccin in situ » et abscopal de la cryoablation combinée aux inhibiteurs de points de contrôle immunitaire (ICI).",
        "summary_fr_detailed": "La prise en charge des métastases osseuses a évolué d'une approche purement palliative vers une stratégie proactive intégrée à l'oncologie de précision. Cette revue détaille l'arsenal interventionnel moderne : (1) prélèvements biopsiques scanoguidés à haut rendement pour séquençage génomique (NGS) sur os décalcifié doux, (2) consolidation mécanique immédiate par ostéosynthèse percutanée cimentée (vissage + cimentoplastie) prévenant les fractures pathologiques en zone portante (cotyle, col fémoral, sacrum, rachis selon les scores SINS et Mirels), (3) destruction tumorale locale à visée curative chez le patient oligométastatique par cryoablation ou thermoablation, et (4) potentiel immuno-oncologique de la cryoablation qui préserve la structure native des antigènes tumoraux et libère des signaux de danger (DAMPs), favorisant une synergie systémique avec l'immunothérapie.",
        "protocol_fr": "Évaluation multidisciplinaire (RCP Métastases Osseuses : score SINS rachidien, score de Mirels appendiculaire, statut oligométastatique) • Biopsie coaxiale première si besoin de re-profilage moléculaire • Ablation thermique (cryoablation privilégiée sur les lésions ostéocondensantes, volumineuses ou péri-nerveuses avec suivi TDM de l'iceball et thermoprotection) • Stabilisation hybride immédiate dans le même temps par vissage canulé et cimentoplastie PMMA en zone de contrainte mécanique • Articulation coordonnée avec la radiothérapie stéréotaxique (SBRT) et l'immunothérapie.",
        "key_points_fr": [
            "Consacre la radiologie interventionnelle comme le « 4e pilier » de l'oncologie musculosquelettique, passant du dernier recours palliatif au contrôle local précoce et curatif des oligométastases.",
            "La stabilisation hybride (vissage percutané + cimentoplastie) restaure immédiatement la résistance aux forces de torsion/cisaillement et de compression sans retarder les thérapies systémiques.",
            "Contrairement aux ablations hyperthermiques qui dénaturent les protéines, la cryoablation préserve les néo-antigènes tumoraux et agit comme un vaccin in situ potentiel en synergie avec l'immunothérapie."
        ],
        "tags": ["Métastases osseuses", "Cryoablation", "Stabilisation hybride", "Vissage cimenté", "Effet abscopal", "Joint Bone Spine 2026"]
    },
    "42167590": {
        "category_id": "ect_mets",
        "title_fr": "Électroporation irréversible (IRE) des tumeurs vertébrales sous guidage scanner : efficacité tumoricide et profil de neurotoxicité médullaire/radiculaire (JVIR 2026)",
        "modality": "Scanner TDM Interventionnel & IRM de Suivi",
        "intervention_type": "Électroporation Bipolaire (IRE / ECT) des Tumeurs du Rachis & Épidurales",
        "cochin_link": "Éclaire directement les paramètres électriques et les marges de sécurité neurologique lors des procédures d'« Électrochimiothérapie (ECT) / Électroporation des métastases rachidiennes et épidurales » réalisées au scanner de Cochin.",
        "summary_fr_short": "Étude préclinique sur gros animal (*Journal of Vascular and Interventional Radiology — JVIR*, mai 2026, IF 2,6) évaluant l'ablation bipolaire par électroporation irréversible (IRE) sous guidage TDM sur 11 tumeurs vertébrales thoraco-lombaires (champ électrique moyen 526,1 ± 53,8 V/cm) : succès technique de 100 %, nécrose histologique constatée sur tous les niveaux traités, réponse IRM à 30 jours dans 86 % des tumeurs (6/7), aucun déficit neurologique moteur post-procédural et lésions médullaires limitées à un grade histologique ≤ 2, mais dégénérescence wallérienne de grade ≥ 3 observée sur 22 % (4/18) des racines nerveuses émergentes.",
        "summary_fr_detailed": "L'ablation des tumeurs rachidiennes à extension épidurale ou foraminale est limitée par la thermosensibilité extrême de la moelle épinière et des racines nerveuses. L'électroporation (réversible sous forme d'électrochimiothérapie [ECT] à la bléomycine, ou irréversible [IRE] à champ électrique plus élevé) repose sur des impulsions électriques microsecondes non thermiques. Dans ce modèle de tumeurs vertébrales thoraco-lombaires implantées (1,5 cm) traitées sous guidage TDM par électrodes bipolaires (champ moyen ~526 V/cm), aucun animal survivant à 30 jours n'a développé de parésie ou de déficit clinique et la moelle épinière a été préservée (modifications histologiques ≤ Grade 2). Toutefois, 22 % des racines nerveuses émergentes situées au contact direct du champ d'électroporation irréversible ont présenté une dégénérescence wallérienne histologique de grade 3, démontrant pourquoi l'électrochimiothérapie réversible (ECT, seuil ~400 V/cm avec bléomycine) reste plus sûre que l'IRE pure au contact immédiat des racines foraminales.",
        "protocol_fr": "Planification TDM et modélisation du champ électrique vertébral • Positionnement transpédiculaire ou paravertébral des électrodes sous scanner • Au voisinage immédiat du cordon médullaire et des foramens radiculaires : privilégier à Cochin les paramètres d'électroporation réversible (ECT + bléomycine IV 15 000 UI/m²) plutôt qu'un surdosage en électroporation irréversible (> 500–600 V/cm) afin de prévenir toute dégénérescence wallérienne radiculaire • Contrôle IRM à 1 mois.",
        "key_points_fr": [
            "Démontre une réponse IRM de 86 % à 30 jours et l'absence complète de déficit moteur médullaire après électroporation bipolaire scanoguidée de tumeurs vertébrales.",
            "La moelle épinière tolère remarquablement le champ électrique (lésions histologiques ≤ Grade 2), mais 22 % des racines émergentes présentent une dégénérescence wallérienne de grade 3 sous IRE à 526 V/cm.",
            "Confirme l'intérêt supérieur de l'électrochimiothérapie réversible (ECT à la bléomycine) à Cochin pour traiter les extensions épidurales et foraminales en préservant les racines nerveuses."
        ],
        "tags": ["Électroporation", "IRE", "Électrochimiothérapie", "Tumeur vertébrale", "Neurotoxicité radiculaire", "JVIR 2026"]
    },
    "42809929": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Vissage percutané postérieur de l'anneau pelvien par vis trans-sacrées et ilio-sacrées multiples de gros diamètre (≥ 7 mm) en décubitus dorsal : faisabilité, balistique S1/S2 et résultats sur 149 vis (Injury 2026)",
        "modality": "Fluoroscopie Biplan (Inlet / Outlet / Profil Sacré) & Contrôle TDM",
        "intervention_type": "Vissage Percutané Trans-Sacré (TSS) & Ilio-Sacré (ISS) Multiple du Bassin",
        "cochin_link": "Directement applicable aux procédures de « Vissage percutané du bassin postérieur (vis ilio-sacrées et trans-sacrées S1/S2) » réalisées à l'Hôpital Cochin.",
        "summary_fr_short": "Étude de cohorte sur 69 patients consécutifs (149 vis canulées de gros diamètre ≥ 7 mm : 123 vis trans-sacrées [TSS] et 26 vis ilio-sacrées [ISS]) traités en décubitus dorsal avec suivi moyen de 19,5 mois (*Injury*, sept. 2026, IF 2,2) : 100 % de trajet strictement intra-osseux au scanner post-opératoire, 0 % de complication neurovasculaire ou infectieuse, 0 % de descellement et 0 % de pseudarthrose (1 seul bris de vis S2 asymptomatique, soit 0,67 %).",
        "summary_fr_detailed": "Lors du vissage percutané de l'anneau pelvien postérieur en décubitus dorsal, le rebord de la table d'examen gêne fréquemment l'inclinaison postéro-antérieure nécessaire aux vis ilio-sacrées (ISS) obliques, exposant au risque d'effraction corticale antérieure ou foraminale sacrée, en particulier lorsqu'un montage à vis multiples est requis pour stabiliser durablement le sacrum. Cette série de 149 vis de gros calibre (≥ 7 mm) codifie les combinaisons de vissage trans-sacré (TSS, traversant les deux articulations sacro-iliaques de part en part selon un axe strictement transversal non gêné par la table) et ilio-sacré en fonction du morphotype du couloir osseux transversal de S1 et S2. Le contrôle TDM systématique confirme 100 % de positionnement intra-osseux sans effraction foraminale ni canalaire, et une consolidation complète chez tous les patients suivis en moyenne 19,5 mois.",
        "protocol_fr": "Analyse TDM pré-opératoire de la largeur antéro-postérieure du couloir osseux transversal de S1 (sacrum normal vs sacrum dysmorphique) et de S2 • Installation en décubitus dorsal surélevé • Combinaison de vis canulées ≥ 7,0–7,3 mm : privilégier les vis trans-sacrées (TSS) S1 et/ou S2 (trajectoire horizontale pure évitant le conflit avec la table) associées à une vis ilio-sacrée (ISS) selon la géométrie de S1 • Contrôle fluoroscopique strict (vues Inlet, Outlet et profil sacré vrai alignant les grandes échancrures sciatiques) ou guidage TDM.",
        "key_points_fr": [
            "100 % de précision intra-osseuse au scanner sur 149 vis pelviennes postérieures de gros diamètre (123 trans-sacrées et 26 ilio-sacrées) posées en décubitus dorsal.",
            "Le vissage trans-sacré (TSS) bi-cortical ilio-sacro-iliaque neutralise le conflit d'angulation avec la table en décubitus dorsal et offre une tenue mécanique supérieure.",
            "Zéro descellement, zéro pseudarthrose et 0 % de lésion radiculaire sacrée sur un suivi moyen de près de 20 mois."
        ],
        "tags": ["Vissage percutané du bassin", "Vis trans-sacrée", "Vis ilio-sacrée", "Anneau pelvien postérieur", "Sacrum", "Injury 2026"]
    },
    "42801267": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Neuromodulation percutanée du nerf obturateur par radiofréquence pulsée (PRF) sous guidage scanner dans la coxarthrose réfractaire : résultats à 12 mois selon le grade de Kellgren-Lawrence (Hip International 2026)",
        "modality": "Scanner TDM Interventionnel",
        "intervention_type": "Radiofréquence Pulsée (PRF) / Neurolyse Percutanée Scanoguidée du Nerf Obturateur (Hanche Douloureuse)",
        "cochin_link": "Ouvre et documente directement les procédures de « Radiofréquence / Cryoneurolyse percutanée sous scanner des branches articulaires de la hanche (nerf obturateur et nerf fémoral) pour coxarthrose réfractaire ou inopérable » à Cochin.",
        "summary_fr_short": "Étude clinique (*Hip International*, sept. 2026, IF 1,6) évaluant la radiofréquence pulsée (PRF pendant 12 minutes) du nerf obturateur sous guidage scanner sur 33 hanches (30 patients, âge moyen 69 ans, coxarthrose Kellgren-Lawrence grades 2 à 4) avec suivi jusqu'à 12 mois : chute immédiate majeure de l'EVA (~9 points), maintien durable du soulagement dans les coxarthroses légères à modérées (baisse moyenne de -6 points d'EVA à 6 mois et -4 points à 12 mois), contre un effet transitoire (~3 mois) dans les coxarthroses terminales de stade 4, avec 0 % de complication CIRSE.",
        "summary_fr_detailed": "L'innervation nociceptive de la capsule antéro-médiale et inféro-médiale de l'articulation coxo-fémorale dépend principalement des rameaux articulaires du nerf obturateur (responsables des douleurs inguinales irradiant à la face médiale de la cuisse et du genou). Sur 33 hanches réfractaires au traitement médical traitées par radiofréquence pulsée (PRF, 12 minutes) ciblant le nerf obturateur sous contrôle tomodensitométrique, aucune complication motrice (parésie des adducteurs) ou vasculaire n'est survenue (0 % selon la classification CIRSE). L'efficacité antalgique à moyen et long terme dépend étroitement du stade radiographique initial : alors que les grades Kellgren-Lawrence 2–3 conservent un bénéfice cliniquement majeur à 6 mois (-6 points d'EVA) et 12 mois (-4 points), les stades 4 avec destruction articulaire complète présentent une récidive douloureuse moyenne dès 3 mois.",
        "protocol_fr": "Patient en décubitus dorsal au scanner • Repérage TDM du foramen obturé et de la gouttière sous-pubienne (bord antéro-latéral du foramen obturé / jonction branche ilio-pubienne et ischio-pubienne pour cibler les rameaux articulaires du nerf obturateur tout en épargnant le tronc moteur destiné aux adducteurs) • Confirmation par stimulation sensitive (< 0,5 V reproduisant la douleur inguinale) et vérification de l'absence de contraction des adducteurs en stimulation motrice • Radiofréquence pulsée (42°C, 12 minutes) ou radiofréquence/cryoneurolyse des rameaux articulaires.",
        "key_points_fr": [
            "Sécurité parfaite (0 % de complication CIRSE, aucune faiblesse des adducteurs) grâce à la précision du guidage scanner sur le repère osseux sous-pubien/obturateur.",
            "Excellente durabilité antalgique jusqu'à 12 mois dans les coxarthroses de grade Kellgren-Lawrence 2 et 3 (-6 points d'EVA à 6 mois, -4 points à 12 mois).",
            "Dans la coxarthrose destructrice terminale (KL grade 4), l'effet de la PRF seule s'épuise vers 3 mois, orientant vers une dénervation thermique/cryoneurolyse élargie (rameaux articulaires obturateurs + fémoraux) chez les patients contre-indiqués à la PTH."
        ],
        "tags": ["Nerf obturateur", "Coxarthrose", "Radiofréquence pulsée", "Guidage scanner", "Douleur de hanche", "Hip Int 2026"]
    },
    "42677326": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Radiofréquence pulsée haute tension longue durée (HV-LD PRF) combinée à l'ozonothérapie dans la névralgie pudendale réfractaire : série clinique avec suivi en aveugle à 6 mois (Journal of Pain Research 2026)",
        "modality": "Scanner TDM / Guidage Imagerie + Neurostimulation",
        "intervention_type": "Radiofréquence Pulsée Haute Tension Longue Durée (HV-LD PRF) du Nerf Pudendal",
        "cochin_link": "Complète directement l'arsenal de « Prise en charge interventionnelle de la névralgie pudendale réfractaire (bloc test scanoguidé, cryoneurolyse pudendale et radiofréquence pulsée haute tension) » à l'Hôpital Cochin.",
        "summary_fr_short": "Étude clinique rétrospective avec évaluation indépendante en aveugle (*Journal of Pain Research*, août 2026, IF 2,5, Open-Access) chez des patients souffrant de névralgie pudendale réfractaire confirmée par les critères de Nantes et un bloc diagnostique positif : taux de succès primaire (réduction ≥ 50 % de l'EVA) de 93,3 % (14/15) à 12 semaines et maintien d'une réponse favorable chez 80,0 % (12/15) des patients à 24 semaines (6 mois), avec amélioration significative des scores d'anxiété/dépression (HAMA/HAMD), du sommeil (PSQI) et de la qualité de vie (SF-36), sans aucun événement indésirable grave.",
        "summary_fr_detailed": "Lorsque les infiltrations cortisoniques scanoguidées du nerf pudendal n'apportent qu'un soulagement transitoire, la neuromodulation par radiofréquence pulsée à haute tension et longue durée (HV-LD PRF, délivrant un champ électrique accru sans dépasser le seuil thermique neurodestructeur de 42°C) constitue une option conservatrice vis-à-vis de la fonction sphinctérienne et motrice. Dans cette série évaluée jusqu'à 24 semaines par un examinateur indépendant en aveugle, 93,3 % des patients atteignent au moins 50 % de réduction douloureuse à 3 mois et 80,0 % maintiennent ce bénéfice à 6 mois (3 patients ayant présenté une récidive vers la 20e semaine). Aucune complication sphinctérienne, motrice ou infectieuse n'a été observée.",
        "protocol_fr": "Sélection rigoureuse selon les critères de Nantes et positivité du bloc anesthésique diagnostique du nerf pudendal • Ciblage guidé par l'image du nerf pudendal (épine ischiatique / pince ligamentaire sacro-épineuse et sacro-tubérale ou canal d'Alcock) • Confirmation électrophysiologique sensitive (< 0,5 V reproduisant la douleur périnéale concordante) • Application de radiofréquence pulsée haute tension (60–80 V) longue durée (900 s) à température contrôlée ≤ 42°C (ou cryoneurolyse pudendale sous scanner à Cochin en cas d'échec ou de douleur oncologique/neuropathique sévère).",
        "key_points_fr": [
            "Taux de réponse clinique (baisse ≥ 50 % de l'EVA) de 93,3 % à 3 mois et 80,0 % à 6 mois dans la névralgie pudendale réfractaire.",
            "Amélioration globale démontrée sur le sommeil (PSQI), le retentissement thymique (HAMD/HAMA) et la qualité de vie (SF-36).",
            "Positionne la PRF haute tension longue durée et la cryoneurolyse scanoguidée comme les deux piliers percutanés après échec des infiltrations pudendales simples."
        ],
        "tags": ["Névralgie pudendale", "Nerf pudendal", "Radiofréquence pulsée haute tension", "Douleur pelvi-périnéale", "J Pain Res 2026"]
    },
    "40664401": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Controverses actuelles dans l'ablation par radiofréquence des nerfs géniculés pour gonarthrose chronique : mise au point critique en 6 questions clés (Regional Anesthesia & Pain Medicine 2026)",
        "modality": "Échographie & Fluoroscopie Interventionnelles",
        "intervention_type": "Radiofréquence / Cryoneurolyse des Nerfs Géniculés (Standardisation Technique & Sélection)",
        "cochin_link": "Référentiel méthodologique majeur pour optimiser nos protocoles de « Test anesthésique sous écho + Radiofréquence / Cryoneurolyse des nerfs géniculés (natif ou post-PTG) » à l'Hôpital Cochin.",
        "summary_fr_short": "Mise au point critique de référence (*Regional Anesthesia and Pain Medicine*, oct. 2026, IF 5,1) analysant les 6 controverses expliquant les résultats discordants des essais randomisés sur la radiofréquence des nerfs géniculés : (1) valeur pronostique des blocs tests préalables, (2) positionnement optimal des canules sur les cibles classiques, (3) nombre de branches nerveuses à cibler (au-delà de la triade classique SMGN/SLGN/IMGN), (4) avantages comparés du guidage échographique, fluoroscopique ou combiné, (5) place de la radiofréquence pulsée (PRF), et (6) indications après prothèse totale de genou (PTG).",
        "summary_fr_detailed": "Alors que de nombreuses études observationnelles et essais cliniques montrent un soulagement durable jusqu'à 12 mois après radiofréquence des nerfs géniculés, certains essais contrôlés récents ont rapporté des résultats mitigés en raison de protocoles techniques obsolètes (ciblage limité à 3 nerfs avec de petites électrodes monopolaires à distance de la diaphyse/épiphyse). Cet article de synthèse publié dans *Regional Anesthesia & Pain Medicine* démontre que le succès clinique dépend directement de l'évolution anatomique du ciblage : inclusion de cibles nerveuses additionnelles (nerf géniculé médial récurrent, nerf du vaste intermédiaire, nerf infrapatellaire, nerf géniculé inféro-latéral en respectant le nerf fibulaire commun), positionnement plus postérieur et plus proche de la jonction diaphyso-métaphysaire fémorale, utilisation d'un guidage combiné échographique + fluoroscopique (ou de sondes refroidies / cryoneurolyse à large zone d'ablation), et intérêt confirmé dans les douleurs persistantes post-PTG.",
        "protocol_fr": "Stratégie optimisée à Cochin : (1) Bloc test diagnostique sous échographie à faible volume d'anesthésique local (≤ 0,5–1 mL par nerf pour éviter la diffusion intra-articulaire faussement positive) • (2) Ciblage anatomique élargi adapté à la topographie douloureuse (SMGN, SLGN, IMGN + branche supra-patellaire / nerf du vaste intermédiaire ou rameau infrapatellaire) • (3) Utilisation d'un guidage échographique/TDM ou biplan permettant de visualiser directement les pédicules artério-nerveux géniculés et d'élargir la géométrie d'ablation (radiofréquence refroidie, lésions bipolaires en palissade ou cryoneurolyse).",
        "key_points_fr": [
            "Explique pourquoi les essais utilisant l'ancien protocole à 3 cibles monopolaires étroites sous-performant par rapport aux protocoles élargis (5 à 7 branches articulaires ou sondes refroidies/cryoneurolyse).",
            "Un volume excessif lors du bloc test (> 1 mL par site) diffuse dans l'articulation ou les loges musculaires et diminue la spécificité prédictive du test pré-RFA.",
            "Valide l'approche combinée (repérage échographique direct des pédicules + contrôle osseux) et confirme la pertinence du geste sur les genoux prothésés (post-PTG) douloureux."
        ],
        "tags": ["Nerfs géniculés", "Radiofréquence", "Gonarthrose", "Bloc pronostique", "Anatomie nerveuse", "Reg Anesth Pain Med 2026"]
    },
    "42925628": {
        "category_id": "msk_imaging",
        "title_fr": "Lésions médullaires rachidiennes fortuites en hyposignal T1 en IRM : application rétrospective de la classification Bone-RADS sur 256 989 IRM du rachis (Clinical Imaging 2026)",
        "modality": "IRM du Rachis (Séquences T1, T2, Fat-Sat / Dixon & Scanner Complémentaire)",
        "intervention_type": "Classification Bone-RADS des Lésions Osseuses Vertébrales Fortuites & Triage avant Biopsie",
        "cochin_link": "Outil décisionnel direct pour le « Triage IRM des lésions vertébrales fortuites en hyposignal T1 (Bone-RADS 1 vs Bone-RADS 2/3/4) afin d'éviter les IRM de contrôle et biopsies rachidiennes inutiles » à Cochin.",
        "summary_fr_short": "Étude de cohorte rétrospective (*Clinical Imaging*, oct. 2026, IF 1,8) issue de l'analyse de 256 989 comptes rendus d'IRM rachidiennes (6 709 mentionnant une lésion en hyposignal T1, 212 lésions solitaires suivies analysées selon le système Bone-RADS 2022 de la Society of Skeletal Radiology) : 87,7 % (186/212) des lésions solitaires étaient classables d'emblée en Bone-RADS 1 (« leave-alone » bénin certain) mais avaient pourtant généré 295 examens d'imagerie de suivi inutiles ; aucune lésion Bone-RADS 1 n'a évolué vers la malignité ni nécessité de biopsie sur le suivi.",
        "summary_fr_detailed": "La découverte fortuite d'un nodule médullaire vertébral en hyposignal T1 sur une IRM du rachis est un motif extrêmement fréquent de demande de contrôle IRM ou d'avis en staff de radiologie interventionnelle pour biopsie osseuse. En appliquant l'algorithme Bone-RADS de la Society of Skeletal Radiology (basé sur la présence de graisse intralésionnelle macroscopique ou microscopique en Dixon, l'intensité T2, le rehaussement et le contexte oncologique) à 212 lésions solitaires ayant fait l'objet d'un suivi, les auteurs montrent que 186 lésions (87,7 %) répondaient dès l'IRM initiale aux critères Bone-RADS 1 (hémangiome atypique, îlot de moelle rouge focale, énostose : abstention de tout suivi). L'application stricte de Bone-RADS aurait permis d'économiser 295 IRM/TDM de contrôle sans manquer aucune lésion maligne (0 % de transformation agressive ou de biopsie secondaire).",
        "protocol_fr": "Devant toute lésion vertébrale solitaire en hyposignal T1 à Cochin : (1) Rechercher un signal hyperintense en T1 par rapport au disque ou au muscle et une chute de signal ≥ 20–29 % en séquence Chemical-Shift Dixon non injectée → si présents sans signe agressif : classer **Bone-RADS 1** (bénin certain : moelle rouge focale ou hémangiome lipidique pauvre, aucun suivi ni biopsie) • (2) Si hyposignal T1 ET hyposignal T2 franc sans prise de contraste : vérifier l'ostéocondensation homogène en TDM (énostose / îlot condensant bénin = Bone-RADS 1) • (3) Réserver le suivi court (Bone-RADS 3) ou la biopsie transpédiculaire sous scanner (Bone-RADS 4) aux lésions hyperintenses en T2/STIR ou rehaussées sans chute de signal en Dixon, a fortiori en contexte oncologique.",
        "key_points_fr": [
            "Sur 212 lésions rachidiennes solitaires en hyposignal T1 suivies en imagerie, 87,7 % (186/212) étaient en réalité des lésions bénignes Bone-RADS 1 ne nécessitant aucun contrôle.",
            "Aucune lésion classée Bone-RADS 1 n'a développé de critère d'agressivité ni requis de biopsie osseuse au cours du suivi.",
            "L'intégration du score Bone-RADS dans les comptes rendus d'IRM rachidienne à Cochin sécurise l'abstention et filtre efficacement les indications de biopsie vertébrale scanoguidée."
        ],
        "tags": ["Bone-RADS", "Lésion vertébrale fortuite", "Hyposignal T1", "IRM rachis", "Pertinence des soins", "Clin Imaging 2026"]
    },
    "42861351": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Cryoablation guidée par IRM d'une tumeur desmoïde récidivante de la main au contact des tendons extenseurs : suivi longitudinal sur 5 ans (Radiology Case Reports 2026)",
        "modality": "IRM Interventionnelle & Suivi IRM Multiparamétrique",
        "intervention_type": "Cryoablation Percutanée Ciblée des Tumeurs Desmoïdes des Extrémités (Main / Poignet)",
        "cochin_link": "Illustre la faisabilité et la sécurité des « Cryoablations percutanées itératives à la demande pour les tumeurs desmoïdes récidivantes des extrémités au contact immédiat des tendons et pédicules vasculo-nerveux » discutées en RCP Sarcomes à Cochin.",
        "summary_fr_short": "Étude longitudinale sur 5 ans (*Radiology Case Reports*, sept. 2026, IF 1,0, Open-Access) d'une tumeur desmoïde dorsale de la main multi-récidivante après 5 exérèses chirurgicales chez une adolescente de 14 ans, engainant l'appareil extenseur des 2e et 3e rayons : la réalisation de 4 séances ciblées de cryoablation percutanée guidée par IRM sur 5 ans (ciblant sélectivement les foyers d'hypersignal T2 évolutifs et douloureux pendant le pic de croissance pubertaire) a permis un contrôle local durable, une disparition des douleurs et une préservation fonctionnelle complète des tendons extenseurs de la main sans recours à la radiothérapie ni à l'amputation.",
        "summary_fr_detailed": "Les tumeurs desmoïdes de la main sont exceptionnelles (< 20 cas rapportés) et posent un défi majeur d'épargne fonctionnelle en raison de la contiguïté immédiate du derme, des tendons extenseurs/fléchisseurs et des nerfs collatéraux digitaux. Après 5 récidives post-chirurgicales entraînant une hyperextension douloureuse des 2e et 3e doigts, la patiente a été traitée par cryoablations percutanées ciblées sous guidage IRM (choisi pour son contraste tissus mous supérieur au scanner sur cette lésion de la face dorsale de la main). Quatre procédures focales réparties sur 5 ans ont permis de détruire sélectivement les bourgeons actifs tout en protégeant la peau et le coulissement tendineux, confirmant que les tendons matures riches en collagène tolèrent le gel cryogénique et que des séances de cryoablation « à la demande » permettent de franchir la période d'activité biologique maximale de la fibromatose.",
        "protocol_fr": "Planification IRM haute résolution (T2 Fat-Sat et T1 Gado pour distinguer les plages hypercellulaires actives en hypersignal T2 de la fibrose cicatricielle en hyposignal T2) • Insertion de cryosondes de petit calibre parallèlement aux gaines tendineuses • Hydrodissection sous-cutanée et réchauffement cutané actif continu par gant d'eau tiède (indispensable à la face dorsale de la main où l'espace dermo-tumoral est millimétrique) • Suivi IRM longitudinal et retraitement focal ciblé uniquement en cas de nodule symptomatique progressif.",
        "key_points_fr": [
            "Confirme que la matrice collagénique des tendons de la main résiste à la cryoablation sans rupture tendineuse secondaire, contrairement aux ablations hyperthermiques (RF/MWA).",
            "Valide la stratégie de cryoablations focales répétées « à la demande » sur les seuls foyers évolutifs en hypersignal T2 pour préserver la fonction fine de la main.",
            "Alternative conservatrice précieuse évitant la radiothérapie (toxique chez le sujet jeune) ou la chirurgie mutilante des extrémités."
        ],
        "tags": ["Tumeur desmoïde", "Main", "Cryoablation", "Guidage IRM", "Préservation tendineuse", "Radiol Case Rep 2026"]
    },
    "42592941": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Fractures et disjonctions verticalement instables de l'anneau pelvien : impact majeur du vissage percutané trans-sacré multi-étagé (S1 + S2) sur le taux d'échec mécanique (Journal of Orthopaedic Trauma 2026)",
        "modality": "Fluoroscopie Biplan / Scanner TDM Interventionnel",
        "intervention_type": "Vissage Percutané Trans-Sacré Multi-Étagé (MAT) vs Vissage Ilio-Sacré Simple (SS) du Bassin",
        "cochin_link": "Référence biomécanique et clinique directe pour les « Vissages percutanés du bassin postérieur (choix d'un montage trans-sacré multi-étagé S1+S2 vs vis sacro-iliaque isolée) » réalisés à l'Hôpital Cochin.",
        "summary_fr_short": "Étude de cohorte en centre de traumatologie de niveau I (*Journal of Orthopaedic Trauma*, juil./déc. 2026, IF 2,3, 67 patients avec lésion pelvienne verticalement instable OTA/AO 61C déplacée ≥ 10 mm) comparant le vissage percutané combinant fixation sacrée multi-étagée et au moins 1 vis trans-sacrée (groupe MAT, n = 38) au vissage mono-étagé ou par vis sacro-iliaques seules (groupe SS, n = 29) : chute spectaculaire du taux d'échec mécanique avec déplacement secondaire ≥ 10 mm (2,6 % dans le groupe MAT contre 48,3 % dans le groupe SS, p < 0,001) et division par 12 du taux de reprise chirurgicale (2,6 % vs 31,0 %, p = 0,002).",
        "summary_fr_detailed": "La stabilisation purement percutanée des lésions postérieures verticalement instables de l'anneau pelvien (fractures sacrées longitudinales [53,7 %], fractures-luxations sacro-iliaques [25,3 %] et disjonctions sacro-iliaques complètes [20,9 %]) expose à un risque élevé de déplacement secondaire par cisaillement vertical lorsque l'ancrage mécanique est insuffisant. Sur 67 patients consécutifs, les auteurs démontrent que les montages associant une fixation sur plusieurs étages sacrés (S1 et S2) et au moins une vis trans-sacrée (TS, prenant appui dans les trois corticales ilio-sacro-iliaques jusqu'à l'ilion controlatéral) réduisent le taux de faillite mécanique à seulement 2,6 % (1/38), contre 48,3 % (14/29) lorsque seules des vis sacro-iliaques courtes (arrêtées dans le corps de S1) ou un seul niveau sacré sont utilisés (p < 0,001). Le taux de réintervention chirurgicale chute parallèlement de 31,0 % à 2,6 % (p = 0,002).",
        "protocol_fr": "Analyse TDM pré-opératoire systématique des couloirs osseux transversaux de S1 et S2 (dépistage d'un sacrum dysmorphique) • En présence d'une instabilité verticale ou à fort cisaillement postérieur : proscrire le vissage ilio-sacré court mono-étagé isolé • Réaliser un montage percutané **MAT (Multilevel And Transsacral)** associant deux niveaux sacrés (S1 + S2) dont au moins une vis trans-sacrée (TSS) traversant les deux articulations sacro-iliaques pour s'ancrer dans la corticale externe de l'ilion controlatéral.",
        "key_points_fr": [
            "Démonstration majeure : le vissage percutané multi-étagé incluant au moins une vis trans-sacrée (MAT) abaisse le taux de faillite mécanique de 48,3 % à 2,6 % (p < 0,001).",
            "Divise par 12 le taux de reprise chirurgicale (2,6 % vs 31,0 %, p = 0,002) dans les lésions postérieures instables de l'anneau pelvien.",
            "Confirme que l'ancrage tri-cortical/quadri-cortical d'une vis trans-sacrée (S1 et/ou S2) est indispensable pour neutraliser les contraintes de cisaillement vertical."
        ],
        "tags": ["Vissage percutané du bassin", "Vis trans-sacrée", "Fixation multi-étagée", "S1-S2", "Instabilité pelvienne", "J Orthop Trauma 2026"]
    },
    "42999649": {
        "category_id": "consolidation_screw_cement",
        "title_fr": "Radiofréquence concomitante du nerf basivertébral (BVN RFA) et cimentoplastie vertébrale dans le traitement palliatif multimodal des fractures vertébrales pathologiques tumorales (Interventional Pain Medicine 2026)",
        "modality": "Fluoroscopie Biplan / Scanner TDM Interventionnel",
        "intervention_type": "Ablation par Radiofréquence du Nerf Basivertébral (BVN RFA) + Cimentoplastie Vertébrale",
        "cochin_link": "En lien direct avec les procédures combinées de « Thermoablation / Radiofréquence + Cimentoplastie / Vertébroplastie / Kyphoplastie pour fracture vertébrale tumorale douloureuse » réalisées à Cochin.",
        "summary_fr_short": "Série clinique innovante (*Interventional Pain Medicine*, oct. 2026, IF 1,8, Open-Access) évaluant l'association dans le même temps opératoire d'une ablation par radiofréquence ciblée du nerf basivertébral (BVN RFA) et d'une cimentoplastie d'augmentation vertébrale (VA) chez des patients présentant une fracture vertébrale par compression pathologique d'origine tumorale : réduction immédiate et soutenue de la douleur rachidienne avec amélioration fonctionnelle chez 100 % des patients et 0 % de complication péri- ou post-procédurale.",
        "summary_fr_detailed": "Bien que la vertébroplastie / kyphoplastie stabilise mécaniquement les fractures vertébrales pathologiques secondaires aux métastases rachidiennes, certains patients conservent des douleurs résiduelles liées à la transmission nociceptive des plateaux vertébraux fracturés via le nerf basivertébral (BVN, branche du nerf sinu-vertébral pénétrant par le foramen basivertébral postérieur et arborisant au centre du corps vertébral). En ciblant électivement le tronc du nerf basivertébral par radiofréquence thermique (au tiers postéro-central du corps vertébral, à 30–50 % de la paroi postérieure) immédiatement avant l'injection de ciment PMMA par la même canule transpédiculaire, cette approche réalise une dénervation complète des plateaux vertébraux associée à la stabilisation mécanique, sans allonger significativement la procédure ni induire de complication neurologique.",
        "protocol_fr": "Abord transpédiculaire unipédiculaire ou bipédiculaire sous guidage scopique biplan ou scanner • Positionnement initial de l'électrode de radiofréquence bipolaire au confluent du nerf basivertébral (centre du corps vertébral dans le plan coronal, entre les 30 % et 50 % postérieurs dans le plan sagittal, à distance de sécurité du mur postérieur) • Thermoablation du nerf basivertébral (85°C pendant 15 min ou protocole RF tumoral dédié) • Par le même introducteur coaxial : vertébroplastie / kyphoplastie au ciment PMMA haute viscosité sous contrôle fluoroscopique continu.",
        "key_points_fr": [
            "Synergie antalgique directe entre la dénervation thermique du nerf basivertébral (suppression de la nociception des plateaux vertébraux fracturés) et la consolidation mécanique par cimentoplastie PMMA.",
            "Réalisable en un seul temps opératoire par le même abord transpédiculaire coaxial sans sur-risque procédural (0 % de complication).",
            "Particulièrement pertinent à Cochin lors des cimentoplasties oncologiques avec atteinte douloureuse prédominante des plateaux vertébraux."
        ],
        "tags": ["Nerf basivertébral", "Radiofréquence", "Cimentoplastie", "Vertébroplastie", "Fracture vertébrale pathologique", "Interv Pain Med 2026"]
    },
    "41694550": {
        "category_id": "pudendal_cryoneurolysis",
        "title_fr": "Essai randomisé contrôlé comparant la radiofréquence pulsée bilatérale des racines sacrées S2–S4 et la neurolyse chimique du ganglion Impar pour les douleurs périnéales oncologiques sévères (Pain Reports 2026)",
        "modality": "Fluoroscopie / Scanner Interventionnel + Neurostimulation",
        "intervention_type": "Radiofréquence Pulsée Sélective Bilatérale des Racines Sacrées (S2–S4) vs Neurolyse du Ganglion Impar",
        "cochin_link": "Référence comparative directe pour le choix de la cible lors des « Procédures antalgiques pelvi-périnéales oncologiques et réfractaires (nerf pudendal / racines sacrées S2–S4 vs ganglion Impar) » à l'Hôpital Cochin.",
        "summary_fr_short": "Essai prospectif randomisé contrôlé (*Pain Reports*, févr. 2026, IF 3,4, Open-Access, 40 patients avec douleur cancéreuse périnéale ou périanale sévère EVA ≥ 7 randomisés 1:1) comparant la radiofréquence pulsée (PRF) sélective bilatérale des racines sacrées S2–S4 (n = 20) à la neurolyse chimique au phénol 6 % du ganglion Impar (GIN, n = 20) : baisse significative de l'EVA jusqu'à 12 semaines dans les deux bras (p < 0,001), mais supériorité statistiquement significative du groupe PRF S2–S4 sur le soulagement douloureux en salle de réveil et à 1, 4 et 8 semaines (p < 0,05), moindre consommation d'oxycodone et de prégabaline, et meilleurs scores de qualité de vie et de satisfaction des patients.",
        "summary_fr_detailed": "Les douleurs périnéales et périanales d'origine oncologique (cancers pelviens, rectaux, gynécologiques ou sacrés) combinent une composante sympathique viscérale (relayée par le ganglion Impar pré-sacro-coccygien) et une composante somatique/neuropathique majeure véhiculée par le nerf pudendal issu des racines sacrées S2, S3 et S4. Cet essai randomisé compare face-à-face la neurolyse chimique du ganglion Impar (phénol 6 %) et la radiofréquence pulsée (PRF) sélective bilatérale des racines sacrées S2–S4 (origine directe du nerf pudendal). Bien que les deux techniques diminuent significativement l'EVA jusqu'à 3 mois, le ciblage direct des afférences somatiques S2–S4/pudendales procure une analgésie significativement plus puissante à 1, 4 et 8 semaines, réduit la consommation d'opioïdes forts (oxycodone) et de gabapentinoïdes (prégabaline), et améliore significativement la qualité de vie sans induire de déficit sphinctérien.",
        "protocol_fr": "Repérage fluoroscopique ou TDM des foramens sacrés postérieurs S2, S3 et S4 bilatéraux (et/ou du nerf pudendal à l'épine ischiatique / canal d'Alcock et de l'interligne sacro-coccygien pour le ganglion Impar) • Confirmation par stimulation sensitive (< 0,5 V reproduisant les paresthésies dans le territoire périnéal douloureux) et motrice • Radiofréquence pulsée (42°C) bilatérale S2–S4 ou cryoneurolyse pudendale sélective sous scanner à Cochin • Possibilité d'associer en un temps un bloc/neurolyse du ganglion Impar en cas de composante ténesmoïde/sympathique rectale prédominante.",
        "key_points_fr": [
            "Premier essai randomisé contrôlé démontrant que la neuromodulation des racines sacrées S2–S4 (contingent pudendal) surpasse la neurolyse isolée du ganglion Impar sur les douleurs périnéales cancéreuses sévères (EVA ≥ 7).",
            "Réduit significativement les besoins en oxycodone et prégabaline tout en améliorant la qualité de vie globale.",
            "Confirme que les douleurs pelvi-périnéales oncologiques nécessitent de cibler prioritairement la voie somatique pudendale / S2–S4 (par PRF ou cryoneurolyse scanoguidée à Cochin), éventuellement couplée au ganglion Impar."
        ],
        "tags": ["Douleur périnéale oncologique", "Racines sacrées S2-S4", "Ganglion Impar", "Nerf pudendal", "Radiofréquence pulsée", "Essai randomisé", "Pain Rep 2026"]
    },
    "42803616": {
        "category_id": "pain_cryoneurolysis",
        "title_fr": "Radiofréquence pulsée échoguidée des nerfs supra-scapulaire et axillaire pour épaule douloureuse chronique réfractaire : étude comparative en double aveugle du voltage de sortie (45 V vs 85 V, 80 patients, Pain Management 2026)",
        "modality": "Échographie Interventionnelle + Neurostimulation",
        "intervention_type": "Radiofréquence Pulsée (PRF) Échoguidée Combinée des Nerfs Supra-Scapulaire & Axillaire",
        "cochin_link": "Directement applicable aux procédures de « Radiofréquence / Cryoneurolyse de nerfs superficiels et articulaires de l'épaule (nerf supra-scapulaire et nerf axillaire) » réalisées à Cochin.",
        "summary_fr_short": "Étude prospective comparative en double aveugle (*Pain Management*, sept. 2026, IF 2,0) portant sur 80 patients souffrant d'épaule douloureuse chronique réfractaire traités par radiofréquence pulsée (PRF) combinée sous guidage échographique des nerfs supra-scapulaire et axillaire à tension standard (45 V, n = 40) versus haute tension (85 V, n = 40) avec suivi à 6 mois : amélioration fonctionnelle et antalgique dans les deux groupes sans différence significative sur l'EVA à 6 mois entre 45 V et 85 V (5,89 vs 5,47, p = 0,137), mais interaction temps × groupe significative en faveur du 85 V sur le score fonctionnel QuickDASH (49,86 vs 53,84, p = 0,018) et tolérance parfaite dans les deux bras.",
        "summary_fr_detailed": "Le nerf supra-scapulaire assure environ 70 % de l'innervation sensitive de l'articulation gléno-humérale (capsule postéro-supérieure et coiffe des rotateurs), tandis que le nerf axillaire (circonflexe) innerve le contingent capsulaire inféro-postérieur. Cette étude prospective en double insu portant sur 80 patients évalue le double ciblage échoguidé (nerf supra-scapulaire dans l'échancrure scapulaire/fosse supra-épineuse + nerf axillaire au col chirurgical postérieur de l'humérus dans l'espace quadrilatère) en comparant deux niveaux de tension de sortie (45 V vs 85 V à température maximale contrôlée ≤ 42°C). L'augmentation du voltage à 85 V est parfaitement sûre sans aucune parésie motrice du supra-/infra-épineux ni du deltoïde, et s'accompagne d'une cinétique de récupération fonctionnelle QuickDASH significativement plus favorable au cours du suivi (p = 0,018), bien que l'EVA moyenne à 6 mois reste proche entre les deux réglages.",
        "protocol_fr": "Guidage échographique haute fréquence : (1) Ciblage du nerf supra-scapulaire dans la fosse supra-épineuse / échancrure coracoïdienne sous le ligament transverse supérieur de la scapula (en repérant l'artère supra-scapulaire au Doppler couleur) • (2) Ciblage des rameaux articulaires du nerf axillaire à la face postérieure du col chirurgical de l'humérus (au voisinage de l'artère circonflexe postérieure de l'humérus) • Confirmation électrophysiologique sensitive (< 0,5 V) • Radiofréquence pulsée (45 à 85 V, maintien thermique ≤ 42°C) préservant intégralement la fonction motrice de la coiffe et du deltoïde.",
        "key_points_fr": [
            "Valide sur 80 patients le double ciblage échoguidé associant le nerf supra-scapulaire (70 % de l'innervation capsulaire) et le nerf axillaire (contingent inférieur) dans les omalgies chroniques réfractaires.",
            "Sécurité motrice absolue (0 % de déficit du deltoïde ou des rotateurs) y compris à haut voltage (85 V) tant que le plafond thermique non destructeur (≤ 42°C) est respecté.",
            "Alternative précieuse en cas d'échec des infiltrations/arthro-infiltrations gléno-humérales ou sous-acromiales chez les patients inopérables."
        ],
        "tags": ["Nerf supra-scapulaire", "Nerf axillaire", "Radiofréquence pulsée", "Épaule douloureuse chronique", "Échographie interventionnelle", "Pain Manag 2026"]
    },
    "42562224": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Sclérothérapie percutanée des malformations veineuses des parties molles : modélisation longitudinale du soulagement douloureux et mise en évidence d'un effet plateau après 3 séances (Annals of Vascular Surgery 2026)",
        "modality": "Échographie Doppler & Fluoroscopie Interventionnelle",
        "intervention_type": "Sclérothérapie Percutanée Itérative des Malformations Veineuses Douloureuses (Règle des 3 Séances)",
        "cochin_link": "Fournit un repère décisionnel concret pour planifier le nombre de séances de « Sclérothérapie percutanée et bascule vers la cryoablation/chirurgie dans les malformations veineuses douloureuses des parties molles » à Cochin.",
        "summary_fr_short": "Analyse longitudinale par modèle linéaire à effets mixtes (*Annals of Vascular Surgery*, août/déc. 2026, IF 1,5) caractérisant la cinétique de réponse antalgique au fil des séances successives de sclérothérapie percutanée des malformations veineuses (MV) : taux d'efficacité globale de 83,4 % avec réduction hautement significative de l'EVA et de la vascularisation Doppler (p < 0,001) et 0 % de complication majeure, mais démonstration mathématique d'un **effet plateau après la 3e séance de sclérothérapie**, justifiant une réévaluation formelle après 3 séances plutôt que la multiplication infinie des injections.",
        "summary_fr_detailed": "Les malformations veineuses (MV) des parties molles nécessitent fréquemment plusieurs séances de sclérothérapie percutanée, mais le nombre optimal de séances au-delà duquel le bénéfice antalgique marginal devient minime restait mal défini. En modélisant longitudinalement les scores EVA et le flux résiduel en écho-Doppler à travers les séances successives (modèle mixte expliquant 68 % de la variance), cette étude démontre que l'essentiel du gain antalgique est acquis au cours des 3 premières séances de sclérothérapie (efficacité globale de 83,4 %), après quoi la courbe de réponse atteint un plateau net. Un jeune âge (p = 0,03) et un score douloureux initial modéré (p < 0,001) prédisent une meilleure réponse finale, tandis que le volume lésionnel initial et l'intervalle entre les séances n'altèrent pas significativement la trajectoire.",
        "protocol_fr": "Programme structuré en 3 séances de sclérothérapie percutanée sous guidage échographique et scopique • À l'issue de la 3e séance : réévaluation clinique (EVA) et IRM/écho-Doppler systématique • En cas de douleur résiduelle malgré l'atteinte du plateau de sclérothérapie (souvent liée à une composante fibro-thrombotique tissulaire ou des phlébolithes enchâssés non accessibles au sclérosant endoluminal), discuter à Cochin un relais par **cryoablation percutanée** de la malformation veineuse résiduelle.",
        "key_points_fr": [
            "Taux d'efficacité antalgique global de 83,4 % sans aucune complication majeure après sclérothérapie percutanée guidée par échographie.",
            "Identification d'un effet plateau franc après la 3e séance de sclérothérapie : au-delà de 3 séances, le bénéfice antalgique supplémentaire d'injections répétées devient limité.",
            "Valide un protocole standardisé de réévaluation après 3 séances à Cochin pour décider soit de l'arrêt thérapeutique (succès), soit d'un relais par cryoablation percutanée sur le contingent tissulaire résiduel."
        ],
        "tags": ["Malformation veineuse", "Sclérothérapie percutanée", "Effet plateau", "Douleur chronique", "Échographie Doppler", "Ann Vasc Surg 2026"]
    },
    "42896215": {
        "category_id": "desmoid_soft_tissue",
        "title_fr": "Sclérothérapie percutanée des malformations vasculaires à flux lent : enquête internationale ISSVA des pratiques (choix du sclérosant, gestion de la coagulation et prévention des complications, Vascular Medicine 2026)",
        "modality": "Échographie & Fluoroscopie Interventionnelles",
        "intervention_type": "Sclérothérapie Percutanée des Malformations Vasculaires à Flux Lent (Éthanol, Bléomycine, Polidocanol)",
        "cochin_link": "Référentiel international des pratiques pour les séances de « Sclérothérapie percutanée (Polidocanol / Bléomycine / Éthanol) et gestion péri-procédurale de la coagulation des malformations vasculaires » à Cochin.",
        "summary_fr_short": "Enquête internationale multicentrique du réseau ISSVA (*Vascular Medicine*, oct. 2026, IF 2,2, 52 spécialistes de 16 pays dont 90 % en CHU et 92 % en RCP dédiée) détaillant les standards pratiques de sclérothérapie des malformations vasculaires à flux lent (veineuses et lymphatiques) : prédominance du trio éthanol (67 %), bléomycine (58 %) et polidocanol (52 %), l'éthanol étant unanimement classé comme l'agent le plus efficace mais le plus à risque de nécrose cutanée (94 %) et de lésion nerveuse (75 %), justifiant l'essor de la mousse de polidocanol, de la bléomycine et de l'éthanol gélifié en zones sensibles.",
        "summary_fr_detailed": "Cette enquête internationale menée auprès des centres experts de l'ISSVA (International Society for the Study of Vascular Anomalies) dresse la cartographie complète des pratiques de radiologie interventionnelle dans les malformations vasculaires à flux lent (SFVM). Dans 92 % des centres universitaires, l'indication est posée en réunion de concertation pluridisciplinaire (RCP). Si l'éthanol absolu reste disponible dans 67 % des centres, sa toxicité locale (nécrose cutanée rapportée comme risque majeur par 94 % des opérateurs, neuropathie périphérique par 75 %) et systémique (collapsus cardiovasculaire / spasme artériel pulmonaire) conduit à privilégier la mousse de polidocanol (52 %) ou la bléomycine (58 %) pour les lésions superficielles, distales ou juxta-nerveuses. Chez l'adulte, près de la moitié des procédures sont réalisées sous anesthésie locale/sédation (41–49 %) lorsque des agents non douloureux (polidocanol, bléomycine) sont utilisés, contre une anesthésie générale quasi systématique sous éthanol pur.",
        "protocol_fr": "Sélection raisonnée de l'agent sclérosant selon la topographie : (1) Lésions superficielles sous-cutanées ou proches d'un tronc nerveux : mousse de polidocanol (1–2 %) ou bléomycine (sans œdème majeur post-procédural) • (2) Lésions intramusculaires profondes à distance des nerfs : éthanol gélifié radio-opaque ou mousse de polidocanol avec contrôle de stase • Bilan d'hémostase pré-procédural (D-dimères, fibrinogène, plaquettes) dans les malformations veineuses étendues pour dépister une coagulopathie intravasculaire localisée (LIC) et encadrer le geste par HBPM préventive/curative si fibrinogène bas.",
        "key_points_fr": [
            "Dans 92 % des centres experts internationaux (ISSVA), la prise en charge des malformations vasculaires à flux lent repose sur une décision de RCP multidisciplinaire.",
            "Hiérarchise clairement le profil de sécurité des 3 sclérosants majeurs : polidocanol et bléomycine permettent des traitements sous anesthésie locale avec un risque cutané et nerveux réduit par rapport à l'éthanol liquide.",
            "Rappelle l'importance du dépistage de la coagulopathie intravasculaire localisée (fibrinogène, D-dimères) avant sclérothérapie des malformations veineuses volumineuses."
        ],
        "tags": ["Malformation vasculaire à flux lent", "ISSVA", "Sclérothérapie", "Polidocanol", "Bléomycine", "Coagulopathie intravasculaire localisée", "Vasc Med 2026"]
    },
    "42849255": {
        "category_id": "msk_imaging",
        "title_fr": "IRM pelvienne oncologique de routine (quantification de graisse Dixon IDEAL-IQ PDFF, R2* et radiomique T1) pour prédire l'ostéoporose rachidienne définie en QCT chez les patients suivis pour cancer (European Journal of Radiology 2026)",
        "modality": "IRM Pelvienne 3T (Séquence Multi-Écho Chemical-Shift IDEAL-IQ : PDFF & R2*) & QCT Lombaire",
        "intervention_type": "Dépistage Opportuniste IRM de la Fragilité Osseuse Trabéculaire avant Geste ou Radiothérapie Pelvienne",
        "cochin_link": "Directement utile lors de la lecture des « IRM pelviennes et rachidiennes oncologiques à Cochin pour évaluer la qualité osseuse trabéculaire et le risque de fracture par insuffisance sacrée/vertébrale avant radiothérapie ou vissage/cimentoplastie ».",
        "summary_fr_short": "Étude prospective sur 123 patients oncologiques (*European Journal of Radiology*, oct. 2026, IF 3,2) corrélant les biomarqueurs médullaires extraits de l'IRM pelvienne de surveillance (fraction graisseuse en densité de protons PDFF et relaxométrie R2* sur séquence Dixon multi-écho IDEAL-IQ au col fémoral, à la tête fémorale et à l'ilion, ainsi que la radiomique T1) à la densité minérale osseuse volumique (vBMD T12–L2) mesurée par QCT : augmentation significative de la PDFF médullaire et baisse du R2* avec la dégradation de la densité osseuse sur tous les sites (p < 0,05), excellente reproductibilité inter-lecteurs (ICC = 0,903–0,996) et bonne capacité discriminante pour identifier l'ostéoporose (AUC = 0,73–0,78) sans examen irradiant supplémentaire.",
        "summary_fr_detailed": "Les patients suivis pour cancer pelvien (prostate, col utérin, rectum, sarcomes) présentent un risque élevé d'ostéoporose secondaire (hormonothérapie, chimiothérapie, radiothérapie pelvienne) et de fractures par insuffisance du sacrum ou des corps vertébraux. Sur 123 patients ayant bénéficié à la fois d'une IRM pelvienne incluant une séquence chimique multi-écho (IDEAL-IQ) et d'un scanner quantitatif lombaire (QCT T12–L2), les auteurs montrent que l'adiposité médullaire mesurée par la PDFF (Proton Density Fat Fraction) augmente significativement tandis que le R2* (sensible à la susceptibilité magnétique des travées osseuses minéralisées) diminue lorsque la densité minérale osseuse chute vers l'ostéoporose (p < 0,05). La reproductibilité inter-observateur de la mesure sur la tête fémorale, le col fémoral et l'aile iliaque est remarquable (ICC moyen de 3 lecteurs : 0,903 à 0,996), permettant un repérage opportuniste fiable des patients ostéoporotiques à haut risque fracturaire directement sur leur IRM oncologique de routine.",
        "protocol_fr": "Sur les IRM du bassin et du rachis réalisées chez les patients oncologiques à Cochin : exploiter les séquences Dixon quantitatives (PDFF / Fat Fraction) et l'analyse du signal T1 sur l'aile iliaque et le fémur proximal • Une élévation marquée de la fraction graisseuse médullaire (PDFF élevée) couplée à une chute du R2* signale une raréfaction trabéculaire ostéoporotique sévère • En tenir compte avant radiothérapie pelvienne (prévention des fractures sacrées) et lors des gestes de stabilisation percutanée (indication préférentielle d'augmentation cimentée des vis ou de sacroplastie/cimentoplastie préventive).",
        "key_points_fr": [
            "Excellente reproductibilité inter-lecteurs (ICC = 0,903–0,996) de la mesure de la fraction graisseuse médullaire (PDFF) et du R2* sur le fémur proximal et l'ilion en IRM pelvienne.",
            "Corrélation physiopathologique directe avec le QCT lombaire : la perte osseuse trabéculaire s'accompagne d'une conversion adipeuse médullaire (hausse de la PDFF) et d'une perte d'effet de susceptibilité trabéculaire (baisse du R2*).",
            "Permet un dépistage opportuniste sans irradiation additionnelle de la fragilité osseuse chez les patients cancéreux candidats à une ostéosynthèse percutanée ou exposés aux fractures par insuffisance sacrée."
        ],
        "tags": ["IRM pelvienne", "Dixon quantitatif", "PDFF", "Ostéoporose oncologique", "Moelle osseuse", "Eur J Radiol 2026"]
    },
    "42720734": {
        "category_id": "percutaneous_ablation_general",
        "title_fr": "Ablation percutanée guidée par l'image des tumeurs solides malignes pédiatriques et de l'adolescent (sarcomes osseux, sarcomes des parties molles, oligométastases) : revue des modalités et indications (Pediatric Radiology 2026)",
        "modality": "Scanner TDM / Échographie / IRM Interventionnelle",
        "intervention_type": "Ablation Percutanée Multimodale (Cryoablation, RFA, MWA, IRE, ECT) des Sarcomes & Oligométastases du Sujet Jeune",
        "cochin_link": "Utile pour les discussions de RCP Sarcomes / AJA (Adolescents et Jeunes Adultes) à Cochin concernant « L'ablation percutanée par cryoablation, RF, micro-ondes ou électrochimiothérapie des récidives locales ou oligométastases de sarcomes osseux et des parties molles ».",
        "summary_fr_short": "Synthèse exhaustive de 30 ans de littérature (*Pediatric Radiology*, sept. 2026, IF 2,1) évaluant les 5 modalités d'ablation percutanée guidée par l'image — radiofréquence (RFA), cryoablation, micro-ondes (MWA), électroporation irréversible (IRE) et électrochimiothérapie (ECT) — dans les tumeurs malignes solides de l'enfant et de l'adolescent (dont les ostéosarcomes, sarcomes d'Ewing et sarcomes des parties molles où la survie globale à 5 ans stagne autour de 60 %) : précise les indications validées en situation de récidive locale, de maladie oligométastatique ou de limitation chirurgicale.",
        "summary_fr_detailed": "Chez l'adolescent et le jeune adulte (AJA) atteint d'ostéosarcome, de sarcome d'Ewing ou de sarcome des parties molles non rhabdomyosarcomateux, la chirurgie d'exérèse carcinologique associée à la chimiothérapie demeure le traitement de première ligne, mais les récidives locales en territoire irradié ou multi-opéré et les progressions oligométastatiques (osseuses, pulmonaires ou des parties molles) posent des difficultés majeures d'épargne fonctionnelle. Cette revue compare les profils biophysiques des 5 énergies ablatives : la cryoablation (visualisation directe de l'iceball, préservation de la trame collagénique et moindre douleur péri-opératoire), la RFA et la MWA (destruction thermique rapide des cibles intra-osseuses ou parenchymateuses à distance des nerfs), ainsi que l'IRE et l'ECT (ablation non thermique respectant les axes vasculo-nerveux et le canal rachidien).",
        "protocol_fr": "Indication validée en RCP Sarcomes spécialisée pour les lésions récidivantes, réfractaires ou oligométastatiques lorsque la reprise chirurgicale serait mutilante • Choix de l'énergie selon l'environnement anatomique : Cryoablation pour les masses des parties molles, la paroi thoracique/pelvienne et les métastases osseuses ostéocondensantes ; ECT/IRE en contiguïté immédiate d'un plexus nerveux majeur ou de l'espace épidural ; MWA/RFA pour les cibles intra-osseuses ou pulmonaires profondes • Thermoprotection active systématique (hydrodissection, carbodissection, neuromonitoring).",
        "key_points_fr": [
            "Synthétise les indications comparées des 5 technologies ablatives (Cryoablation, RFA, MWA, IRE, ECT) dans les sarcomes osseux et des parties molles en rechute ou oligométastatiques.",
            "Rappelle que la chirurgie et le traitement systémique restent le standard de 1re ligne, l'ablation percutanée constituant une arme d'épargne fonctionnelle majeure en rechute locale ou oligométastatique.",
            "Souligne la complémentarité entre cryoablation (suivi visuel de l'iceball) et électroporation réversible/irréversible (ECT/IRE) au contact des structures neurovasculaires critiques."
        ],
        "tags": ["Sarcome osseux", "Sarcome des parties molles", "Oligométastases", "Cryoablation", "Électrochimiothérapie", "Pediatr Radiol 2026"]
    }
}


def is_real_pdf(pdf_path: Path) -> bool:
    """Return True only if pdf_path exists and is a genuine publisher/author PDF (never ReportLab-generated)."""
    if not pdf_path.exists():
        return False
    try:
        b = pdf_path.read_bytes()
        return len(b) > 50_000 and b.startswith(b"%PDF") and b"ReportLab PDF Library" not in b[:4096]
    except Exception:
        return False


def try_download_real_pdf(pmid: str, doi: str, pdf_path: Path, pmcid: str = "") -> bool:
    """
    Attempt to download the genuine publisher or open-access repository PDF (Springer, Nature,
    PMC/EuropePMC, Unpaywall, OpenAlex, HAL). Never generates a synthetic PDF.
    """
    if is_real_pdf(pdf_path):
        return True
    if pdf_path.exists():
        pdf_path.unlink()

    if not doi and not pmcid:
        return False

    candidates = []
    if pmcid:
        candidates.append(f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf")
        candidates.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/")
    if doi.startswith("10.1007/") or doi.startswith("10.1186/") or doi.startswith("10.1245/"):
        candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if doi.startswith("10.1038/"):
        suffix = doi.split("/", 1)[1]
        candidates.append(f"https://www.nature.com/articles/{suffix}.pdf")
    if doi.startswith("10.3389/"):
        candidates.append(f"https://www.frontiersin.org/articles/{doi}/pdf")

    # Query Unpaywall
    try:
        uw_url = f"https://api.unpaywall.org/v2/{doi}?email=thomas.lefevre@aphp.fr"
        req = urllib.request.Request(uw_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as uwr:
            uwd = json.loads(uwr.read().decode())
            best = uwd.get("best_oa_location") or {}
            if best.get("url_for_pdf"):
                candidates.append(best["url_for_pdf"])
            for loc in uwd.get("oa_locations", []):
                u = loc.get("url_for_pdf")
                if u and u not in candidates:
                    candidates.append(u)
    except Exception:
        pass

    # Query OpenAlex as backup for institutional/HAL OA links
    try:
        oa_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
        req = urllib.request.Request(oa_url, headers={"User-Agent": "BiblioOsteo/1.0 (mailto:thomas.lefevre@aphp.fr)"})
        with urllib.request.urlopen(req, timeout=8) as oar:
            oad = json.loads(oar.read().decode())
            for loc in oad.get("locations", []):
                u = loc.get("pdf_url")
                if u and u not in candidates:
                    candidates.append(u)
    except Exception:
        pass

    tmp_path = Path(f"/tmp/biblio_dl_{pmid}.pdf")
    for c in candidates:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "15",
                    "-c",
                    f"/tmp/biblio_cookies_{pmid}.txt",
                    "-b",
                    f"/tmp/biblio_cookies_{pmid}.txt",
                    c,
                    "-o",
                    str(tmp_path),
                ],
                check=False,
            )
            if is_real_pdf(tmp_path):
                pdf_path.write_bytes(tmp_path.read_bytes())
                tmp_path.unlink()
                print(f"[PDF] Downloaded real PDF for PMID {pmid} ({pdf_path.stat().st_size // 1024} KB)")
                return True
        except Exception:
            pass
    if tmp_path.exists():
        tmp_path.unlink()
    return False


MONTHS_FR = {
    1: "Janv.",
    2: "Févr.",
    3: "Mars",
    4: "Avr.",
    5: "Mai",
    6: "Juin",
    7: "Juil.",
    8: "Août",
    9: "Sept.",
    10: "Oct.",
    11: "Nov.",
    12: "Déc.",
}

JOURNAL_IMPACT_FACTORS = {
    "radiology": (12.1, "Radiology"),
    "radiographics": (5.2, "RadioGraphics"),
    "regional anesthesia and pain medicine": (5.1, "Reg Anesth Pain Med"),
    "european journal of cancer": (7.6, "Eur J Cancer"),
    "european radiology experimental": (3.7, "Eur Radiol Exp"),
    "european radiology": (4.7, "Eur Radiol"),
    "european journal of radiology": (3.2, "Eur J Radiol"),
    "insights into imaging": (4.1, "Insights Imaging"),
    "current treatment options in oncology": (4.1, "Curr Treat Options Oncol"),
    "neurosurgery": (3.9, "Neurosurgery"),
    "joint bone spine": (3.8, "Joint Bone Spine"),
    "pain reports": (3.4, "Pain Rep"),
    "skeletal radiology": (1.9, "Skeletal Radiol"),
    "cardiovascular and interventional radiology": (2.8, "CVIR"),
    "journal of vascular and interventional radiology": (2.6, "JVIR"),
    "diagnostic and interventional imaging": (3.9, "Diagn Interv Imaging"),
    "diagnostic and interventional radiology": (1.9, "Diagn Interv Radiol"),
    "current oncology reports": (4.7, "Curr Oncol Rep"),
    "current oncology": (2.8, "Curr Oncol"),
    "clinical orthopaedics and related research": (4.2, "Clin Orthop Relat Res"),
    "scientific reports": (3.8, "Sci Rep"),
    "annals of surgical oncology": (3.4, "Ann Surg Oncol"),
    "journal of bone oncology": (3.4, "J Bone Oncol"),
    "international journal of hyperthermia": (3.1, "Int J Hyperthermia"),
    "diagnostics": (3.0, "Diagnostics"),
    "journal of clinical medicine": (3.0, "J Clin Med"),
    "pain medicine": (2.9, "Pain Med"),
    "journal of orthopaedic surgery and research": (2.8, "J Orthop Surg Res"),
    "abdominal radiology": (2.8, "Abdom Radiol"),
    "neuroradiology": (2.8, "Neuroradiology"),
    "european spine journal": (2.6, "Eur Spine J"),
    "bone & joint open": (2.5, "Bone Jt Open"),
    "journal of pain research": (2.5, "J Pain Res"),
    "journal of orthopaedic trauma": (2.3, "J Orthop Trauma"),
    "vascular medicine": (2.2, "Vasc Med"),
    "international orthopaedics": (2.0, "Int Orthop"),
    "international journal of general medicine": (2.1, "Int J Gen Med"),
    "pediatric radiology": (2.1, "Pediatr Radiol"),
    "brain & spine": (1.9, "Brain Spine"),
    "american journal of hospice & palliative care": (1.9, "Am J Hosp Palliat Care"),
    "interventional pain medicine": (1.8, "Interv Pain Med"),
    "clinical imaging": (1.8, "Clin Imaging"),
    "sicot-j": (1.8, "SICOT-J"),
    "seminars in musculoskeletal radiology": (1.8, "Semin Musculoskelet Radiol"),
    "journal of medical imaging and radiation oncology": (1.8, "J Med Imaging Radiat Oncol"),
    "hip international": (1.6, "Hip Int"),
    "annals of vascular surgery": (1.5, "Ann Vasc Surg"),
    "acta radiologica": (1.5, "Acta Radiol"),
    "european journal of orthopaedic surgery": (1.5, "Eur J Orthop Surg Traumatol"),
    "journal of ultrasonography": (1.6, "J Ultrason"),
    "bjr open": (1.3, "BJR Open"),
    "radiology case reports": (1.0, "Radiol Case Rep"),
    "la radiologia medica": (8.9, "Radiol Med"),
    "radiologia medica": (8.9, "Radiol Med"),
    "medicina": (2.4, "Medicina (Kaunas)"),
    "pain management": (2.0, "Pain Manag"),
    "european journal of surgical oncology": (3.5, "Eur J Surg Oncol"),
    "world journal of surgical oncology": (2.5, "World J Surg Oncol"),
    "neurochirurgie": (1.8, "Neurochirurgie"),
    "neuro-chirurgie": (1.8, "Neurochirurgie"),
    "journal of robotic surgery": (2.2, "J Robot Surg"),
    "quantitative imaging in medicine and surgery": (2.9, "Quant Imaging Med Surg"),
    "indian journal of orthopaedics": (1.2, "Indian J Orthop"),
    "critical reviews in oncology/hematology": (5.5, "Crit Rev Oncol Hematol"),
    "pain and therapy": (3.8, "Pain Ther"),
    "orthopaedic surgery": (2.1, "Orthop Surg"),
    "injury": (2.2, "Injury"),
    "journal of visualized experiments": (1.2, "JoVE"),
    "world journal of radiology": (2.5, "World J Radiol"),
    "pain physician": (3.1, "Pain Physician"),
    "frontiers in surgery": (1.8, "Front Surg"),
    "cancers": (4.5, "Cancers"),
    "journal of personalized medicine": (3.0, "J Pers Med"),
    "clinical radiology": (2.1, "Clin Radiol"),
    "american journal of translational research": (1.7, "Am J Transl Res"),
    "asia-pacific journal of sports medicine": (1.7, "Asia Pac J Sports Med"),
}


def get_journal_info_and_if(journal_title: str) -> tuple:
    j_low = (journal_title or "").lower()
    # Sort keys by length descending so "european radiology experimental" matches before "european radiology"
    for key in sorted(JOURNAL_IMPACT_FACTORS.keys(), key=len, reverse=True):
        if key in j_low:
            return JOURNAL_IMPACT_FACTORS[key]
    return (2.5, journal_title)


def extract_pub_month_and_date(r: dict, fallback_year_str: str) -> tuple:
    """
    Extract (year_int, month_int, month_fr, pub_date_fr) prioritizing actual online/first publication date
    (firstPublicationDate / electronicPublicationDate) over the print volume/issue month (journalInfo.monthOfPublication),
    which Publishers often set to a future end-of-year issue (e.g., Dec 2026 for an article published in March 2026).
    """
    ji = r.get("journalInfo", {})
    y_num = 0
    m_num = 0

    # 1. Prioritize actual publication date (firstPublicationDate / electronicPublicationDate)
    fpd = r.get("firstPublicationDate") or r.get("electronicPublicationDate") or ""
    parts = str(fpd).split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        y_cand = int(parts[0])
        m_cand = int(parts[1])
        if 1990 <= y_cand <= 2030 and 1 <= m_cand <= 12:
            y_num = y_cand
            m_num = m_cand

    # 2. Fallback to journalInfo year/month if firstPublicationDate is missing
    if not (1 <= m_num <= 12):
        try:
            m_cand = int(ji.get("monthOfPublication") or 0)
            if 1 <= m_cand <= 12:
                m_num = m_cand
        except (TypeError, ValueError):
            pass

    if not y_num:
        try:
            y_num = int(ji.get("yearOfPublication") or fallback_year_str or 2024)
        except (TypeError, ValueError):
            y_num = 2024

    month_fr = MONTHS_FR.get(m_num, "")
    pub_date_fr = f"{month_fr} {y_num}".strip() if month_fr else str(y_num)
    return y_num, (m_num if m_num else 1), month_fr, pub_date_fr


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)

    # Remove any legacy synthetic PDFs (SYNTHESE_* or ReportLab-generated files)
    for p in PDFS_DIR.glob("*.pdf"):
        if p.name.startswith("SYNTHESE_") or not is_real_pdf(p):
            p.unlink()

    pmids = list(CURATED_DATA.keys())
    by_pmid = {}

    # Load cached metadata from existing data/articles.json first so offline/503 never breaks existing entries
    existing_json_path = DATA_DIR / "articles.json"
    if existing_json_path.exists():
        try:
            for ea in json.loads(existing_json_path.read_text(encoding="utf-8")):
                ep = str(ea.get("pmid", ""))
                if ep:
                    by_pmid[ep] = {
                        "pmid": ep,
                        "title": ea.get("title", ""),
                        "pubYear": str(ea.get("year", 2026)),
                        "firstPublicationDate": f"{ea.get('year', 2026)}-{int(ea.get('month_num', 1)):02d}-01",
                        "journalInfo": {
                            "volume": ea.get("volume", ""),
                            "issue": ea.get("issue", ""),
                            "yearOfPublication": ea.get("year", 2026),
                            "monthOfPublication": ea.get("month_num", 1),
                            "journal": {"title": ea.get("journal", "")},
                        },
                        "pageInfo": ea.get("pages", ""),
                        "doi": ea.get("doi", ""),
                        "pmcid": ea.get("pmcid", ""),
                        "abstractText": ea.get("abstract_en", ""),
                        "authorList": {"author": [{"fullName": nm} for nm in ea.get("authors_list", [])]},
                    }
        except Exception:
            pass

    # Query Europe PMC for uncached PMIDs if available
    uncached_pmids = [p for p in pmids if p not in by_pmid or not by_pmid[p].get("title")]
    if uncached_pmids:
        try:
            query = " OR ".join([f"EXT_ID:{p}" for p in uncached_pmids])
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
                "query": query,
                "format": "json",
                "pageSize": 200,
                "resultType": "core",
            })
            req = urllib.request.Request(url, headers={"User-Agent": "BiblioOsteo-Cochin/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_results = json.loads(resp.read().decode("utf-8"))["resultList"]["result"]
            for r in raw_results:
                if r.get("pmid"):
                    by_pmid[str(r.get("pmid"))] = r
        except Exception as e:
            print(f"[Metadata] Europe PMC unavailable ({e}), falling back to PubMed MEDLINE for missing PMIDs")

    # Fetch any still-missing PMIDs from NCBI E-utilities efetch XML (or PubMed MEDLINE fallback)
    missing_pmids = [p for p in pmids if p not in by_pmid or not by_pmid[p].get("title")]
    if missing_pmids:
        try:
            import xml.etree.ElementTree as ET
            ef_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode({
                "db": "pubmed",
                "id": ",".join(missing_pmids),
                "retmode": "xml",
            })
            ef_req = urllib.request.Request(ef_url, headers={"User-Agent": "BiblioOsteo-Cochin/1.0"})
            with urllib.request.urlopen(ef_req, timeout=20) as ef_resp:
                ef_root = ET.fromstring(ef_resp.read())
            month_map = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
            for pa in ef_root.findall(".//PubmedArticle"):
                p_id = (pa.findtext(".//MedlineCitation/PMID") or "").strip()
                if not p_id:
                    continue
                ti_el = pa.find(".//ArticleTitle")
                ti_txt = "".join(ti_el.itertext()).strip() if ti_el is not None else ""
                j_title = pa.findtext(".//Journal/Title") or pa.findtext(".//Journal/ISOAbbreviation") or ""
                vol = pa.findtext(".//JournalIssue/Volume") or ""
                iss = pa.findtext(".//JournalIssue/Issue") or ""
                pg = pa.findtext(".//Pagination/MedlinePgn") or ""
                yr_str = pa.findtext(".//JournalIssue/PubDate/Year") or (pa.findtext(".//JournalIssue/PubDate/MedlineDate") or "2026")[:4]
                mo_str = pa.findtext(".//JournalIssue/PubDate/Month") or ""
                ep_yr = pa.findtext(".//Article/ArticleDate/Year") or ""
                ep_mo = pa.findtext(".//Article/ArticleDate/Month") or ""
                m_int = int(ep_mo) if ep_mo.isdigit() else (int(mo_str) if mo_str.isdigit() else month_map.get(mo_str[:3].title(), 1))
                y_int = int(ep_yr) if ep_yr.isdigit() else (int(yr_str) if yr_str[:4].isdigit() else 2026)
                fpd = f"{y_int}-{m_int:02d}-01"
                ab_elems = pa.findall(".//Abstract/AbstractText")
                ab_txt = " ".join("".join(e.itertext()).strip() for e in ab_elems if "".join(e.itertext()).strip()) or "Abstract non disponible."
                doi_val = ""
                pmc_val = ""
                for aid in pa.findall(".//PubmedData/ArticleIdList/ArticleId"):
                    if aid.attrib.get("IdType") == "doi" and aid.text:
                        doi_val = aid.text.strip()
                    elif aid.attrib.get("IdType") == "pmc" and aid.text:
                        pmc_val = aid.text.strip()
                authors = []
                for au in pa.findall(".//AuthorList/Author"):
                    ln = au.findtext("LastName") or au.findtext("CollectiveName") or ""
                    ini = au.findtext("Initials") or ""
                    full = f"{ln} {ini}".strip()
                    if full:
                        authors.append({"fullName": full})
                by_pmid[p_id] = {
                    "pmid": p_id,
                    "title": ti_txt,
                    "pubYear": str(y_int),
                    "firstPublicationDate": fpd,
                    "journalInfo": {
                        "volume": vol,
                        "issue": iss,
                        "yearOfPublication": y_int,
                        "monthOfPublication": m_int,
                        "journal": {"title": j_title},
                    },
                    "pageInfo": pg,
                    "doi": doi_val,
                    "pmcid": pmc_val,
                    "abstractText": ab_txt,
                    "authorList": {"author": authors},
                }
        except Exception as e:
            print(f"[Metadata] NCBI efetch XML fallback error: {e}")
    articles = []

    import html as htmllib
    for pmid, cdata in CURATED_DATA.items():
        r = by_pmid.get(pmid, {})
        title_raw = htmllib.unescape(r.get("title", ""))
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title_raw)).strip().rstrip(".")
        journal_info = r.get("journalInfo", {})
        journal = journal_info.get("journal", {}).get("title", "")
        raw_year = str(r.get("pubYear", "2024"))
        year_int, month_num, month_fr, pub_date_fr = extract_pub_month_and_date(r, raw_year)
        impact_factor, journal_short = get_journal_info_and_if(journal)

        volume = str(journal_info.get("volume", ""))
        issue = str(journal_info.get("issue", ""))
        pages = str(r.get("pageInfo", ""))
        doi = str(r.get("doi", ""))
        pmcid = str(r.get("pmcid", ""))
        abstract_raw = htmllib.unescape(r.get("abstractText", "Abstract non disponible."))
        abstract_clean = re.sub(r"<[^>]+>", " ", abstract_raw)
        abstract_clean = re.sub(r"\s+", " ", abstract_clean).strip()

        authors_list = []
        for a in r.get("authorList", {}).get("author", []):
            full = a.get("fullName") or f"{a.get('lastName', '')} {a.get('initials', '')}".strip()
            if full:
                authors_list.append(full)
        if not authors_list and r.get("authorString"):
            authors_list = [x.strip() for x in r["authorString"].rstrip(".").split(",") if x.strip()]

        if len(authors_list) > 3:
            authors_short = f"{authors_list[0]}, {authors_list[1]} et al."
        else:
            authors_short = ", ".join(authors_list)

        cat = CATEGORIES[cdata["category_id"]]
        rel_pdf = f"pdfs/PMID_{pmid}.pdf"
        pdf_path = BASE_DIR / rel_pdf

        has_real_pdf = is_real_pdf(pdf_path) or try_download_real_pdf(pmid, doi, pdf_path, pmcid=pmcid)

        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        doi_url = f"https://doi.org/{doi}" if doi else pubmed_url
        pmc_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else ""
        article_url = pmc_url or doi_url or pubmed_url

        art_obj = {
            "id": f"pmid-{pmid}",
            "pmid": pmid,
            "pmcid": pmcid,
            "doi": doi,
            "title": title,
            "title_fr": cdata["title_fr"],
            "authors_list": authors_list,
            "authors_short": authors_short,
            "journal": journal,
            "journal_short": journal_short,
            "impact_factor": impact_factor,
            "year": year_int,
            "month_num": month_num,
            "month_fr": month_fr,
            "pub_date_fr": pub_date_fr,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "category_id": cdata["category_id"],
            "category_label": cat["label"],
            "category_short": cat["short_label"],
            "category_color": cat["color"],
            "modality": cdata["modality"],
            "intervention_type": cdata["intervention_type"],
            "cochin_link": cdata["cochin_link"],
            "summary_fr_short": cdata["summary_fr_short"],
            "summary_fr_detailed": cdata["summary_fr_detailed"],
            "protocol_fr": cdata["protocol_fr"],
            "key_points_fr": cdata["key_points_fr"],
            "abstract_en": abstract_clean,
            "tags": cdata["tags"],
            "pdf_file": rel_pdf if has_real_pdf else None,
            "pdf_source": "publisher_oa_pdf" if has_real_pdf else "external_link",
            "pdf_size_kb": round(pdf_path.stat().st_size / 1024) if has_real_pdf else None,
            "pubmed_url": pubmed_url,
            "doi_url": doi_url,
            "pmc_url": pmc_url,
            "article_url": article_url,
        }
        articles.append(art_obj)

    # Sort articles by year and month descending, then category
    articles.sort(key=lambda x: (-x["year"], -x.get("month_num", 1), x["category_id"]))

    (DATA_DIR / "articles.json").write_text(
        json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / "categories.json").write_text(
        json.dumps(list(CATEGORIES.values()), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    js_content = (
        f"window.BIBLIO_ARTICLES = {json.dumps(articles, ensure_ascii=False)};\n"
        f"window.BIBLIO_CATEGORIES = {json.dumps(list(CATEGORIES.values()), ensure_ascii=False)};\n"
        + (f"window.BIBLIO_SYNTHESES = {(DATA_DIR / 'syntheses.json').read_text(encoding='utf-8')};\n" if (DATA_DIR / "syntheses.json").exists() else "")
    )
    (DATA_DIR / "embedded_data.js").write_text(js_content, encoding="utf-8")

    real_pdf_count = sum(1 for a in articles if a.get("pdf_file"))
    print(f"[Database] Saved {len(articles)} articles ({real_pdf_count} with real PDFs, {len(articles) - real_pdf_count} with external links) to {DATA_DIR / 'articles.json'} and embedded_data.js")

    # Generate static Zotero exports (.ris, .bib, .json)
    from zotero_sync import generate_static_exports
    generate_static_exports(articles)


if __name__ == "__main__":
    main()
