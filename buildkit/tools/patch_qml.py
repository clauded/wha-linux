"""Semantic anchors + approved token hashes, not line offsets or whole files.

Whitespace/comments may change; changed executable code must be reviewed.
All preconditions are checked before any file is written. Already-fixed
functions are accepted without edits. No proprietary source is embedded.
"""
import hashlib
import json
import re
import sys
from pathlib import Path


def fingerprint(text):
    # These guarded functions contain no regex literals or template strings.
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|//[^\n]*|/\*[\s\S]*?\*/|\S', text)
    return hashlib.sha256("".join(t for t in tokens if not t.startswith(("//", "/*"))).encode()).hexdigest()


def function_span(text, name):
    matches = list(re.finditer(r"\bfunction\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", text))
    if len(matches) != 1:
        raise ValueError("Expected one function %s, found %d" % (name, len(matches)))
    start = matches[0].start()
    tokens = re.finditer(r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|//[^\n]*|/\*[\s\S]*?\*/|[{}]', text[matches[0].end()-1:])
    depth = 0
    for token in tokens:
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return start, matches[0].end()-1+token.end()
    raise ValueError("Unbalanced function " + name)


def apply(app, manifest_path):
    spec = json.loads(manifest_path.read_text())
    pending, report = {}, []
    for edit in spec:
        path = app / edit["path"]
        text = pending.get(path, path.read_text())
        if "function" in edit:
            start, end = function_span(text, edit["function"])
        else:
            matches = list(re.finditer(r"(?m)^\s*sourceComponent:\s*([^\n]*homeSkeletonComponent[^\n]*homeContentComponent[^\n]*)$", text))
            if len(matches) != 1:
                raise ValueError("Expected exactly one TIDAL Home content Loader")
            start, end = matches[0].span(1)
        replacement = (manifest_path.parent / edit["replacement"]).read_text().strip()
        current = fingerprint(text[start:end])
        if current == fingerprint(replacement):
            report.append({"target": edit["path"], "status": "already-fixed"})
            continue
        if current not in edit["accepted"]:
            raise ValueError("Patch review required for %s/%s (token SHA-256 %s)"
                             % (edit["path"], edit.get("function", "home-loader"), current))
        pending[path] = text[:start] + replacement + text[end:]
        report.append({"target": edit["path"], "status": "patched"})
    for path, text in pending.items():
        path.write_text(text)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    apply(Path(sys.argv[1]), Path(sys.argv[2]))
