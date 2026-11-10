"""Bilingual static site generator with Markdown news support; Python 3.9+."""
import publications
from pathlib import Path
from html import escape
from urllib.parse import urlsplit, quote
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date
from markdown_it import MarkdownIt
from appearance import settings as appearance_settings, stylesheet as appearance_stylesheet

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
MARKDOWN = MarkdownIt("js-default")


def validate(data):
    """Shared validation for the editor and CI builds."""
    appearance_settings(data)
    def string(value, field, required=False):
        if not isinstance(value, str) or len(value) > 100000 or (required and not value.strip()):
            raise ValueError(f"{field}: 请填写有效文字")
    for field in ("url", "github"):
        string(data[field], field, True)
        link(data[field])
    email = data["email"]
    string(email, "email")
    if email and (any(c.isspace() or c in '?&<>"' for c in email) or email.count('@') != 1 or not all(email.split('@'))):
        raise ValueError("联系邮箱格式无效")
    groups = data["people_categories"]
    if not isinstance(groups, list) or not groups:
        raise ValueError("至少保留一个成员分类")
    slugs = []
    for group in groups:
        slug = group["id"]
        string(slug, "category id", True)
        if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug):
            raise ValueError("分类 id 只允许小写字母、数字、连字符")
        slugs.append(slug)
        for lang in ("en", "zh"):
            string(group[lang], "分类名称", True)
    if len(slugs) != len(set(slugs)):
        raise ValueError("分类 id 不能重复")
    for lang in ("en", "zh"):
        t = data[lang]
        profile_owners = set()
        for field in ("name", "other_name", "institution", "eyebrow", "intro", "about"):
            string(t[field], f"{lang}.{field}", field == "name")
        recruitment = t.get("recruitment")
        if recruitment is not None:
            if not isinstance(recruitment, dict) or not isinstance(recruitment.get("enabled", True), bool):
                raise ValueError("加入我们模块格式无效")
            for field in ("title", "body_markdown", "cta_label", "email_subject"):
                string(recruitment.get(field, ""), f"{lang}.recruitment.{field}", recruitment.get("enabled", True) and field in ("title", "body_markdown"))
        for key in ("news", "publications", "people"):
            if not isinstance(t[key], list) or len(t[key]) > 5000:
                raise ValueError(f"{lang}.{key}: 列表格式无效")
            for item in t[key]:
                if item.get("url"):
                    string(item["url"], "链接")
                    link(item["url"])
                if key == "news":
                    if date.fromisoformat(item["date"]).isoformat() != item["date"]:
                        raise ValueError("新闻日期应为 YYYY-MM-DD")
                    string(item.get("title", item.get("text", "")), "新闻标题", True)
                    string(item.get("body_markdown", ""), "Markdown 正文")
                    if not isinstance(item.get("draft", False), bool):
                        raise ValueError("草稿状态格式无效")
                elif key == "publications":
                    for field in ("title", "authors", "venue"):
                        string(item[field], field, field == "title")
                    if type(item["year"]) is not int or not 1900 <= item["year"] <= 2200:
                        raise ValueError("论文年份应为 1900–2200")
                else:
                    string(item["name"], "成员姓名", True)
                    string(item["role"], "成员身份")
                    if item["category"] not in slugs:
                        raise ValueError("成员分类不存在")
                    owner = item.get("github_username", "")
                    if owner:
                        if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner) or owner.lower() in profile_owners:
                            raise ValueError("成员 GitHub 用户名无效或重复")
                        profile_owners.add(owner.lower())
                    avatar = item.get("avatar", "")
                    defaults = {"assets/people/default-male.svg", "assets/people/default-female.svg"}
                    if not isinstance(avatar, str) or (avatar not in defaults and not re.fullmatch(r"assets/people/[a-zA-Z0-9_-]+\.(?:jpg|png|webp)", avatar)):
                        raise ValueError("请上传成员头像")
                    if not (ROOT / avatar).is_file():
                        raise ValueError("成员头像文件不存在：" + avatar)
                    string(item.get("bio_markdown", ""), "成员 Markdown 简介")
                    string(item.get("description", ""), "成员描述")
                    publications.validate_profile(item)


