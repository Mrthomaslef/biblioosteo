#!/usr/bin/env python3
"""
Builds the BiblioOstéo dataset (data/articles.json), downloads Open-Access Publisher PDFs,
generates full-text/clinical synthesis PDFs for articles without direct publisher PDF links,
and generates Zotero export files (.ris, .bib, .json).
"""

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

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
        "label": "Douleur & Neurolyse : Morton, Géniculés, Intercostaux",
        "short_label": "Cryoneurolyse & RF Nerveuse",
        "icon": "activity",
        "color": "#ec4899",
        "agenda_examples": [
            "Cryothérapie sous AL au scanner de névrome de Morton (3e espace)",
            "Test anesthésique sous écho + Radiofréquence des nerfs géniculés (gonarthrose)",
            "Cryoneurolyse du nerf intercostal (douleurs post-zona) & douleurs post-amputation"
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
    }
}


def strip_xml_tags(elem) -> str:
    return "".join(elem.itertext()).strip()


def extract_jats_sections(xml_bytes: bytes) -> list:
    """Extract clean readable sections from Europe PMC JATS fullTextXML."""
    sections = []
    try:
        root = ET.fromstring(xml_bytes)
        body = root.find(".//body")
        if body is None:
            return sections
        for sec in body.findall("./sec"):
            title_el = sec.find("title")
            sec_title = strip_xml_tags(title_el) if title_el is not None else "Section"
            paras = []
            for p in sec.findall(".//p"):
                txt = strip_xml_tags(p)
                if len(txt) > 30:
                    paras.append(txt)
            if paras:
                sections.append((sec_title, paras[:8]))
    except Exception:
        pass
    return sections[:8]


