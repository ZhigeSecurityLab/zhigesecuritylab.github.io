Zhige Security Lab — Faculty Editor v1.2.0

解压到 Documents 等可写文件夹，保留完整目录，不需要另装 Python/Git。
Windows: 双击 Start-Faculty-Editor.bat。
Mac: 双击 Start-Faculty-Editor.command。首次可能需 Finder 右键 > 打开。
正式入口仅供 garrisongys，发布目标为 main。

测试入口 Start-Faculty-Test.bat/.command 仅供 zhengfeiLian，目标 faculty-publications-test。
测试入口的编辑和推送不会更新正式网站。不要把测试资料复制到正式入口。

1. 可上传真实头像，也可选男/女默认头像；不要求真实照片。
2. 在 ORCID 输入本人号码或网址，同步公开成果，核对姓名和成果后再保存。
   这里是关联公开标识，不是 ORCID OAuth 身份认证。只能读取公开记录。
3. 勾选要展示的论文；会议/期刊分别分组，A/B/C 层次由本人确认，不自动认定 CCF。
   组内按年份倒序。选中时尝试获取 BibTeX、作者、发表场所、PDF链接。
   展开论文可补全/修改所有字段。缺失或不可访问的 PDF 请自行补充合法链接。
   取消勾选只隐藏论文；再次同步保留已有选择和人工编辑，新成果默认不勾选。
4. 中英文个人简介与 Recruitment 可继续使用 Markdown 编辑。
5. 保存并本地预览，检查 Faculty 和 Publications；连接指定 GitHub 账号后推送。
   账号需要仓库 Write 权限。只更新本人资料/成果与 Recruitment，保留其他成员。

编辑时保持终端窗口开启。勿分享已使用目录中的 .local 授权文件，只分发原始 ZIP。


v1.3 测试：CCF 自动分级与标题搜索
测试入口仅使用 zhengfeiLian / faculty-ccf-test，不更新正式网站。
CCF 根据随包官方第七版目录匹配，老师无需填写；未能可靠匹配的显示待核验。
可输入标题查询 Crossref、arXiv、OpenAlex，核对候选后勾选并添加。
搜索结果不会自动发布；添加后保存本地预览，再推送测试分支。
BibTeX 可在线获取或依据元数据生成；PDF 仅在数据源提供时展示，不保证每篇可获取。
预印本保留原年份/类型，不自动升级成正式会议成果或继承 CCF 等级。
亦可添加空白论文并手工填写元数据、BibTeX和链接。勿将作者名/奖项等未核实信息当作自动验证。
