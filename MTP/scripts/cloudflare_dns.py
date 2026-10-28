#!/usr/bin/env python3
"""Update one DNS-only A record. Token and all unrelated records stay private."""
import argparse, ipaddress, json, pathlib, sys, urllib.request, urllib.error, urllib.parse

def fetch(url, headers=None, data=None, method=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get('errors', [])
            msg = '; '.join(str(x.get('code')) + ': ' + x.get('message', '') for x in err)
        except (ValueError, AttributeError):
            msg = 'non-JSON response'
        raise RuntimeError(f'HTTP {e.code}: {msg}') from None

def public_ipv4():
    answers = []
    for u in ('https://api.ipify.org', 'https://ifconfig.co/ip'):
        a = ipaddress.ip_address(fetch(u, {'User-Agent': 'obfuscator-ddns/1.0'}).decode().strip())
        if a.version != 4 or not a.is_global:
            raise ValueError('IP discovery returned a non-public IPv4 address')
        answers.append(str(a))
    if len(set(answers)) != 1:
        raise ValueError('IP discovery providers disagree; DNS left unchanged')
    return answers[0]

def sync(config, apply=False):
    if apply and config.get('ingress_confirmed') is not True:
        raise ValueError('Set ingress_confirmed=true only after public ingress is configured; external IP discovery cannot detect CGNAT')
    token = pathlib.Path(config['token_file']).read_text().strip()
    if not token or any(c.isspace() for c in token):
        raise ValueError('Expected a raw Cloudflare API token, not a shell assignment')
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    def api(path, data=None, method=None):
        d = json.loads(fetch('https://api.cloudflare.com/client/v4/' + path, head, data, method))
        if not d.get('success'):
            raise RuntimeError('Cloudflare rejected request')
        return d['result']
    zone = config['zone']; name = config['name']
    if name != zone and not name.endswith('.' + zone):
        raise ValueError('Record must belong to configured zone')
    zs = api('zones?' + urllib.parse.urlencode({'name': zone}))
    if len(zs) != 1:
        raise ValueError('Expected exactly one accessible DNS zone')
    ip = config.get('ipv4', 'auto')
    if ip == 'auto': ip = public_ipv4()
    address = ipaddress.ip_address(ip)
    if address.version != 4 or not address.is_global:
        raise ValueError('Refusing to publish a non-public IPv4')
    base = f'zones/{zs[0]["id"]}/dns_records'
    rs = api(base + '?' + urllib.parse.urlencode({'type': 'A', 'name': name}))
    if len(rs) > 1:
        raise ValueError('Multiple A records exist; refusing destructive reconciliation')
    if rs and rs[0]['content'] == ip and not rs[0]['proxied']:
        print(f'{name}: unchanged ({ip}, DNS-only)'); return
    if not apply:
        print(f'{name}: would set A {ip}, DNS-only'); return
    data = {'type': 'A', 'name': name, 'content': ip, 'ttl': 120, 'proxied': False}
    api(base + '/' + rs[0]['id'] if rs else base, data, 'PUT' if rs else 'POST')
    print(f'{name}: set A {ip}, DNS-only')

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--config', required=True); p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    try: sync(json.loads(pathlib.Path(a.config).read_text()), a.apply)
    except Exception as e: print(f'DDNS failed: {e}', file=sys.stderr); sys.exit(1)
