#!/bin/bash
# Keep this terminal running. Both forwards bind loopback only.
set -euo pipefail
exec ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -L 127.0.0.1:1337:127.0.0.1:19337 user@192.168.0.192 'exec ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -NT -L 127.0.0.1:19337:127.0.0.1:1337 -p 2222 deploy@de1.obfuscator.funsociety.dev'
