---
name: search-campaign-builder
description: Guided, step-by-step interview to create a Search campaign (with RSAs, keywords, ad group structure). Use whenever the user wants to "create search campaign", "vytvoriť search kampaň", "novú search", "spustiť SEA", "rozbehnúť SEA", "set up search campaign". DO NOT skip steps - interview first, mutate last.
---

# Search campaign builder (guided)

Same principle as PMax builder: interview, validate, preview, then send.

## Conversation rules

1. Slovak/Czech if they wrote in SK/CZ.
2. One phase per message.
3. Show defaults; "default" lets them skip.
4. Validate as you go (RSA limits, char counts).
5. Preview full plan before validate.
6. Default to PAUSED.

---

## PHASE 0 - Pre-flight

- Check credentials, list accounts.
- Ask which customer + login_customer_id (if MCC).

## PHASE 1 - Goal & basics

```
1. NÁZOV kampane (napr. "SEA | Brand | CZ")
2. CIEĽ:
   - traffic? maximize_clicks (target_spend)
   - prevalený? maximize_conversions (s/bez tCPA)
   - tržby? maximize_conversion_value (s/bez tROAS)
   - manuálna kontrola? manual_cpc
3. ROZPOČET denný (CZK/EUR/...)
4. KRAJINA + jazyk
5. NETWORK SETTINGS:
   - target_google_search: ON (default ON)
   - target_search_network (search partners): ON/OFF (default OFF, partneri sú často slabší)
   - target_content_network: OFF (display, vypnúť pre čistú search)
   - target_partner_search_network: OFF (default)
6. AD ROTATION: optimize / rotate_indefinitely (default optimize - Google si vyberie najlepší ad)
7. ŠTART/KONIEC: dátumy alebo ihneď + bez konca
8. STATUS: PAUSED (default)
```

## PHASE 2 - Conversion goals

Same as PMax PHASE 2.

## PHASE 3 - Ad group structure

```
SEA potrebuje LOGICKÚ STRUKTÚRU. Najlepšie ad groups = jedna téma = priliehavé ads.

PRÍKLADY pre eshop "Trenky":
A) Brand-kategórie:
   AG "Calvin Klein - trenky"
   AG "Tommy Hilfiger - boxerky"
   AG "Hugo Boss - prádlo"

B) Generic-kategórie:
   AG "Pánské trenky generic"
   AG "Pánské boxerky generic"
   AG "Trenky zľava"

C) Brand defense (keď je kampaň Brand):
   AG "Trenýrkárna brand"
   AG "Trenýrkárna kontakt"

Aké ad groups by si chcel? (alebo nech ti navrhnem na základe URL/produktov)
```

For each ad group, run phases 4-6.

## PHASE 4 - Ad group basics (per ad group)

```
1. NÁZOV ad group
2. DEFAULT BID (cpc_bid_micros) - relevantné len pri MANUAL_CPC; pri smart bidding ignorované
3. TARGET CPA / TARGET ROAS override (volitelne, ad-group level)
4. TYPE: SEARCH_STANDARD (default)
```

## PHASE 5 - Keywords (per ad group)

```
KEYWORDS pre tento ad group:

1. Match types do akých:
   A) iba EXACT [precízny match]
   B) iba PHRASE "fráza match"
   C) iba BROAD široký match (vyžaduje smart bidding)
   D) mix - poviem ktoré sú EXACT, ktoré PHRASE

2. Pošli zoznam keywords (po jednom na riadok), napr:
   pánske trenky calvin klein  EXACT
   calvin klein trenky          PHRASE
   trenky ck                    EXACT
   ck boxerky muzske            EXACT

   alebo len text - ja sa spýtam na match types

3. NEGATIVE KEYWORDS (ad group level):
   napr. "zadarmo", "free", "ako vyrobiť"
   (campaign-level negatives nastavíme zvlášť - PHASE 7)

4. INITIAL BIDS (ak manual_cpc):
   - default ad group bid = X
   - alebo per-keyword bid override
```

