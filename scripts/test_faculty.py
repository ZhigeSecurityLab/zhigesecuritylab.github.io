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
from build import validate


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
        self.assertEqual(next(p for p in merged["en"]["people"] if p["name"] == "Another Member"), source["en"]["people"][-1])
        self.assertEqual(next(p for p in merged["en"]["people"] if p.get("github_username") == "garrisongys")["name"], "Example Name")
        self.assertEqual(next(p for p in merged["zh"]["people"] if p.get("github_username") == "garrisongys")["name"], "示例姓名")
        self.assertEqual(merged["en"]["news"], source["en"]["news"])
        with self.assertRaises(ValueError):
            faculty.merge(source, {**self.submitted(), "news": []})

    def test_recruitment_can_be_edited_before_faculty_photo_exists(self):
        source = copy.deepcopy(self.data)
        recruitment = {lang: copy.deepcopy(source[lang]["recruitment"]) for lang in ("en", "zh")}
        recruitment["en"]["body_markdown"] += "\n\nNew details."
        merged = faculty.merge(source, recruitment=recruitment)
        self.assertEqual(merged["en"]["people"], source["en"]["people"])
        self.assertEqual(merged["en"]["news"], source["en"]["news"])
        self.assertIn("New details.", merged["en"]["recruitment"]["body_markdown"])

    def test_incomplete_faculty_can_be_built_as_local_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            (root / "assets/logo.jpg").write_bytes(b"preview image")
            with patch.object(faculty, "ROOT", root):
                draft = self.submitted(avatar="")
                draft["en"]["name"] = ""
                draft["zh"]["name"] = ""
                prepared = faculty.preview_profile(draft)
                merged = faculty.merge(self.data, prepared)
                self.assertEqual(prepared["avatar"], faculty.DRAFT_AVATAR)
                self.assertEqual(prepared["en"]["name"], faculty.DRAFT_NAMES["en"])
                self.assertTrue((root / faculty.DRAFT_AVATAR).is_file())
                self.assertIn("**Secure systems**", next(p for p in merged["en"]["people"] if p.get("github_username") == faculty.OWNER)["bio_markdown"])
                self.assertEqual(draft["avatar"], "")

    def test_student_editor_only_changes_its_own_profile_and_accepts_default_avatar(self):
        source = copy.deepcopy(self.data)
        submitted = {"category": "phd", "avatar": "assets/people/default-female.svg",
                     "en": {"name": "Student Test", "role": "PhD student", "url": "", "bio_markdown": "", "description": "First line\nSecond line"},
                     "zh": {"name": "测试学生", "role": "博士生", "url": "", "bio_markdown": "", "description": "第一行\n第二行"}}
        with patch.object(faculty, "STUDENT", True), patch.object(faculty, "OWNER", "student-example"):
            merged = faculty.merge(source, submitted)
            validate(merged)
            self.assertEqual(merged["en"]["people"][-1]["github_username"], "student-example")
            self.assertEqual(merged["en"]["people"][-1]["category"], "phd")
            self.assertEqual(merged["en"]["people"][-1]["description"], "First line\nSecond line")
            self.assertEqual(merged["en"]["recruitment"], source["en"]["recruitment"])
            with self.assertRaisesRegex(ValueError, "Recruitment"):
                faculty.merge(source, recruitment={lang: source[lang]["recruitment"] for lang in ("en", "zh")})

    def test_student_publish_with_default_avatar_only_updates_own_record(self):
        source = copy.deepcopy(self.data)
        submitted = {"category": "masters", "avatar": "assets/people/default-male.svg",
                     "en": {"name": "Student Test", "role": "Master's student", "url": "", "bio_markdown": "", "description": "Line one"},
                     "zh": {"name": "测试学生", "role": "硕士生", "url": "", "bio_markdown": "", "description": "第一行"}}
        with patch.object(faculty, "STUDENT", True), patch.object(faculty, "OWNER", "student-example"):
            local = faculty.merge(source, submitted)
            with tempfile.TemporaryDirectory() as temp:
                content = Path(temp) / "site.json"
                content.write_text(json.dumps(local))
                remote_file = {"sha": "old", "content": base64.b64encode(json.dumps(source).encode()).decode()}
                with patch.object(faculty.admin, "CONTENT", content), \
                     patch.object(faculty, "baseline_hash", side_effect=lambda scope: faculty.profile_hash(source) if scope == "profile" else faculty.recruitment_hash(source)), \
                     patch.object(faculty, "connection", return_value={"connected": True}), \
                     patch.object(faculty, "save_baseline"), patch.object(faculty, "gh") as gh:
                    gh.side_effect = [remote_file, {"commit": {"sha": "student-sha"}}]
                    result = faculty.publish_profile()
                    uploaded = json.loads(base64.b64decode(gh.call_args_list[-1].args[1]["content"]))
            self.assertEqual(result["commit"], "student-sha")
            self.assertEqual(gh.call_count, 2)
            self.assertEqual(uploaded["en"]["people"][-1]["category"], "masters")
            self.assertEqual(uploaded["en"]["recruitment"], source["en"]["recruitment"])

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
                 patch.object(faculty, "baseline_hash", side_effect=lambda scope: faculty.profile_hash(remote) if scope == "profile" else faculty.recruitment_hash(remote)), \
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

    def test_recruitment_only_publish_needs_no_photo_and_targets_test_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local = copy.deepcopy(self.data)
            local["en"]["recruitment"]["body_markdown"] += "\n\nTest update."
            content = root / "site.json"
            content.write_text(json.dumps(local))
            remote = copy.deepcopy(self.data)
            remote["en"]["news"].append({"title": "Other news", "date": "2026-11-05"})
            file = {"sha": "old", "content": base64.b64encode(json.dumps(remote).encode()).decode()}
            baseline = lambda scope: faculty.profile_hash(self.data) if scope == "profile" else faculty.recruitment_hash(self.data)
            with patch.object(faculty, "BRANCH", "faculty-editor-test"), patch.object(faculty.admin, "CONTENT", content), \
                 patch.object(faculty, "BASELINE", root / "baseline.json"), \
                 patch.object(faculty, "baseline_hash", side_effect=baseline), \
                 patch.object(faculty, "connection", return_value={"connected": True}), \
                 patch.object(faculty, "gh") as gh:
                gh.side_effect = [file, {"commit": {"sha": "test-content"}}]
                result = faculty.publish_profile()
                uploaded = json.loads(base64.b64decode(gh.call_args_list[-1].args[1]["content"]))
        self.assertEqual(result["branch"], "faculty-editor-test")
        self.assertEqual(gh.call_count, 2)
        self.assertEqual(gh.call_args_list[-1].args[1]["branch"], "faculty-editor-test")
        self.assertEqual(uploaded["en"]["news"][-1]["title"], "Other news")
        self.assertIn("Test update.", uploaded["en"]["recruitment"]["body_markdown"])