def e(value):
    return escape(str(value), quote=True)


def link(value):
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError(f"Expected an absolute HTTP(S) URL: {value!r}")
    return e(value)


def labels(lang):
    return dict(zip(("home", "publications", "people", "news", "contact"),
                    ("首页", "学术论文", "实验室成员", "最新动态", "联系我们") if lang == "zh" else
                    ("Home", "Publications", "People", "News", "Contact Us")))


def empty(message):
    return f'<p class="empty-state">{e(message)}</p>'


def news_list(data, lang):
    rows = ""
    for item in sorted((entry for entry in data[lang]["news"] if not entry.get("draft", False)),
                       key=lambda entry: entry["date"], reverse=True):
        title = e(item.get("title", item.get("text", "")))
        if item.get("url"):
            title = f'<a href="{link(item["url"])}">{title}</a>'
        body = MARKDOWN.render(item.get("body_markdown", ""))
        rows += f'<li class="news-row"><time datetime="{e(item["date"])}">{e(item["date"])}</time><article><h3>{title}</h3><div class="markdown-body">{body}</div></article></li>'
    return f'<ul class="plain-list">{rows}</ul>' if rows else empty("最新动态待更新。" if lang == "zh" else "News and updates will be added.")


def publication_list(items, lang):
    selected = [publications.classify(dict(p)) for p in items if p.get("selected")]
    if not selected:
        return ""
    result = '<div class="faculty-publications">'
    for kind, title in (("conference", "会议论文" if lang == "zh" else "Conference Papers"), ("journal", "期刊论文" if lang == "zh" else "Journal Articles"), ("other", "其他成果" if lang == "zh" else "Other Works")):
        group = [p for p in selected if p.get("kind", "other") == kind]
        if not group:
            continue
        result += f'<h2>{title}</h2>'
        for tier in publications.TIERS:
            papers = [p for p in group if p.get("tier", "Unrated") == tier]
            if not papers:
                continue
            label = ("CCF 待核验" if lang == "zh" else "CCF unverified") if tier == "Unrated" else f'CCF {tier} · 2026'
            result += f'<h3>{label}</h3><ul class="plain-list">'
            for p in sorted(papers, key=lambda x: (-x["year"], x["title"])):
                title = e(p["title"])
                if p.get("url"):
                    title = f'<a href="{link(p["url"])}">{title}</a>'
                actions = f'<a href="{link(p["pdf_url"])}" target="_blank" rel="noopener">PDF ↗</a>' if p.get("pdf_url") else '<span class="muted">PDF ' + ("待补充" if lang == "zh" else "unavailable") + '</span>'
                if p.get("bibtex"):
                    actions += f'<a download="citation.bib" href="data:application/x-bibtex;charset=utf-8,{quote(p["bibtex"], safe="")}">BibTeX ↓</a><details><summary>View BibTeX</summary><pre><code>{e(p["bibtex"])}</code></pre></details>'
                else:
                    actions += '<span class="muted"> · BibTeX ' + ("待补充" if lang == "zh" else "unavailable") + '</span>'
                award = f'<p class="publication-award">{e(p.get("award", ""))}</p>' if p.get("award") else ""
                result += f'<li class="publication"><h3>{title}</h3>{award}<p>{e(p.get("authors", ""))}</p><p class="muted">{e(p.get("venue", ""))} · {p["year"]}</p><div class="publication-actions">{actions}</div></li>'
            result += '</ul>'
    return result + '</div>'


