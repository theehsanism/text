#!/usr/bin/env python3
"""
Parse index.html — extract each of the 11 lists into individual JSON files
plus one combined file with titles as keys.

Rules:
  - Every element node has: tag, and optionally class, text, href, children
    (fields are ONLY included when they have content — no empty [], "", etc.)
  - text = direct text nodes + text from <a> children (in document order).
    <ul> has no text. <li> text = its <a> label + any trailing text.
  - href = only for <a> tags that actually have it.
  - class = array of class names, only if the element has classes.
  - children = array of child nodes, only if non-empty.
  - File names derived from the <a> text of each top-level <li> (slugified).
  - all_lists.json is a dict keyed by section title.
"""

import json
import os
import re
from html.parser import HTMLParser


# ── DOM Model ─────────────────────────────────────────────────────────

class DOMNode:
    __slots__ = ('tag', 'attrs', 'children', 'parent')

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs) if attrs else {}
        self.children = []  # list of DOMNode | str
        self.parent = None


class DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = DOMNode('#root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = DOMNode(tag, attrs)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def get_node_text(node):
    """Text = direct text nodes + text from <a> children, in document order.

    This means:
      <li> text = <a> child's text + trailing text  (e.g. "FAQ — FAQ: ...")
      <a>  text = the link text
      <ul> text = "" (no direct text, children are <li> not <a>)
    """
    parts = []
    for child in node.children:
        if isinstance(child, str):
            s = child.strip()
            if s:
                parts.append(s)
        elif child.tag == 'a':
            t = get_node_text(child)
            if t:
                parts.append(t)
    return ' '.join(parts).strip()


def slugify(text):
    """Convert text to a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[''`:]", '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def node_to_dict(node):
    """Convert a DOMNode to a clean JSON dict — only non-empty fields."""
    result = {"tag": node.tag}

    # class — only if present
    cls = node.attrs.get("class", "")
    if cls:
        result["class"] = cls.split()

    # text — only if non-empty
    text = get_node_text(node)
    if text:
        result["text"] = text

    # href — only for <a> tags that have it
    if node.tag == "a":
        href = node.attrs.get("href", "")
        if href:
            result["href"] = href

    # children — only if non-empty
    child_nodes = [c for c in node.children if not isinstance(c, str)]
    if child_nodes:
        result["children"] = [node_to_dict(c) for c in child_nodes]

    return result


# ── Main ──────────────────────────────────────────────────────────────

with open('index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

builder = DOMBuilder()
builder.feed(html_content)

root_ul = None
for child in builder.root.children:
    if not isinstance(child, str) and child.tag == 'ul':
        root_ul = child
        break

if not root_ul:
    print("ERROR: Could not find root <ul>!")
    exit(1)

top_items = [c for c in root_ul.children
             if not isinstance(c, str) and c.tag == 'li']

print(f"Found {len(top_items)} top-level <li> items\n")

# Clean output directory of old files
os.makedirs('output', exist_ok=True)
for old in os.listdir('output'):
    os.remove(os.path.join('output', old))

# Build section names from the <a> text of each top-level <li>
sections = []
for item in top_items:
    # Find the <a> child to get the section name
    a_child = None
    for c in item.children:
        if not isinstance(c, str) and c.tag == 'a':
            a_child = c
            break
    if a_child:
        section_name = get_node_text(a_child)
    else:
        section_name = get_node_text(item)
    slug = slugify(section_name)
    sections.append((section_name, slug))

# Write 11 individual files
all_dicts = {}  # keyed by section name for combined file
for i, item in enumerate(top_items):
    d = node_to_dict(item)
    section_name, slug = sections[i]
    fname = f"output/{slug}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    child_count = len(d.get("children", []))
    print(f"  [{i+1:2d}] {fname:45s}  title=\"{section_name}\"  children={child_count}")
    all_dicts[section_name] = d

# Write combined file with titles as keys
with open('output/all_lists.json', 'w', encoding='utf-8') as f:
    json.dump(all_dicts, f, ensure_ascii=False, indent=2)
print(f"\n  Combined: output/all_lists.json ({len(all_dicts)} sections)")


# ── Verification ──────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("VERIFICATION — PHASE 1: No empty fields anywhere")
print("=" * 70)

def check_no_empty_fields(node, path="root"):
    """Recursively verify no empty [], "", or unnecessary fields exist."""
    issues = []
    for key, val in node.items():
        if key == "tag":
            continue
        if val == "" or val == [] or val == {}:
            issues.append(f"   EMPTY: {path}.{key} = {repr(val)}")
        if key == "children" and isinstance(val, list):
            for idx, child in enumerate(val):
                issues.extend(check_no_empty_fields(child, f"{path}.children[{idx}]"))
    return issues

issues = []
for section_name, d in all_dicts.items():
    section_issues = check_no_empty_fields(d, section_name)
    issues.extend(section_issues)

if issues:
    for iss in issues:
        print(iss)
else:
    print("   No empty fields found anywhere. OK.")

# ── Phase 2: <ul> elements have NO text field ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 2: <ul> elements have no text field")
print("-" * 70)

def collect_by_tag(node, tag_name):
    result = []
    if node.get("tag") == tag_name:
        result.append(node)
    for c in node.get("children", []):
        result.extend(collect_by_tag(c, tag_name))
    return result

ul_issues = []
for section_name, d in all_dicts.items():
    for ul in collect_by_tag(d, 'ul'):
        if "text" in ul:
            ul_issues.append(f"   {section_name}: <ul> has text=\"{ul['text'][:50]}\"")

if ul_issues:
    for iss in ul_issues:
        print(iss)
else:
    print("   No <ul> has a text field. OK.")

# ── Phase 3: Every <a> has href and text ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 3: Every <a> has both text and href")
print("-" * 70)

a_issues = []
for section_name, d in all_dicts.items():
    for a in collect_by_tag(d, 'a'):
        if "href" not in a:
            a_issues.append(f"   {section_name}: <a> missing href, text=\"{a.get('text','?')}\"")
        if "text" not in a:
            a_issues.append(f"   {section_name}: <a> missing text, href=\"{a.get('href','?')}\"")

if a_issues:
    for iss in a_issues:
        print(iss)
else:
    print("   All <a> elements have both text and href. OK.")

# ── Phase 4: Class extraction ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 4: <ul> classes are properly split arrays")
print("-" * 70)

class_issues = []
for section_name, d in all_dicts.items():
    for ul in collect_by_tag(d, 'ul'):
        if "class" not in ul:
            class_issues.append(f"   {section_name}: <ul> missing class")
        else:
            expected = ["chunklist", "chunklist_set", "chunklist_children"]
            if ul["class"] != expected:
                class_issues.append(f"   {section_name}: <ul> class={ul['class']}, expected={expected}")

if class_issues:
    for iss in class_issues:
        print(iss)
else:
    print("   All <ul> classes are correct arrays. OK.")

# ── Phase 5: Special text after </a> ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 5: Special text (after </a>) is correct")
print("-" * 70)

specials = [
    ("FAQ", "FAQ — FAQ: Frequently Asked Questions", "faq.html"),
    ("Features", "Command line usage — Using PHP from the command line", "features.commandline.html"),
    ("FAQ", "Password Hashing — Safe Password Hashing", "faq.passwords.html"),
]

def find_li_with_text(node, target_text):
    if node.get("tag") == "li" and node.get("text") == target_text:
        return node
    for c in node.get("children", []):
        r = find_li_with_text(c, target_text)
        if r:
            return r
    return None

def find_a_with_href(node, target_href):
    if node.get("tag") == "a" and node.get("href") == target_href:
        return node
    for c in node.get("children", []):
        r = find_a_with_href(c, target_href)
        if r:
            return r
    return None

special_ok = True
for section, expected_text, href in specials:
    d = all_dicts.get(section)
    if not d:
        print(f"   Section '{section}' not found!")
        special_ok = False
        continue
    li = find_li_with_text(d, expected_text)
    if not li:
        print(f"   NOT FOUND: li text=\"{expected_text}\"")
        special_ok = False
        continue
    a = find_a_with_href(li, href)
    if not a:
        print(f"   NOT FOUND: <a> href={href} inside that <li>")
        special_ok = False
        continue
    print(f"   OK: li.text=\"{expected_text}\"  a.text=\"{a.get('text','')}\"  a.href={href}")

# ── Phase 6: Expected child counts ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 6: Child count per section")
print("-" * 70)

expected_counts = {
    "Copyright": 0, "PHP Manual": 1, "Getting Started": 2,
    "Installation and Configuration": 9, "Language Reference": 19,
    "Security": 13, "Features": 12, "Function Reference": 27,
    "PHP at the Core: A Hacker's Guide": 16,
    "FAQ": 11, "Appendices": 29,
}

count_ok = True
for section_name, d in all_dicts.items():
    # Count <li> inside the <ul> child
    ul_children = [c for c in d.get("children", []) if c.get("tag") == "ul"]
    li_count = 0
    for ul in ul_children:
        li_count += sum(1 for c in ul.get("children", []) if c.get("tag") == "li")
    exp = expected_counts.get(section_name)
    if exp is None:
        print(f"   {section_name}: no expected count defined")
        continue
    ok = "OK" if li_count == exp else "MISMATCH!"
    if li_count != exp:
        count_ok = False
    print(f"   {section_name:45s}  expected={exp:2d}  actual={li_count:2d}  {ok}")

# ── Phase 7: File naming ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 7: File names are slugified titles, not numbers")
print("-" * 70)

expected_files = [
    "copyright.json",
    "php-manual.json",
    "getting-started.json",
    "installation-and-configuration.json",
    "language-reference.json",
    "security.json",
    "features.json",
    "function-reference.json",
    "php-at-the-core-a-hackers-guide.json",
    "faq.json",
    "appendices.json",
]

actual_files = sorted(f for f in os.listdir('output') if f != 'all_lists.json')
expected_sorted = sorted(expected_files)

if actual_files == expected_sorted:
    print("   File names are correct slugified titles. OK.")
else:
    print("   MISMATCH!")
    print(f"   Expected: {expected_sorted}")
    print(f"   Actual:   {actual_files}")

# ── Phase 8: all_lists.json structure ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 8: all_lists.json is keyed by section title")
print("-" * 70)

with open('output/all_lists.json', 'r') as f:
    combined = json.load(f)

if not isinstance(combined, dict):
    print("   FAIL: all_lists.json is not a dict/object")
else:
    print(f"   Type: dict with {len(combined)} keys")
    for key in combined:
        print(f"     \"{key}\"")
    expected_keys = list(expected_counts.keys())
    if list(combined.keys()) == expected_keys:
        print("   Keys match section titles in order. OK.")
    else:
        print(f"   Key order mismatch!")
        print(f"   Expected: {expected_keys}")
        print(f"   Actual:   {list(combined.keys())}")

# ── Phase 9: Re-read individual files match combined ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 9: Individual files match combined file")
print("-" * 70)

match_ok = True
for section_name, slug in sections:
    with open(f"output/{slug}.json", 'r') as f:
        individual = json.load(f)
    combined_entry = combined[section_name]
    if individual == combined_entry:
        pass  # match
    else:
        print(f"   MISMATCH: {slug}.json vs all_lists.json[{section_name}]")
        match_ok = False

if match_ok:
    print("   All 11 individual files match their entries in all_lists.json. OK.")

# ── Phase 10: Independent cross-verification ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 10: Independent manual parser cross-check")
print("-" * 70)

def manual_parse(html_str):
    """Parse HTML by manually scanning characters. Completely independent
    from html.parser. Returns dict keyed by section title."""

    pos = 0
    n = len(html_str)

    def parse_element(p):
        p += 1  # skip '<'
        start = p
        while p < n and html_str[p] not in ' \t\n\r>':
            p += 1
        tag = html_str[start:p].lower()
        # Parse attributes
        attrs = {}
        while p < n and html_str[p] != '>':
            while p < n and html_str[p] in ' \t\n\r':
                p += 1
            if p >= n or html_str[p] == '>':
                break
            s = p
            while p < n and html_str[p] not in ' \t\n\r=>':
                p += 1
            name = html_str[s:p].lower()
            while p < n and html_str[p] in ' \t\n\r':
                p += 1
            if p < n and html_str[p] == '=':
                p += 1
                while p < n and html_str[p] in ' \t\n\r':
                    p += 1
                if p < n and html_str[p] == '"':
                    p += 1
                    s = p
                    while p < n and html_str[p] != '"':
                        p += 1
                    attrs[name] = html_str[s:p]
                    p += 1
                elif p < n and html_str[p] == "'":
                    p += 1
                    s = p
                    while p < n and html_str[p] != "'":
                        p += 1
                    attrs[name] = html_str[s:p]
                    p += 1
                else:
                    s = p
                    while p < n and html_str[p] not in ' \t\n\r>':
                        p += 1
                    attrs[name] = html_str[s:p]
            else:
                attrs[name] = ''
        p += 1  # skip '>'

        ordered = []  # [("text", str), ("elem", dict), ...]

        while p < n:
            ts = p
            while p < n and html_str[p] != '<':
                p += 1
            if p > ts:
                t = html_str[ts:p].strip()
                if t:
                    ordered.append(("text", t))
            if p >= n:
                break
            if p + 1 < n and html_str[p+1] == '/':
                p += 2
                while p < n and html_str[p] != '>':
                    p += 1
                p += 1
                break
            else:
                child, p = parse_element(p)
                ordered.append(("elem", child))

        # Build text: direct text + <a> children text only
        text_parts = []
        children = []
        for itype, ival in ordered:
            if itype == "text":
                text_parts.append(ival)
            else:
                children.append(ival)
                if ival["tag"] == "a" and "text" in ival:
                    text_parts.append(ival["text"])
        text = ' '.join(text_parts).strip()

        node = {"tag": tag}
        cls = attrs.get("class", "")
        if cls:
            node["class"] = cls.split()
        if text:
            node["text"] = text
        if tag == "a" and attrs.get("href", ""):
            node["href"] = attrs["href"]
        if children:
            node["children"] = children
        return node, p

    # Find root <ul>
    sp = 0
    while sp < n:
        if html_str[sp] == '<':
            tp = sp + 1
            while tp < n and html_str[tp] in ' \t\n\r':
                tp += 1
            if html_str[tp:tp+2].lower() == 'ul' and (tp+2 >= n or html_str[tp+2] in ' \t\n\r>'):
                root, sp = parse_element(sp)
                lis = [c for c in root.get("children", []) if c["tag"] == "li"]
                # Build dict keyed by section name (from <a> text)
                result = {}
                for li in lis:
                    a = None
                    for c in li.get("children", []):
                        if c["tag"] == "a":
                            a = c
                            break
                    title = a["text"] if a and "text" in a else li.get("text", "")
                    result[title] = li
                return result
        sp += 1
    return {}

manual_result = manual_parse(html_content)
print(f"   Manual parser found {len(manual_result)} sections")

manual_match = True
for section_name, d in all_dicts.items():
    if section_name not in manual_result:
        print(f"   {section_name}: NOT FOUND in manual parse")
        manual_match = False
        continue
    if manual_result[section_name] == d:
        pass
    else:
        print(f"   {section_name}: MISMATCH")
        def find_diff(a, b, path="root"):
            if a == b:
                return None
            if type(a) != type(b):
                return f"{path}: type {type(a).__name__} vs {type(b).__name__}"
            if isinstance(a, dict):
                for k in sorted(a.keys()):
                    if k not in b:
                        return f"{path}.{k}: missing in manual"
                    d2 = find_diff(a[k], b[k], f"{path}.{k}")
                    if d2:
                        return d2
                for k in sorted(b.keys()):
                    if k not in a:
                        return f"{path}.{k}: missing in main"
            elif isinstance(a, list):
                if len(a) != len(b):
                    return f"{path}: len {len(a)} vs {len(b)}"
                for idx, (ai, bi) in enumerate(zip(a, b)):
                    d2 = find_diff(ai, bi, f"{path}[{idx}]")
                    if d2:
                        return d2
            else:
                return f"{path}: '{a}' vs '{b}'"
            return None
        diff = find_diff(d, manual_result[section_name])
        print(f"      First diff: {diff}")
        manual_match = False

if manual_match:
    print("   All sections match between both parsers. OK.")
else:
    print("   >>> MANUAL PARSER CROSS-CHECK FAILED <<<")

# ── Phase 11: Show sample output ──
print("\n" + "-" * 70)
print("VERIFICATION — PHASE 11: Sample output (language-reference.json)")
print("-" * 70)

with open('output/language-reference.json', 'r') as f:
    sample = json.load(f)
print(json.dumps(sample, ensure_ascii=False, indent=2)[:2000])
print("   ...")

# ── Final ──
print("\n" + "=" * 70)
all_pass = (not issues and not ul_issues and not a_issues
            and not class_issues and special_ok and count_ok
            and actual_files == expected_sorted
            and match_ok and manual_match)
if all_pass:
    print(">>> ALL VERIFICATIONS PASSED <<<")
else:
    print(">>> SOME VERIFICATIONS FAILED — REVIEW ABOVE <<<")
print("=" * 70)
