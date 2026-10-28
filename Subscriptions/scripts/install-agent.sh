#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
install -o root -g root -m 755 node_agent.py /usr/local/sbin/obfuscator-node-agent
printf '{"action":"baseline"}' | /usr/local/sbin/obfuscator-node-agent
