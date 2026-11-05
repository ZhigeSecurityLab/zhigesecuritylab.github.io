"""Integration checks use isolated content/output; real lab data is never modified."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import admin
from build import MARKDOWN, render, validate


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.original = json.loads(admin.CONTENT.read_text(encoding="utf-8"))
        self.patches = [patch.object(admin, key, value) for key, value in {
            "CONTENT": root / "site.json", "OUT": root / "_site",
            "LOCAL": root / "local", "BACKUPS": root / "local/backups",
        }.items()]
        for item in self.patches:
            item.start()
        admin.CONTENT.write_text(json.dumps(self.original), encoding="utf-8")

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_save_builds_and_backs_up_without_losing_content(self):
        before = admin.CONTENT.read_bytes()
        draft = copy.deepcopy(self.original)
        draft['en']['intro'] = 'Updated introduction.'
        result = admin.save(draft, admin.revision(before))
        self.assertEqual(result['data'], draft)
        self.assertEqual(len(list(admin.OUT.rglob('index.html'))), 14)
        self.assertIn('Updated introduction.', (admin.OUT / 'index.html').read_text())
        self.assertEqual((admin.BACKUPS / result['backups'][0]).read_bytes(), before)
        self.assertFalse((admin.OUT / 'admin').exists())

    def test_conflict_cannot_overwrite_newer_edits(self):
        before = admin.CONTENT.read_bytes()
        with self.assertRaises(RuntimeError):
            admin.save(self.original, 'outdated-revision')
        self.assertEqual(before, admin.CONTENT.read_bytes())

    def test_invalid_content_cannot_replace_current_files(self):
        before = admin.CONTENT.read_bytes()
        invalid = copy.deepcopy(self.original)
        invalid['email'] = 'bad?@example.org'
        with self.assertRaises(ValueError):
            admin.save(invalid, admin.revision(before))
        self.assertEqual(admin.CONTENT.read_bytes(), before)
        self.assertFalse(admin.BACKUPS.exists())

    def test_news_markdown_drafts_and_legacy_text(self):
        data = copy.deepcopy(self.original)
        data['en']['news'] = [
            {'title':'Visible news', 'date':'2026-11-05', 'body_markdown':'**Strong**\n\n- One\n- Two\n\n[Paper](https://example.org)'},
            {'title':'Hidden draft', 'date':'2026-11-05', 'body_markdown':'Never published', 'draft':True},
            {'text':'Legacy news', 'date':'2026-11-04'},
        ]
        validate(data)
        html = render(data, 'en')
        self.assertIn('<strong>Strong</strong>', html)
        self.assertIn('<li>One</li>', html)
        self.assertIn('Legacy news', html)
        self.assertNotIn('Hidden draft', html)
        self.assertNotIn('Never published', html)

    def test_markdown_cannot_execute_raw_html_or_script_links(self):
        html = MARKDOWN.render('<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n<img src=x onerror=alert(1)>')
        self.assertNotIn('<script', html)
        self.assertNotIn('<img', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn('&lt;script&gt;', html)

    def test_recruitment_renders_markdown_and_email_in_both_languages(self):
        for language in ('en', 'zh'):
            html = render(self.original, language)
            self.assertIn('id="recruitment"', html)
            self.assertIn('href="./#recruitment"', html)
            self.assertIn('class="recruitment-cta"', html)
            self.assertIn('mailto:zhige.sec.lab@hotmail.com?subject=%5BZhige%20Lab%5D', html)
            self.assertIn('<strong>', html)
        self.assertIn('Research Assistants', render(self.original, 'en'))
        self.assertIn('科研助理', render(self.original, 'zh'))

    def test_recruitment_can_be_hidden_and_old_content_remains_valid(self):
        data = copy.deepcopy(self.original)
        data['en']['recruitment']['enabled'] = False
        html = render(data, 'en')
        self.assertNotIn('id="recruitment"', html)
        self.assertNotIn('#recruitment', html)
        for language in ('en', 'zh'):
            data[language].pop('recruitment', None)
        validate(data)
        self.assertNotIn('id="recruitment"', render(data, 'zh'))

    def test_http_save_restore_and_request_guards(self):
        with patch.object(admin.Handler, 'log_message', lambda *args: None):
            server = admin.ThreadingHTTPServer(('127.0.0.1', 0), admin.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            def post(path, body, headers=None):
                request = Request(base + path, data=json.dumps(body).encode(), method='POST', headers=headers or {'Content-Type':'application/json', 'X-Editor-Token':admin.TOKEN})
                return json.load(urlopen(request))
            try:
                state = json.load(urlopen(base + '/api/state'))
                with self.assertRaises(HTTPError) as rejected:
                    post('/api/save', {'data':self.original,'revision':state['revision']}, {'Content-Type':'application/json'})
                self.assertEqual(rejected.exception.code, 403)
                with self.assertRaises(HTTPError) as rejected:
                    post('/api/markdown', {'markdown':'hello'}, {'Content-Type':'application/json', 'X-Editor-Token':admin.TOKEN, 'Origin':'https://other.example'})
                self.assertEqual(rejected.exception.code, 403)
                self.assertEqual(post('/api/markdown', {'markdown':'**hello**'})['html'], '<p><strong>hello</strong></p>\n')
                data = copy.deepcopy(self.original)
                data['en']['intro'] = 'Changed via HTTP.'
                saved = post('/api/save', {'data':data,'revision':state['revision']})
                self.assertEqual(urlopen(base + '/preview/assets/logo.svg').status, 200)
                self.assertEqual(urlopen(base + '/assets/logo.svg').status, 200)
                restored = post('/api/restore', {'backup':saved['backups'][0], 'revision':saved['revision']})
                self.assertEqual(restored['data'], self.original)
                self.assertEqual(len(restored['backups']), 2)
                with self.assertRaises(HTTPError) as rejected:
                    urlopen(base + '/preview/%2e%2e/site.json')
                self.assertEqual(rejected.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
