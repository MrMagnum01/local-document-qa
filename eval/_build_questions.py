"""One-time generator for the frozen eval/questions.jsonl.

This script is dev tooling, not part of the runtime pipeline. It was run
once, by hand, before any answers were generated; its output
(eval/questions.jsonl) is the frozen artifact from that point on. Do not
re-run it and overwrite questions.jsonl after evaluation has started — see
MANIFEST.md.
"""
import json

Q = []


def add(id, category, question, gold_action, gold_passage_ids=None, facts=None,
        forbidden=None, notes=""):
    Q.append({
        "id": id,
        "category": category,
        "question": question,
        "gold_action": gold_action,
        "gold_passage_ids": gold_passage_ids or [],
        "gold_atomic_facts": facts or [],
        "forbidden_terms": forbidden or [],
        "notes": notes,
    })


# ---- 20 ordinary single-document answerable ----------------------------
add("q001", "answerable_single",
    "What VPN protocol does SecureLink use by default?",
    "ANSWER", ["solstice-vpn-manual#overview"],
    [{"fact": "default protocol is WireGuard", "aliases": ["wireguard"]}],
    ["openvpn is the default"])

add("q002", "answerable_single",
    "Is split tunneling in SecureLink on by default?",
    "ANSWER", ["solstice-vpn-manual#split-tunneling"],
    [{"fact": "split tunneling is off by default", "aliases": ["off by default", "disabled by default"]}],
    ["on by default", "enabled by default"])

add("q003", "answerable_single",
    "What should a SecureLink user do if their VPN connection keeps dropping?",
    "ANSWER", ["solstice-vpn-manual#troubleshooting-connection-drops"],
    [{"fact": "switch protocol from WireGuard to OpenVPN", "aliases": ["switch", "openvpn"]}],
    [])

add("q004", "answerable_single",
    "How long is a SecureLink SSO login session cached before re-authentication?",
    "ANSWER", ["solstice-vpn-manual#login-and-authentication"],
    [{"fact": "sessions cached for 12 hours", "aliases": ["12 hours"]}],
    ["24 hours", "8 hours"])

add("q005", "answerable_single",
    "What encryption does CloudVault use to protect backed-up files?",
    "ANSWER", ["solstice-backup-manual#encryption"],
    [{"fact": "AES-256 client-side encryption", "aliases": ["aes-256", "aes 256"]}],
    ["not encrypted", "aes-128"])

add("q006", "answerable_single",
    "Does CloudVault have a native Linux backup agent with a scheduling UI?",
    "ANSWER", ["solstice-backup-manual#supported-platforms"],
    [{"fact": "no Linux agent; Linux uses a CLI uploader without the scheduling UI",
      "aliases": ["no linux agent", "command-line uploader", "command line uploader"]}],
    ["linux is fully supported with the scheduling ui"])

add("q007", "answerable_single",
    "What is the default backup schedule for a new CloudVault install?",
    "ANSWER", ["solstice-backup-manual#scheduling-backups"],
    [{"fact": "daily at 2:00 AM local time", "aliases": ["daily at 2:00 am", "daily at 2 am"]}],
    ["hourly by default", "weekly by default"])

add("q008", "answerable_single",
    "Does restoring a large CloudVault snapshot require any special confirmation?",
    "ANSWER", ["solstice-backup-manual#restore-procedure"],
    [{"fact": "restores over 50 GB require confirmation because they can take hours",
      "aliases": ["50 gb", "confirmation"]}],
    [])

add("q009", "answerable_single",
    "Can a customer buy the SecureLink VPN client without the CloudVault backup tool?",
    "ANSWER", ["solstice-faq#general"],
    [{"fact": "no, both are sold only as a single combined subscription",
      "aliases": ["combined subscription", "cannot be purchased separately", "single combined subscription"]}],
    ["yes, they can be purchased separately"])

add("q010", "answerable_single",
    "What is the billing advantage of paying for the Solstice subscription annually instead of monthly?",
    "ANSWER", ["solstice-faq#pricing"],
    [{"fact": "two months free compared to paying monthly for twelve months", "aliases": ["two months free"]}],
    ["one month free", "no discount"])

add("q011", "answerable_single",
    "At what rate do full-time Meridian employees accrue PTO?",
    "ANSWER", ["meridian-pto-policy#accrual"],
    [{"fact": "1.25 days per month, 15 days per year", "aliases": ["1.25 days per month", "15 days per year"]}],
    [])

add("q012", "answerable_single",
    "How many unused Meridian PTO days can be carried into the next calendar year?",
    "ANSWER", ["meridian-pto-policy#carryover"],
    [{"fact": "up to 5 days", "aliases": ["5 days", "5 unused pto days"]}],
    ["10 days", "unlimited carryover"])

add("q013", "answerable_single",
    "What is the maximum unused PTO payout Meridian gives an employee who leaves the company?",
    "ANSWER", ["meridian-pto-policy#unused-pto-payout"],
    [{"fact": "up to a maximum of 10 days, at final base rate of pay", "aliases": ["10 days"]}],
    ["15 days", "unlimited payout"])

