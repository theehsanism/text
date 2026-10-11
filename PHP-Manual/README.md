# PHP Manual (organized)

Pages grouped by the 11 top-level sections of the official table of contents
(`data/toc/all-sections.json`). Internal links between pages were rewritten to the new locations.

| Folder | Section | Pages |
|---|---|---|
| [01-copyright](manual/01-copyright/) | Copyright | 1 |
| [02-php-manual](manual/02-php-manual/) | PHP Manual | 3 |
| [03-getting-started](manual/03-getting-started/) | Getting Started | 11 |
| [04-installation-and-configuration](manual/04-installation-and-configuration/) | Installation and Configuration | 49 |
| [05-language-reference](manual/05-language-reference/) | Language Reference | 247 |
| [06-security](manual/06-security/) | Security | 28 |
| [07-features](manual/07-features/) | Features | 35 |
| [08-function-reference](manual/08-function-reference/) | Function Reference | 14446 |
| [09-php-at-the-core-a-hackers-guide](manual/09-php-at-the-core-a-hackers-guide/) | PHP at the Core: A Hacker's Guide | 213 |
| [10-faq](manual/10-faq/) | FAQ | 12 |
| [11-appendices](manual/11-appendices/) | Appendices | 192 |

## Other folders
- `data/toc/` – table-of-contents tree (`toc-tree.json`), all sections, one file per section.
- `data/search/` – search index and descriptions.
- `data/page-index.json` – map of every page name to its new path.
- `data/original-file-tree.json` – file tree of the original export.
- `tools/toc-parser/` – script that builds the TOC JSON from `index.html` (`python3 parse.py`).
- `tools/dom-knowledge/` – DOM-split data and helper scripts.

Entry point: [manual/02-php-manual/index.html](manual/02-php-manual/index.html)
