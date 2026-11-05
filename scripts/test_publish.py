"""Offline publishing checks; never write to the real GitHub repository."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publish
from appearance import settings, stylesheet


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(publish, 'LOCAL', Path(self.temp.name)),
                        patch.object(publish, 'STATE_FILE', Path(self.temp.name) / 'publish-state.json'),
                        patch.object(publish, 'JOB', {'state': 'idle'}),
                        patch.object(publish, 'LOGIN', {'state': 'idle'})]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_only_content_is_sent_with_expected_remote_sha(self):
        raw = b'{"appearance":{"body":20}}'
        with patch.object(publish, 'base_sha', return_value='old'), patch.object(publish, 'gh') as gh:
            gh.side_effect = [{'sha':'old'}, {'commit':{'sha':'new'}}]
            publish._publish(raw)
            args, payload = gh.call_args.args
            self.assertIn('/contents/content/site.json', args[3])
            self.assertEqual(payload['sha'], 'old')
            self.assertEqual(payload['branch'], 'main')
            self.assertEqual(base64.b64decode(payload['content']), raw)
            self.assertNotIn('token', payload)
            self.assertEqual(publish.JOB['state'], 'submitted')
            self.assertEqual(publish.load_record()['content_sha'], publish.blob_sha(raw))

    def test_remote_edit_cannot_be_overwritten(self):
        with patch.object(publish, 'base_sha', return_value='old'), patch.object(publish, 'gh', return_value={'sha':'someone-elses-edit'}) as gh:
            publish._publish(b'{"en":{"people":[]},"zh":{"people":[]}}')
            self.assertEqual(gh.call_count, 1)
            self.assertEqual(publish.JOB['state'], 'error')
            self.assertIn('其他人', publish.JOB['message'])
            self.assertFalse(publish.STATE_FILE.exists())

    def test_failed_put_does_not_advance_baseline_and_can_be_retried(self):
        with patch.object(publish, 'base_sha', return_value='old'), patch.object(publish, 'gh') as gh:
            gh.side_effect = [{'sha':'old'}, RuntimeError('network failed')]
            publish._publish(b'{"en":{"people":[]},"zh":{"people":[]},"x":1}')
            self.assertEqual(publish.JOB['state'], 'error')
            self.assertFalse(publish.STATE_FILE.exists())
            gh.side_effect = [{'sha':'old'}, {'commit':{'sha':'retry'}}]
            publish._publish(b'{"en":{"people":[]},"zh":{"people":[]},"x":1}')
            self.assertEqual(publish.JOB['commit'], 'retry')

    def test_same_content_does_not_create_duplicate_commit(self):
        raw = b'{"en":{"people":[]},"zh":{"people":[]}}'
        with patch.object(publish, 'gh') as gh:
            gh.side_effect = [{'sha':publish.blob_sha(raw)}, {'sha':'main-sha'}]
            publish._publish(raw)
            self.assertEqual(gh.call_count, 2)
            self.assertTrue(all('--method' not in c.args[0] for c in gh.call_args_list))
            self.assertEqual(publish.JOB['commit'], 'main-sha')

    def test_avatar_is_uploaded_before_content(self):
        avatar = 'assets/people/test-avatar.png'
        raw = json.dumps({'en':{'people':[{'avatar':avatar}]},'zh':{'people':[]}}).encode()
        image = Path(self.temp.name) / avatar
        image.parent.mkdir(parents=True)
        image.write_bytes(b'\x89PNG\r\n\x1a\nexample')
        with patch.object(publish, 'ROOT', Path(self.temp.name)), patch.object(publish, 'base_sha', return_value='old'), patch.object(publish, 'gh') as gh:
            gh.side_effect = [{'sha':'old'}, RuntimeError('404'), {'commit':{'sha':'image-commit'}}, {'commit':{'sha':'content-commit'}}]
            publish._publish(raw)
        self.assertEqual(publish.JOB['commit'], 'content-commit')
        self.assertIn('assets/people/test-avatar.png', gh.call_args_list[2].args[0][3])
        self.assertEqual(base64.b64decode(gh.call_args_list[2].args[1]['content']), image.read_bytes())

    def test_identical_content_can_retry_failed_deployment(self):
        raw = b'{"en":{"people":[]},"zh":{"people":[]}}'
        publish.save_record({'state':'deploy_error','commit':'main-sha','run_id':42})
        with patch.object(publish, 'gh') as gh:
            gh.side_effect = [{'sha':publish.blob_sha(raw)}, {'sha':'main-sha'}, {}]
            publish._publish(raw)
            self.assertIn('/actions/runs/42/rerun', gh.call_args.args[0][-1])
            self.assertEqual(publish.JOB['state'],'submitted')

    def test_overlapping_publish_is_rejected(self):
        for state in ('publishing', 'submitted'):
            publish.JOB['state'] = state
            with self.assertRaises(RuntimeError): publish.begin_publish(b'next')

    def test_deployment_only_reports_matching_workflow_and_success(self):
        publish.JOB.update(state='submitted',commit='expected',content_sha='blob')
        run={'id':12,'path':'.github/workflows/pages.yml','status':'completed','conclusion':'success','html_url':'https://github.com/example/actions/runs/12'}
        with patch.object(publish,'LAST_CHECK',float('-inf')), patch.object(publish,'urlopen') as opened:
            opened.return_value.read.return_value=json.dumps({'workflow_runs':[run]}).encode()
            result=publish.deployment()
        self.assertEqual(result['state'],'success')
        self.assertIn('head_sha=expected',opened.call_args.args[0].full_url)
        self.assertEqual(publish.load_record()['state'],'success')

    def test_appearance_rejects_css_injection_unknown_keys_and_invalid_ranges(self):
        for value in ({'body':'18px;display:none'}, {'body':100}, {'body':True}, {'body':float('nan')}, {'extra':20}):
            with self.assertRaises(ValueError): settings({'appearance':value})
        css=stylesheet({'appearance':{'body':20,'navigation':22}})
        self.assertIn('font-size:20px',css)
        self.assertIn('font-size:22px',css)
        self.assertIn('@media(max-width:680px)',css)


if __name__ == '__main__': unittest.main()