def members(data, lang, category):
    items = [person for person in data[lang]["people"] if person["category"] == category]
    if not items:
        return empty("成员信息待更新。" if lang == "zh" else "Member information will be added.")
    rows = ""
    for person in items:
        name = e(person["name"])
        if person.get("url"):
            name = f'<a href="{link(person["url"])}">{name}</a>'
        rich = category in ("faculty", "postdocs")
        description = (f'<div class="markdown-body">{MARKDOWN.render(person.get("bio_markdown", ""))}</div>'
                       if rich else f'<p class="person-description">{e(person.get("description", ""))}</p>')
        orcid = person.get("orcid", "")
        identity = f'<p><a href="https://orcid.org/{e(orcid)}" target="_blank" rel="noopener">ORCID: {e(orcid)}</a></p>' if orcid else ''
        papers = publication_list(person.get("publications", []), lang) if rich else ''
        rows += f'<li class="person"><img class="person-avatar" src="/{e(person["avatar"])}" alt="" loading="lazy"><div><h3>{name}</h3><p class="muted">{e(person["role"])}</p>{identity}{description}{papers}</div></li>'
    return f'<ul class="plain-list people-list">{rows}</ul>'


def home_content(data, lang):
    t = data[lang]
    zh = lang == "zh"
    names = labels(lang)
    institution = f' <span class="affiliation">@ {e(t["institution"])}</span>' if t["institution"] else ""
    other = data['en' if zh else 'zh']
    other_institution = f' <span class="affiliation">@ {e(other["institution"])}</span>' if other['institution'] else ""
    result = f'''<section id="about" class="intro-section">
      <p class="eyebrow">{e(t['eyebrow'])}</p><h1>{e(t['name'])}{institution}</h1><p class="other-name">{e(t['other_name'])}{other_institution}</p>
      <p class="intro">{e(t['intro'])}</p><p class="about-copy">{e(t['about'])}</p>
    </section>'''

    return result + f'<section id="news" class="section"><h2>{names["news"]}</h2>{news_list(data, lang)}</section>'


def section_content(data, lang, page):
    t = data[lang]
    zh = lang == "zh"
    names = labels(lang)
    label = ("加入我们" if zh else "Recruitment") if page == "recruitment" else names[page]
    result = f'<div class="page-heading"><a class="back-link" href="../">← {"返回首页" if zh else "Back to home"}</a><p class="eyebrow">ZHIGE SECURITY LAB</p><h1>{e(label)}</h1></div>'
    if page == "news":
        return result + f'<section id="news" class="section">{news_list(data, lang)}</section>'
    recruitment = t.get("recruitment", {})
    if page == "recruitment" and recruitment and recruitment.get("enabled", True):
        contact = ""
        if data["email"]:
            subject = quote(recruitment.get("email_subject", ""), safe="")
            cta = recruitment.get("cta_label") or ("邮件咨询" if zh else "Get in touch")
            contact = f'<a class="recruitment-cta" href="mailto:{e(data["email"])}?subject={subject}">{e(cta)} <span aria-hidden="true">↗</span></a>'
        result += f'<section id="recruitment" class="section recruitment-section"><div class="markdown-body recruitment-copy">{MARKDOWN.render(recruitment["body_markdown"])}</div>{contact}</section>'
    if page == "publications":
        works = list(t["publications"])
        for person in t["people"]:
            works.extend(p for p in person.get("publications", []) if p.get("selected"))
        seen = set()
        unique = []
        for paper in works:
            key = paper.get("doi") or paper.get("id") or paper["title"].casefold()
            if key not in seen:
                seen.add(key)
                unique.append(dict(paper, selected=True))
        result += publication_list(unique, lang) or empty("论文信息待更新。" if zh else "Publication information will be added.")
    if page == "contact" and data["email"]:
        email = data["email"]
        if any(c in email for c in "\r\n?&") or "@" not in email:
            raise ValueError("Invalid contact email")
        result += f'<section id="contact" class="section"><h2>{names["contact"]}</h2><a href="mailto:{e(email)}">{e(email)}</a></section>'
    return result


