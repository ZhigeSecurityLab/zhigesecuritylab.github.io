#!/bin/zsh
cd "${0:A:h}"
./ZhigeMemberEditor --student --branch faculty-editor-test --port 8005 --open
result=$?
if [ "$result" -ne 0 ]; then
  echo "启动失败，错误码：$result"
  read -k 1 "?按任意键关闭窗口。"
fi
