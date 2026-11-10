# Faculty 与 Recruitment 资料维护

这是**本机运行**的专用编辑入口。正式模式只显示和保存 `garrisongys` 的 Faculty 资料及中英文 Recruitment；测试模式使用 `zhengfeiLian` 和独立测试分支。公开 GitHub Pages 只显示生成的网站，不运行编辑后台。网页界面不提供修改其他成员或其他网站栏目的操作；GitHub 账号本身的仓库权限仍由组织设置决定。

## 首次准备

1. 正式维护时用 `garrisongys` 登录 GitHub，确认自己对 `ZhigeSecurityLab/zhigesecuritylab.github.io` 有写入权限。
2. 下载或克隆[网站源码仓库](https://github.com/ZhigeSecurityLab/zhigesecuritylab.github.io)。后续每次编辑前，先从仓库的 `main` 分支更新本地副本，避免在旧资料上继续编辑。
3. 安装 Python 3.9+、[GitHub CLI](https://cli.github.com/) 和 Git。Windows 安装 Git for Windows 后，在命令提示符中确认 `git --version` 和 `gh --version` 均可运行。Windows 可以双击仓库中的 **Start Faculty Editor.bat**，macOS 可以双击 **Start Faculty Editor.command**；第一次启动会自动创建虚拟环境并安装 Python 依赖。Linux 可在仓库目录运行：

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python scripts/faculty.py --open
   ```

4. 打开 `http://127.0.0.1:8002/`。后台仅监听本机，不需要对外开放端口。

## 编辑与发布

1. 填写中英文姓名、职务；个人主页可留空。上传一张 JPEG、PNG 或 WebP 头像（最大 2.5 MB），中英文共用。
2. 在 English／中文之间切换，分别写 Markdown。可以点「在光标处插入模板」，再删改不适用的小节；已有文字不会被替换。模板不会自动发布。
3. Faculty 和 Recruitment 都有 Markdown 即时预览；Recruitment 会自动载入现有文案，也可以不填写 Faculty 而单独更新 Recruitment。点击「保存并更新本地预览」，再查看下方的完整页面；可切换英文、中文。Faculty 资料未填完整时仍可保存本地草稿并预览，空缺姓名与头像会显示临时占位；正式推送前须补齐中英文姓名和头像。
4. 首次发布时点击「连接 GitHub」，用 **garrisongys** 登录设备授权页并核对权限。授权信息由本机 GitHub CLI 保存，不放入仓库或网页源码。
5. 点击「推送到网站」。后台会从 GitHub 读取最新内容，只合并实际修改的 `garrisongys` Faculty 条目与 Recruitment 文案，必要时上传头像，并提交到 `main`。GitHub Actions 部署完成后，查看[英文 Faculty 页面](https://zhigesecuritylab.github.io/people/faculty/)或[中文 Faculty 页面](https://zhigesecuritylab.github.io/zh/people/faculty/)。

若提示线上资料已有变化，先更新本地仓库再重试，避免覆盖别人对该资料的修改。网站其他栏目不通过此入口编辑。

## 可修改的 Markdown 框架

```markdown
## Biography / 个人简介

在这里介绍研究经历和当前工作。

## Research Interests / 研究方向

- 研究方向一
- 研究方向二

## Selected Publications / 代表性论文

- [论文标题](https://example.org/paper) — 作者，会议或期刊，年份

## Projects and Service / 项目与学术服务

按需填写。

## Contact / 联系方式

按需填写公开的联系渠道。
```

这里的示例文字和链接只是占位，发布前请替换或删除。

## Windows 免安装包与测试账号

如果不想安装 Python、Git 和 GitHub CLI，可以从仓库 **Actions → Build portable Windows editor** 的最新成功运行中下载 `Zhige-Member-Editor-Windows`，完整解压到“文档”等可写目录。包中已经带有运行环境和 GitHub CLI。

- 正式维护：双击 `Start-Faculty-Editor.bat`，以 `garrisongys` 授权，发布到 `main`，会更新正式网站。
- 测试演练：双击 `Start-Test-Editor.bat`，以 `zhengfeiLian` 授权，发布到 `faculty-editor-test`。该分支不会触发正式网站部署。编辑器里也会明确显示账号和目标分支。

两个模式请分别解压到不同目录，避免本地草稿和登录配置混用。首次启动需要联网获取当前分支内容；之后可编辑离线草稿，发布时仍需联网。下载的包有有效期，过期后可重新运行构建工作流。

Recruitment 的现有英文和中文内容会自动填入编辑器；可以单独修改 Recruitment，无需先填写 Faculty 头像。保存后可预览独立的 Recruitment 页面。发布时只合并本账号 Faculty 条目与 Recruitment 两个范围中实际修改的部分。


## v1.2: ORCID 与成果维护

完整 Faculty 包包含 `Start-Faculty-Editor` 正式入口及 `Start-Faculty-Test` 测试入口。
正式入口为 garrisongys/main；测试入口为 zhengfeiLian/faculty-publications-test。

可直接选择与网页配色统一的男女默认头像，或上传个人照片。
ORCID 输入号码/网址，点击“同步公开成果”，核对记录姓名；这是公开标识关联，不是 OAuth 身份认证。
新成果默认不选；重复同步按 DOI/ORCID 工作编号去重，并保留既有手工修改和选择。
展开成果可编辑类型、作者、年份、会议/期刊、层次 A/B/C、BibTeX、PDF链接。
A/B/C 由本人确认，不能据此声称自动取得 CCF 分级。
勾选成果自动尝试补充公开 Crossref/DOI 元数据；网络或来源缺失时可再点获取或手工补充。
只将勾选成果展示在本人 Faculty 及实验室 Publications；取消勾选不会删除本地成果。
公开数据未给出 PDF/BibTeX 时明确显示待补充，不伪造下载地址。出版商 PDF 可能需要访问权限。
保存与推送仍有账号范围限制、远程冲突检查，测试分支不影响 main。


## CCF 自动分级测试（2026-11-10）

`faculty-ccf-test` 仅供测试，未部署至正式网站。
分级使用 CCF 第七版（2026-03-31 发布、4月9日勘误）的官方 PDF 快照。
`content/ccf-2026.json` 保留来源、校验哈希、页码；当前保守抽取 602 条可可靠解析的场所，无法解析或匹配的条目标记待核验，不推断等级。
Faculty 不再手工选择等级。同步、补全、保存和静态页面生成都会重新匹配；会议/期刊名称可修正。
按最新目录显示场所推荐等级，不表示单篇论文质量评级。会议的短文、Demo、Findings、Workshop 等不能继承主会等级。
仅有主会名称的记录仍需确认其为正式长文；程序不能由 ORCID 元数据完整判断论文类型。
ORCID 仅返回已关联且公开的成果，不能保证收齐作者所有论文。2026-11-10 检查主记录 123 组，没有 CompLeak；次记录无公开成果。
CompLeak 获奖来源：https://secartifacts.github.io/usenixsec2026/awards


v1.3 测试：CCF 自动分级与标题搜索
测试入口仅使用 zhengfeiLian / faculty-ccf-test，不更新正式网站。
CCF 根据随包官方第七版目录匹配，老师无需填写；未能可靠匹配的显示待核验。
可输入标题查询 Crossref、arXiv、OpenAlex，核对候选后勾选并添加。
搜索结果不会自动发布；添加后保存本地预览，再推送测试分支。
BibTeX 可在线获取或依据元数据生成；PDF 仅在数据源提供时展示，不保证每篇可获取。
预印本保留原年份/类型，不自动升级成正式会议成果或继承 CCF 等级。
亦可添加空白论文并手工填写元数据、BibTeX和链接。勿将作者名/奖项等未核实信息当作自动验证。

## v1.4 修正
- 正式入口固定 garrisongys/main，启动读取老师正式资料。取消预填 ORCID 与测试论文。
- 页面显示同步状态；可重新读取正式资料，保留本地草稿前会备份。
- USENIX 官方站内搜索实时发现正式论文，解析其元数据、BibTeX、PDF和获奖标记；预印本不会冒充正式版。
- 修正女性默认头像额头区域，保持原配色。

## v1.5 空白搜索与论文核对

首次打开搜索框无具体论文示例，候选结果和待添加条目为空，不进行自动查询。
查询专用索引覆盖已核对的 12 篇，均有来源、核对日期且 selected=false；该文件不是 profile 数据。
Crossref 的标题/副标题合并读取，避免 STRIP 的副标题被丢弃。
会议名称尾部的 CCF 目录简称（如 HPCA、CCS）可可靠归一化，Workshop 不继承主会等级。
