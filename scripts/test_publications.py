import copy
import unittest
from unittest.mock import patch
import publications as p
from build import publication_list

class PublicationsTests(unittest.TestCase):
    def paper(self):
        return dict(id='doi:10.1234/test', title='<Security>', authors='A & B', venue='Test', year=2026, kind='conference', tier='A', doi='10.1234/test', url='https://doi.org/10.1234/test', pdf_url='https://example.org/paper.pdf', bibtex='@inproceedings{x, title={<Security>}}', selected=True)

    def test_orcid_checksum_and_url(self):
        self.assertEqual(p.orcid_id('https://orcid.org/0000-0001-6029-5064'), '0000-0001-6029-5064')
        for value in ('0000-0001-6029-5065', 'file:///etc/passwd', ''):
            with self.assertRaises(ValueError): p.orcid_id(value)

    def test_unsafe_fields_and_duplicate_ids_rejected(self):
        paper=self.paper()
        p.validate_profile({'publications':[paper]})
        for change in ({'pdf_url':'javascript:alert(1)'},{'selected':'yes'},{'year':True},{'tier':'CCF-A'}):
            with self.assertRaises(ValueError): p.validate_profile({'publications':[dict(paper,**change)]})
        with self.assertRaises(ValueError): p.validate_profile({'publications':[paper,paper]})

    def test_render_selected_only_groups_and_escape(self):
        output=publication_list([self.paper(),dict(self.paper(),selected=False,title='HIDDEN')],'en')
        self.assertIn('Conference Papers',output)
        self.assertIn('BibTeX',output)
        self.assertIn('paper.pdf',output)
        self.assertIn('&lt;Security&gt;',output)
        self.assertNotIn('HIDDEN',output)

    def test_no_pdf_fabrication(self):
        paper=self.paper();paper.update(pdf_url='',bibtex='')
        with patch.object(p,'request',side_effect=OSError('offline')):
            result=p.enrich(paper)
        self.assertEqual(result['pdf_url'],'')
        self.assertIn('PDF unavailable',publication_list([result],'en'))

    def test_normalization_and_dedup(self):
        summary={'put-code':1,'title':{'title':{'value':'Paper'}},'type':'journal-article','publication-date':{'year':{'value':'2025'}},'external-ids':{'external-id':[{'external-id-type':'doi','external-id-value':'10.1234/ABC'}]}}
        person={'name':{'given-names':{'value':'Yansong'},'family-name':{'value':'Gao'}}}
        with patch.object(p,'request',side_effect=lambda url: person if url.endswith('/person') else {'group':[{'work-summary':[summary]},{'work-summary':[summary]}]} if url.endswith('/works') else summary):
            result=p.sync('0000-0001-6029-5064')
        self.assertEqual(len(result['works']),1)
        self.assertEqual(result['works'][0]['kind'],'journal')
        self.assertFalse(result['works'][0]['selected'])
