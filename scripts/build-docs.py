#!/usr/bin/env python3
"""Build the repository's Markdown documentation and live GitHub release page."""
import argparse
import html
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]


def build(root, output, repository='fetian-debug/FetianOS', revision='main'):
    import markdown
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository): raise ValueError('Invalid repository')
    if output.exists(): raise FileExistsError('Choose a fresh documentation destination')
    if any(output.resolve().is_relative_to((root / folder).resolve()) for folder in ('docs', 'website')):
        raise ValueError('Documentation output must be outside its source directories')
    sources = list((root / 'docs').rglob('*.md')) + [root / 'README.md', root / 'website/index.md', root / 'website/downloads.md']
    mapping = {path.resolve(): path.relative_to(root).with_suffix('.html') for path in sources}
    mapping[(root / 'README.md').resolve()] = Path('docs/project-readme.html')
    mapping[(root / 'website/index.md').resolve()] = Path('index.html')
    mapping[(root / 'website/downloads.md').resolve()] = Path('downloads.html')
    output.mkdir(parents=True); (output / '.nojekyll').touch()
    shutil.copytree(root / 'website/assets', output / 'assets')
    (output / 'assets/repository.json').write_text(json.dumps({'repository': repository}) + '\n')
    # Retain diagrams, public machine-readable audits and source Markdown.
    shutil.copytree(root / 'docs', output / 'docs', dirs_exist_ok=True)
    titles = {}
    for source in sources:
        match = re.search(r'^# (.+)$', source.read_text(), re.MULTILINE)
        titles[source.resolve()] = match.group(1).strip() if match else source.stem
    for source in sources:
        destination = mapping[source.resolve()]; prefix = posixpath.relpath('.', str(destination.parent))
        def link(path): return posixpath.relpath(str(path), str(destination.parent))
        def rewrite(value):
            parsed = urlsplit(html.unescape(value))
            if parsed.scheme or parsed.netloc: return value if parsed.scheme in ('http', 'https', 'mailto') else '#'
            if not parsed.path: return value
            target = (source.parent / unquote(parsed.path)).resolve()
            if target in mapping: target_url = link(mapping[target])
            elif target.is_relative_to(root.resolve()) and target.is_file():
                relative = target.relative_to(root.resolve()).as_posix()
                target_url = link(Path(relative)) if relative.startswith('docs/') else f'https://github.com/{repository}/blob/{revision}/{relative}'
            else: return value
            return html.escape(urlunsplit(('', '', target_url, parsed.query, parsed.fragment)), quote=True)
        content = markdown.markdown(source.read_text(), extensions=['fenced_code', 'tables', 'toc'])
        content = re.sub(r'\b(href|src)="([^"]*)"', lambda match: match[1] + '="' + rewrite(match[2]) + '"', content)
        title = html.escape(titles[source.resolve()]); repo_url = 'https://github.com/' + repository
        sidebar = ''.join(f'<a href="{link(mapping[path.resolve()])}">{html.escape(titles[path.resolve()])}</a>' for path in sorted((root / 'docs').glob('*.md')))
        downloads = destination == Path('downloads.html')
        script = f'<script src="{prefix}/assets/downloads.js" defer></script>' if downloads else ''
        body_class = 'documentation' if destination.parts[0] == 'docs' else 'landing'
        page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · FetianOS</title><meta name="color-scheme" content="dark light"><link rel="stylesheet" href="{prefix}/assets/site.css">{script}</head>
<body class="{body_class}"><a class="skip" href="#content">Skip to content</a><header><a class="brand" href="{link(Path('index.html'))}">FETIAN<span>OS</span></a>
<nav aria-label="Main navigation"><a href="{link(Path('downloads.html'))}">Downloads</a><a href="{link(Path('docs/index.html'))}">Documentation</a><a href="{repo_url}">GitHub ↗</a></nav></header>
<div class="layout">{'<aside aria-label="Documentation pages">' + sidebar + '</aside>' if body_class == 'documentation' else ''}
<main id="content">{content}</main></div><footer>Developer preview · Rust system services · Sway recovery · Hyprland opt-in<br>
<a href="{link(Path('docs/release-acceptance.html'))}">Release acceptance</a> · <a href="{repo_url}/actions">Build status</a> · <a href="{repo_url}/releases">All releases</a></footer></body></html>'''
        target = output / destination; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(page)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'fetian-debug/FetianOS'))
    args = parser.parse_args()
    try: print(build(ROOT, args.output, args.repository, os.environ.get('GITHUB_SHA', 'main')))
    except (OSError, ValueError, ImportError) as error: parser.exit(1, str(error) + '\n')