def people_content(data, lang, category):
    zh = lang == "zh"
    groups = data["people_categories"]
    selected = next((group for group in groups if group["id"] == category), None)
    title = selected[lang] if selected else labels(lang)["people"]
    home_prefix = "../../" if category else "../"
    all_people = "../" if category else "./"
    tabs = f'<a href="{all_people}"' + (' aria-current="page"' if not category else '') + f'>{"全部成员" if zh else "All people"}</a>'
    for group in groups:
        href = ("../" if category else "") + group["id"] + "/"
        current = ' aria-current="page"' if category == group["id"] else ''
        tabs += f'<a href="{href}"{current}>{e(group[lang])}</a>'
    back_label = "返回首页" if zh else "Back to home"
    description = "按成员类别浏览实验室。" if zh else "Explore the lab by member category."
    result = f'''<div class="page-heading"><a class="back-link" href="{home_prefix}">← {back_label}</a>
      <p class="eyebrow">ZHIGE SECURITY LAB</p><h1>{e(title)}</h1><p class="section-description">{description}</p></div>
      <nav class="people-tabs" aria-label="{'成员分类' if zh else 'People categories'}">{tabs}</nav>'''
    for group in groups:
        if selected and group["id"] != category:
            continue
        heading = ("成员" if zh else "Members") if selected else e(group[lang])
        if not selected:
            heading = f'<a href="{group["id"]}/">{heading} <span aria-hidden="true">↗</span></a>'
        result += f'<section class="section people-group" id="{group["id"]}"><h2>{heading}</h2>{members(data, lang, group["id"])}</section>'
    return result


def render(data, lang, page="home", category=None):
    t = data[lang]
    zh = lang == "zh"
    names = labels(lang)
    subpath = "" if page == "home" else ("people/" + (category + "/" if category else "") if page == "people" else page + "/")
    prefix = "../" * (subpath.count("/") + int(zh))
    local_home = "../" * subpath.count("/") or "./"
    base = data["url"].rstrip("/")
    en_path = subpath
    zh_path = "zh/" + subpath
    canonical_path = zh_path if zh else en_path
    switch_path = en_path if zh else zh_path
    title = t["name"] if page == "home" else (labels(lang)["people"] if page == "people" else ("加入我们" if zh else "Recruitment") if page == "recruitment" else names[page])
    if category:
        title = next(group[lang] for group in data["people_categories"] if group["id"] == category)
    document_title = f'{title} | {t["other_name"] if page == "home" else t["name"]}'
    menu = f'<a href="{local_home}"' + (' aria-current="page"' if page == "home" else '') + f'>{names["home"]}</a>'
    menu += f'<a href="{local_home}news/"' + (' aria-current="page"' if page == "news" else '') + f'>{names["news"]}</a>'
    if t.get("recruitment") and t["recruitment"].get("enabled", True):
        menu += f'<a href="{local_home}recruitment/"' + (' aria-current="page"' if page == "recruitment" else '') + f'>{"加入我们" if zh else "Recruitment"}</a>'
    menu += f'<a href="{local_home}publications/"' + (' aria-current="page"' if page == "publications" else '') + f'>{names["publications"]}</a>'
    people_home = local_home + "people/"
    submenu = f'<a href="{people_home}">{"全部成员" if zh else "All people"}</a>'
    submenu += "".join(f'<a href="{people_home}{g["id"]}/">{e(g[lang])}</a>' for g in data["people_categories"])
    menu += f'<details class="people-menu"><summary>{names["people"]}</summary><div class="people-submenu">{submenu}</div></details>'
    if data["email"]:
        menu += f'<a href="{local_home}contact/"' + (' aria-current="page"' if page == "contact" else '') + f'>{names["contact"]}</a>'
    content = home_content(data, lang) if page == "home" else people_content(data, lang, category) if page == "people" else section_content(data, lang, page)
    return f'''<!doctype html>
<html lang="{'zh-CN' if zh else 'en'}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(document_title)}</title><meta name="description" content="{e(t['intro'])}"><meta name="theme-color" content="#ffffff">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(t['intro'])}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(base + '/' + canonical_path)}">
<link rel="canonical" href="{e(base + '/' + canonical_path)}">
<link rel="alternate" hreflang="en" href="{e(base + '/' + en_path)}"><link rel="alternate" hreflang="zh-CN" href="{e(base + '/' + zh_path)}">
<link rel="alternate" hreflang="x-default" href="{e(base + '/' + en_path)}">
<link rel="icon" type="image/jpeg" href="{prefix}assets/logo.jpg"><script src="{prefix}assets/site.js"></script><link rel="stylesheet" href="{prefix}assets/style.css"><link rel="stylesheet" href="{prefix}assets/appearance.css">
</head><body>
<a class="skip-link" href="#main">{'跳转到正文' if zh else 'Skip to content'}</a>
<div class="site-shell"><aside class="sidebar">
<a class="brand" href="{local_home}" aria-label="Zhige Security Lab — 止戈安全实验室"><img class="brand-logo" src="{prefix}assets/logo.jpg" width="210" height="210" alt="止戈安全实验室 · Zhige Security Lab @ SEU"></a>
<nav class="main-nav" aria-label="{'主导航' if zh else 'Main navigation'}">{menu}</nav>
<div class="sidebar-bottom"><button type="button" class="theme-toggle" data-theme-toggle hidden><svg class="theme-icon-night" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M20.5 13.1A8.7 8.7 0 0 1 10.9 3.5 8.7 8.7 0 1 0 20.5 13.1Z"/></svg><svg class="theme-icon-day" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg><span data-theme-label>{'夜间模式' if zh else 'Night mode'}</span></button><a class="language-switch" href="{prefix}{switch_path or './'}" lang="{'en' if zh else 'zh-CN'}" hreflang="{'en' if zh else 'zh-CN'}">{'English' if zh else '中文'} <span aria-hidden="true">↗</span></a><a href="{link(data['github'])}">GitHub <span aria-hidden="true">↗</span></a></div>
</aside><main id="main">{content}
<footer><span>Zhige Security Lab <span class="footer-dot">·</span> 止戈安全实验室</span><div class="footer-meta"><span class="visit-counter" title="{'全站页面浏览次数，包含重复访问；由不蒜子提供统计' if zh else 'Total page views, including repeat visits; powered by Busuanzi'}">{'累计访问量' if zh else 'Site views'} <span id="busuanzi_value_site_pv" role="status" aria-live="polite">—</span></span><a href="{link(data['github'])}">GitHub ↗</a></div></footer>
</main></div></body></html>'''


