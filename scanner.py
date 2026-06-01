from pathlib import Path
import re


RULES = [
    {
        "name": "Hardcoded password",
        "severity": "HIGH",
        "patterns": [r"password\s*[:=]\s*[\"']?[^\"'\n,]+"],
        "recommendation": "Remove hardcoded credentials and require per-device password setup."
    },
    {
        "name": "Private key exposed",
        "severity": "HIGH",
        "patterns": [r"BEGIN RSA PRIVATE KEY", r"BEGIN PRIVATE KEY"],
        "recommendation": "Do not store private keys in firmware images."
    },
    {
        "name": "Telnet enabled",
        "severity": "HIGH",
        "patterns": [r"\btelnetd\b"],
        "recommendation": "Disable Telnet and use SSH or another secure management channel."
    },
    {
        "name": "Insecure HTTP URL",
        "severity": "MEDIUM",
        "patterns": [r"http://"],
        "recommendation": "Use HTTPS and verify certificates."
    },
    {
        "name": "Debug mode enabled",
        "severity": "LOW",
        "patterns": [r"debug\s*[:=]\s*true"],
        "recommendation": "Disable debug mode in production firmware."
    },
    {
        "name": "Possible unsigned update",
        "severity": "HIGH",
        "patterns": [r"wget .*firmware", r"sh /tmp/firmware"],
        "recommendation": "Verify firmware updates using cryptographic signatures before installation."
    }
]


def scan_file(path: Path):
    findings = []

    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return findings

    for rule in RULES:
        for pattern in rule["patterns"]:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                findings.append({
                    "file": str(path),
                    "finding": rule["name"],
                    "severity": rule["severity"],
                    "pattern": pattern,
                    "recommendation": rule["recommendation"]
                })
                break

    return findings


def scan_firmware(root: str):
    root_path = Path(root)
    all_findings = []

    for path in root_path.rglob("*"):
        if path.is_file():
            all_findings.extend(scan_file(path))

    return all_findings