# 成员一站式资料维护

每位成员使用自己的 GitHub 账号编辑本人资料。编辑器自动从 GitHub 登录状态识别账号，只更新 `content/site.json` 中 `github_username` 与该账号相同的中英文 People 条目；其他成员、News、Publications 和 Recruitment 不在此入口的编辑范围内。

## 获取安装包

打开仓库的 Actions 页面，选择最新成功的 **Build portable Windows editor** 或 **Build portable macOS member editor** 运行，在页面底部下载 Artifacts：

- Windows：`Zhige-Faculty-Editor-Windows`，解压后双击 `Start-Member-Editor.bat`。
- macOS Apple Silicon：`Zhige-Member-Editor-macOS-Apple-Silicon`，解压里面的 ZIP，双击 `Start-Member-Editor.command`。
- macOS Intel：`Zhige-Member-Editor-macOS-Intel`，操作相同。

请把整个文件夹放在“文档”等可写位置，保留所有文件，不需要单独安装 Python、Git 或 GitHub CLI。macOS 的包未使用实验室开发者证书公证；若首次打开被系统拦住，在 Finder 中右键 `Start-Member-Editor.command`，选“打开”。程序只监听本机 `127.0.0.1:8005`。

## 第一次登记与以后更新

1. 负责人先把成员的个人 GitHub 账号加入组织，并赋予网站仓库 **Write** 权限。成员接受邀请。
2. 启动安装包，点击“连接 GitHub”，在设备授权页面用**自己的账号**完成授权。编辑器显示识别到的用户名后才开放表单。
3. 选成员类别，填写中英文姓名与身份，选择一张默认头像或上传照片。Faculty 与博士后可编辑 Markdown；博士、硕士等类别使用不限行数的描述。
4. 点击“保存并更新本地预览”，分别检查中英文页面。资料可以先作为本地草稿保存；正式推送前须填写中英文姓名并选头像。
5. 点击“推送更新”。程序先读取 GitHub 上的最新内容，只合并本人资料；若本人资料已被其他人改动，会拒绝覆盖并提示重新同步。推送到 `main` 后，GitHub Pages 自动部署。

每人请保留自己的安装包文件夹；本地 `.local` 中有登录凭据和草稿，不要分享这个文件夹。若下载了新版安装包，把旧文件夹中的 `.local` 和本人尚未发布的草稿先妥善保存，避免丢失。

## 权限边界

编辑器界面和提交逻辑只处理当前 GitHub 账号对应的 People 条目。**GitHub 的 Write 权限本身仍允许账号直接修改仓库其他文件**；GitHub 不支持按 JSON 条目授予写权限。若实验室需要强制审核每位学生的更新，可在仓库启用 `main` 分支保护及 Pull Request 审核，再把编辑器改为提交 PR 的流程。

负责 Recruitment 的 `garrisongys` 仍可使用原有的 `Start-Faculty-Editor.bat` 入口；该入口维护其 Faculty 资料和 Recruitment。学生通用入口不能修改 Recruitment。