add("q014", "answerable_single",
    "Is there a per-person cap on client meal expenses under Meridian's expense policy?",
    "ANSWER", ["meridian-expense-policy#reimbursable-expenses"],
    [{"fact": "$50 per person cap on client meals", "aliases": ["$50 per person", "up to $50"]}],
    ["$100 per person", "no cap"])

add("q015", "answerable_single",
    "Who must approve a Meridian employee expense of $600?",
    "ANSWER", ["meridian-expense-policy#approval-thresholds"],
    [{"fact": "director approval, since it falls in the $200 to $1,000 range", "aliases": ["director approval"]}],
    ["cfo approval", "auto-approved"])

add("q016", "answerable_single",
    "How many weeks of paid parental leave does Meridian give the primary caregiver?",
    "ANSWER", ["meridian-hr-faq#parental-leave"],
    [{"fact": "12 weeks for the primary caregiver", "aliases": ["12 weeks"]}],
    ["4 weeks for the primary caregiver", "8 weeks"])

add("q017", "answerable_single",
    "On the Cascade POS terminal, above what refund amount is a manager PIN required?",
    "ANSWER", ["cascade-pos-manual#processing-refunds"],
    [{"fact": "over $100", "aliases": ["$100", "over $100"]}],
    ["over $50", "over $200"])

add("q018", "answerable_single",
    "What does error code E12 mean on the Cascade POS terminal?",
    "ANSWER", ["cascade-pos-manual#error-codes"],
    [{"fact": "lost sync with the manager portal; transactions queue locally until connectivity is restored",
      "aliases": ["lost sync", "queue locally"]}],
    ["card reader connection failure", "receipt printer paper jam"])

add("q019", "answerable_single",
    "How many Cascade Rewards points equal a $5 reward?",
    "ANSWER", ["cascade-support-faq#loyalty-program"],
    [{"fact": "100 points", "aliases": ["100 points"]}],
    ["50 points", "200 points"])

add("q020", "answerable_single",
    "Within how many days of delivery must a Cascade customer report a missing or damaged item?",
    "ANSWER", ["cascade-support-faq#order-issues"],
    [{"fact": "within 7 days of delivery", "aliases": ["7 days"]}],
    ["14 days", "30 days"])

# ---- 8 multi-document answerable ----------------------------------------
add("q021", "answerable_multi",
    "If a SecureLink customer has repeated connection drops, which protocol should they switch to, and does CloudVault offer the same scheduling UI on Linux as it does on Windows and macOS?",
    "ANSWER",
    ["solstice-vpn-manual#troubleshooting-connection-drops", "solstice-backup-manual#supported-platforms"],
    [{"fact": "switch to OpenVPN", "aliases": ["openvpn"]},
     {"fact": "no, Linux has no scheduling UI / no native Linux agent", "aliases": ["no linux agent", "no scheduling ui on linux", "command-line uploader"]}],
    [])

add("q022", "answerable_multi",
    "Under Meridian's current remote work policy, is the $500 home office stipend counted against the expense policy's rule that home office equipment is non-reimbursable?",
    "ANSWER",
    ["meridian-remote-work-v2#home-office-stipend", "meridian-expense-policy#non-reimbursable-items"],
    [{"fact": "no, the $500 stipend is separate from and not deducted against the expense policy's general limits",
      "aliases": ["separate from", "not deducted"]}],
    ["it is deducted from the reimbursement limit", "it is not offered at all"])

add("q023", "answerable_multi",
    "Should a Meridian employee check the HR FAQ or the Remote Work Policy for the current home office stipend amount, and what is that amount?",
    "ANSWER",
    ["meridian-hr-faq#remote-work-faq", "meridian-remote-work-v2#equipment"],
    [{"fact": "the Remote Work Policy, not the FAQ, governs this; the FAQ explicitly defers to it", "aliases": ["remote work policy", "governed by"]},
     {"fact": "$500 stipend", "aliases": ["$500"]}],
    [])

add("q024", "answerable_multi",
    "Under Cascade's current returns policy, how many days does a customer have to return a purchase, and does the support FAQ offer an extended warranty on electronics?",
    "ANSWER",
    ["cascade-returns-policy-v2#return-window", "cascade-support-faq#warranty"],
    [{"fact": "45 days generally (14 days for electronics)", "aliases": ["45 days"]},
     {"fact": "no extended warranty; only the manufacturer's warranty applies", "aliases": ["no extended warranty", "manufacturer's warranty"]}],
    ["30 days", "cascade offers an extended warranty"])

add("q025", "answerable_multi",
    "If a Cascade POS terminal shows error E12, are transactions lost, and per the support FAQ, how long does a customer have to report a missing item from an order?",
    "ANSWER",
    ["cascade-pos-manual#error-codes", "cascade-support-faq#order-issues"],
    [{"fact": "transactions are not lost; they queue locally until connectivity returns", "aliases": ["queue locally", "not lost"]},
     {"fact": "7 days", "aliases": ["7 days"]}],
    ["transactions are lost"])