def build(data=None, output=None):
    data = data if data is not None else json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
    validate(data)
    output = Path(output) if output is not None else OUT
    categories = [group["id"] for group in data["people_categories"]]
    if len(categories) != len(set(categories)) or any(not slug or not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug) for slug in categories):
        raise ValueError("Category ids must be unique lowercase URL slugs")
    pages = {}
    for lang in ("en", "zh"):
        for person in data[lang]["people"]:
            if person["category"] not in categories:
                raise ValueError(f'Unknown member category: {person["category"]}')
        prefix = "zh/" if lang == "zh" else ""
        pages[prefix + "index.html"] = render(data, lang)
        for section in ("news", "recruitment", "publications", "contact"):
            if section != "recruitment" or data[lang].get("recruitment", {}).get("enabled", True):
                pages[prefix + section + "/index.html"] = render(data, lang, section)
        pages[prefix + "people/index.html"] = render(data, lang, "people")
        for category in categories:
            pages[prefix + f"people/{category}/index.html"] = render(data, lang, "people", category)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    shutil.copytree(ROOT / "assets", output / "assets")
    (output / "assets/appearance.css").write_text(appearance_stylesheet(data), encoding="utf-8")
    for path, html in pages.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    (output / ".nojekyll").touch()
    (output / "404.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Page not found · Zhige Security Lab</title><body style="font-family:system-ui;max-width:40rem;margin:15vh auto;padding:2rem"><h1>Page not found / 页面未找到</h1><p><a href="/">English home</a> · <a href="/zh/">中文首页</a></p></body></html>', encoding="utf-8")
    base = data["url"].rstrip("/")
    (output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in pages:
        ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = base + "/" + path.removesuffix("index.html")
    ET.ElementTree(sitemap).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    print(f"Built {len(pages)} bilingual pages in {output}")


if __name__ == "__main__":
    build()
