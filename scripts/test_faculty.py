"""Profile-scoped edits and publishing are checked without contacting GitHub."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import faculty


class FacultyEditorTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(subprocess.check_output(["git", "show", "HEAD:content/site.json"], cwd=faculty.ROOT))

    def submitted(self, avatar="assets/people/example.png"):
        return {"avatar": avatar,
                "en": {"name": "Example Name", "role": "Faculty", "url": "", "bio_markdown": "## Research\n\n**Secure systems**"},
                "zh": {"name": "示例姓名", "role": "教师", "url": "", "bio_markdown": "## 研究方向\n\n安全系统"}}

    def test_merge_changes_only_named_faculty_records(self):
        source = copy.deepcopy(self.data)
        source["en"]["people"].append({"name": "Another Member", "category": "faculty", "avatar": "assets/people/other.jpg"})
        merged = faculty.merge(source, self.submitted())
        self.assertEqual(merged["en"]["people"][0], source["en"]["people"][0])
        self.assertEqual(merged["en"]["people"][1]["github_username"], "garrisongys")
        self.assertEqual(merged["zh"]["people"][0]["name"], "示例姓名")
        self.assertEqual(merged["en"]["news"], source["en"]["news"])
        with self.assertRaises(ValueError):
            faculty.merge(source, {**self.submitted(), "news": []})

    def test_publish_merges_latest_remote_content_and_uploads_photo_first(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "assets/people/example.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"sample photo bytes")
            local = faculty.merge(self.data, self.submitted())
            content = root / "site.json"
            content.write_text(json.dumps(local))
            remote = copy.deepcopy(self.data)
            remote["en"]["news"].append({"title": "Remote news", "date": "2026-11-05"})
            file = {"sha": "old", "content": base64.b64encode(json.dumps(remote).encode()).decode()}
            with patch.object(faculty, "ROOT", root), patch.object(faculty.admin, "CONTENT", content), \
                 patch.object(faculty, "BASELINE", root / "baseline.json"), \
                 patch.object(faculty, "baseline_hash", return_value=faculty.profile_hash(remote)), \
                 patch.object(faculty, "connection", return_value={"connected": True}), \
                 patch.object(faculty.subprocess, "check_output", return_value="head"), \
                 patch.object(faculty, "gh") as gh:
                gh.side_effect = [file, FileNotFoundError(), {"commit": {"sha": "image"}}, {"commit": {"sha": "content"}}]
                result = faculty.publish_profile()
                uploaded = json.loads(base64.b64decode(gh.call_args_list[-1].args[1]["content"]))
        self.assertEqual(result["commit"], "content")
        self.assertEqual(uploaded["en"]["news"][-1]["title"], "Remote news")
        self.assertEqual(uploaded["en"]["people"][0]["github_username"], "garrisongys")
        self.assertEqual(uploaded["zh"]["people"][0]["avatar"], "assets/people/example.png")
