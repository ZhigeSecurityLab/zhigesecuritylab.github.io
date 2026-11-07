#!/bin/zsh
cd "${0:A:h}"
./ZhigeMemberEditor --user garrisongys --branch main --port 8002 --open
if [ "$?" -ne 0 ]; then read -k 1 "?启动失败，按任意键关闭。"; fi