Validate: warn if BROAD without smart bidding, if no keywords, if very long phrases.

## PHASE 6 - RSA ads (per ad group)

```
RESPONSIVE SEARCH AD pre tento ad group.

Limity:
- HEADLINES: 3-15, max 30 chars každý (min 3 nutné, ideál 10+)
- DESCRIPTIONS: 2-4, max 90 chars (min 2 nutné, ideál 4)
- PATH1, PATH2: max 15 chars každý (zobrazia sa v URL)
- FINAL URLS: 1+ (kde má reklama smerovať; všetky musia mať rovnaký doména)
- PINNING: optional, na pozíciu HEADLINE_1/2/3 alebo DESC_1/2 (zhoršuje performance, použiť len ak musí - legal/brand)

HEADLINES (5-15 ks, max 30 chars):
napr.
- "Calvin Klein Trenky Online"
- "Akcia až -50%"
- "Doprava ZDARMA od 1000 Kč"
- ...

DESCRIPTIONS (2-4 ks, max 90 chars):
napr.
- "Originálne Calvin Klein boxerky a trenky. Doprava zdarma od 1000 Kč."
- "Skladom v Prahe, expedícia do 24h. 30-dní vrátenie zadarmo."

PATH1: napr. "trenky"
PATH2: napr. "calvin-klein"

FINAL URL: https://trenyrkarna.cz/calvin-klein

CHCEŠ POUŽIŤ PINNING? (default NIE)
```

Validate every headline/description char count. Reject and propose shorter.

Compute `ad_strength` heuristic: count distinct words across headlines, warn if <30 unique words.

## PHASE 7 - Campaign-level negatives + ad extensions

```
CAMPAIGN-LEVEL NEGATIVES:
- napr. "zadarmo", "návod", "torrent", "porn" (často general blocklist)
- pošli zoznam s match types

EXTENSIONS / ASSETS (ad-level + campaign-level):
1. SITELINKS (4+ odporúčané): napr. "Doprava", "Kontakt", "Akcie", "O nás"
   pre každý: link text (max 25), description1 (max 35), description2 (max 35), final_url
2. CALLOUTS (4+ odporúčané): napr. "Doprava zdarma", "30-dní vrátenie" (max 25 chars)
3. STRUCTURED SNIPPETS: header (z fixného zoznamu) + values
   napr. header="Brands", values=["Calvin Klein", "Tommy", "Boss"]
4. CALL extension: telefón
5. PROMOTION asset: zľavy
6. PRICE asset: cenové bloky
7. LEAD FORM: ak chcete leady priamo z reklamy

Iba SITELINKS + CALLOUTS sú must-have. Ostatné podľa potreby.
```

## PHASE 8 - Geo & schedule

```
GEO:
- Krajina (z PHASE 1)
- Konkrétne mestá / regióny include / exclude?
- Targeting type: PRESENCE (kto je tam) vs PRESENCE_OR_INTEREST (default; aj kto sa zaujíma)

SCHEDULE:
- 24/7 alebo iba určité dni/hodiny?
- Ad rotation: optimize (default) / rotate_indefinitely
```

## PHASE 9 - PREVIEW

```
=== Search Campaign - PREVIEW ===

Campaign:
  name: "SEA | Brand Calvin Klein | CZ"
  channel: SEARCH
  status: PAUSED
  bidding: target_roas, target=4.0
  budget: 200 CZK/day STANDARD
  network: google_search ON, search_partners OFF, content OFF
  geo: CZ
  language: CZ
  start: ihneď, end: žiadny

Ad Groups (3):
  1. "Calvin Klein - trenky" (default_cpc 5 CZK)
     keywords: 12 (8 EXACT, 4 PHRASE)
     negatives: 3 ad-group level
     RSA: 11 headlines, 4 descriptions, paths trenky/calvin-klein
     final_url: https://trenyrkarna.cz/calvin-klein
  2. "CK - boxerky" ...
  3. ...

Campaign-level:
  negative keywords: 8 (zdarma, návod, torrent, ...)
  sitelinks: 4 (Doprava, Akcie, Kontakt, O nás)
  callouts: 5

Spustím VALIDATE-ONLY?
```

