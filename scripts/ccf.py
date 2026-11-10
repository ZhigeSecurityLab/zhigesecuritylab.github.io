"""Conservative venue matching against a versioned official CCF catalog snapshot."""
import json
import re
import sys
from pathlib import Path
ROOT = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT/'content/ccf-2026.json').read_text(encoding='utf-8'))

def key(value):
    value = re.sub(r'\(USENIX\s+Security\s*\d*\)', '', value, flags=re.I)
    value = re.sub(r'\b(?:19|20)\d{2}\b|\b\d+(?:st|nd|rd|th)\b','',value,flags=re.I)
    value = re.sub(r'^\s*(?:proceedings\s+of\s+(?:the\s+)?|the\s+)','',value,flags=re.I)
    return re.sub(r'[^a-z0-9]','',value.casefold())

ALIASES={'usenixconferenceonsecuritysymposium':'usenixsecuritysymposium','usenixsecurity':'usenixsecuritysymposium',
         'ieeesymposiumonsecurityandprivacysp':'ieeesymposiumonsecurityandprivacy',
         'acmasiaconferenceoncomputerandcommunicationssecurityasiaccs':'acmasiaconferenceoncomputerandcommunicationssecurity',
         'acmsigsacconferenceoncomputerandcommunicationssecurity':'acmconferenceoncomputerandcommunicationssecurity'}

def classify(item):
    venue=item.get('venue','')
    item['tier']='Unrated'
    item['ccf_edition']=CATALOG['edition']
    item['ccf_source']=CATALOG['source']
    item['ccf_status']='venue_unmatched'
    # Companion/provisional records do not inherit the main conference rank.
    if item.get('kind')=='conference' and re.search(r'\b(workshops?|companion|demo|short\s+papers?|findings|artifact)\b',venue,re.I):
        item['ccf_status']='paper_type_not_eligible_or_unverified'
        return item
    normalized=key(venue);normalized=ALIASES.get(normalized,normalized)
    tail=re.search(r'\(([^()]+)\)\s*$',venue)
    stripped=key(venue[:tail.start()]) if tail else ''
    stripped=ALIASES.get(stripped,stripped)
    def match(row):
        if row['kind']!=item.get('kind'):return False
        if normalized and normalized in (key(row['name']),key(row['abbreviation'])):return True
        # Ignore a trailing parenthesis only when it is that venue's catalog abbreviation.
        return bool(tail and key(tail[1])==key(row['abbreviation']) and stripped==key(row['name']))
    matches=[row for row in CATALOG['records'] if match(row)]
    tiers={row['tier'] for row in matches}
    if len(tiers)==1:
        item['tier']=next(iter(tiers));item['ccf_status']='venue_matched'
        item['ccf_venue']=matches[0]['name'];item['ccf_page']=matches[0]['page']
    else:
        item.pop('ccf_venue',None);item.pop('ccf_page',None)
    return item
