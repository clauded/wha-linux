#!/usr/bin/env python3
"""Unpack the single typed PYZ entry; validate bytecode before unmarshalling."""
import importlib.util
import dis
import json
import marshal
import pathlib
import re
import sys


def archive_name(toc):
    names = [name for name, entry in toc.items() if entry[-1] == "z"]
    if len(names) != 1:
        raise ValueError("Expected exactly one PYZ archive; found %s" % names)
    return names[0]


def main(source, target):
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    target.mkdir(parents=True, exist_ok=True)
    archive = CArchiveReader(str(source))
    name = archive_name(archive.toc)
    data = archive.extract(name)
    if data[:4] != b"PYZ\0" or data[4:8] != importlib.util.MAGIC_NUMBER:
        raise ValueError("Unsupported Python bytecode magic %s; runtime is %s. Review required."
                         % (data[4:8].hex(), importlib.util.MAGIC_NUMBER.hex()))
    pyz_path = target.parent / "application.pyz"
    pyz_path.write_bytes(data)
    pyz = ZlibArchiveReader(str(pyz_path), check_pymagic=True)
    header = importlib.util.MAGIC_NUMBER + b"\0" * 12
    if "main" not in archive.toc:
        raise ValueError("No supported main entry point; review required")
    (target / "main.pyc").write_bytes(header + archive.extract("main"))
    for module, entry in pyz.toc.items():
        if entry[0] not in (0, 1, 3):
            raise ValueError("Unknown PYZ module type %s" % (entry[0],))
        if entry[0] == 3:
            continue
        if not all(re.fullmatch(r"[\w-]+", part) for part in module.split(".")):
            raise ValueError("Unsafe Python module path: %r" % module)
        code = pyz.extract(module, raw=True)
        if code is None:
            continue
        relative = module.replace(".", "/")
        output = target / relative / "__init__.pyc" if entry[0] == 1 else target / (relative + ".pyc")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(header + code)
    ui = marshal.loads(pyz.extract("LPGlobalUI", raw=True))
    bindings = {ins.argval.split(".")[0] for ins in dis.get_instructions(ui)
                if ins.opname == "IMPORT_NAME" and ins.argval.split(".")[0] in ("PySide6", "PyQt6")}
    if len(bindings) != 1:
        raise ValueError("No unambiguous supported Qt binding in LPGlobalUI: %s" % bindings)
    binding = bindings.pop()
    metadata = {"pyz_entry": name, "python_magic": data[4:8].hex(), "qt_binding": binding,
                "module_count": len(pyz.toc)}
    (target.parent / "archive-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
