Zhige Security Lab Faculty + Recruitment editor

1. Extract the whole ZIP to a writable folder such as Documents. Keep all files together.
2. For formal editing, double-click Start-Faculty-Editor.bat. This uses garrisongys and publishes to main.
3. For testing, double-click Start-Test-Editor.bat. This uses zhengfeiLian and publishes only to faculty-editor-test. The public site does not change.
4. In the browser, edit Faculty and/or Recruitment, save and preview, then connect the matching GitHub account and publish.
5. Keep the console window open while editing. Close it after you finish.

For every lab member: double-click Start-Member-Editor.bat. Connect your own GitHub account with Write access. Choose PhD or Master on first registration, save/preview, and publish to main. The first save binds this copy to your GitHub account and one People record. Later edits update the same record; the category is locked.
You can choose a male or female default avatar, or upload a photo. Faculty and postdoctoral profiles use Markdown; other members use a multiline description.

This package includes Python, the Markdown renderer, and GitHub CLI. No separate installation is needed.
GitHub authorization is completed in the browser on first use. Credentials stay in the local .local folder.
The editor listens only on 127.0.0.1. Do not share the .local folder or your edited copy of the package.

Details: https://github.com/ZhigeSecurityLab/zhigesecuritylab.github.io/blob/main/FACULTY_MAINTENANCE.md

For safe testing use Start-Member-Test.bat; it publishes only to member-editor-test.
A bound copy requires the same GitHub account. Ask the lab maintainer to change your category if needed.
