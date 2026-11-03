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
        "short_label": "RF & Cryo (OO / Chondroblastome)",
        "icon": "flame",
        "color": "#f97316",
        "agenda_examples": [
            "RF ostéome ostéoïde coude, tibia proximal, hanche",
            "RF / Cryothérapie ostéome ostéoïde de l'astragale (no-touch)",
            "RF & Cryoablation de chondroblastome du genou (à distance lame sous-chondrale)"
        ]
    },
    "desmoid_soft_tissue": {
        "id": "desmoid_soft_tissue",
        "label": "Cryoablation des Tumeurs Desmoïdes & Parties Molles",
        "short_label": "Cryo Desmoïdes & Tissus Mous",
        "icon": "snowflake",
        "color": "#06b6d4",
        "agenda_examples": [
            "Cryothérapie tumeur desmoïde creux sus-claviculaire (proximité plexus brachial)",
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
            "Cimentoplastie cervicale sous AG post-radiothérapie (gestion Eliquis + Plavix)"
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
            "Suivi TDM à 1 an de kyste osseux anévrismal (KOA) de l'humérus traité par alcoolisation"
        ]
    },
    "pain_cryoneurolysis": {
        "id": "pain_cryoneurolysis",
        "label": "Douleur & Neurolyse : Morton, Géniculés, Intercostaux & Clunéal",
        "short_label": "Cryoneurolyse & RF Nerveuse",
        "icon": "activity",
        "color": "#ec4899",
        "agenda_examples": [
            "Cryothérapie sous AL au scanner de névrome de Morton (3e espace)",
            "Test anesthésique sous écho + Radiofréquence des nerfs géniculés (gonarthrose)",
            "Cryoneurolyse percutanée du nerf clunéal et du nerf intercostal sous scanner"
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
            "Biopsie osseuse sous scanner (récidive lymphome B, masse pré-sacrée / sacrum)",
            "Biopsie de masse des parties molles sous écho sans traverser le fascia (sarcome)"
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
        "category_id": "pain_cryoneurolysis",
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
    }
}


def is_real_pdf(pdf_path: Path) -> bool:
    """Return True only if pdf_path exists and is a genuine publisher/author PDF (never ReportLab-generated)."""
    if not pdf_path.exists():
        return False
    try:
        b = pdf_path.read_bytes()
        return len(b) > 50_000 and b.startswith(b"%PDF") and b"ReportLab" not in b
    except Exception:
        return False


def try_download_real_pdf(pmid: str, doi: str, pdf_path: Path) -> bool:
    """
    Attempt to download the genuine publisher or open-access repository PDF (Springer, Nature,
    Unpaywall, OpenAlex, HAL). Never generates a synthetic PDF.
    """
    if is_real_pdf(pdf_path):
        return True
    if pdf_path.exists():
        pdf_path.unlink()

    if not doi:
        return False

    candidates = []
    if doi.startswith("10.1007/") or doi.startswith("10.1186/"):
        candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if doi.startswith("10.1038/"):
        suffix = doi.split("/", 1)[1]
        candidates.append(f"https://www.nature.com/articles/{suffix}.pdf")

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
    "european journal of cancer": (7.6, "Eur J Cancer"),
    "european radiology experimental": (3.7, "Eur Radiol Exp"),
    "european radiology": (4.7, "Eur Radiol"),
    "insights into imaging": (4.1, "Insights Imaging"),
    "current treatment options in oncology": (4.1, "Curr Treat Options Oncol"),
    "skeletal radiology": (1.9, "Skeletal Radiol"),
    "cardiovascular and interventional radiology": (2.8, "CVIR"),
    "journal of vascular and interventional radiology": (2.6, "JVIR"),
    "diagnostic and interventional imaging": (3.9, "Diagn Interv Imaging"),
    "current oncology reports": (4.7, "Curr Oncol Rep"),
    "current oncology": (2.8, "Curr Oncol"),
    "clinical orthopaedics and related research": (4.2, "Clin Orthop Relat Res"),
    "scientific reports": (3.8, "Sci Rep"),
    "journal of bone oncology": (3.4, "J Bone Oncol"),
    "international journal of hyperthermia": (3.1, "Int J Hyperthermia"),
    "diagnostics": (3.0, "Diagnostics"),
    "journal of clinical medicine": (3.0, "J Clin Med"),
    "pain medicine": (2.9, "Pain Med"),
    "journal of orthopaedic surgery and research": (2.8, "J Orthop Surg Res"),
    "abdominal radiology": (2.8, "Abdom Radiol"),
    "neuroradiology": (2.8, "Neuroradiology"),
    "european spine journal": (2.6, "Eur Spine J"),
    "international journal of general medicine": (2.1, "Int J Gen Med"),
    "pediatric radiology": (2.1, "Pediatr Radiol"),
    "brain & spine": (1.9, "Brain Spine"),
    "american journal of hospice & palliative care": (1.9, "Am J Hosp Palliat Care"),
    "seminars in musculoskeletal radiology": (1.8, "Semin Musculoskelet Radiol"),
    "journal of medical imaging and radiation oncology": (1.8, "J Med Imaging Radiat Oncol"),
    "acta radiologica": (1.5, "Acta Radiol"),
    "european journal of orthopaedic surgery": (1.5, "Eur J Orthop Surg Traumatol"),
    "journal of ultrasonography": (1.6, "J Ultrason"),
    "bjr open": (1.3, "BJR Open"),
}


