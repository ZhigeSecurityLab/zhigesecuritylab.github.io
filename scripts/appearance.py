"""Validated appearance settings shared by the builder and local editor."""
FIELDS = {
    'body': ('正文', 18, 14, 26),
    'navigation': ('左侧导航', 18, 14, 26),
    'heading': ('首页主标题', 58, 32, 76),
    'subtitle': ('另一语言名称', 28, 18, 40),
    'eyebrow': ('页首关键词', 14, 10, 22),
    'description': ('说明与待更新文字', 18, 14, 26),
    'intro': ('首页主要简介', 22, 16, 30),
    'tabs': ('People 分类标签', 16, 12, 24),
    'markdown': ('News / Recruitment 正文', 17, 14, 26),
    'footer': ('页脚', 14, 12, 20),
    'logo': ('Logo 宽度', 210, 120, 240),
    'line_height': ('正文行距', 1.8, 1.4, 2.2),
}


def settings(data):
    raw = data.get('appearance', {})
    if not isinstance(raw, dict) or set(raw) - set(FIELDS):
        raise ValueError('外观设置格式无效')
    result = {}
    for key, (_, default, low, high) in FIELDS.items():
        value = raw.get(key, default)
        if type(value) not in (float, int) or not low <= value <= high:
            raise ValueError(f'外观设置 {key} 应在 {low}–{high} 之间')
        result[key] = value
    return result


def stylesheet(data):
    s = settings(data)
    return f'''/* Generated from content/site.json; edit in the local maintenance panel. */
body {{ font-size:{s['body']}px; line-height:{s['line_height']}; }}
.main-nav a,.people-menu summary {{ font-size:{s['navigation']}px; }}
h1 {{ font-size:clamp(36px,4.4vw,{s['heading']}px); }}
.other-name {{ font-size:{s['subtitle']}px; }}
.eyebrow {{ font-size:{s['eyebrow']}px; }}
.section-description,.empty-state,.about-copy {{ font-size:{s['description']}px; }}
.intro {{ font-size:{s['intro']}px; }}
.people-tabs a,.people-submenu a,.back-link {{ font-size:{s['tabs']}px; }}
.markdown-body {{ font-size:{s['markdown']}px; line-height:{s['line_height']}; }}
footer {{ font-size:{s['footer']}px; }}
.brand {{ max-width:100%; }}
.brand-logo {{ width:{s['logo']}px; max-width:100%; }}
@media(max-width:960px) {{ .brand-logo {{ width:min({s['logo']}px,180px); }} }}
@media(max-width:680px) {{
  .brand-logo {{ width:min({s['logo']}px,148px); }}
  .main-nav a,.people-menu summary {{ font-size:{max(14, s['navigation']-2)}px; }}
  h1 {{ font-size:clamp(28px,8.5vw,{max(32, s['heading']*0.83):g}px); }}
  .other-name {{ font-size:{max(18,s['subtitle']-5)}px; }}
  .eyebrow {{ font-size:{max(10,s['eyebrow']-2)}px; }}
  .intro {{ font-size:{max(16,s['intro']-2)}px; }}
  .about-copy {{ font-size:{max(14,s['description']-1)}px; }}
  footer {{ font-size:{max(12,s['footer']-1)}px; }}
}}
'''
