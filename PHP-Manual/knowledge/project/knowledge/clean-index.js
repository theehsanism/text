const fs = require("fs");
const path = require("path");

const indexFile = path.join(__dirname, "dom-structure-index.json");
const index = JSON.parse(fs.readFileSync(indexFile, "utf-8"));

// Remove stale references
delete index.meta.compactOutputDir;
index.meta.splitDir = "knowledge/dom-split/";

// Remove old single-file references from categories
for (const [cat, info] of Object.entries(index.categories)) {
  delete info.file;
}

// Reorder for readability
const cleaned = {
  meta: index.meta,
  stats: index.stats,
  categories: {},
  splitFiles: index.splitFiles,
};

// Merge category info with splitFiles for each category
for (const cat of Object.keys(index.categories)) {
  cleaned.categories[cat] = {
    pages: index.categories[cat].pages,
    skipped: index.categories[cat].skipped,
    files: index.splitFiles[cat].files,
  };
}

// Add file sizes
for (const cat of Object.keys(cleaned.categories)) {
  const files = cleaned.categories[cat].files;
  cleaned.categories[cat].fileDetails = files.map((f) => {
    const stat = fs.statSync(path.join(__dirname, "dom-split", f));
    return {
      name: f,
      sizeKB: Math.round(stat.size / 1024),
    };
  });
}

fs.writeFileSync(indexFile, JSON.stringify(cleaned, null, 2));
console.log("Index cleaned and updated");
