"""Explicit, checksum-verified weight download and loopback model serving."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / 'model-artifact.json').read_text())
WEIGHTS = ROOT / 'models/model.gguf'


def verify(path=WEIGHTS):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise ValueError('Model file is absent or is a symlink; run the explicit fetch task first.')
    if path.stat().st_size != MODEL['size']:
        raise ValueError('Model size does not match the pinned artifact.')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != MODEL['sha256']:
        raise ValueError('Model checksum does not match the pinned artifact.')
    return h.hexdigest()


def fetch():
    if WEIGHTS.exists() or WEIGHTS.is_symlink():
        verify()
        return
    WEIGHTS.parent.mkdir(exist_ok=True)
    if WEIGHTS.parent.is_symlink():
        raise ValueError('Model directory must be inside this package.')
    url = f"https://huggingface.co/{MODEL['repository']}/resolve/{MODEL['revision']}/{MODEL['filename']}"
    fd, name = tempfile.mkstemp(prefix='.download-', dir=WEIGHTS.parent)
    try:
        with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(url, timeout=60) as response:
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > MODEL['size']:
                    raise ValueError('Download exceeds the pinned artifact size.')
                output.write(block)
        verify(name)
        os.replace(name, WEIGHTS)
    finally:
        if os.path.exists(name): os.unlink(name)


def serve():
    verify()
    token = os.environ.get('COG_QWEN_BACKEND_TOKEN', '')
    if len(token) < 32 or any(c in token for c in '\r\n'):
        raise ValueError('Set COG_QWEN_BACKEND_TOKEN to a random token of at least 32 characters.')
    executable = ROOT / '.pixi/envs/default/bin/llama-server'
    if not executable.is_file():
        raise ValueError('Install the locked Pixi environment first.')
    # Do not allow inherited llama options, remote model fetches, or alternate
    # proxy endpoints to override the pinned model and loopback transport.
    env = {k: v for k, v in os.environ.items() if k in
           {'PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'SYSTEMROOT'}}
    env['LLAMA_API_KEY'] = token
    # llama.cpp names this option LLAMA_API_KEY; no secret enters argv.
    argv = [str(executable), '--model', str(WEIGHTS), '--alias', MODEL['model_id'],
            '--host', '127.0.0.1', '--port', '8080', '--ctx-size', '8192', '--jinja',
            '--chat-template-kwargs', '{"enable_thinking":false}']
    os.execve(str(executable), argv, env)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['fetch', 'serve', 'check'])
    args = p.parse_args()
    try:
        if args.operation == 'fetch': fetch()
        elif args.operation == 'serve': serve()
        else: verify()
        print(json.dumps({'ok': True, 'model': MODEL['model_id'], 'sha256': MODEL['sha256']}))
    except (OSError, ValueError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
