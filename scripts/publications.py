"""Public ORCID import; no private credentials or automatic ownership claim."""
import concurrent.futures
import json
import re
import ssl
from urllib.request import Request, urlopen
from urllib.parse import quote
import certifi
from ccf import classify

CONTEXT = ssl.create_default_context(cafile=certifi.where())
TIERS = ('A', 'B', 'C', 'Unrated')
KINDS = ('conference', 'journal', 'other')


def orcid_id(value):
    value = str(value).strip().removeprefix('https://orcid.org/').rstrip('/').upper()
    if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', value):
        raise ValueError('请输入有效 ORCID，例如 0000-0001-6029-5064')
    total = 0
    for digit in value.replace('-', '')[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if value[-1] != ('X' if check == 10 else str(check)):
        raise ValueError('ORCID 校验位不正确')
    return value


def request(url, accept='application/json'):
    with urlopen(Request(url, headers={'Accept': accept, 'User-Agent': 'ZhigeFacultyEditor/1.2 (public academic metadata)'}), timeout=25, context=CONTEXT) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError('数据源响应过大')
    return json.loads(raw) if accept == 'application/json' else raw.decode('utf-8')


def val(obj):
    return (obj or {}).get('value', '') or ''


def normalize(work, oid):
    doi = next((x['external-id-value'].strip().removeprefix('https://doi.org/').lower()
                for x in (work.get('external-ids') or {}).get('external-id', []) if x.get('external-id-type') == 'doi'), '')
    title = val((work.get('title') or {}).get('title'))
    subtitle = val((work.get('title') or {}).get('subtitle'))
    if subtitle:
        title += ': ' + subtitle
    year = int(val((work.get('publication-date') or {}).get('year')) or 1900)
    kind = {'conference-paper': 'conference', 'journal-article': 'journal'}.get(work.get('type'), 'other')
    authors = ', '.join(val(c.get('credit-name')) for c in (work.get('contributors') or {}).get('contributor', []) if val(c.get('credit-name')))
    citation = work.get('citation') or {}
    bib = citation.get('citation-value', '') if citation.get('citation-type') == 'bibtex' else ''
    url = val(work.get('url'))
    return classify({'id': 'doi:' + doi if doi else 'orcid:' + oid + ':' + str(work['put-code']),
            'title': title, 'year': year, 'authors': authors, 'venue': val(work.get('journal-title')),
            'kind': kind, 'tier': 'Unrated', 'doi': doi, 'url': 'https://doi.org/' + doi if doi else url,
            'pdf_url': url if re.search(r'\.pdf(?:[?#]|$)', url, re.I) else '', 'bibtex': bib,
            'orcid': oid, 'put_code': work['put-code'], 'selected': False})


def sync(value):
    oid = orcid_id(value)
    person = request(f'https://pub.orcid.org/v3.0/{oid}/person')
    name = person.get('name') or {}
    display = val(name.get('credit-name')) or ' '.join(filter(None, [val(name.get('given-names')), val(name.get('family-name'))]))
    groups = request(f'https://pub.orcid.org/v3.0/{oid}/works').get('group', [])
    if len(groups) > 2000:
        raise ValueError('成果超过 2000 条，请联系维护人员')
    summaries = [sorted(g['work-summary'], key=lambda w: int(w.get('display-index') or 0), reverse=True)[0] for g in groups if g.get('work-summary')]
    warnings = []
    def load(summary):
        try:
            return normalize(request(f'https://pub.orcid.org/v3.0/{oid}/work/{summary["put-code"]}'), oid)
        except Exception:
            warnings.append(str(summary['put-code']))
            return normalize(summary, oid)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(load, summaries))
    unique = {item['id']: item for item in records}
    return {'orcid': oid, 'name': display, 'works': sorted(unique.values(), key=lambda x: (-x['year'], x['title'])),
            'warning': f'{len(warnings)} 条详情暂未取得，可稍后重试。' if warnings else ''}


def enrich(item):
    """Only fixed DOI resolver/Crossref endpoints, never fetch user-supplied PDF URLs."""
    doi = item.get('doi', '')
    if not isinstance(doi, str) or not re.fullmatch(r'10\.\d{4,9}/\S{1,500}', doi):
        return classify(fallback_bibtex(item))
    encoded = quote(doi, safe='')
    try:
        data = request('https://api.crossref.org/works/' + encoded)['message']
        if not item.get('authors'):
            item['authors'] = ', '.join(' '.join(filter(None, [a.get('given'), a.get('family')])) for a in data.get('author', []))
        if not item.get('venue'):
            item['venue'] = next(iter(data.get('container-title', [])), '')
        if not item.get('pdf_url'):
            item['pdf_url'] = next((x['URL'] for x in data.get('link', []) if x.get('content-type') == 'application/pdf' and x.get('URL', '').startswith('https://')), '')
    except Exception:
        pass
    if not item.get('bibtex'):
        try:
            item['bibtex'] = request('https://doi.org/' + encoded, 'application/x-bibtex')
        except Exception:
            pass
    return classify(fallback_bibtex(item))


def fallback_bibtex(item):
    if item.get('bibtex'):
        return item
    def escape(value):
        return str(value).replace('\\', r'\textbackslash{}').replace('{', r'\{').replace('}', r'\}').replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')
    kind = {'conference': 'inproceedings', 'journal': 'article'}.get(item.get('kind'), 'misc')
    fields = [('title', item.get('title')), ('author', item.get('authors', '').replace(', ', ' and ')),
              ('year', item.get('year')), ('booktitle' if kind == 'inproceedings' else 'journal', item.get('venue')),
              ('doi', item.get('doi')), ('url', item.get('url'))]
    item['bibtex'] = '@' + kind + '{zhige' + str(item.get('year', '')) + ',\n' + ',\n'.join('  ' + key + ' = {' + escape(value) + '}' for key, value in fields if value) + '\n}'
    item['bibtex_source'] = 'Generated from public metadata; please verify author names and fields.'
    return item


def validate_profile(person):
    oid = person.get('orcid', '')
    if oid:
        orcid_id(oid)
    works = person.get('publications', [])
    if not isinstance(works, list) or len(works) > 2000:
        raise ValueError('论文列表格式无效')
    ids = set()
    for item in works:
        for key in ('id', 'title', 'authors', 'venue', 'doi', 'url', 'pdf_url', 'bibtex'):
            value = item.get(key, '')
            if not isinstance(value, str) or len(value) > 100000:
                raise ValueError('论文字段无效：' + key)
        if not item.get('id') or item['id'] in ids or not item.get('title'):
            raise ValueError('论文编号重复或标题为空')
        ids.add(item['id'])
        if item.get('kind') not in KINDS or item.get('tier') not in TIERS or type(item.get('selected')) is not bool:
            raise ValueError('论文分类、层次或选择状态无效')
        if type(item.get('year')) is not int or not 1900 <= item['year'] <= 2200:
            raise ValueError('论文年份无效')
        for key in ('url', 'pdf_url'):
            if item.get(key) and not re.match(r'^https?://[^\s<>"\']+$', item[key]):
                raise ValueError('论文链接必须为 HTTP(S) 地址')
