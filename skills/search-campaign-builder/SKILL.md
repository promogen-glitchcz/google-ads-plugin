---
name: search-campaign-builder
description: Guided, step-by-step interview to create a Search campaign (with RSAs, keywords, ad group structure). Use whenever the user wants to "create search campaign", "vytvoriť search kampaň", "novú search", "spustiť SEA", "rozbehnúť SEA", "set up search campaign". DO NOT skip steps - interview first, mutate last.
---

# Search campaign builder (guided)

Same principle as PMax builder: interview, validate, preview, then send.

## Conversation rules

1. **Mluv s uživatelem ČESKY** (ne slovensky). Otázky, návrhy, errory - vše v češtině. Technické bloky (Python, JSON) zůstávají anglicky.
2. Jedna fáze = jedna zpráva.
3. Defaults ukazuj jasně; "default" znamená skip.
4. Validuj průběžně (RSA limity, počty znaků).
5. Preview celého plánu před validate.
6. Defaultně PAUSED.

---

## PHASE 0 - Pre-flight

- Spusť `check_credentials`, vypiš dostupné účty.
- Zeptej se který customer + login_customer_id (pokud MCC).

## PHASE 1 - Cíl & základy

```
1. NÁZEV kampaně (např. "SEA | Brand | CZ")
2. CÍL:
   - traffic? maximize_clicks (target_spend)
   - prodej? maximize_conversions (s/bez tCPA)
   - tržby? maximize_conversion_value (s/bez tROAS)
   - manuální kontrola? manual_cpc
3. ROZPOČET denní (Kč/EUR/...)
4. ZEMĚ + jazyk
5. NETWORK SETTINGS:
   - target_google_search: ON (default ON)
   - target_search_network (search partners): ON/OFF (default OFF, partneři jsou často slabší)
   - target_content_network: OFF (display, vypnout pro čistou search)
   - target_partner_search_network: OFF (default)
6. AD ROTATION: optimize / rotate_indefinitely (default optimize - Google si vybere nejlepší ad)
7. START/KONEC: data nebo ihned + bez konce
8. STATUS: PAUSED (default)
```

## PHASE 2 - Konverzní cíle

Stejné jako PMax PHASE 2 (všechny primary konverze účtu nebo konkrétní výběr - jen v češtině).

## PHASE 3 - Struktura ad groups

```
SEA potřebuje LOGICKOU STRUKTURU. Nejlepší ad groups = jedno téma = přiléhavé ads.

PŘÍKLADY pro e-shop "Trenky":
A) Brand-kategorie:
   AG "Calvin Klein - trenky"
   AG "Tommy Hilfiger - boxerky"
   AG "Hugo Boss - prádlo"

B) Generic-kategorie:
   AG "Pánské trenky generic"
   AG "Pánské boxerky generic"
   AG "Trenky sleva"

C) Brand defense (když je kampaň Brand):
   AG "Trenýrkárna brand"
   AG "Trenýrkárna kontakt"

Jaké ad groups bys chtěl? (nebo ať ti navrhnu na základě URL/produktů)
```

Pro každou ad group projdi fáze 4-6.

## PHASE 4 - Ad group základy (pro každou ad group)

```
1. NÁZEV ad group
2. DEFAULT BID (cpc_bid_micros) - relevantní jen při MANUAL_CPC; při smart bidding ignorováno
3. TARGET CPA / TARGET ROAS override (volitelně, ad-group level)
4. TYPE: SEARCH_STANDARD (default)
```

## PHASE 5 - Keywords (pro každou ad group)

```
KEYWORDS pro tuhle ad group:

1. Match types jaké:
   A) jen EXACT [přesný match]
   B) jen PHRASE "frázový match"
   C) jen BROAD široký match (vyžaduje smart bidding)
   D) mix - řeknu které jsou EXACT, které PHRASE

2. Pošli seznam keywords (po jednom na řádek), např:
   pánské trenky calvin klein  EXACT
   calvin klein trenky          PHRASE
   trenky ck                    EXACT
   ck boxerky panske            EXACT

   nebo jen text - já se zeptám na match types

3. NEGATIVE KEYWORDS (ad group level):
   např. "zdarma", "free", "jak vyrobit"
   (campaign-level negatives nastavíme zvlášť - PHASE 7)

4. INITIAL BIDS (pokud manual_cpc):
   - default ad group bid = X
   - nebo per-keyword bid override
```

Validuj: varuj při BROAD bez smart bidding, při žádných keywords, při velmi dlouhých frázích.

## PHASE 6 - RSA ads (pro každou ad group)

