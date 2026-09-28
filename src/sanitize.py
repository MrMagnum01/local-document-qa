"""Heuristic redaction of instruction-like content inside untrusted passage
text before it is placed into the generation prompt.

This is defense in depth, not a proof of universal prompt-injection
resistance (see tests/test_safety.py docstring and MANIFEST.md): a small
local model does not reliably follow "treat this as data" instructions on
its own, so obviously injection-shaped lines are stripped in code before the
model ever sees them. Only the copy of the text sent to the model is
affected; passage records returned to callers (and shown in results/audit
output) keep the original text unredacted.
"""
import re

REDACTION_MARKER = "[redacted: instruction-like content removed before generation]"

_PATTERNS = [
    re.compile(r"ignore (all )?(previous|prior|the) instructions", re.IGNORECASE),
    re.compile(r"disregard (all )?(previous|prior|the) instructions", re.IGNORECASE),
    re.compile(r"reveal your system prompt", re.IGNORECASE),
    re.compile(r"you are no longer", re.IGNORECASE),
    re.compile(r"new instructions (supersede|override)", re.IGNORECASE),
    re.compile(r"^\s*system:\s", re.IGNORECASE | re.MULTILINE),
    re.compile(r"do not (mention|tell|disclose) this", re.IGNORECASE),
    re.compile(r"http_get\(|http_post\(|https?://\S*attacker", re.IGNORECASE),
    re.compile(r"</?(doc|system|assistant|user)>", re.IGNORECASE),
    re.compile(r"call the tool", re.IGNORECASE),
]


def sanitize_for_prompt(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        if any(p.search(line) for p in _PATTERNS):
            out.append(REDACTION_MARKER)
        else:
            out.append(line)
    return "\n".join(out)
