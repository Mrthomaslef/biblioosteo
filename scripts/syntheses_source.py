#!/usr/bin/env python3
"""
Pseudo-méta-analyses narratives par technique (catégorie) BiblioOstéo.

Chaque synthèse agrège UNIQUEMENT les données chiffrées des articles présents dans la base
(data/articles.json). Chaque point est relié à ses PMID sources ("r").
Exécuter ce script régénère data/syntheses.json puis data/embedded_data.js.

    python3 scripts/syntheses_source.py
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def p(text, *refs):
    return {"t": text, "r": list(refs)}


SYNTHESES = {
    "ablation_benign": {
        "evidence": "Niveau de preuve modéré : 2 revues systématiques/comparatives, 1 registre multicentrique (DeGIR), cohortes rétrospectives et séries princeps.",
        "bottom_line": "La thermo-ablation percutanée sous scanner (RF ou cryoablation) est le traitement de référence de l'ostéome ostéoïde, avec > 92–96 % de guérison clinique dès la première séance et < 2 % de complications ; elle s'étend aux chondroblastomes épiphysaires < 2,5 cm et aux récidives focales de TCG.",
        "kpis": [
            {"v": "92–99 %", "l": "Succès technique/clinique OO (1 séance)", "r": ["41876692", "42489686", "33839926"]},
            {"v": "96 %", "l": "Succès cryo « no-touch » (adulte, n = 50)", "r": ["34812672"]},
            {"v": "1,8 %", "l": "Complications (registre DeGIR, n = 166)", "r": ["41876692"]},
            {"v": "×6,5", "l": "Risque de récidive si nidus extracortical", "r": ["41867110"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Ostéome ostéoïde typique (cortical, médullaire, intra-articulaire) : RF = gold standard historique (71 % des procédures du registre DeGIR), cryoablation d'efficacité équivalente (> 93 %).", "41876692", "33839926"),
                p("OO intra-articulaire (cotyle, coude, talus) : la RF scanoguidée accède aux nidus inaccessibles à l'arthroscopie et fait céder la synovite réactionnelle.", "42931896"),
                p("Chondroblastome épiphysaire < 2,5 cm : alternative au curetage avec préservation articulaire.", "19304917"),
                p("Récidive locale focale de TCG après curetage : RF/cryo ± comblement PMMA si corticale ou os sous-chondral fragilisé.", "41568883"),
            ]},
            {"k": "technique", "title": "Technique & choix de l'énergie", "items": [
                p("Cryoablation « no-touch » extra-osseuse : pas de forage du nidus, visualisation de l'iceball, 60 % des gestes sous AL + sédation ; privilégiée au tarse et sur les lésions superficielles.", "34812672", "33839926"),
                p("L'os cortical freine la RF (haute impédance) mais laisse diffuser le froid : penser cryo pour les lésions corticales épaisses/scléreuses.", "24838839"),
                p("Nidus extracortical + DCE-MRI lent (TTP > 40 s, MRE < 300 %) : risque de récidive > 55 % → prolonger l'ablation, augmenter la température ou basculer en cryo.", "41867110"),
                p("Robotique : moins de repositionnements dans les trajets obliques, sans gain d'efficacité vs guidage TDM expert (440 procédures).", "42671500"),
            ]},
            {"k": "safety", "title": "Sécurité & structures nobles", "warn": True, "items": [
                p("Seuils de neurotoxicité : < 10 °C et > 45 °C au contact des troncs nerveux ; hydro-/carbodissection pour écarter peau, nerfs et tube digestif.", "24838839"),
                p("Lésions superficielles (tibia antérieur, talus, coude) : risque de brûlure cutanée/cartilagineuse.", "42489686"),
                p("Chondroblastome : préserver la lame sous-chondrale (risque d'effondrement ostéochondral).", "19304917"),
                p("Dosimétrie (enfant) : DLP médian 124 mGy·cm (membres) / 222 mGy·cm (axial) comme référentiel ALARA ; collimation serrée et bas kV.", "41876692", "42489686"),
            ]},
            {"k": "followup", "title": "Bilan & suivi", "items": [
                p("IRM dynamique injectée pré-geste pour confirmer le nidus et limiter les acquisitions TDM diagnostiques.", "42489686", "41867110"),
                p("Chondroblastome / TCG : IRM + TDM à 3, 6 et 12 mois (réossification, interface os-ciment).", "19304917", "41568883"),
            ]},
        ],
    },

    "desmoid_soft_tissue": {
        "evidence": "Niveau de preuve modéré à élevé : 1 essai prospectif de phase II (CRYODESMO-01), consensus SIR, cohortes rétrospectives et revues 2024–2026.",
        "bottom_line": "La cryoablation percutanée est la modalité ablative de choix des tumeurs desmoïdes extra-abdominales symptomatiques ou progressives : 85–91 % de contrôle local à 12–16 mois, 78–79 % de réponse objective (mRECIST) et ~5 % de complications majeures, avec retraitement itératif possible.",
        "kpis": [
            {"v": "85,6 %", "l": "Non-progression à 12 mois (phase II, n = 50)", "r": ["33290994"]},
            {"v": "78–79 %", "l": "Réponse objective mRECIST", "r": ["42731622", "42384128"]},
            {"v": "94,6 %", "l": "Contrôle de la maladie (n = 44, 6,9 cm)", "r": ["42731622"]},
            {"v": "5,3 %", "l": "Complications majeures (SIR ≥ 3)", "r": ["42731622"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Desmoïde extra-abdominale progressive ou symptomatique après surveillance active ou traitement systémique (alternative à la chirurgie délabrante).", "33290994", "42631901"),
                p("Ablation subtotale délibérée à visée antalgique/fonctionnelle au contact d'un plexus (creux sus-claviculaire / plexus brachial).", "42955498", "42631901"),
                p("Oligoprogression sous traitement systémique : cryo focale sur le contingent résiduel ; consensus SIR plaçant la cryo au premier plan de la stratégie multimodale chez le sujet jeune.", "42955498", "42641400"),
                p("Autres cibles parties molles : endométriomes pariétaux, nodules oligométastatiques musculaires/sous-cutanés.", "39556172"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("Isotherme létal (−20 à −40 °C) à 3–5 mm en dedans du bord visible du glaçon (0 °C) : planifier la couverture en conséquence.", "39556172"),
                p("Planification multi-sondes selon volume tumoral et proximité nerveuse ; retraitement itératif chez 26 % des patients.", "33290994", "42731622"),
                p("Petites lésions à distance des troncs moteurs : faisable sous AL + sédation consciente.", "39556172"),
            ]},
            {"k": "safety", "title": "Sécurité & protection", "warn": True, "items": [
                p("Hydrodissection sous-cutanée continue et réchauffement cutané pour les nodules superficiels (trapèze, paroi thoracique).", "39556172", "42955498"),
                p("Protection nerveuse active au contact des plexus ; accepter une ablation subtotale plutôt qu'un déficit moteur.", "42955498", "42631901"),
            ]},
            {"k": "followup", "title": "Évaluation de la réponse (IRM)", "items": [
                p("Utiliser mRECIST / volumétrie du tissu viable rehaussé, pas RECIST 1.1 : ORR 79,4 % vs 28,6 % ; concordance mRECIST–volumétrie 3D κ = 0,895.", "42384128", "42731622"),
                p("Une cicatrice fibreuse non rehaussée de taille inchangée peut correspondre à une réponse complète ; utiliser la soustraction post-gadolinium.", "42384128", "41357250"),
            ]},
        ],
    },

    "ect_mets": {
        "evidence": "Niveau de preuve modéré : 1 méta-analyse PRISMA (toxicité bléomycine, 7 601 patients), 1 revue systématique, séries cliniques, étude préclinique et protocole prospectif (BOREALIS).",
        "bottom_line": "L'électrochimiothérapie (bléomycine IV + électroporation réversible) est la seule technique ablative percutanée utilisable au contact direct de la moelle, des racines ou de la peau : antalgie rapide (EVA 7 → 1 à 1 mois dans l'épidurite réfractaire) et réponse épidurale objective chez 77 % des patients, sans effet thermique.",
        "kpis": [
            {"v": "7 → 1", "l": "EVA médiane à 1 mois (épidurite réfractaire, n = 40)", "r": ["37030078"]},
            {"v": "77 %", "l": "Réponse épidurale objective en IRM", "r": ["37030078"]},
            {"v": "56 %", "l": "Amélioration neurologique à 1 mois", "r": ["37030078"]},
            {"v": "85–92 %", "l": "Contrôle local à 1 an (cryo oligométastatique)", "r": ["37504355"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Coulée épidurale / compression médullaire métastatique réfractaire à la radiothérapie, au contact du fourreau dural.", "37030078", "42785703"),
                p("Métastases distales (pied, main), juxta-articulaires ou radiorésistantes (rein, mélanome).", "37834793", "38732352"),
                p("Lésions volumineuses : association « cryoablation centrale (debulking) + couronne périphérique d'ECT » ± cimentoplastie dans le même temps.", "38732352", "37834793"),
                p("Maladie oligométastatique osseuse : cryoablation à visée curative avec marge ≥ 5 mm (protocole BOREALIS).", "42618654", "37504355"),
            ]},
            {"k": "technique", "title": "Technique & pharmacologie", "items": [
                p("Bléomycine 15 000 UI/m² IV en bolus ; impulsions délivrées entre 8 et 40 min après l'injection.", "37834793", "42998777"),
                p("Électrodes : voie transpédiculaire validée au rachis ; électrodes bipolaires mono-aiguille pour réduire le nombre d'insertions et confiner le champ.", "40906057", "42804145"),
                p("Planification patient-spécifique du champ électrique (3D Slicer / AI4DEEP) : isodose 160–200 V/cm corrélée à la nécrose IRM.", "42612110"),
            ]},
            {"k": "safety", "title": "Sécurité", "warn": True, "items": [
                p("Anesthésie : FiO2 < 30 % après bléomycine (risque de toxicité pulmonaire) — coordination indispensable avec l'anesthésiste.", "38732352", "42998777"),
                p("Âge avancé et métastases pulmonaires ne contre-indiquent pas une séance unique d'ECT (méta-analyse 7 601 patients : risque lié aux doses cumulées de chimiothérapie).", "42998777"),
                p("Neuromonitoring : chute transitoire des PEM après impulsion, récupération complète < 30 min ; aucune lésion médullaire histologique.", "40906057"),
                p("Cryoablation distale ou sous anti-angiogéniques (lenvatinib) : vigilance cutanée renforcée.", "37504355"),
            ]},
            {"k": "followup", "title": "Suivi", "items": [
                p("IRM injectée à 1 et 3 mois : réponse du contingent épidural (score ESCCS) et douleur ; réduction des opioïdes dès le 1er mois.", "37030078", "38732352"),
            ]},
        ],
    },

    "consolidation_screw_cement": {
        "evidence": "Niveau de preuve modéré : 2 revues systématiques (dont 76 études / 3 234 patients en cimentoplastie rachidienne), cohortes multicentriques et séries techniques.",
        "bottom_line": "La cimentoplastie traite la compression (corps vertébral, toit du cotyle) et le vissage percutané ± cimenté le cisaillement (anneau pelvien, sacrum, col) : antalgie > 80–88 %, complications symptomatiques ~3 % et reprise d'appui précoce ; l'association ablation + vis + ciment en une séance est validée pour les métastases pelviennes.",
        "kpis": [
            {"v": "3,4 %", "l": "Complications symptomatiques (cimentoplastie, 3 234 pts)", "r": ["42780331"]},
            {"v": "20,7 %", "l": "Fuites de ciment (majoritairement asymptomatiques)", "r": ["42780331"]},
            {"v": "88 %", "l": "Succès antalgique os thoraciques extra-rachidiens", "r": ["42439173"]},
            {"v": "97 %", "l": "Positionnement intra-osseux vis ilio-sacrées", "r": ["42767629"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Métastases et myélome rachidiens douloureux : cimentoplastie (39 % des patients de RCP Métastases Osseuses en CHU vs 22 % de chirurgie).", "42947096", "40911195"),
                p("Fractures sacrées par insuffisance (U / Rommens IVb) et fractures pathologiques ou post-radiques de l'anneau pelvien : vissage ilio-/trans-sacré.", "42891691", "26318372"),
                p("Métastases pelviennes douloureuses : cryoablation + vissage + cimentoplastie en une séance.", "42173356"),
                p("Sites atypiques : rachis cervical (voie antéro-latérale C3–C7), sternum/côtes/clavicule/scapula, humérus (ballonnet photopolymérisable, Mirels 8–10).", "20848245", "42439173", "42938822"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("Ciment = compression ; vis canulées = cisaillement ; scellement cimenté des vis en os irradié/ostéoporotique pour éviter migration.", "38544877", "26318372", "42173356"),
                p("Après cryoablation, attendre le réchauffement complet avant d'injecter le PMMA (polymérisation retardée, fuites).", "42173356", "38544877"),
                p("Corridors S1/S2 très variables (10–32 mm) : planification 3D/CBCT ; procubitus pour associer vissage et sacroplastie ; incidences COOHO/Outlet/Profil strict pour les colonnes acétabulaires.", "42471112", "42767629", "42663695"),
            ]},
            {"k": "safety", "title": "Sécurité & pièges", "warn": True, "items": [
                p("Embolie pulmonaire de ciment 1,08 % ; le contrôle TDM détecte 2,4× plus de fuites que la scopie.", "42780331"),
                p("Fuite intradiscale : risque de fracture adjacente 31 % vs 8,8 % (myélome) — à éviter.", "40911195"),
                p("Rachis cervical = geste à haut risque hémorragique : arrêt AOD et gestion des antiagrégants en consultation d'anesthésie.", "20848245"),
            ]},
            {"k": "followup", "title": "Résultats à long terme", "items": [
                p("Myélome : 1,4 % de refracture locale à > 5 ans sur 142 sites cimentés.", "40911195"),
                p("Vissage pelvien : appui dès J1, complication 0,6 % (169 vis), durée médiane 47 min.", "26318372", "42471112"),
            ]},
        ],
    },

    "cyst_sclerotherapy": {
        "evidence": "Niveau de preuve faible à modéré : 1 étude prospective, séries cliniques (dont recul > 5 ans), étude physiopathologique et revues de synthèse.",
        "bottom_line": "La sclérothérapie percutanée (éthanol, polidocanol, doxycycline) ± comblement est devenue le traitement de première intention de nombreux KOA et KOE : guérison en 1–2 séances dans 74–95 % des cas, avec très peu de complications, à condition d'avoir éliminé un ostéosarcome télangiectasique.",
        "kpis": [
            {"v": "80–90 %", "l": "Ostéogenèse réparatrice après alcoolisation (1–2 séances)", "r": ["34367902"]},
            {"v": "95 %", "l": "Sans récidive à 30 mois (polidocanol + moelle, KOA)", "r": ["42483265"]},
            {"v": "74,1 %", "l": "Guérison en 1 séance (Sclerograft modifié, KOA)", "r": ["42477120"]},
            {"v": "87,1 %", "l": "Succès en 1 séance (ciment phosphocalcique, KOE)", "r": ["42729247"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("KOA primaire (réarrangement USP6) et KOE symptomatiques ou à risque fracturaire, en première intention avant curetage.", "41857607", "35941207"),
                p("KOE volumineux (aile iliaque, humérus) : alcoolisation + comblement/cimentoplastie avant reprise sportive.", "34367902", "42729247"),
                p("KOA volumineux, axiaux ou récidivants : sclérothérapie ± cryoablation des contingents charnus ou embolisation sélective.", "42477120", "41857607"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("Montage à double trocart (décompression/drainage) : l'hyperpression intrakystique (90 vs 67 mmHg) justifie physiologiquement la décompression.", "42234093", "34367902"),
                p("Kystographie iodée préalable obligatoire avant alcoolisation (fuite veineuse directe, passage articulaire).", "35941207"),
                p("Options d'adjuvants : disruption des cloisons + doxycycline + substitut osseux ; moelle autologue après polidocanol ; ciment phosphocalcique résorbable chez le jeune (≠ PMMA).", "42477120", "42483265", "42729247"),
            ]},
            {"k": "safety", "title": "Pièges diagnostiques", "warn": True, "items": [
                p("Toute lésion multiloculée à niveaux liquide-liquide atypique : confirmation histologique/moléculaire (USP6) avant sclérothérapie — diagnostic différentiel de l'ostéosarcome télangiectasique.", "35941207"),
            ]},
            {"k": "followup", "title": "Suivi", "items": [
                p("TDM ou radiographies à 3, 6 et 12 mois : épaississement cortical, disparition de l'effet soufflant, ossification centripète sur 6–24 mois (Neer I/II).", "41857607", "35941207", "42729247"),
                p("Récidive partielle : nouvelle injection percutanée possible sans chirurgie ouverte.", "42729247"),
            ]},
        ],
    },

    "pain_cryoneurolysis": {
        "evidence": "Niveau de preuve élevé pour les nerfs géniculés (méta-analyse de 8 ECR vs sham, 627 patients) et les nerfs clunéaux (méta-analyse, 628 patients) ; modéré pour Morton et intercostaux (cohortes).",
        "bottom_line": "Après bloc test positif, la neurolyse percutanée (RF conventionnelle ou cryoneurolyse) procure ≥ 50 % de soulagement chez 70–85 % des patients sélectionnés (genou, clunéaux, Morton, intercostaux), sans événement indésirable grave ; la cryoneurolyse induit une axonotmésis réversible (Sunderland II) sans névrome.",
        "kpis": [
            {"v": "−1,65 pt", "l": "EVA à 12 sem. vs sham (géniculés, 8 ECR)", "r": ["41063397"]},
            {"v": "78–83 %", "l": "Répondeurs névralgie clunéale (3–6 mois)", "r": ["42182575"]},
            {"v": "> 80 %", "l": "Succès cryoneurolyse Morton (AL, ambulatoire)", "r": ["38438685", "42942556"]},
            {"v": "OR 9,4", "l": "RF conventionnelle vs pulsée (intercostaux)", "r": ["42804317"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Gonarthrose sévère (KL 3–4) réfractaire ou en attente de PTG, et douleurs persistantes après prothèse.", "41063397", "42977533", "42803442"),
                p("Névralgie clunéale supérieure/moyenne (lombo-fessalgies) après bloc diagnostique positif.", "42182575"),
                p("Névrome de Morton réfractaire au traitement conservateur, y compris après échec d'une première RF.", "38438685", "42942556"),
                p("Névralgie intercostale (post-zostérienne, post-traumatique, oncologique) et douleurs post-amputation.", "42804317", "28431129"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("Bloc test sous échographie à faible volume (0,5–1 mL par nerf) = meilleur prédicteur d'efficacité ; prérequis dans les douleurs non oncologiques.", "42602563", "42995280", "28431129"),
                p("Genou : repères vasculaires Doppler (artères géniculées) et périostés ; extension à 4–5 cibles possible.", "42602563", "42803442"),
                p("Préférer une modalité neurolytique vraie (RF conventionnelle ou cryo) à la RF pulsée pour une analgésie durable (NRS 6 mois 2,8 vs 6,3).", "42804317"),
                p("Clunéal supérieur : franchissement de la crête iliaque postéro-supérieure à 6–8 cm de la ligne médiane.", "42182575"),
            ]},
            {"k": "safety", "title": "Sécurité & pièges", "warn": True, "items": [
                p("Ne jamais cibler le nerf géniculé inféro-latéral (risque de lésion du nerf fibulaire commun / steppage).", "42602563"),
                p("Tests de stimulation sensitive (50 Hz) et motrice (2 Hz) avant toute anesthésie du nerf cible ; ropivacaïne 0,2 % en multi-sites.", "42742682", "28431129"),
                p("Morton : protection cutanée dans l'espace inter-métatarsien étroit ; Intercostaux : guidage TDM au bord inférieur costal (pneumothorax).", "38438685", "28431129"),
            ]},
            {"k": "followup", "title": "Suivi", "items": [
                p("Pas d'aggravation des BML ni de l'arthrose en IRM à 3 mois après RF géniculée refroidie ; bénéfice WOMAC jusqu'à 24 semaines.", "42977533", "41063397"),
                p("> 70 % des patients sélectionnés maintiennent ≥ 50 % de soulagement à 6–12 mois.", "28431129"),
            ]},
        ],
    },

    "pudendal_cryoneurolysis": {
        "evidence": "Niveau de preuve modéré : 1 série de référence de 362 procédures sur 10 ans, cohortes comparatives (224, 95 et 84 patients), étude IRM et série princeps ; pas d'essai randomisé.",
        "bottom_line": "La cryoneurolyse du nerf pudendal sous scanner, chez un patient bien sélectionné (triade : facteur déclenchant + douleur périnéale unilatérale systématisée + bloc TDM positif), obtient ~77 % de succès clinique, un intervalle libre moyen de 31,8 mois et 0 % de complication majeure ou sphinctérienne.",
        "kpis": [
            {"v": "77,4 %", "l": "Succès clinique si triade de sélection (vs 36,4 %)", "r": ["42276242"]},
            {"v": "31,8 mois", "l": "Délai moyen avant réintervention", "r": ["42276242"]},
            {"v": "0 %", "l": "Complication majeure / sphinctérienne", "r": ["42276242", "41999357", "32602380"]},
            {"v": "OR 4,88", "l": "Bloc diagnostique positif → réponse", "r": ["42999001"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Névralgie pudendale réfractaire (critères cliniques) avec bloc diagnostique positif ; étiologie post-chirurgicale = facteur prédictif favorable (OR 2,83).", "42276242", "42999001"),
                p("Douleurs pelvi-périnéales oncologiques réfractaires : cryoneurolyse pudendale, éventuellement bilatérale en un temps (−5,2 pts d'EVA, sortie en 2,3 j).", "32602380", "41999357"),
                p("Composante sympathique médiane associée : ajouter le ganglion impar (EVA 6 mois 2,09 vs 3,81 avec PRF pudendale seule).", "42263315", "41440950"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("Procubitus, guidage TDM ; cible au niveau de la pince ligamentaire (épine ischiatique / ligament sacro-épineux) ou du canal d'Alcock selon le site du conflit.", "41594302", "25511935"),
                p("Bloc test TDM indispensable dans les névralgies fonctionnelles/canalaires ; peut être omis en oncologie pelvienne à cible évidente (succès 81,1 % vs 69,7 %, NS ; gain de ~16 jours).", "42527618"),
                p("Cryo-axonotmésis (−20 à −100 °C) : préservation de l'endonèvre, pas de névrite ni de névrome de désafférentation ; supérieure en durabilité à la RF pulsée (neuromodulation).", "41440950", "42999001"),
            ]},
            {"k": "safety", "title": "Sécurité", "warn": True, "items": [
                p("Aucune incontinence ni complication sphinctérienne rapportée, y compris en bilatéral, grâce à la précision du guidage TDM et à la réversibilité de l'axonotmésis.", "32602380", "41440950", "25511935"),
                p("Hors triade de sélection, le taux de succès chute à 36,4 % : ne pas multiplier les gestes sans bloc positif.", "42276242"),
            ]},
            {"k": "followup", "title": "Bilan & suivi", "items": [
                p("IRM pelvienne avec neurographie de diffusion (b = 0, 100, 600) : anomalie du nerf chez 51,9 % des patients, cause compressive identifiée chez ~55 % d'entre eux.", "41594302"),
                p("Antalgie dès 24 h–J7, maintenue à 6 mois (EVA 7,6 → 3,1) avec épargne morphinique ; retraitement possible après ~2,5 ans.", "25511935", "41999357", "42276242"),
            ]},
        ],
    },

    "msk_biopsy": {
        "evidence": "Niveau de preuve modéré : études multicentriques et cohortes rétrospectives (64 à 183 patients), revue critique de la concordance biopsie-résection.",
        "bottom_line": "La biopsie percutanée sous scanner/écho atteint 94–97 % de rendement diagnostique avec 0 % de complication majeure ; ses limites sont le sous-grading des tumeurs cartilagineuses (surtout pelviennes) et le faible rendement microbiologique des spondylodiscites (37 %, 86 % avec technique optimisée + 16S).",
        "kpis": [
            {"v": "93,8 %", "l": "Rendement diagnostique biopsie osseuse TDM", "r": ["42964659"]},
            {"v": "95–97 %", "l": "Précision bénin/malin (parties molles, écho)", "r": ["34497298"]},
            {"v": "κ 0,12", "l": "Concordance de grade chondrosarcome pelvien", "r": ["42997475"]},
            {"v": "51 → 86 %", "l": "Rendement spondylodiscite (technique modifiée + 16S)", "r": ["42363976"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Histologie systématique avant ablation ou radiothérapie : le diagnostic clinique pré-geste est corrigé dans 9,4 % des cas.", "42964659"),
                p("Masse lipomateuse profonde > 5 cm avec septas épais ou nodule non graisseux : microbiopsie ciblée + recherche d'amplification MDM2.", "42129022"),
                p("Suspicion de spondylodiscite : ne pas récuser la biopsie sous antibiothérapie probabiliste (36,4 % vs 37,8 %, NS).", "42736384"),
            ]},
            {"k": "technique", "title": "Technique", "items": [
                p("≥ 3 carottes de ≥ 10 mm ; cibler la berge ostéolytique active / le nodule charnu, pas le centre nécrotique ; envoyer le caillot aspiré en « cell block » (+7 % de rendement).", "41204964"),
                p("Chondrosarcome : carottes multiples dans des cadrans distincts, viser le contingent non cartilagineux (100 % de sensibilité pour le dédifférencié).", "42874309", "42997475"),
                p("Spondylodiscite : prélever simultanément l'os sous-chondral du plateau et le disque + séquençage ARN 16S.", "42363976"),
                p("Lymphome / infiltration médullaire : cibler l'hypersignal diffusion/rehaussement IRM, éviter l'écrasement des carottes.", "41838307"),
            ]},
            {"k": "safety", "title": "Règles carcinologiques", "warn": True, "items": [
                p("Ne jamais traverser un compartiment sain ni le fascia profond ; trajet sur la future voie d'incision définie avec les chirurgiens.", "34497298"),
                p("Une biopsie « bas grade » sur une lésion cartilagineuse pelvienne agressive en IRM ne récuse pas un haut grade (concordance globale 48 %) : relecture et décision en RCP.", "42874309", "42997475"),
            ]},
        ],
    },

    "msk_imaging": {
        "evidence": "Niveau de preuve modéré : cohortes diagnostiques (70 à 261 patients), revues de radiomique et atlas iconographiques, publications princeps (Radiology, RadioGraphics).",
        "bottom_line": "L'IRM fonctionnelle (diffusion/ADC, DCE-MRI, IVIM) améliore la caractérisation des tumeurs des parties molles (AUC 0,86–0,96) et conditionne le ciblage biopsique, le dépistage du nidus d'ostéome ostéoïde et l'évaluation post-ablation, où les critères de viabilité supplantent les critères dimensionnels.",
        "kpis": [
            {"v": "AUC 0,96", "l": "Fasciite nodulaire vs sarcome (ADC + queue fasciale)", "r": ["42970180"]},
            {"v": "AUC 0,86", "l": "Ktrans / D* (IVIM) – angiogenèse sarcomes", "r": ["42997935"]},
            {"v": "35 %", "l": "Nidus d'OO manqués sans séquence dynamique", "r": ["12773675"]},
        ],
        "sections": [
            {"k": "indications", "title": "Apports diagnostiques", "items": [
                p("DCE-MRI au temps artériel précoce (< 30 s) avec wash-out : signature du nidus d'ostéome ostéoïde, indispensable en intra-articulaire.", "12773675"),
                p("ADC élevé + « fascial tail sign » → fasciite nodulaire ; radiomique et IVIM pour grader les sarcomes et orienter la biopsie vers l'« habitat » le plus agressif.", "42970180", "42955458", "42997935"),
                p("TTCG/SVN : hyposignal T1/T2 avec blooming T2* (hémosidérine).", "31601938"),
                p("Lésion solitaire rachidienne/sacrée : topographie (arc postérieur vs corps) et âge orientent le diagnostic ; cartographier V2 et foramen avant geste cervical.", "18635627", "41473339"),
            ]},
            {"k": "followup", "title": "Suivi post-thérapeutique", "items": [
                p("Post-cryo desmoïde : fine prise de contraste périphérique régulière à 3–6 mois = cicatrice granulomateuse normale ; hypersignal T1 spontané → soustraction obligatoire.", "41357250"),
                p("Évaluer la nécrose/viabilité plutôt que la taille (radiomique, mRECIST) après traitement néoadjuvant ou ablation.", "42955458", "42384128"),
            ]},
        ],
    },

    "percutaneous_ablation_general": {
        "evidence": "Niveau de preuve modéré : recommandations CIRSE 2022, 2 revues systématiques (endométriose pariétale, chordomes), étude robotique prospective multicentrique, cohortes et revues d'état de l'art.",
        "bottom_line": "L'ablation percutanée (cryoablation, RF, micro-ondes) suit un paradigme palliatif-curatif : contrôle local à 1 an de 67 % en intention de traiter, > 85 % pour les oligométastases métachrones < 2 cm à corticale intacte ; toute ablation en zone portante doit être couplée à une consolidation.",
        "kpis": [
            {"v": "67 % → > 85 %", "l": "Contrôle local 1 an (global → oligo < 2 cm)", "r": ["24859596"]},
            {"v": "73 %", "l": "Réponse clinique cryo MSK (0 % complication majeure)", "r": ["42909541"]},
            {"v": "8 → 1", "l": "EVA endométriose pariétale (cryo, 8 études)", "r": ["39576446"]},
            {"v": "2,0 mm", "l": "Précision robot Epione® (98,9 % succès)", "r": ["42527616"]},
        ],
        "sections": [
            {"k": "indications", "title": "Indications retenues", "items": [
                p("Curatif : oligométastase métachrone < 2 cm, corticale intacte, à distance des nerfs (5 facteurs prédictifs).", "24859596", "35348870"),
                p("Palliatif : douleur réfractaire ; chordomes rachidiens/sacrés inopérables ou en néoadjuvant (RF + vertébroplastie avant spondylectomie).", "37742284", "42782915"),
                p("Endométriose pariétale abdominale : cryoablation (80–100 % de réponse complète) ou RF « moving-shot » sous écho (EVA 7,4 → 1,7, −77,5 % de volume).", "39576446", "42667387"),
            ]},
            {"k": "technique", "title": "Choix de l'énergie", "items": [
                p("RF : petit nidus intra-osseux, métastase lytique corporéale ; cryoablation : volume > 2–3 cm, extension aux parties molles, matrice sclérotique, visualisation de l'iceball.", "42645393", "35348870"),
                p("Optimisation de l'iceball par synergie multi-sondes ; baisse de densité TDM (UH) post-cryo dans 94 % des cas comme marqueur simple de nécrose.", "41720112", "42909541"),
                p("Robotique : utile pour les abords obliques/multi-aiguilles (rachis, bassin).", "42527616"),
            ]},
            {"k": "safety", "title": "Sécurité", "warn": True, "items": [
                p("Thermoprotection standardisée (CO2, sérum glucosé/salé, thermocouples) selon les recommandations CIRSE.", "35348870", "41720112"),
                p("Endométriose pariétale : hydrodissection pour protéger le derme et le péritoine/anses digestives.", "39576446"),
                p("Zone portante : associer cimentoplastie ou vissage (SINS, Mirels).", "42645393", "37742284"),
            ]},
        ],
    },
}


def main():
    articles = json.loads((DATA_DIR / "articles.json").read_text(encoding="utf-8"))
    pmids_by_cat = {}
    for a in articles:
        pmids_by_cat.setdefault(a["category_id"], set()).add(str(a["pmid"]))

    out = []
    for cat_id, s in SYNTHESES.items():
        known = pmids_by_cat.get(cat_id, set())
        all_pmids = set()
        for k in s["kpis"]:
            all_pmids.update(k["r"])
        for sec in s["sections"]:
            for it in sec["items"]:
                all_pmids.update(it["r"])
        missing = sorted(all_pmids - set().union(*pmids_by_cat.values()))
        if missing:
            raise SystemExit(f"[{cat_id}] PMID absents de la base : {missing}")
        out.append({
            "category_id": cat_id,
            "evidence": s["evidence"],
            "bottom_line": s["bottom_line"],
            "kpis": s["kpis"],
            "sections": s["sections"],
            "sources": sorted(all_pmids & known) + sorted(all_pmids - known),
        })

    (DATA_DIR / "syntheses.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    categories = json.loads((DATA_DIR / "categories.json").read_text(encoding="utf-8"))
    (DATA_DIR / "embedded_data.js").write_text(
        f"window.BIBLIO_ARTICLES = {json.dumps(articles, ensure_ascii=False)};\n"
        f"window.BIBLIO_CATEGORIES = {json.dumps(categories, ensure_ascii=False)};\n"
        f"window.BIBLIO_SYNTHESES = {json.dumps(out, ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    print(f"[Synthèses] {len(out)} pseudo-méta-analyses écrites dans data/syntheses.json + embedded_data.js")


if __name__ == "__main__":
    main()
