# PHP Manual Knowledge Graph

Built from **only** the main content node `/html/body/div[3]/div/div` of all 15,237 pages.
Formula: **tags + classes + links + children**.

## Key finding
The `class` of that root div is a DocBook page type and fully determines the page's structure (12 types):

| type | pages | typical children |
|---|---|---|
| refentry | 11163 | refnamediv > description > parameters > returnvalues > examples > seealso |
| section | 1462 | title > para / nested section |
| reference | 960 | title > partintro > chunklist_reference (class/extension index) |
| chapter | 509 | h1 > h2 > chunklist_chapter |
| sect1 | 306 | title > sect2 ... |
| appendix | 268 | h1 > simpara / dl |
| book | 259 | title > chunklist_book (one extension) |
| preface | 241 | title > para (intro) |
| set | 33 | title > chunklist_set |
| part | 19 | h1 > chunklist_part |
| article | 16 | free form |
| root | 1 | copyright page |

## Files
- `nodes/<section>.json` — one node per page: `id, type, section, path, title, purpose, children[{tag,class,id}], tags{}, classes{}, out_links`
- `edges/child_of.json` — hierarchy from breadcrumbs (15,236 edges, single tree rooted at `index`)
- `edges/links_to.json` — internal links inside the content node (84,141 edges, weight = link count)
- `ontology.json` — page types with their canonical child structures, all 855 classes with the page types they appear in, tag counts
