"""Conservative venue matching against a versioned official CCF catalog snapshot."""
import json
import re
import sys
from pathlib import Path
ROOT = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT/'content/ccf-2026.json').read_text(encoding='utf-8'))

def key(value):
    value = re.sub(r'\b(?:19|20)\d{2}\b|\b\d+(?:st|nd|rd|th)\b','',value,flags=re.I)
    value = re.sub(r'^\s*(?:proceedings\s+of\s+(?:the\s+)?|the\s+)','',value,flags=re.I)
    return re.sub(r'[^a-z0-9]','',value.casefold())

ALIASES={'usenixconferenceonsecuritysymposium':'usenixsecuritysymposium','usenixsecurity':'usenixsecuritysymposium',
         'ieeesymposiumonsecurityandprivacysp':'ieeesymposiumonsecurityandprivacy',
         'acmasiaconferenceoncomputerandcommunicationssecurityasiaccs':'acmasiaconferenceoncomputerandcommunicationssecurity'}

def classify(item):
    venue=item.get('venue','')
    item['tier']='Unrated'
    item['ccf_edition']=CATALOG['edition']
    item['ccf_source']=CATALOG['source']
    item['ccf_status']='venue_unmatched'
    # Companion/provisional records do not inherit the main conference rank.
    if item.get('kind')=='conference' and re.search(r'\b(workshop|companion|demo|short\s+papers?|findings|artifact)\b',venue,re.I):
        item['ccf_status']='paper_type_not_eligible_or_unverified'
        return item
    normalized=key(venue);normalized=ALIASES.get(normalized,normalized)
    matches=[row for row in CATALOG['records'] if row['kind']==item.get('kind') and normalized and normalized in (key(row['name']),key(row['abbreviation']))]
    tiers={row['tier'] for row in matches}
    if len(tiers)==1:
        item['tier']=next(iter(tiers));item['ccf_status']='venue_matched'
        item['ccf_venue']=matches[0]['name'];item['ccf_page']=matches[0]['page']
    else:
        item.pop('ccf_venue',None);item.pop('ccf_page',None)
    return item
