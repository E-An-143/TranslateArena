"""Audit and optionally package an explicit set of public source files.

Only file names and finding categories are reported, never matched values.
Local data, virtual environments and QA artifacts are not release inputs.
"""
import argparse
import hashlib
import os
import re
import zipfile
from pathlib import Path


ROOT_FILES = (
    ".gitignore", "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md",
    "main.py", "build.bat", "build.ps1",
    "requirements.txt", "requirements-build.txt", "TranslateArena.spec",
)
PUBLIC_DOCS = (
    "ARCHITECTURE.md", "DEEPSEEK_API.md", "MULTI_JUDGE_PROMPT.md",
    "PROMPT_EXAMPLES.json", "RELEASE_PRIVACY.md",
)
TREE_SUFFIXES = {
    "arena": {".py", ".qml", ".json", ".svg", ".ico", ".ttf", ".txt", ".pdf"},
    "scripts": {".py"},
    ".github": {".yml", ".yaml"},
}
PRIVATE_NAMES = {
    "credentials", "logs", "backups", "cache", "data-location.json",
    ".git", ".venv", ".qa", "qa-data", ".aws", ".ssh",
}
PRIVATE_SUFFIX = re.compile(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$|\.(?:dpapi|pem|key|log|tmp)$", re.I)
CONTENT_RULES = {
    "credential-like value": re.compile(
        rb"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        rb"github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
        rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----)"
    ),
    "personal home directory": re.compile(
        rb"(?:[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"<>]+|/(?:home|Users)/[^/\s\"<>]+)", re.I
    ),
}


def private_name(name):
    lowered = name.lower()
    return (lowered in PRIVATE_NAMES or lowered.startswith(".env")
            or bool(PRIVATE_SUFFIX.search(lowered)))


def content_findings(data, personal_names=()):
    # Also catch UTF-16 paths embedded in Windows files without exposing values.
    samples = (data, data.replace(b"\0", b""))
    findings = {label for label, pattern in CONTENT_RULES.items()
                if any(pattern.search(sample) for sample in samples)}
    for name in personal_names:
        if len(name) >= 4:
            value = name.encode("utf-8").lower()
            if any(value in sample.lower() for sample in samples):
                findings.add("local account name")
    return sorted(findings)


def collect_release_files(root):
    root = root.resolve(strict=True)
    files = []

    def add(path):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Release inputs must stay inside the project")
        if not path.is_file():
            raise ValueError("Missing release input: " + path.relative_to(root).as_posix())
        if private_name(path.name):
            raise ValueError("Private release input: " + path.relative_to(root).as_posix())
        files.append(path)

    for name in ROOT_FILES:
        add(root / name)
    for name in PUBLIC_DOCS:
        add(root / "docs" / name)
    for tree, suffixes in TREE_SUFFIXES.items():
        directory = root / tree
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Invalid release directory: " + tree)
        for base, dirs, names in os.walk(directory, followlinks=False):
            dirs.sort()
            for name in list(dirs):
                path = Path(base) / name
                if path.is_symlink() or private_name(name):
                    raise ValueError("Private or linked release directory: " + path.relative_to(root).as_posix())
                if name == "__pycache__":
                    if path.relative_to(root).parts[:2] in (("arena", "ui"), ("arena", "resources")):
                        raise ValueError("Bytecode in bundled resources")
                    dirs.remove(name)
            for name in sorted(names):
                path = Path(base) / name
                if path.suffix == ".pyc":
                    if path.relative_to(root).parts[:2] in (("arena", "ui"), ("arena", "resources")):
                        raise ValueError("Bytecode in bundled resources")
                    continue
                if path.suffix.lower() not in suffixes and not (tree == "arena" and name == "qmldir"):
                    raise ValueError("Unexpected release input: " + path.relative_to(root).as_posix())
                add(path)
    return sorted(files)


def audit_release(root, files):
    root = root.resolve(strict=True)
    profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    personal_names = (Path(profile).name,) if profile else ()
    findings = []
    for path in files:
        for category in content_findings(path.read_bytes(), personal_names):
            findings.append((path.relative_to(root).as_posix(), category))
    return findings


def write_source_zip(root, files, destination):
    root = root.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing archive")
    if destination.is_relative_to(root / "arena") or destination in files:
        raise ValueError("Archive must not replace a source input")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            manifest = []
            for path in files:
                data = path.read_bytes()
                relative = path.relative_to(root).as_posix()
                # Fixed archive metadata avoids retaining machine paths and file dates.
                entry = zipfile.ZipInfo("TranslateArena/" + relative, (2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data)
                manifest.append(hashlib.sha256(data).hexdigest() + "  " + relative)
            entry = zipfile.ZipInfo("TranslateArena/CHECKSUMS.sha256", (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, "\n".join(manifest) + "\n")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-zip", type=Path, help="Write an audited public source archive")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        files = collect_release_files(root)
        findings = audit_release(root, files)
        if findings:
            for filename, category in findings:
                print("BLOCKED:", filename, "-", category)
            return 1
        print("Release privacy check passed:", len(files), "public files; no detected private values.")
        if args.source_zip:
            write_source_zip(root, files, args.source_zip)
            print("Audited source archive created:", args.source_zip.name)
        return 0
    except (OSError, ValueError, zipfile.BadZipFile):
        # Do not echo exceptions that may contain private input or machine paths.
        print("Release privacy check failed; check for missing, private, linked or unexpected release inputs.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
