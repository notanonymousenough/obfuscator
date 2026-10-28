#!/usr/bin/env python3
"""Explicitly display a private Telegram link on the server; never run in public logs."""
import argparse,pathlib,tomllib,urllib.parse
a=argparse.ArgumentParser();a.add_argument("--server",help="Override connection host, e.g. LAN IP for local testing");args=a.parse_args()
p=pathlib.Path('/etc/obfuscator')
domain=(p/'domain').read_text().strip()
secret=tomllib.loads((p/'mtg.toml').read_text())['secret']
print('tg://proxy?'+urllib.parse.urlencode({'server':args.server or domain,'port':443,'secret':secret}))
