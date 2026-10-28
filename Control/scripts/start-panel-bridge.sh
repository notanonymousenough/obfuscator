#!/bin/bash
set -euo pipefail
systemctl enable --now obfuscator-panel-bridge
systemctl is-active obfuscator-panel-bridge
