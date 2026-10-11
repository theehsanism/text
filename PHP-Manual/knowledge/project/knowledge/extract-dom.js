const fs = require("fs");
const path = require("path");
const cheerio = require("cheerio");

const PHP_DIR = path.join(__dirname, "..", "Ref", "PHP");
const OUTPUT_DIR = path.join(__dirname, "dom-output");
const INDEX_FILE = path.join(__dirname, "dom-structure-index.json");

if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const htmlFiles = fs
  .readdirSync(PHP_DIR)
  .filter((f) => f.endsWith(".html"));

const index = {
  meta: {
    source: "Ref/PHP/*.html",
    xpath: "/html/body/div[3]/div/div",
    extractedFields: ["tag", "class", "href", "id", "children"],
    note: "Only structural metadata extracted — no text content included",
    totalFiles: htmlFiles.length,
    generatedAt: new Date().toISOString(),
  },
  categories: {},
  stats: {
    filesProcessed: 0,
    filesSkipped: 0,
    totalSections: 0,
    errors: [],
  },
};

// Categorize files by prefix
function categorize(filename) {
  const base = filename.replace(/\.html$/, "");
  if (base.startsWith("function.")) return "functions";
  if (base.startsWith("class.")) return "classes";
  if (base.startsWith("ref.")) return "references";
  if (base.startsWith("language.")) return "language";
  if (base.startsWith("about.")) return "about";
  if (base.startsWith("appendix.") || base.startsWith("aliases.") || base === "appendices") return "appendices";
  if (base.startsWith("book.") || base.startsWith("intro.") || base.startsWith("setup.")) return "books";
  if (base.startsWith("security.")) return "security";
  if (base.startsWith("faq.")) return "faq";
  if (base.startsWith("install.") || base.startsWith("configuration.")) return "installation";
  if (base.startsWith("history.")) return "history";
  if (base.startsWith("migration") || base.startsWith("upgrade.")) return "migration";
  if (base.startsWith("reserved.") || base.startsWith("aliases.")) return "reserved";
  if (base === "index") return "index";
  return "misc";
}

// Extract structure recursively (no text content)
function extractChildren($, el) {
  const result = [];
  const children = $(el).children().toArray();
  for (const child of children) {
    const $child = $(child);
    const entry = {
      tag: child.tagName.toLowerCase(),
      class: $child.attr("class") || null,
      href: $child.attr("href") || null,
      id: $child.attr("id") || null,
    };
    const sub = extractChildren($, child);
    if (sub.length > 0) {
      entry.children = sub;
    }
    result.push(entry);
  }
  return result;
}

function extractTopDiv($, el) {
  const $el = $(el);
  return {
    tag: "div",
    id: $el.attr("id") || null,
    class: $el.attr("class") || null,
    href: null,
    children: extractChildren($, el),
  };
}

// Group files by category
const categorized = {};
for (const file of htmlFiles) {
  const cat = categorize(file);
  if (!categorized[cat]) categorized[cat] = [];
  categorized[cat].push(file);
}

// Process each category
for (const [cat, files] of Object.entries(categorized)) {
  const catData = {};
  let catCount = 0;
  let catSkipped = 0;

  for (const file of files) {
    try {
      const raw = fs.readFileSync(path.join(PHP_DIR, file), "utf-8");
      const $ = cheerio.load(raw, { decodeEntities: false });

      // /html/body/div[3] — third direct child div of body
      const bodyDivs = $("body > div").toArray();
      if (bodyDivs.length < 3) {
        catSkipped++;
        index.stats.errors.push({ file, reason: `only ${bodyDivs.length} body>div` });
        continue;
      }

      const layoutDiv = bodyDivs[2]; // div[3]

      // /html/body/div[3]/div — first direct child div of layout
      const innerDivs = $(layoutDiv).children("div").toArray();
      if (innerDivs.length === 0) {
        catSkipped++;
        index.stats.errors.push({ file, reason: "no inner div" });
        continue;
      }

      const innerDiv = innerDivs[0];

      // /html/body/div[3]/div/div — all direct child divs of inner div
      const targetDivs = $(innerDiv).children("div").toArray();
      if (targetDivs.length === 0) {
        catSkipped++;
        index.stats.errors.push({ file, reason: "no target div" });
        continue;
      }

      const pageId = file.replace(/\.html$/, "");
      const sections = targetDivs.map((d) => extractTopDiv($, d));

      catData[pageId] = sections;
      catCount++;
      index.stats.totalSections += sections.length;
    } catch (e) {
      catSkipped++;
      index.stats.errors.push({ file, reason: e.message });
    }
  }

  // Write category file
  const catFilename = `dom-${cat}.json`;
  const catOutput = {
    category: cat,
    fileCount: catCount,
    skipped: catSkipped,
    pages: catData,
  };
  fs.writeFileSync(
    path.join(OUTPUT_DIR, catFilename),
    JSON.stringify(catOutput, null, 2)
  );

  index.categories[cat] = {
    file: catFilename,
    pages: catCount,
    skipped: catSkipped,
  };

  index.stats.filesProcessed += catCount;
  index.stats.filesSkipped += catSkipped;

  console.log(`[${cat}] ${catCount} processed, ${catSkipped} skipped`);
}

// Write index
if (index.stats.errors.length > 100) {
  index.stats.errors = index.stats.errors.slice(0, 100);
  index.stats.errorsTruncated = true;
}

fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));

console.log(`\nDone: ${index.stats.filesProcessed} files, ${index.stats.totalSections} sections, ${index.stats.filesSkipped} skipped`);
console.log(`Output: ${OUTPUT_DIR}/ and ${INDEX_FILE}`);
