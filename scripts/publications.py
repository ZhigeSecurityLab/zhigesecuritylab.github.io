"""Public ORCID import; no private credentials or automatic ownership claim."""
import concurrent.futures
import json
import re
import ssl
from urllib.request import Request, urlopen
from urllib.parse import quote
import certifi
from ccf import classify, ROOT as DATA_ROOT

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
    with urlopen(Request(url, headers={'Accept': accept, 'User-Agent': 'ZhigeFacultyEditor/1.2 (public academic metadata)'}), timeout=12 if url.startswith("https://www.usenix.org/") else 25, context=CONTEXT) as response:
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
    if not item.get('bibtex') or item.get('bibtex_source'):
        try:
            item['bibtex'] = request('https://doi.org/' + encoded, 'application/x-bibtex')
            item.pop('bibtex_source', None)
        except Exception:
            pass
    return classify(fallback_bibtex(item))


def fallback_bibtex(item):
    if item.get('bibtex'):
        return item
    def escape(value):
        return str(value).replace('\\', r'\textbackslash{}').replace('{', r'\{').replace('}', r'\}').replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')
    kind = {'conference': 'inproceedings', 'journal': 'article'}.get(item.get('kind'), 'misc')
    fields = [('title', item.get('title')), ('author', item.get('authors_bibtex') or item.get('authors', '').replace(', ', ' and ')),
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


def title_key(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def same_work(left, right):
    if left.get('doi') and right.get('doi'):
        return left['doi'].casefold() == right['doi'].casefold()
    return bool(title_key(left.get('title'))) and title_key(left.get('title')) == title_key(right.get('title'))


def crossref_record(work):
    doi = work.get('DOI', '').lower()
    year = next((work[key]['date-parts'][0][0] for key in ('published', 'issued', 'published-print', 'published-online') if work.get(key, {}).get('date-parts')), 1900)
    return classify({'id': 'doi:' + doi, 'title': next(iter(work.get('title', [])), '') + (': ' + work['subtitle'][0] if work.get('subtitle') and work['subtitle'][0] else ''),
        'authors': ', '.join(' '.join(filter(None, [a.get('given'), a.get('family')])) for a in work.get('author', [])),
        'authors_bibtex': ' and '.join(' '.join(filter(None, [a.get('given'), a.get('family')])) for a in work.get('author', [])),
        'venue': next(iter(work.get('container-title', [])), ''), 'year': year,
        'kind': {'proceedings-article':'conference', 'journal-article':'journal'}.get(work.get('type'), 'other'),
        'tier':'Unrated', 'doi':doi, 'url':'https://doi.org/' + doi,
        'pdf_url':next((x['URL'] for x in work.get('link', []) if x.get('content-type') == 'application/pdf' and x.get('URL','').startswith('https://')), ''),
        'bibtex':'', 'selected':False, 'search_source':'Crossref'})


def arxiv_records(text):
    import xml.etree.ElementTree as ET
    ns={'a':'http://www.w3.org/2005/Atom'}
    root=ET.fromstring(text)
    result=[]
    for entry in root.findall('a:entry',ns):
        identifier=entry.findtext('a:id','',ns).rsplit('/',1)[-1]
        if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?',identifier):
            continue
        title=' '.join(entry.findtext('a:title','',ns).split())
        url='https://arxiv.org/abs/'+identifier
        item={'id':'arxiv:'+re.sub(r'v\d+$','',identifier),'title':title,
              'authors':', '.join(a.findtext('a:name','',ns) for a in entry.findall('a:author',ns)),
              'authors_bibtex':' and '.join(a.findtext('a:name','',ns) for a in entry.findall('a:author',ns)),
              'venue':'arXiv (preprint)', 'year':int(entry.findtext('a:published','1900',ns)[:4]),
              'kind':'other','tier':'Unrated','doi':'','url':url,'pdf_url':'https://arxiv.org/pdf/'+identifier,
              'bibtex':'','selected':False,'search_source':'arXiv'}
        result.append(classify(fallback_bibtex(item)))
    return result


def usenix_record(html, url):
    from html.parser import HTMLParser
    class Page(HTMLParser):
        def __init__(self):
            super().__init__(); self.meta={}; self.bib=[]; self.depth=0; self.text=[]
        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs)
            if tag=='meta' and attrs.get('name','').startswith('citation_'):
                self.meta.setdefault(attrs['name'],[]).append(attrs.get('content',''))
            if tag=='div':
                if self.depth:self.depth+=1
                elif 'bibtex-text-entry' in attrs.get('class',''):self.depth=1
            if tag=='br' and self.depth:self.bib.append('\n')
        def handle_endtag(self,tag):
            if tag=='div' and self.depth:self.depth-=1
        def handle_data(self,text):
            self.text.append(text)
            if self.depth:self.bib.append(text)
    page=Page();page.feed(html);meta=page.meta
    def first(key):return next(iter(meta.get('citation_'+key,[])),'')
    title=first('title').replace('{','').replace('}','')
    if not title or not first('conference_title'):raise ValueError('USENIX 页面缺少论文元数据')
    year_match=re.search(r'20\d{2}',first('publication_date'))
    if not year_match:raise ValueError('USENIX 论文年份缺失')
    item={'id':'usenix:'+url.split('/conference/',1)[-1], 'title':title,
          'authors':', '.join(meta.get('citation_author',[])),
          'authors_bibtex':' and '.join(meta.get('citation_author',[])),
          'venue':first('conference_title'),'year':int(year_match[0]),'kind':'conference','tier':'Unrated',
          'doi':first('doi'),'url':url,'pdf_url':first('pdf_url'),'bibtex':''.join(page.bib).strip(),
          'selected':False,'search_source':'USENIX official'}
    for label in ('Distinguished Artifact Award', 'Distinguished Paper Award', 'Honorable Mention Paper Award'):
        if label in ' '.join(page.text):
            item['award']=label
            item['award_source']=url
            break
    return classify(fallback_bibtex(item))


def search_usenix(query):
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urlsplit
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='a':
                url=urljoin('https://www.usenix.org',attrs.get('href',''))
                parts=urlsplit(url)
                if parts.hostname=='www.usenix.org' and re.fullmatch(r'/conference/[a-z0-9-]+/presentation/[a-zA-Z0-9_-]+',parts.path):
                    if url not in self.links:self.links.append(url)
    term=query.split(':',1)[0].strip()
    if len(term)<4:term=query
    try:
        html=request('https://www.usenix.org/search/site/'+quote(term,safe=''),'text/html')
    except Exception:
        html=''
    links=Links();links.feed(html)
    def load(url):
        try:return usenix_record(request(url,'text/html'),url)
        except Exception:return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        live = [item for item in pool.map(load,links.links[:6]) if item]
    # Search-only bibliographic cache, not prefilled profile content. Make provenance explicit.
    import difflib
    try:
        cache=json.loads((DATA_ROOT/'content/publication-search-cache.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        cache={'works':[]}
    for source in cache['works']:
        if not source.get('search_source','').startswith('USENIX official'):continue
        if difflib.SequenceMatcher(None,title_key(query),title_key(source['title'])).ratio() < .65:
            continue
        if any(same_work(source,item) for item in live):
            continue
        item=dict(source)
        item['search_source']='USENIX official (verified cache '+cache['checked']+')'
        item['source_checked']=cache['checked']
        item['source_warning']='USENIX 实时检索暂未返回此论文，使用已核对的官方元数据缓存；可点击来源复核。'
        live.append(classify(item))
    return live


def search_title(value):
    import difflib
    if not isinstance(value,str) or not 4 <= len(value.strip()) <= 500:
        raise ValueError('请输入 4–500 字符的论文标题')
    query=value.strip()
    warnings=[]
    def crossref():
        return [crossref_record(w) for w in request('https://api.crossref.org/works?rows=8&query.title='+quote(query,safe=''))['message']['items'] if w.get('DOI') and w.get('title')]
    def arxiv():
        terms=' AND '.join('ti:'+word for word in re.findall(r'[A-Za-z0-9]+',query)[:30])
        return arxiv_records(request('https://export.arxiv.org/api/query?max_results=8&search_query='+quote(terms,safe=''),'application/atom+xml'))
    def openalex():
        raw=request('https://api.openalex.org/works?per-page=8&search='+quote(query,safe=''))
        records=[]
        for w in raw.get('results',[]):
            loc=w.get('primary_location') or {};source=loc.get('source') or {};doi=(w.get('doi') or '').removeprefix('https://doi.org/').lower()
            pdf=next((l.get('pdf_url') for l in w.get('locations',[]) if l.get('pdf_url','') and l['pdf_url'].startswith('https://')), '')
            records.append(classify({'id':'doi:'+doi if doi else 'openalex:'+w['id'].rsplit('/',1)[-1],
                'title':w.get('display_name') or '', 'authors':', '.join(a['author']['display_name'] for a in w.get('authorships',[])),
                'authors_bibtex':' and '.join(a['author']['display_name'] for a in w.get('authorships',[])),
                'venue':source.get('display_name') or '', 'year':w.get('publication_year') or 1900,
                'kind': 'other' if w.get('type') in ('preprint','posted-content') else {'journal':'journal','conference':'conference'}.get(source.get('type'),'other'),
                'tier':'Unrated','doi':doi,'url':loc.get('landing_page_url') or w['id'],'pdf_url':pdf,'bibtex':'','selected':False,'search_source':'OpenAlex'}))
        return records
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(fn):name for name,fn in [('USENIX 官方',lambda: search_usenix(query)),('Crossref',crossref),('arXiv',arxiv),('OpenAlex',openalex)]}
        for future in concurrent.futures.as_completed(tasks):
            try:records.extend(future.result())
            except Exception:warnings.append(tasks[future]+' 暂不可用')
    try:
        cache=json.loads((DATA_ROOT/'content/publication-search-cache.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):cache={'works':[]}
    for source in cache['works']:
        if difflib.SequenceMatcher(None,title_key(query),title_key(source['title'])).ratio()<.85:continue
        previous=next((p for p in records if same_work(p,source) and p['kind']==source['kind']),None)
        if previous:
            for field in ('pdf_url','bibtex','award','award_source'):
                if not previous.get(field) and source.get(field):previous[field]=source[field]
            continue
        item=dict(source);item['search_source']=source.get('search_source','Verified source')+' (verified cache '+cache['checked']+')'
        item['source_checked']=cache['checked'];item['source_warning']='在线来源暂未返回此记录，使用已核对的元数据缓存；请通过来源链接复核。'
        records.append(classify(item))
    records.sort(key=lambda p:not p.get('search_source','').startswith('USENIX official'))
    candidates=[]
    q=title_key(query)
    for item in records:
        similarity=difflib.SequenceMatcher(None,q,title_key(item['title'])).ratio()
        if similarity < .45:continue
        item['title_similarity']=round(similarity*100)
        try:validate_profile({'publications':[item]})
        except (ValueError,TypeError):continue
        previous=next((p for p in candidates if same_work(p,item) and p['kind']==item['kind']),None)
        if previous:
            for field in ('pdf_url','authors','venue','doi'):
                if not previous.get(field) and item.get(field):previous[field]=item[field]
        else:candidates.append(item)
    candidates.sort(key=lambda p:(-p['title_similarity'],not p.get('search_source','').startswith('USENIX official'),p['kind']=='other',-p['year']))
    for item in candidates:
        fallback_bibtex(item)
    if any(p.get('source_warning') for p in candidates):
        warnings.append('部分结果来自已核对的元数据缓存，来源与核对日期已标明')
    return {'results':candidates[:12], 'warning':'；'.join(warnings), 'query':query}
