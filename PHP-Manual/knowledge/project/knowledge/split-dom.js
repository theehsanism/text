const fs = require("fs");
const path = require("path");

const OUTPUT_DIR = path.join(__dirname, "dom-output");
const SPLIT_DIR = path.join(__dirname, "dom-split");
const TARGET_SIZE = 3 * 1024 * 1024; // 3MB target per file

if (!fs.existsSync(SPLIT_DIR)) fs.mkdirSync(SPLIT_DIR, { recursive: true });

const files = fs.readdirSync(OUTPUT_DIR).filter((f) => f.endsWith(".json"));

const splitIndex = {};

for (const file of files) {
  const data = JSON.parse(fs.readFileSync(path.join(OUTPUT_DIR, file), "utf-8"));
  const cat = data.category;
  const pages = data.pages;
  const pageKeys = Object.keys(pages);

  if (pageKeys.length <= 80) {
    fs.copyFileSync(path.join(OUTPUT_DIR, file), path.join(SPLIT_DIR, file));
    splitIndex[cat] = { files: [file], totalPages: pageKeys.length };
    continue;
  }

  // Sort keys alphabetically, then chunk by accumulated size
  pageKeys.sort();
  const chunks = [];
  let currentChunk = [];
  let currentSize = 0;

  for (const key of pageKeys) {
    const pageSize = JSON.stringify({ [key]: pages[key] }).length;
    if (currentSize + pageSize > TARGET_SIZE && currentChunk.length > 0) {
      chunks.push(currentChunk);
      currentChunk = [];
      currentSize = 0;
    }
    currentChunk.push(key);
    currentSize += pageSize;
  }
  if (currentChunk.length > 0) chunks.push(currentChunk);

  const catFiles = [];
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const chunkPages = {};
    for (const k of chunk) chunkPages[k] = pages[k];

    const chunkName = `dom-${cat}-${String(i + 1).padStart(2, "0")}.json`;
    const chunkData = {
      category: cat,
      chunk: i + 1,
      totalChunks: chunks.length,
      pageCount: chunk.length,
      pageRange: { from: chunk[0], to: chunk[chunk.length - 1] },
      pages: chunkPages,
    };
    fs.writeFileSync(path.join(SPLIT_DIR, chunkName), JSON.stringify(chunkData));
    catFiles.push(chunkName);
  }

  splitIndex[cat] = { files: catFiles, totalPages: pageKeys.length };
  console.log(`${cat}: ${pageKeys.length} pages -> ${catFiles.length} files`);
}

// Update index
const indexFile = path.join(__dirname, "dom-structure-index.json");
const existingIndex = JSON.parse(fs.readFileSync(indexFile, "utf-8"));
existingIndex.splitFiles = splitIndex;
existingIndex.meta.splitDir = "knowledge/dom-split/";
existingIndex.meta.compactOutputDir = "knowledge/dom-output/";
fs.writeFileSync(indexFile, JSON.stringify(existingIndex, null, 2));

console.log("\nSplit index written to dom-structure-index.json");
console.log(`Total split files: ${Object.values(splitIndex).reduce((a, c) => a + c.files.length, 0)}`);
