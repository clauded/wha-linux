"""Device-free builder tests; all fixture code/data is authored, not extracted."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "buildkit/tools"))
from unpack_pyz import archive_name
from patch_qml import apply, fingerprint, function_span


class BuilderTests(unittest.TestCase):
    def test_typed_archive_not_basename(self):
        for name in ("PYZ-00.pyz", "PYZ.pyz", "different-name.arc"):
            self.assertEqual(archive_name({"main": ("s",), name: ("z",)}), name)
        for toc in ({}, {"one": ("z",), "two": ("z",)}):
            with self.assertRaises(ValueError):
                archive_name(toc)

    def test_comment_whitespace_and_string_safety(self):
        first = 'function demo(v) { return "http://example.test/{}" + v; }'
        second = 'function demo (v) { /* changed comment { } */ return "http://example.test/{}"+ v ; }'
        self.assertEqual(fingerprint(first), fingerprint(second))
        self.assertNotEqual(fingerprint(first), fingerprint(first.replace("+ v", "+ 7")))
        a, b = function_span("// before\n" + second + "\n// after", "demo")
        self.assertEqual(("// before\n" + second + "\n// after")[a:b], second)

    def test_atomic_guarded_idempotent_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "function demo(v) { return v.count; }"
            replacement = "function demo(v) { return v.rowCount(); }"
            (root / "new.txt").write_text(replacement)
            (root / "one.qml").write_text(original)
            (root / "two.qml").write_text(original.replace("v.count", "v.different"))
            edits = [{"path": name, "function": "demo", "accepted": [fingerprint(original)], "replacement": "new.txt"}
                     for name in ("one.qml", "two.qml")]
            manifest = root / "spec.json"
            manifest.write_text(json.dumps(edits))
            with self.assertRaisesRegex(ValueError, "review required"):
                apply(root, manifest)
            self.assertEqual((root / "one.qml").read_text(), original)
            (root / "two.qml").write_text(original.replace("return", "/* cosmetic */ return"))
            apply(root, manifest)
            apply(root, manifest)
            self.assertEqual((root / "one.qml").read_text(), replacement)

    def test_readable_unpack_and_guarded_untested_cli(self):
        wrapper = ROOT / "wha-linux.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unpacked = root / "kit"
            subprocess.run(["/bin/sh", str(wrapper), "--unpack", str(unpacked)], check=True, capture_output=True)
            self.assertTrue((unpacked / "linux/qt_compat/QtCore.py").is_file())
            self.assertFalse(list(unpacked.rglob("*.pyc")))
            for path in unpacked.rglob("*"):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (ROOT / "buildkit" / path.relative_to(unpacked)).read_bytes())
            dmg = root / "untested.dmg"
            dmg.write_bytes(b"authored invalid input")
            env = dict(os.environ, XDG_DATA_HOME=str(root / "data"))
            result = subprocess.run(["/bin/sh", str(wrapper), str(dmg)], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--allow-untested", result.stderr)
            bindir = root / "bin"
            bindir.mkdir()
            (bindir / "python3").symlink_to(sys.executable)
            env["PATH"] = str(bindir)
            result = subprocess.run(["/bin/sh", str(wrapper), str(dmg), "--allow-untested"], env=env, capture_output=True, text=True)
            self.assertIn("WARNING: untested", result.stdout)
            self.assertIn("Missing:", result.stderr)
            self.assertNotIn("NoneType", result.stderr)


if __name__ == "__main__":
    unittest.main()
