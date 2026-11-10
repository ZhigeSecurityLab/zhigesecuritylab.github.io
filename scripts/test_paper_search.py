import unittest
from unittest.mock import patch
import publications as p
class SearchTests(unittest.TestCase):
    def test_search_partial_failure_and_no_auto_publish(self):
        def request(url,accept='application/json'):
            if 'crossref' in url:return {'message':{'items':[{'DOI':'10.1234/a','title':['CompLeak: Example Paper'],'author':[{'given':'Yansong','family':'Gao'}],'container-title':['USENIX Security'],'type':'proceedings-article','published':{'date-parts':[[2026]]}}]}}
            raise OSError('source offline')
        with patch.object(p,'request',side_effect=request): result=p.search_title('CompLeak: Example Paper')
        self.assertEqual(len(result['results']),1)
        item=result['results'][0]
        self.assertEqual(item['tier'],'A');self.assertFalse(item['selected']);self.assertTrue(item['bibtex']);self.assertEqual(item['pdf_url'],'')
        self.assertIn('暂不可用',result['warning'])
    def test_arxiv_preprint_not_claimed_conference(self):
        text='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2507.16872v1</id><title>CompLeak</title><published>2025-07-22</published><author><name>Na Li</name></author></entry></feed>'''
        item=p.arxiv_records(text)[0]
        self.assertEqual(item['kind'],'other');self.assertEqual(item['tier'],'Unrated');self.assertEqual(item['pdf_url'],'https://arxiv.org/pdf/2507.16872v1')
    def test_duplicate_and_distinct_published_dois(self):
        self.assertTrue(p.same_work({'title':'CompLeak: Test'},{'title':'Compleak Test'}))
        self.assertFalse(p.same_work({'title':'Same','doi':'10.1/a'},{'title':'Same','doi':'10.1/b'}))
    def test_title_bounds(self):
        for title in [None,'ab','x'*501]:
            with self.assertRaises(ValueError):p.search_title(title)

    def test_official_usenix_metadata_and_preprint_are_distinct(self):
        html='<meta name="citation_title" content="{CompLeak}: Example"><meta name="citation_author" content="Na Li"><meta name="citation_author" content="Yansong Gao"><meta name="citation_publication_date" content="2026"><meta name="citation_conference_title" content="35th USENIX Security Symposium (USENIX Security 26)"><meta name="citation_pdf_url" content="https://www.usenix.org/system/files/usenixsecurity26-li-na.pdf"><div class="bibtex-text-entry">@inproceedings {x,<br>title={CompLeak}, year={2026}}</div><p>Distinguished Artifact Award Winner</p>'
        official=p.usenix_record(html,'https://www.usenix.org/conference/usenixsecurity26/presentation/li-na')
        self.assertEqual(official['tier'],'A');self.assertEqual(official['year'],2026)
        self.assertEqual(official['award'],'Distinguished Artifact Award');self.assertIn('@inproceedings',official['bibtex'])
        def request(url,accept='application/json'):
            if '/search/site/' in url:return '<a href="/conference/usenixsecurity26/presentation/li-na">CompLeak</a>'
            if '/presentation/' in url:return html
            if 'crossref' in url:return {'message':{'items':[]}}
            if 'openalex' in url:return {'results':[]}
            raise OSError('offline')
        with patch.object(p,'request',side_effect=request): result=p.search_title('CompLeak: Example')
        self.assertEqual(result['results'][0]['search_source'],'USENIX official')
        self.assertEqual(result['results'][0]['pdf_url'],'https://www.usenix.org/system/files/usenixsecurity26-li-na.pdf')

    def test_split_title_and_subtitle_are_combined(self):
        paper=p.crossref_record({'DOI':'10.1145/3359789.3359790','title':['STRIP'],'subtitle':['a defence against trojan attacks on deep neural networks'],'type':'proceedings-article','published':{'date-parts':[[2019]]}})
        self.assertEqual(paper['title'],'STRIP: a defence against trojan attacks on deep neural networks')

    def test_verified_index_recovers_all_audited_titles_without_prefilling_profiles(self):
        import json
        cache=json.loads((p.DATA_ROOT/'content/publication-search-cache.json').read_text())
        self.assertEqual(len(cache['works']),12)
        with patch.object(p,'request',side_effect=OSError('network unavailable')):
            for expected in cache['works']:
                with self.subTest(title=expected['title']):
                    result=p.search_title(expected['title'])
                    matching=[w for w in result['results'] if p.title_key(w['title'])==p.title_key(expected['title']) and w['year']==expected['year']]
                    self.assertTrue(matching)
                    self.assertFalse(matching[0]['selected'])
                    self.assertTrue(matching[0]['bibtex'])
                    self.assertIn('verified cache',matching[0]['search_source'])
