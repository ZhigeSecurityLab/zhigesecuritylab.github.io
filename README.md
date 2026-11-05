# Zhige Security Lab · 止戈安全实验室

实验室双语主页，默认英文，中文位于 `/zh/`。公开网站为静态页面，无前端框架或外部字体依赖；构建时使用 Python 和 Markdown 渲染器。

## 可视化维护（推荐）

在 macOS 的 Finder 中双击仓库里的 **`Start Maintenance.command`**，会启动本地后台并打开浏览器。首次启动会自动准备 Python 虚拟环境和依赖。已有后台时会打开原来的后台。运行期间保留启动终端窗口；关闭服务可在该窗口按 `Ctrl+C`。

后台地址：`http://127.0.0.1:8001/`。它只接受本机访问，不随静态网站发布到 GitHub Pages；点击“发布到网站”后才会提交 GitHub 并部署。

1. 在左侧选择 **简介与首页、News、Publications、People、Recruitment、外观与字号或网站发布**。
2. 选择 **英文 EN** 或 **中文 ZH**，分别维护两种语言。切换模块或语言会保留尚未保存的修改。
3. 编辑内容后，点击右上角 **保存并更新预览**。保存成功后，下面的网站预览会刷新，原有 8000 端口的预览也会使用新内容。
4. 准备上线时，首次在“网站发布”连接 GitHub，然后点击“发布到网站”。后台会通过 HappyYoung8310 提交内容、头像与外观，并显示自动部署结果。

详细操作见 [MAINTENANCE.md](MAINTENANCE.md)。也可以手动启动：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/admin.py
```

## 日常维护

后台实际保存的是 **`content/site.json`**，也可直接在 GitHub 网页端编辑。`en` 与 `zh` 分别对应英文与中文，请同步更新。手动编辑 JSON 时使用英文双引号，最后一项后不要加逗号。

| 内容 | 字段 |
| --- | --- |
| 名称与简介 | 各语言的 `name`、`intro`、`about` |
| 所属学校／单位 | 各语言的 `institution`，显示在首页中英文名称后，留空隐藏 |
| 联系邮箱 | 顶层 `email`，留空隐藏联系栏目 |
| 研究方向描述 | 各语言的 `intro`、`about` |
| 新闻 | 各语言的 `news` 数组，日期降序 |
| 论文 | 各语言的 `publications` 数组，年份降序 |
| 成员 | 各语言的 `people` 数组，使用 `category` 指定分类 |
| 成员分类 | 顶层 `people_categories`，含中英文名称及页面路径 |
| 招募信息 | 各语言的 `recruitment`：标题、Markdown 正文、邮件按钮与显示开关 |

Publications、News 和 People 始终保留。内容为空时显示简短的待更新提示。People 菜单可展开分类，每类有独立页面；中文切换会保留当前分类。以下仅为字段示例，请确认真实资料后填写。

默认分类为 `faculty`（教师）、`postdocs`（博士后）、`phd`（博士生）、`masters`（硕士生）、`alumni`（毕业成员）。例如英文博士生页面为 `/people/phd/`，中文为 `/zh/people/phd/`。

新闻格式：
```json
{"date": "2026-11-05", "title": "新闻标题", "body_markdown": "支持 **Markdown** 正文。", "url": "https://example.org/news", "draft": true}
```

论文格式：
```json
{"year": 2026, "title": "论文标题", "authors": "作者列表", "venue": "会议或期刊", "url": "https://example.org/paper"}
```

成员格式：
```json
{"name": "姓名", "role": "身份或职务", "category": "phd", "avatar": "assets/people/上传后的文件名.jpg", "description": "可换行的介绍", "url": "https://example.org/profile"}
```

头像 `avatar` 是必填的本地图片路径，建议通过后台上传；教师与博士后可使用 `bio_markdown` 编写 Markdown 简介，其他成员用 `description` 编写多行纯文本。`url` 可以省略或留空，非空时用完整的 HTTP(S) 地址。邮箱不加 `mailto:`。成员的 `category` 必须与顶层 `people_categories` 中的一个 `id` 对应。增加分类时需同时填写中英文名称，`id` 使用小写英文字母、数字或连字符；构建时会自动生成对应页面。

## 本地预览

需要 Python 3.9+；构建与后台共用虚拟环境。

```sh
.venv/bin/python scripts/build.py
python3 -m http.server 8000 --directory _site --bind 127.0.0.1
```

打开 `http://127.0.0.1:8000/`。修改文件后重新构建并刷新。不要直接修改自动生成的 `_site/`。