def generate_article_pdf(art: dict, pdf_path: Path, jats_sections: list = None):
    """Generate a multi-page professional clinical + original abstract/full-text PDF using ReportLab."""
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=art["title"],
        author=", ".join(art.get("authors_list", [])[:5]),
    )
    styles = getSampleStyleSheet()
    style_badge = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=4,
    )
    style_title_fr = ParagraphStyle(
        "TitleFR",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    style_title_en = ParagraphStyle(
        "TitleEN",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    style_meta = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    style_h2 = ParagraphStyle(
        "SecH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=5,
    )
    style_body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.8,
        leading=14.2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    style_box = ParagraphStyle(
        "Box",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.8,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f0f9ff"),
        borderColor=colors.HexColor("#bae6fd"),
        borderWidth=0.8,
        borderPadding=8,
        spaceAfter=8,
    )
    style_bullet = ParagraphStyle(
        "BulletItem",
        parent=style_body,
        leftIndent=12,
        spaceAfter=4,
    )

    story = []
    story.append(
        Paragraph(
            f"BIBLIOOSTÉO — HÔPITAL COCHIN (RADIOLOGIE B) • {html.escape(art['category_label'].upper())}",
            style_badge,
        )
    )
    story.append(Paragraph(html.escape(art["title_fr"]), style_title_fr))
    story.append(Paragraph(f"Titre original : {html.escape(art['title'])}", style_title_en))

    meta_str = (
        f"<b>Auteurs :</b> {html.escape(art.get('authors_short', ''))} &nbsp;|&nbsp; "
        f"<b>Revue :</b> <i>{html.escape(art.get('journal', ''))}</i> "
        f"(<b>IF : {html.escape(str(art.get('impact_factor', 'N/A')))}</b>) &nbsp;|&nbsp; "
        f"<b>Date :</b> {html.escape(art.get('pub_date_fr', str(art.get('year', ''))))} &nbsp;|&nbsp; "
        f"<b>PMID :</b> {art.get('pmid', '')} &nbsp;|&nbsp; "
        f"<b>Modalité :</b> {html.escape(art.get('modality', ''))}"
    )
    story.append(Paragraph(meta_str, style_meta))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    story.append(Paragraph("1. Pertinence Clinique & Lien avec l'Agenda Interventionnel (Cochin)", style_h2))
    story.append(Paragraph(html.escape(art["cochin_link"]), style_box))

    story.append(Paragraph("2. Synthèse Clinique en Français", style_h2))
    story.append(Paragraph(f"<b>Résumé exécutif :</b> {html.escape(art['summary_fr_short'])}", style_body))
    story.append(Paragraph(f"<b>Analyse détaillée :</b> {html.escape(art['summary_fr_detailed'])}", style_body))

    story.append(Paragraph("3. Protocole Technique & Paramètres Opératoires", style_h2))
    story.append(Paragraph(html.escape(art["protocol_fr"]), style_box))

    story.append(Paragraph("4. Points Clés à Retenir pour la Pratique", style_h2))
    for kp in art.get("key_points_fr", []):
        story.append(Paragraph(f"• {html.escape(kp)}", style_bullet))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
    story.append(Paragraph("5. Original PubMed Abstract (Texte Intégral de l'Abstract)", style_h2))
    clean_abs = re.sub(r"<[^>]+>", " ", art.get("abstract_en", ""))
    story.append(Paragraph(html.escape(clean_abs), style_body))

    if jats_sections:
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        story.append(Paragraph("6. Full-Text Sections (Europe PMC Open Access JATS XML)", style_h2))
        for sec_title, paras in jats_sections:
            story.append(Paragraph(f"<b>{html.escape(sec_title)}</b>", style_body))
            for p_txt in paras:
                story.append(Paragraph(html.escape(p_txt), style_body))

    doc.build(story)


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
    "skeletal radiology": (1.9, "Skeletal Radiol"),
    "cardiovascular and interventional radiology": (2.8, "CVIR"),
    "journal of vascular and interventional radiology": (2.6, "JVIR"),
    "diagnostic and interventional imaging": (3.9, "Diagn Interv Imaging"),
    "current oncology reports": (4.7, "Curr Oncol Rep"),
    "current oncology": (2.8, "Curr Oncol"),
    "clinical orthopaedics and related research": (4.2, "Clin Orthop Relat Res"),
    "scientific reports": (3.8, "Sci Rep"),
    "journal of bone oncology": (3.4, "J Bone Oncol"),
    "diagnostics": (3.0, "Diagnostics"),
    "journal of clinical medicine": (3.0, "J Clin Med"),
    "pain medicine": (2.9, "Pain Med"),
    "pediatric radiology": (2.1, "Pediatr Radiol"),
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

    pmids = list(CURATED_DATA.keys())
    query = " OR ".join([f"EXT_ID:{p}" for p in pmids])
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "pageSize": 35,
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
        rel_synth_pdf = f"pdfs/SYNTHESE_PMID_{pmid}.pdf"
        synth_pdf_path = BASE_DIR / rel_synth_pdf

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
            "pdf_file": rel_pdf,
            "synth_pdf_file": rel_synth_pdf,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi_url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

        # 1. Try downloading direct publisher PDF if not already downloaded
        downloaded_publisher_pdf = False
        if pdf_path.exists() and pdf_path.stat().st_size > 120_000:
            downloaded_publisher_pdf = True
        else:
            candidates = []
            if doi.startswith("10.1007/") or doi.startswith("10.1186/"):
                candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
            if doi.startswith("10.1038/"):
                suffix = doi.split("/")[1]
                candidates.append(f"https://www.nature.com/articles/{suffix}.pdf")
            try:
                uw_url = f"https://api.unpaywall.org/v2/{doi}?email=thomas.lefevre@aphp.fr"
                with urllib.request.urlopen(uw_url, timeout=8) as uwr:
                    uwd = json.loads(uwr.read().decode())
                    best = uwd.get("best_oa_location") or {}
                    if best.get("url_for_pdf"):
                        candidates.append(best["url_for_pdf"])
            except Exception:
                pass

            for c in candidates:
                try:
                    req_pdf = urllib.request.Request(c, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_pdf, timeout=15) as pr:
                        b = pr.read()
                        if b.startswith(b"%PDF") and len(b) > 50_000:
                            pdf_path.write_bytes(b)
                            downloaded_publisher_pdf = True
                            print(f"[PDF] Downloaded publisher PDF for PMID {pmid} ({len(b)//1024} KB)")
                            break
                except Exception:
                    pass

        # 2. Fetch Europe PMC JATS XML if available
        jats_sections = []
        if pmcid:
            try:
                xurl = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
                with urllib.request.urlopen(xurl, timeout=10) as xr:
                    xb = xr.read()
                    if b"<article" in xb:
                        jats_sections = extract_jats_sections(xb)
            except Exception:
                pass

        # 3. Always generate the French Clinical Synthesis + Original Abstract PDF
        generate_article_pdf(art_obj, synth_pdf_path, jats_sections=jats_sections)

        # 4. If publisher PDF wasn't directly downloadable, use the complete generated PDF as the primary PDF too
        if not downloaded_publisher_pdf:
            pdf_path.write_bytes(synth_pdf_path.read_bytes())
            art_obj["pdf_source"] = "full_synthesis_pdf"
            print(f"[PDF] Generated full synthesis + abstract PDF for PMID {pmid} ({pdf_path.stat().st_size//1024} KB)")
        else:
            art_obj["pdf_source"] = "publisher_oa_pdf"

        art_obj["pdf_size_kb"] = round(pdf_path.stat().st_size / 1024)
        articles.append(art_obj)

    # Sort articles by year and month descending, then category
    articles.sort(key=lambda x: (-x["year"], -x.get("month_num", 1), x["category_id"]))

    (DATA_DIR / "articles.json").write_text(
        json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / "categories.json").write_text(
        json.dumps(list(CATEGORIES.values()), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[Database] Saved {len(articles)} articles to {DATA_DIR / 'articles.json'}")

    # Generate static Zotero exports (.ris, .bib, .json)
    from zotero_sync import generate_static_exports
    generate_static_exports(articles)


if __name__ == "__main__":
    main()
