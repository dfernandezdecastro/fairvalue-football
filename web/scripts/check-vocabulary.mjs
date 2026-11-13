// Rule R1 guard: fails if UI source contains verdict language (docs/PRODUCT_SPEC.md section 2).
// Run: npm run lint:vocab (also in CI). A line may opt out with a "vocab-ok" comment, only to explain what we do NOT say.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOTS = ["app", "components", "lib"];
const EXT = /\.(tsx?|mdx?)$/;
const BANNED = [
  /\bover-?paid\b/i,
  /\bunder-?paid\b/i,
  /\bbargains?\b/i,
  /\bsteals?\b/i,
  /\bflops?\b/i,
  /\btrue value\b/i,
  /\breal worth\b/i,
  /\bfair price\b/i,
  /\bmispric(ed|ing)\b/i,
  /\bover-?rated\b/i,
  /\bunder-?rated\b/i,
  /\bover-?valued\b/i,
  /\bunder-?valued\b/i,
  /\bbad (deal|signing|transfer)\b/i,
  /\bgood (deal|signing|transfer)\b/i,
];

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* files(p);
    else if (EXT.test(name)) yield p;
  }
}

const hits = [];
for (const root of ROOTS) {
  for (const file of files(root)) {
    readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        // Explicit, reviewable exception for sentences that explain what FairValue does NOT say.
        if (line.includes("vocab-ok")) return;
        for (const re of BANNED) if (re.test(line)) hits.push(`${relative(".", file)}:${i + 1}  ${line.trim()}`);
      });
  }
}
if (hits.length) {
  console.error("Banned verdict language found (rule R1, docs/PRODUCT_SPEC.md section 2):\n" + hits.join("\n"));
  process.exit(1);
}
console.log("vocabulary check: OK");