## PHASE 10 - Apply (po validate OK)

```
✅ Validate OK.

Vytvorím TERAZ?
- Kampaň bude PAUSED
- Po vytvorení dostaneš resource names všetkých entít
- Aktivuj manuálne po overení
```

## Build pattern (technical)

Single batch via `googleAds:mutate` (cross-resource):

```python
mutate_ops = [
    # 1. Budget
    {"campaignBudgetOperation": {"create": {
        "resourceName": f"customers/{cid}/campaignBudgets/-1",
        "name": f"Budget for {name}",
        "amountMicros": str(budget_micros),
        "deliveryMethod": "STANDARD",
    }}},
    # 2. Campaign
    {"campaignOperation": {"create": {
        "resourceName": f"customers/{cid}/campaigns/-2",
        "name": name,
        "advertisingChannelType": "SEARCH",
        "status": "PAUSED",
        "campaignBudget": f"customers/{cid}/campaignBudgets/-1",
        "manualCpc": {"enhancedCpcEnabled": False},  # or maximizeConversions, etc.
        "networkSettings": {
            "targetGoogleSearch": True,
            "targetSearchNetwork": False,
            "targetContentNetwork": False,
            "targetPartnerSearchNetwork": False,
        },
    }}},
    # 3. Geo
    {"campaignCriterionOperation": {"create": {
        "campaign": f"customers/{cid}/campaigns/-2",
        "location": {"geoTargetConstant": "geoTargetConstants/2203"},
    }}},
    # 4. Negative keywords - campaign level
    *[{"campaignCriterionOperation": {"create": {
        "campaign": f"customers/{cid}/campaigns/-2",
        "negative": True,
        "keyword": {"text": kw, "matchType": "BROAD"},
    }}} for kw in campaign_negs],
    # 5. Per ad group:
    {"adGroupOperation": {"create": {
        "resourceName": f"customers/{cid}/adGroups/-10",
        "campaign": f"customers/{cid}/campaigns/-2",
        "name": "Calvin Klein - trenky",
        "type": "SEARCH_STANDARD",
        "status": "ENABLED",
        "cpcBidMicros": str(default_bid_micros),
    }}},
    # Keywords
    *[{"adGroupCriterionOperation": {"create": {
        "adGroup": f"customers/{cid}/adGroups/-10",
        "status": "ENABLED",
        "keyword": {"text": text, "matchType": match_type},
    }}} for text, match_type in keywords],
    # RSA
    {"adGroupAdOperation": {"create": {
        "adGroup": f"customers/{cid}/adGroups/-10",
        "status": "ENABLED",
        "ad": {
            "responsiveSearchAd": {
                "headlines": [{"text": h} for h in headlines],
                "descriptions": [{"text": d} for d in descriptions],
                "path1": "trenky",
                "path2": "calvin-klein",
            },
            "finalUrls": ["https://trenyrkarna.cz/calvin-klein"],
        },
    }}},
    # ... repeat for other ad groups
]

c.mutate_batch(cid, mutate_ops, validate_only=True)
```

## Common pitfalls

- **BROAD match without smart bidding** = waste. Buď ohraničiť na PHRASE/EXACT pri manual_cpc, alebo prepnúť na maximize_conversions.
- **Žiadne negatives** = každý SEA má aspoň 5 negatives od štartu (napr. "zdarma", "free", "návod").
- **Príliš málo headlines/descriptions** = horšia performance. Odporúčam 10+ headlines, 4 descriptions.
- **Pinning na všetko** = stratíte výhody RSA. Pinujte iba ak musíte (legal copy).
- **Nezvolené konverzie** = bidding nemá na čo optimalizovať.
- **Štart ENABLED** = NIE. PAUSED, over, enable.

## Reference
- [reference/mutations-guide.md](../../reference/mutations-guide.md)
- [reference/resources-catalog.md](../../reference/resources-catalog.md)