def get_journal_info_and_if(journal_title: str) -> tuple:
    j_low = (journal_title or "").lower()
    # Sort keys by length descending so "european radiology experimental" matches before "european radiology"
    for key in sorted(JOURNAL_IMPACT_FACTORS.keys(), key=len, reverse=True):
        if key in j_low:
            return JOURNAL_IMPACT_FACTORS[key]
    return (2.5, journal_title)


def extract_pub_month_and_date(r: dict, year_str: str) -> tuple:
    ji = r.get("journalInfo", {})
    m_num = ji.get("monthOfPublication")
    try:
        m_num = int(m_num)
    except (TypeError, ValueError):
        m_num = 0

    if not (1 <= m_num <= 12):
        fpd = r.get("firstPublicationDate") or r.get("electronicPublicationDate") or ""
        parts = str(fpd).split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            m_cand = int(parts[1])
            if 1 <= m_cand <= 12:
                m_num = m_cand

    month_fr = MONTHS_FR.get(m_num, "")
    pub_date_fr = f"{month_fr} {year_str}".strip() if month_fr else str(year_str)
    return m_num if m_num else 1, month_fr, pub_date_fr


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)

    # Remove any legacy synthetic PDFs (SYNTHESE_* or ReportLab-generated files)
    for p in PDFS_DIR.glob("*.pdf"):
        if p.name.startswith("SYNTHESE_") or not is_real_pdf(p):
            p.unlink()

    pmids = list(CURATED_DATA.keys())
    query = " OR ".join([f"EXT_ID:{p}" for p in pmids])
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "pageSize": 100,
        "resultType": "core",
    })
    req = urllib.request.Request(url, headers={"User-Agent": "BiblioOsteo-Cochin/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw_results = json.loads(resp.read().decode("utf-8"))["resultList"]["result"]

    by_pmid = {str(r.get("pmid")): r for r in raw_results if r.get("pmid")}
    articles = []

    for pmid, cdata in CURATED_DATA.items():
        r = by_pmid.get(pmid, {})
        title = r.get("title", "").rstrip(".")
        journal_info = r.get("journalInfo", {})
        journal = journal_info.get("journal", {}).get("title", "")
        year = str(r.get("pubYear", "2024"))
        month_num, month_fr, pub_date_fr = extract_pub_month_and_date(r, year)
        impact_factor, journal_short = get_journal_info_and_if(journal)

        volume = str(journal_info.get("volume", ""))
        issue = str(journal_info.get("issue", ""))
        pages = str(r.get("pageInfo", ""))
        doi = str(r.get("doi", ""))
        pmcid = str(r.get("pmcid", ""))
        abstract_raw = r.get("abstractText", "Abstract non disponible.")
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

        has_real_pdf = is_real_pdf(pdf_path) or try_download_real_pdf(pmid, doi, pdf_path)

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
            "year": int(year) if year.isdigit() else 2024,
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
    real_pdf_count = sum(1 for a in articles if a.get("pdf_file"))
    print(f"[Database] Saved {len(articles)} articles ({real_pdf_count} with real PDFs, {len(articles) - real_pdf_count} with external links) to {DATA_DIR / 'articles.json'}")

    # Generate static Zotero exports (.ris, .bib, .json)
    from zotero_sync import generate_static_exports
    generate_static_exports(articles)


if __name__ == "__main__":
    main()