## 首次发布

1. 把源码提交到 `ZhigeSecurityLab/zhigesecuritylab.github.io` 的 `main` 分支，保留隐藏目录 `.github`。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. **Actions → Deploy lab website → Run workflow** 触发首次发布，或推送新提交。
4. 工作流成功后访问 `https://zhigesecuritylab.github.io/`。

之后提交到 `main` 的修改将自动构建发布。需要审核时，用分支及 Pull Request 提交修改，由负责人检查合并。

## 文件结构

```text
content/site.json              中英文内容
assets/style.css               配色和响应式布局
assets/logo.jpg                用户提供的完整 Logo，同时用作网站图标
scripts/build.py               静态页面生成器
scripts/admin.py               本机维护服务
admin/                         维护后台界面，不会发布到公开网站
MAINTENANCE.md                 中文维护指南
Start Maintenance.command      macOS 双击启动入口
requirements.txt               构建依赖
.github/workflows/pages.yml    自动发布工作流
```

页眉使用用户提供的完整 Logo 图片 `assets/logo.jpg`，保持原始比例与颜色，日间／夜间共用同一张图片。更换 Logo 时替换该文件即可，网站图标和本地维护后台同步使用它。首页中英文名称分别追加对应语言的 `@ institution`，目前为 Southeast University／东南大学。导航中的 Contact Us／联系我们直接打开邮件客户端，收件人为 `content/site.json` 中的 `email`；首页联系栏目也显示该邮箱。页面支持记住偏好的日间／夜间模式，页脚显示不蒜子提供的全站浏览量，本地预览不计数。字体和 Logo 不依赖外部服务。更换域名时同步修改 `content/site.json` 的 `url`，并配置 GitHub Pages 自定义域名。

## 外观与按钮发布

在后台「外观与字号」调整正文、导航、首页标题、说明、People 标签、Markdown 正文、页脚字号、Logo 宽度和行距。中英文共用这些设置，手机端自动适配；预览栏可以选择首页／People 子页以及 375px 手机宽度。外观保存在 `content/site.json` 的 `appearance` 中；省略字段时使用推荐值。`assets/appearance.css` 是构建产物，不应手工编辑。

本机已在忽略目录 `.local/bin/gh` 安装官方 GitHub CLI。换电脑时可从 https://cli.github.com/ 安装 CLI。后台「网站发布 → 连接 GitHub」显示设备验证码；在 GitHub 页面输入验证码，核对账户、权限与组织访问后完成一次性授权。凭据由 GitHub CLI 管理，不发送到后台页面，不提交到仓库。后台只接受 HappyYoung8310 授权；账号应拥有组织仓库写入权限。连接成功后日常不需要命令行操作。

点击「发布到网站」会先保存当前修改，再提交 `content/site.json` 和所引用的成员头像到固定实验室仓库的 `main` 分支。界面分别显示提交、构建和部署结果，部署成功才显示「网站已更新」。远程内容发生变化时拒绝覆盖，本地修改与备份保留；请先由维护者合并远程内容。代码、Logo 替换及新功能仍需正常提交源码。

发布基线与上次结果保存在 `.local/publish-state.json`；该文件没有 GitHub token，不随网站发布。发布使用 GitHub 文件 SHA 校验，支持提交后的网络重试和部署失败重试。
