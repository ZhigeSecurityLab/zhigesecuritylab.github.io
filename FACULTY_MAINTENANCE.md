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
2. 在 English／中文之间切换，分别写 Markdown。可以点「插入可修改的模板」，再删改不适用的小节。模板不会自动发布。
3. Faculty 和 Recruitment 都有 Markdown 即时预览；Recruitment 会自动载入现有文案，也可以不填写 Faculty 而单独更新 Recruitment。点击「保存并更新本地预览」，再查看下方的完整页面；可切换英文、中文。
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

如果不想安装 Python、Git 和 GitHub CLI，可以从仓库 **Actions → Build portable Windows editor** 的最新成功运行中下载 `Zhige-Faculty-Editor-Windows`，完整解压到“文档”等可写目录。包中已经带有运行环境和 GitHub CLI。

- 正式维护：双击 `Start-Faculty-Editor.bat`，以 `garrisongys` 授权，发布到 `main`，会更新正式网站。
- 测试演练：双击 `Start-Test-Editor.bat`，以 `zhengfeiLian` 授权，发布到 `faculty-editor-test`。该分支不会触发正式网站部署。编辑器里也会明确显示账号和目标分支。

两个模式请分别解压到不同目录，避免本地草稿和登录配置混用。首次启动需要联网获取当前分支内容；之后可编辑离线草稿，发布时仍需联网。下载的包有有效期，过期后可重新运行构建工作流。

Recruitment 的现有英文和中文内容会自动填入编辑器；可以单独修改 Recruitment，无需先填写 Faculty 头像。保存后可预览独立的 Recruitment 页面。发布时只合并本账号 Faculty 条目与 Recruitment 两个范围中实际修改的部分。
