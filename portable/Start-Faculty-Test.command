#!/bin/zsh
cd "${0:A:h}"
./ZhigeMemberEditor --user zhengfeiLian --branch faculty-ccf-test --port 8003 --open
if [ "$?" -ne 0 ]; then read -k 1 "?启动失败，按任意键关闭。"; fi
