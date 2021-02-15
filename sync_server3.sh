#!/usr/bin/env bash
set -euo pipefail
rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress --exclude '.git' --exclude '__pycache__/' --exclude '*.db' --exclude '.DS_Store' --exclude 'secrets.json' --exclude 'media'  ./ root@server3.vsdg.ru:/root/moisklad_proxy
