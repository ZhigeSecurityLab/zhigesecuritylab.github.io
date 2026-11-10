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