add("q026", "answerable_multi",
    "Can a Meridian employee get their unused PTO paid out while taking parental leave, and how many weeks of paid parental leave does the secondary caregiver get?",
    "ANSWER",
    ["meridian-pto-policy#unused-pto-payout", "meridian-hr-faq#parental-leave"],
    [{"fact": "PTO payout only happens upon separation from the company, not during parental leave", "aliases": ["separation", "upon separation"]},
     {"fact": "4 weeks for the secondary caregiver", "aliases": ["4 weeks"]}],
    ["pto is paid out during parental leave"])

add("q027", "answerable_multi",
    "Per the Solstice FAQ, can a customer buy just the VPN client, and per the VPN manual, can an individual user opt out of two-factor authentication?",
    "ANSWER",
    ["solstice-faq#general", "solstice-vpn-manual#login-and-authentication"],
    [{"fact": "no, only the combined subscription is sold", "aliases": ["combined subscription"]},
     {"fact": "no per-user opt-out; 2FA is enforced automatically if the org has it enabled", "aliases": ["no per-user opt-out", "enforced automatically"]}],
    ["users can opt out of 2fa individually"])

add("q028", "answerable_multi",
    "For a Meridian expense of $600, what approval level is required, and is that expense category affected by the remote work policy's stipend rules?",
    "ANSWER",
    ["meridian-expense-policy#approval-thresholds", "meridian-remote-work-v2#home-office-stipend"],
    [{"fact": "director approval (the $200-$1,000 range)", "aliases": ["director approval"]},
     {"fact": "the home office stipend is a separate benefit and not deducted from expense approval limits", "aliases": ["separate", "not deducted"]}],
    [])

# ---- 4 version-sensitive answerable --------------------------------------
add("q029", "answerable_version",
    "Under Meridian's current remote work policy, does the company provide a home office equipment stipend, and if so how much?",
    "ANSWER", ["meridian-remote-work-v2#equipment"],
    [{"fact": "yes, a one-time $500 stipend", "aliases": ["$500"]}],
    ["no stipend", "bring-your-own-device with no stipend", "$0"],
    notes="Version-sensitive: v1 (superseded) is BYOD with no stipend; only v2 (current) has the $500 stipend.")

add("q030", "answerable_version",
    "Under Cascade's current returns policy, what is the standard return window, and is there an exception for electronics?",
    "ANSWER", ["cascade-returns-policy-v2#return-window"],
    [{"fact": "45 days generally, 14 days for electronics", "aliases": ["45 days"]}],
    ["30 days"],
    notes="Version-sensitive: v1 (superseded) states a 30-day window with no electronics exception.")

add("q031", "answerable_version",
    "Under Meridian's current remote work policy, can an approved employee work fully remote, and what extra approval does that require?",
    "ANSWER", ["meridian-remote-work-v2#eligibility", "meridian-remote-work-v2#work-hours"],
    [{"fact": "yes, up to 5 days per week for approved roles, with director-level sign-off", "aliases": ["director", "5 days"]}],
    ["fully remote work is not allowed", "no employees may work more than 2 days remotely"],
    notes="Version-sensitive: v1 (superseded) caps everyone at 2 days/week and has no fully-remote or director sign-off provision.")

add("q032", "answerable_version",
    "Under Cascade's current returns policy, can a customer choose store credit instead of a refund to their original payment method?",
    "ANSWER", ["cascade-returns-policy-v2#refund-method"],
    [{"fact": "yes, store credit is an option (except for final-sale items)", "aliases": ["store credit"]}],
    ["no, only the original payment method", "refunds are cash only"],
    notes="Version-sensitive: v1 (superseded) allows refunds to the original payment method only, no store credit option.")

# ---- 8 unanswerable -------------------------------------------------------
add("q033", "unanswerable", "What is the Wi-Fi signal range of the Cascade POS terminal?", "ABSTAIN")
add("q034", "unanswerable", "Does Solstice Systems offer a mobile app version of SecureLink for iOS or Android?", "ABSTAIN")
add("q035", "unanswerable", "What is Meridian Health Partners' minimum wage floor by state?", "ABSTAIN")
add("q036", "unanswerable", "How many CloudVault storage buckets can a single Solstice customer configure?", "ABSTAIN")
add("q037", "unanswerable", "Is there a maximum total number of Cascade Rewards points a customer can accumulate?", "ABSTAIN")
add("q038", "unanswerable", "Does Cascade Retail Co offer price matching with competitor stores?", "ABSTAIN")
add("q039", "unanswerable", "What color options are available for the Cascade POS terminal hardware itself?", "ABSTAIN")
add("q040", "unanswerable", "What is Meridian Health Partners' policy on paid jury duty leave?", "ABSTAIN")

assert len(Q) == 40, len(Q)
counts = {}
for q in Q:
    counts[q["category"]] = counts.get(q["category"], 0) + 1
assert counts == {
    "answerable_single": 20,
    "answerable_multi": 8,
    "answerable_version": 4,
    "unanswerable": 8,
}, counts

with open("eval/questions.jsonl", "w", encoding="utf-8") as f:
    for q in Q:
        f.write(json.dumps(q) + "\n")

print(f"Wrote {len(Q)} questions -> eval/questions.jsonl; category counts: {counts}")
