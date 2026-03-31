"""
Generate CIDOC-CRM RDF/Turtle for the Evolving Geography of Canada (1667-2001).

Event-centric model with careful vocabulary:
- Indigenous territories are E53 Place (enduring, not contingent on European recognition)
- Colonial configurations are E93 Presence (time-bound spatial extents)
- Each assertion of jurisdiction is an E7_Activity, typed by the nature of the claim
- Treaties between European powers are typed as inter-European agreements
  (Indigenous nations were not party to most of these)
- The spatial overlap between colonial assertions and Indigenous territories
  uses canadageo:asserted_jurisdiction_over (marking it as the colonial power's
  assertion, not an established fact of sovereignty transfer)

Placeholder namespace: https://example.org/canadageo/
"""

import csv
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('/home/jic823/canada_geo_evolution/web/data')
QIDS_FILE = Path('/home/jic823/canada_geo_evolution/wikidata_qids.csv')
OVERLAPS_FILE = Path('/home/jic823/canada_geo_evolution/claim_indigenous_overlaps.csv')
CHANGES_FILE = DATA_DIR / 'changes.geojson'
OUTPUT = Path('/home/jic823/canada_geo_evolution/canada_geo_evolution.ttl')

BASE = "https://example.org/canadageo/"


def load_qids():
    entities = []
    with open(QIDS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('name,'):
                continue
            parts = line.split(',')
            if len(parts) >= 6:
                entities.append({
                    'name': parts[0],
                    'csv_name': parts[1],
                    'type': parts[2],
                    'qid': parts[3],
                    'label': parts[4],
                    'role': parts[5],
                    'notes': parts[6] if len(parts) > 6 else ''
                })
    return entities


def load_overlaps():
    overlaps = []
    with open(OVERLAPS_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            overlaps.append(row)
    return overlaps


def load_territory_info():
    """Load sovereign and year info from territories_to_disambiguate.csv."""
    info = {}
    with open('/home/jic823/canada_geo_evolution/territories_to_disambiguate.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name']:
                key = (row['name'], row['sovereign'])
                info[key] = {
                    'name': row['name'],
                    'sovereign': row['sovereign'],
                    'year_min': row['year_min'],
                    'year_max': row['year_max']
                }
    return info


def safe_uri(name):
    return (name.lower()
            .replace("'", "")
            .replace("`", "")
            .replace("\u2019", "")
            .replace(" ", "-")
            .replace("/", "-")
            .replace("(", "").replace(")", "")
            .replace(",", "").replace(".", "")
            .replace("&", "and")
            .replace("\u00e9", "e").replace("\u00e8", "e").replace("\u00ea", "e")
            .replace("\u00e0", "a").replace("\u00e2", "a")
            .replace("\u00f4", "o").replace("\u00ee", "i").replace("\u00ef", "i")
            .replace("\u00e7", "c").replace("\u00fc", "u").replace("\u00f6", "o")
            .strip("-"))


def escape_turtle(s):
    return (s.replace('\\', '\\\\')
             .replace('"', '\\"')
             .replace('\n', '\\n')
             .replace('\r', ''))


def entity_uri(qid, fallback_name=""):
    """Return URI for an entity given its QID field."""
    if qid.startswith('LOCAL:'):
        return f"canadageo:{safe_uri(qid.replace('LOCAL:', ''))}"
    elif qid.startswith('Q'):
        return f"wd:{qid}"
    else:
        return f"canadageo:{safe_uri(fallback_name)}"


def generate():
    entities = load_qids()
    overlaps = load_overlaps()
    territory_info = load_territory_info()

    lines = []
    w = lines.append

    # ================================================================
    # Prefixes
    # ================================================================
    w("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    w("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    w("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    w("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    w("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    w("@prefix dcterms: <http://purl.org/dc/terms/> .")
    w("@prefix dcat: <http://www.w3.org/ns/dcat#> .")
    w("@prefix foaf: <http://xmlns.com/foaf/0.1/> .")
    w("@prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .")
    w("@prefix crmgeo: <http://www.ics.forth.gr/isl/CRMgeo/> .")
    w(f"@prefix canadageo: <{BASE}> .")
    w("@prefix wd: <http://www.wikidata.org/entity/> .")
    w("# Native Land territories use full URIs: <https://native-land.ca/maps/territories/{slug}>")
    w("")

    # ================================================================
    # Dataset Metadata and Attribution
    # ================================================================
    w("# ============================================================")
    w("# Dataset Metadata and Attribution")
    w("# ============================================================")
    w("")
    w("canadageo:dataset a dcat:Dataset ;")
    w('    dcterms:title "The Evolving Geography of Canada (1667-2001): A CIDOC-CRM Knowledge Graph"@en ;')
    w('    dcterms:description "A linked open data representation of European/settler territorial assertions over Indigenous lands in what is now Canada, modeled in CIDOC-CRM. Indigenous territory data is referenced by URI from Native Land Digital; boundary geometries are not stored in this dataset."@en ;')
    w('    dcterms:created "2026-03-30"^^xsd:date ;')
    w("    dcterms:license <https://creativecommons.org/licenses/by-nc/4.0/> ;")
    w("    dcterms:source canadageo:source-native-land-digital ;")
    w("    dcterms:source canadageo:source-territorial-evolution ;")
    w("    dcterms:source <http://www.wikidata.org/> .")
    w("")
    w("# --------------------------------------------------------")
    w("# Native Land Digital Attribution")
    w("# Indigenous territory references in this dataset use URIs")
    w("# from Native Land Digital (https://native-land.ca/).")
    w("# Native Land Digital is an Indigenous-led educational")
    w("# platform. This dataset references Indigenous territories")
    w("# by URI only — no NLD boundary data is stored or")
    w("# redistributed. All Indigenous territory data remains")
    w("# under Indigenous governance per NLD's Data Sovereignty")
    w("# Treaty (https://api-docs.native-land.ca/data-sovereignty-treaty).")
    w("# For visualization, use the NLD API directly:")
    w("# https://api-docs.native-land.ca/")
    w("# --------------------------------------------------------")
    w("")
    w("canadageo:source-native-land-digital a foaf:Organization ;")
    w('    rdfs:label "Native Land Digital"@en ;')
    w('    foaf:homepage <https://native-land.ca/> ;')
    w('    dcterms:description "An Indigenous-led non-profit organization entrusted with the stewardship of data from Indigenous communities worldwide. Indigenous communities are the rightful stewards of their territorial data."@en ;')
    w("    rdfs:seeAlso <https://api-docs.native-land.ca/data-sovereignty-treaty> .")
    w("")
    w("canadageo:source-territorial-evolution a dcat:Dataset ;")
    w('    rdfs:label "Territorial Evolution, 1670-2001"@en ;')
    w('    dcterms:creator "Nicholson, Norman L.; Whebell, Charles F. J.; Galois, Robert; Stavely, Michael"@en ;')
    w("    dcterms:identifier <https://doi.org/10.5683/SP2/IQ7E0X> ;")
    w('    dcterms:publisher "Borealis"@en ;')
    w('    dcterms:date "2020"^^xsd:gYear ;')
    w('    dcterms:description "Shapefiles for two interactive maps from the Historical Atlas of Canada Online Learning Project: Boundary Changes 1670-2001 and Newfoundland Joins Confederation 1949."@en ;')
    w("    dcterms:license <https://creativecommons.org/licenses/by-nc/4.0/> ;")
    w('    dcterms:bibliographicCitation "Nicholson, Norman L.; Whebell, Charles F. J.; Galois, Robert; Stavely, Michael, 2020, \\"Territorial Evolution, 1670-2001\\", https://doi.org/10.5683/SP2/IQ7E0X, Borealis, V1"@en .')
    w("")

    # ================================================================
    # Custom Properties
    # ================================================================
    w("# ============================================================")
    w("# Custom Properties")
    w("# ============================================================")
    w("")
    w("canadageo:asserted_jurisdiction_over a rdf:Property ;")
    w('    rdfs:label "asserted jurisdiction over"@en ;')
    w('    rdfs:comment "Links a colonial/political E7 Activity (assertion of jurisdiction) to an Indigenous E53 Place whose territory it spatially overlaps with. This property records the colonial power\'s assertion, not a transfer of sovereignty. Many Indigenous territories were never legally ceded, and effective Indigenous governance persisted long after European assertions."@en ;')
    w("    rdfs:domain crm:E7_Activity ;")
    w("    rdfs:range crm:E53_Place .")
    w("")
    w("canadageo:formally_recognized_sovereignty_of a rdf:Property ;")
    w('    rdfs:label "formally recognized sovereignty of"@en ;')
    w('    rdfs:comment "Links an act of formal recognition to Indigenous E53 Places whose sovereignty was acknowledged within a European legal framework. These rights pre-exist the recognition — the act does not grant them. In practice, there were considerable breaches of these formal commitments."@en ;')
    w("    rdfs:domain crm:E7_Activity ;")
    w("    rdfs:range crm:E53_Place .")
    w("")

    # ================================================================
    # E55 Types — careful vocabulary
    # ================================================================
    w("# ============================================================")
    w("# E55 Types (classification vocabulary)")
    w("# ============================================================")
    w("")

    type_defs = [
        # Assertion types (for E7_Activity)
        ("type-assertion-of-jurisdiction",
         "Assertion of Jurisdiction",
         "A unilateral assertion of political or administrative jurisdiction over territory. Does not imply consent of existing inhabitants or legal cession of Indigenous sovereignty."),
        ("type-inter-european-treaty-assertion",
         "Inter-European Treaty Assertion",
         "Jurisdiction asserted on the basis of a treaty between European powers. Indigenous nations were not party to these agreements."),
        ("type-commercial-monopoly-grant",
         "Commercial Monopoly Grant",
         "Jurisdiction exercised under a commercial charter or monopoly grant (e.g., Hudson's Bay Company). Control was primarily economic, not administrative in many regions."),
        ("type-legislative-assertion",
         "Legislative Assertion",
         "Jurisdiction asserted through unilateral legislation by a settler government (e.g., Acts of Parliament, Orders in Council)."),
        ("type-administrative-jurisdiction",
         "Administrative Jurisdiction",
         "Ongoing administrative governance of a defined territory (e.g., a province or territory within Confederation)."),
        ("type-disputed-assertion",
         "Disputed Assertion",
         "Territory where multiple European/settler powers asserted overlapping and contested jurisdiction."),
        ("type-formal-recognition-of-indigenous-sovereignty",
         "Formal Recognition of Indigenous Sovereignty",
         "Formal legal recognition by a European/settler power of Indigenous sovereignty over territory. Does not grant these rights — they pre-exist the recognition. The Royal Proclamation of 1763 is a key example. In practice, there were considerable breaches of these formal commitments on the ground."),

        # Place types
        ("type-province", "Province", "Canadian province."),
        ("type-territory", "Territory", "Canadian territory."),
        ("type-district", "District", "Administrative district within a territory."),
        ("type-indigenous-territory",
         "Indigenous Territory",
         "Territory of an Indigenous people. These territories are enduring — they are not contingent on European recognition and many have never been legally ceded."),

        # Actor types
        ("type-sovereign-state", "Sovereign State", "A sovereign political entity."),
        ("type-commercial-sovereign",
         "Commercial Sovereign",
         "A commercial entity exercising territorial control under charter or grant."),

        # Event types
        ("type-inter-european-treaty",
         "Inter-European Treaty",
         "A formal agreement between European powers regarding territorial boundaries. Indigenous nations were generally not consulted or party to these agreements."),
        ("type-act-of-parliament",
         "Act of Parliament",
         "Legislation enacted by a parliament, often unilaterally asserting jurisdiction over Indigenous territories."),
        ("type-order-in-council",
         "Order in Council",
         "Executive order by a privy council or governor general."),
        ("type-boundary-decision",
         "Boundary Decision",
         "A judicial or diplomatic boundary determination."),
        ("type-purchase-or-cession",
         "Purchase or Cession",
         "A transfer of claimed jurisdiction between European/settler powers (e.g., Alaska Purchase, Louisiana Purchase). These transfers concerned claims between settler powers and did not involve Indigenous consent."),
    ]

    for uri_frag, label, comment in type_defs:
        safe_frag = uri_frag.replace('/', '-')
        w(f"canadageo:{safe_frag} a crm:E55_Type, skos:Concept ;")
        w(f'    rdfs:label "{label}"@en ;')
        w(f'    skos:prefLabel "{label}"@en ;')
        w(f'    rdfs:comment "{escape_turtle(comment)}"@en .')
        w("")

    # ================================================================
    # E53 Place — Landmass
    # ================================================================
    w("# ============================================================")
    w("# E53 Place — Landmass")
    w("# ============================================================")
    w("")
    w("wd:Q49 a crm:E53_Place ;")
    w('    rdfs:label "North America"@en .')
    w("")

    # ================================================================
    # E74 Group — Sovereign Powers
    # ================================================================
    w("# ============================================================")
    w("# E74 Group — Political and Commercial Powers")
    w("# ============================================================")
    w("")

    sovereigns = [e for e in entities if e['type'] == 'sovereign']
    seen_qids = set()
    sovereign_qid_map = {}

    for sov in sovereigns:
        qid = sov['qid']
        sovereign_qid_map[sov['csv_name']] = qid
        if qid in seen_qids:
            continue
        seen_qids.add(qid)

        uri = f"wd:{qid}"
        label = escape_turtle(sov['name'])
        role = sov['role'].strip()

        if 'E53 Place' in role:
            w(f"{uri} a crm:E74_Group, crm:E53_Place ;")
        else:
            w(f"{uri} a crm:E74_Group ;")
        w(f'    rdfs:label "{label}"@en ;')

        if 'commercial' in sov['notes'].lower() or 'commercial' in sov['role'].lower():
            w(f"    crm:P2_has_type canadageo:type-commercial-sovereign .")
        else:
            w(f"    crm:P2_has_type canadageo:type-sovereign-state .")
        w("")

    # ================================================================
    # E53 Place — Modern Provinces/Territories
    # ================================================================
    w("# ============================================================")
    w("# E53 Place — Modern Provinces and Territories")
    w("# ============================================================")
    w("")

    provinces = [e for e in entities if e['type'] in ('province', 'territory')]
    for prov in provinces:
        uri = f"wd:{prov['qid']}"
        label = escape_turtle(prov['name'])
        ptype = 'type-province' if prov['type'] == 'province' else 'type-territory'
        w(f"{uri} a crm:E53_Place ;")
        w(f'    rdfs:label "{label}"@en ;')
        w(f"    crm:P2_has_type canadageo:{ptype} ;")
        w(f"    crm:P89_falls_within wd:Q16 .")
        w("")

    # ================================================================
    # E53 Place — Other enduring places
    # ================================================================
    enduring = [e for e in entities if e['type'] == 'place']
    if enduring:
        w("# ============================================================")
        w("# E53 Place — Other Enduring Places")
        w("# ============================================================")
        w("")
        for pl in enduring:
            w(f"wd:{pl['qid']} a crm:E53_Place ;")
            w(f'    rdfs:label "{escape_turtle(pl["name"])}"@en .')
            w("")

    # ================================================================
    # E53 Place — Indigenous Territories
    # ================================================================
    w("# ============================================================")
    w("# E53 Place — Indigenous Territories (from Native Land Digital)")
    w("# Indigenous territories are enduring. They are not contingent")
    w("# on European recognition and many have never been legally ceded.")
    w("# ============================================================")
    w("")

    indigenous = {}
    for ov in overlaps:
        slug = ov['indigenous_slug']
        if slug not in indigenous:
            indigenous[slug] = ov['indigenous_territory']

    for slug, name in sorted(indigenous.items()):
        nl_uri = f"<https://native-land.ca/maps/territories/{slug}>"
        w(f"{nl_uri} a crm:E53_Place ;")
        w(f'    rdfs:label "{escape_turtle(name)}"@en ;')
        w(f"    crm:P2_has_type canadageo:type-indigenous-territory ;")
        w(f"    crm:P89_falls_within wd:Q49 .")
        w("")

    # ================================================================
    # E93 Presence — Historical Territorial Configurations
    # These are the spatial extents of colonial/political assertions.
    # ================================================================
    w("# ============================================================")
    w("# E93 Presence — Historical Territorial Configurations")
    w("# These record the spatial extents of colonial/political")
    w("# assertions at particular times. They do not represent")
    w("# effective control or legitimate sovereignty over the")
    w("# Indigenous territories they overlap with.")
    w("# ============================================================")
    w("")

    historical = [e for e in entities if e['type'] in ('historical', 'district')]

    # For each historical territory, find its year range from territory_info
    for hist in historical:
        uri = entity_uri(hist['qid'], hist['name'])
        label = escape_turtle(hist['name'])
        csv_name = hist['csv_name']

        # Find year range — try multiple key combinations
        year_min = year_max = sovereign = None
        for (tname, tsov), tinfo in territory_info.items():
            if csv_name and (tname == csv_name or csv_name in tname or tname in csv_name):
                year_min = tinfo['year_min']
                year_max = tinfo['year_max']
                sovereign = tinfo['sovereign']
                break

        # Determine type
        if 'disputed' in label.lower() or 'claimed' in label.lower():
            presence_type = "type-disputed-assertion"
        elif hist['type'] == 'district':
            presence_type = "type-district"
        else:
            presence_type = "type-assertion-of-jurisdiction"

        w(f"{uri} a crmgeo:E93_Presence ;")
        w(f'    rdfs:label "{label}"@en ;')
        w(f"    crm:P2_has_type canadageo:{presence_type} ;")

        if year_min and year_max:
            ts_uri = f"canadageo:ts-{safe_uri(hist['name'])}"
            w(f"    crmgeo:P164_is_temporally_specified_by {ts_uri} ;")

        if hist['qid'].startswith('Q'):
            w(f"    owl:sameAs wd:{hist['qid']} ;")

        # Close the entity
        lines[-1] = lines[-1].rstrip(' ;') + ' .'
        w("")

        # Emit time-span
        if year_min and year_max:
            w(f"{ts_uri} a crm:E52_Time-Span ;")
            w(f'    rdfs:label "{year_min}\u2013{year_max}"@en ;')
            w(f'    crm:P82_at_some_time_within "{year_min}/{year_max}"^^xsd:string ;')
            w(f'    crm:P82a_begin_of_the_begin "{year_min}-01-01"^^xsd:date ;')
            w(f'    crm:P82b_end_of_the_end "{year_max}-12-31"^^xsd:date .')
            w("")

    # ================================================================
    # E5 Event — Treaties and Acts (event-centric structure)
    # Each event links to participants and affected territories.
    # ================================================================
    w("# ============================================================")
    w("# E5 Event — Treaties, Acts, and Boundary Changes")
    w("# These events are the mechanisms through which European/settler")
    w("# powers asserted, transferred, or reorganized jurisdiction.")
    w("# ============================================================")
    w("")

    events = [e for e in entities if e['type'] == 'event']

    # Map event names to known participant powers
    # (simplified — a fuller model would have per-event participant lists)
    event_participants = {
        'Treaty of Utrecht': ['Q70972', 'Q161885'],          # France, Britain
        'Treaty of Paris (1763)': ['Q70972', 'Q161885'],     # France, Britain
        'Royal Proclamation of 1763': ['Q161885'],           # Britain
        'Quebec Act of 1774': ['Q161885'],                   # Britain
        'Treaty of Paris (1783)': ['Q161885', 'Q30'],        # Britain, USA
        'Nootka Convention': ['Q80702', 'Q161885'],          # Spain, Britain
        'Constitutional Act of 1791': ['Q161885'],           # Britain
        'Louisiana Purchase': ['Q70972', 'Q30'],             # France, USA
        'Newfoundland Act 1809': ['Q161885'],                # Britain
        'Convention of 1818': ['Q145', 'Q30'],               # UK, USA
        'Adams-Onis Treaty': ['Q80702', 'Q30'],              # Spain, USA
        'Treaty of Saint Petersburg': ['Q145', 'Q34266'],    # UK, Russia
        'Act of Union 1840': ['Q145'],                       # UK
        'Webster-Ashburton Treaty': ['Q145', 'Q30'],         # UK, USA
        'Oregon Treaty': ['Q145', 'Q30'],                    # UK, USA
        'Constitution Act 1867': ['Q145', 'Q16'],            # UK, Canada
        'Rupert\'s Land Act 1868': ['Q145', 'Q76039'],       # UK, HBC
        'Manitoba Act 1870': ['Q16'],                        # Canada
        'Alaska Purchase': ['Q34266', 'Q30'],                # Russia, USA
        'Alberta Act': ['Q16'],                              # Canada
        'Saskatchewan Act': ['Q16'],                         # Canada
        'Alaska boundary dispute': ['Q16', 'Q30'],           # Canada, USA
        'Newfoundland Act 1949': ['Q145', 'Q16'],            # UK, Canada
        'Nunavut Act': ['Q16'],                              # Canada
    }

    for evt in events:
        qid = evt['qid']
        label = escape_turtle(evt['name'])
        year = evt['csv_name']
        uri = entity_uri(qid, evt['name'])

        # Determine event type
        name_lower = label.lower()
        if 'treaty' in name_lower or 'convention' in name_lower:
            evt_type = "type-inter-european-treaty"
        elif 'purchase' in name_lower:
            evt_type = "type-purchase-or-cession"
        elif 'act' in name_lower:
            evt_type = "type-act-of-parliament"
        elif 'order' in name_lower:
            evt_type = "type-order-in-council"
        elif 'boundary' in name_lower or 'dispute' in name_lower:
            evt_type = "type-boundary-decision"
        elif 'proclamation' in name_lower:
            evt_type = "type-legislative-assertion"
        else:
            evt_type = "type-inter-european-treaty"

        w(f"{uri} a crm:E5_Event ;")
        w(f'    rdfs:label "{label}"@en ;')
        w(f"    crm:P2_has_type canadageo:{evt_type} ;")

        # Participants
        participants = event_participants.get(evt['name'], [])
        for pqid in participants:
            w(f"    crm:P11_had_participant wd:{pqid} ;")

        # Time-span
        if year and year.isdigit():
            ts_uri = f"canadageo:ts-event-{safe_uri(evt['name'])}"
            w(f"    crm:P4_has_time-span {ts_uri} ;")

        lines[-1] = lines[-1].rstrip(' ;') + ' .'
        w("")

        if year and year.isdigit():
            w(f"{ts_uri} a crm:E52_Time-Span ;")
            w(f'    rdfs:label "{year}"@en ;')
            w(f'    crm:P82_at_some_time_within "{year}"^^xsd:string ;')
            w(f'    crm:P82a_begin_of_the_begin "{year}-01-01"^^xsd:date ;')
            w(f'    crm:P82b_end_of_the_end "{year}-12-31"^^xsd:date .')
            w("")

    # ================================================================
    # E7 Activity — Assertions of Jurisdiction (event-centric core)
    # Each row in the original data (territory + sovereign + year range)
    # becomes an E7_Activity: the act of asserting jurisdiction.
    # ================================================================
    w("# ============================================================")
    w("# E7 Activity — Assertions of Jurisdiction")
    w("# Each assertion links: who asserted (E74 Group), where (E93"),
    w("# Presence for the spatial extent), when (E52 Time-Span), and")
    w("# which Indigenous territories (E53 Place) were affected.")
    w("# These are assertions by European/settler powers. They do not")
    w("# represent consent, cession, or effective control over")
    w("# Indigenous territories. Effective Indigenous governance")
    w("# persisted well beyond these assertion dates in many regions.")
    w("# ============================================================")
    w("")

    # Build E93 URI lookup
    e93_uri_map = {}
    for hist in historical:
        e93_uri_map[hist['name']] = entity_uri(hist['qid'], hist['name'])
        if hist['csv_name']:
            e93_uri_map[hist['csv_name']] = entity_uri(hist['qid'], hist['name'])
    # Also map province names
    for prov in provinces:
        if prov['name'] not in e93_uri_map:
            e93_uri_map[prov['name']] = f"wd:{prov['qid']}"
        if prov['csv_name'] not in e93_uri_map:
            e93_uri_map[prov['csv_name']] = f"wd:{prov['qid']}"

    # Group overlaps by (claim_name, sovereign)
    claim_overlaps = defaultdict(set)
    for ov in overlaps:
        key = (ov['claim_name'], ov['claim_sovereign'])
        claim_overlaps[key].add(ov['indigenous_slug'])

    # Generate one E7_Activity per (territory, sovereign, year_range)
    for (tname, tsov), tinfo in sorted(territory_info.items()):
        year_min = tinfo['year_min']
        year_max = tinfo['year_max']
        is_recognition = (tsov == 'Indigenous')

        # URI and label differ for recognition vs assertion
        if is_recognition:
            activity_uri = f"canadageo:recognition-{safe_uri(tname)}"
            label = escape_turtle(f"Formal recognition of Indigenous sovereignty: {tname}")
            act_type = "type-formal-recognition-of-indigenous-sovereignty"
        elif 'disputed' in tname.lower() or 'claimed' in tname.lower():
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-disputed-assertion"
        elif tsov == 'Hudsons Bay Company':
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-commercial-monopoly-grant"
        elif tsov in ('Britain', 'France', 'Spain', 'Russia', 'Denmark'):
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-inter-european-treaty-assertion"
        elif tsov == 'Canada':
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-administrative-jurisdiction"
        elif tsov == 'USA':
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-legislative-assertion"
        elif tsov == 'Mexico':
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-assertion-of-jurisdiction"
        else:
            activity_uri = f"canadageo:assertion-{safe_uri(tname)}-{safe_uri(tsov)}"
            label = escape_turtle(f"Assertion of jurisdiction: {tname} by {tsov}")
            act_type = "type-assertion-of-jurisdiction"

        # Find sovereign QID — for recognition, the recognizing power was Britain
        if is_recognition:
            sov_qid = sovereign_qid_map.get('Britain')
        else:
            sov_qid = sovereign_qid_map.get(tsov)

        # Find E93 presence URI
        e93_uri = e93_uri_map.get(tname)

        w(f"{activity_uri} a crm:E7_Activity ;")
        w(f'    rdfs:label "{label}"@en ;')
        w(f"    crm:P2_has_type canadageo:{act_type} ;")

        if sov_qid:
            w(f"    crm:P14_carried_out_by wd:{sov_qid} ;")

        # Link to E93 Presence (the spatial extent)
        if e93_uri:
            w(f"    crm:P7_took_place_at {e93_uri} ;")

        # Time-span
        ts_uri = f"canadageo:ts-{safe_uri(activity_uri.split(':',1)[1])}"
        w(f"    crm:P4_has_time-span {ts_uri} ;")

        # Link to overlapping Indigenous territories
        # Use recognized_jurisdiction_of for recognition, asserted_jurisdiction_over otherwise
        key = (tname, tsov)
        indigenous_slugs = claim_overlaps.get(key, set())
        overlap_property = "canadageo:formally_recognized_sovereignty_of" if is_recognition else "canadageo:asserted_jurisdiction_over"
        for slug in sorted(indigenous_slugs):
            nl_uri = f"<https://native-land.ca/maps/territories/{slug}>"
            w(f"    {overlap_property} {nl_uri} ;")

        lines[-1] = lines[-1].rstrip(' ;') + ' .'
        w("")

        # Time-span
        w(f"{ts_uri} a crm:E52_Time-Span ;")
        w(f'    rdfs:label "{year_min}\u2013{year_max}"@en ;')
        w(f'    crm:P82_at_some_time_within "{year_min}/{year_max}"^^xsd:string ;')
        w(f'    crm:P82a_begin_of_the_begin "{year_min}-01-01"^^xsd:date ;')
        w(f'    crm:P82b_end_of_the_end "{year_max}-12-31"^^xsd:date .')
        w("")

    # Write output
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # Stats
    n_indigenous = len(indigenous)
    n_provinces = len(provinces)
    n_enduring = len(enduring)
    n_e93 = len(historical)
    n_sovereigns = len(seen_qids)
    n_events = len(events)
    n_activities = len(territory_info)
    n_overlap_triples = sum(len(slugs) for slugs in claim_overlaps.values())

    print(f"Generated {OUTPUT}")
    print(f"  E53 Place:        {n_indigenous + n_provinces + n_enduring + 1}")
    print(f"    Indigenous:     {n_indigenous}")
    print(f"    Provinces:      {n_provinces}")
    print(f"    Other:          {n_enduring + 1}")
    print(f"  E93 Presence:     {n_e93}")
    print(f"  E74 Group:        {n_sovereigns}")
    print(f"  E5 Event:         {n_events}")
    print(f"  E7 Activity:      {n_activities} assertions of jurisdiction")
    print(f"  Overlap triples:  {n_overlap_triples} (asserted_jurisdiction_over)")


if __name__ == '__main__':
    generate()