```
RESPONSIVE SEARCH AD pro tuhle ad group.

Limity:
- HEADLINES: 3-15, max 30 znaků každý (min 3 nutné, ideál 10+)
- DESCRIPTIONS: 2-4, max 90 znaků (min 2 nutné, ideál 4)
- PATH1, PATH2: max 15 znaků každý (zobrazí se v URL)
- FINAL URLS: 1+ (kam má reklama směřovat; všechny musí mít stejnou doménu)
- PINNING: volitelné, na pozici HEADLINE_1/2/3 nebo DESC_1/2 (zhoršuje performance, použít jen pokud musíš - legal/brand)

HEADLINES (5-15 ks, max 30 znaků):
např.
- "Calvin Klein Trenky Online"
- "Akce až -50%"
- "Doprava ZDARMA od 1000 Kč"
- ...

DESCRIPTIONS (2-4 ks, max 90 znaků):
např.
- "Originální Calvin Klein boxerky a trenky. Doprava zdarma od 1000 Kč."
- "Skladem v Praze, expedice do 24 h. 30 dní na vrácení zdarma."

PATH1: např. "trenky"
PATH2: např. "calvin-klein"

FINAL URL: https://trenyrkarna.cz/calvin-klein

CHCEŠ POUŽÍT PINNING? (default NE)
```

Validuj počet znaků každého headline/description. Odmítni a navrhni kratší.

Spočítej `ad_strength` heuristiku: počet unikátních slov napříč headlines, varuj pokud <30 unikátních slov.

## PHASE 7 - Campaign-level negatives + ad extensions

```
CAMPAIGN-LEVEL NEGATIVES:
- např. "zdarma", "návod", "torrent", "porn" (často obecný blocklist)
- pošli seznam s match types

EXTENSIONS / ASSETS (ad-level + campaign-level):
1. SITELINKS (4+ doporučené): např. "Doprava", "Kontakt", "Akce", "O nás"
   pro každý: link text (max 25), description1 (max 35), description2 (max 35), final_url
2. CALLOUTS (4+ doporučené): např. "Doprava zdarma", "30 dní na vrácení" (max 25 znaků)
3. STRUCTURED SNIPPETS: header (z fixního seznamu) + values
   např. header="Brands", values=["Calvin Klein", "Tommy", "Boss"]
4. CALL extension: telefon
5. PROMOTION asset: slevy
6. PRICE asset: cenové bloky
7. LEAD FORM: pokud chcete leady přímo z reklamy

Pouze SITELINKS + CALLOUTS jsou must-have. Ostatní podle potřeby.
```

## PHASE 8 - Geo & schedule

```
GEO:
- Země (z PHASE 1)
- Konkrétní města / regiony include / exclude?
- Targeting type: PRESENCE (kdo je tam) vs PRESENCE_OR_INTEREST (default; i kdo se zajímá)

SCHEDULE:
- 24/7 nebo jen určité dny/hodiny?
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
  budget: 200 Kč/den STANDARD
  network: google_search ON, search_partners OFF, content OFF
  geo: CZ
  language: CZ
  start: ihned, end: žádný

Ad Groups (3):
  1. "Calvin Klein - trenky" (default_cpc 5 Kč)
     keywords: 12 (8 EXACT, 4 PHRASE)
     negatives: 3 ad-group level
     RSA: 11 headlines, 4 descriptions, paths trenky/calvin-klein
     final_url: https://trenyrkarna.cz/calvin-klein
  2. "CK - boxerky" ...
  3. ...

Campaign-level:
  negative keywords: 8 (zdarma, návod, torrent, ...)
  sitelinks: 4 (Doprava, Akce, Kontakt, O nás)
  callouts: 5

Spustím VALIDATE-ONLY?
```

## PHASE 10 - Apply (po validate OK)

```
✅ Validate OK.

Vytvořím TEĎ?
- Kampaň bude PAUSED
- Po vytvoření dostaneš resource names všech entit
- Aktivuj ručně po ověření
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

- **BROAD match bez smart bidding** = waste. Buď omezit na PHRASE/EXACT při manual_cpc, nebo přepnout na maximize_conversions.
- **Žádné negatives** = každý SEA má aspoň 5 negatives od startu (např. "zdarma", "free", "návod").
- **Příliš málo headlines/descriptions** = horší performance. Doporučuju 10+ headlines, 4 descriptions.
- **Pinning na všechno** = ztratíš výhody RSA. Pinuj jen pokud musíš (legal copy).
- **Nezvolené konverze** = bidding nemá na co optimalizovat.
- **Start ENABLED** = NE. PAUSED, ověř, enable.

## Reference
- [reference/mutations-guide.md](../../reference/mutations-guide.md)
- [reference/resources-catalog.md](../../reference/resources-catalog.md)
