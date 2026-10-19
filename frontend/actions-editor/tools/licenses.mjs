// Writes THIRD_PARTY_LICENSES.txt beside the bundle: the name, version and
// licence of every npm package esbuild put in it, read from its metafile.
// Fails when a package has no licence file.
import {readFileSync, writeFileSync, existsSync, readdirSync} from "node:fs";
import {join} from "node:path";

const [metafile, out] = process.argv.slice(2);
const meta = JSON.parse(readFileSync(metafile, "utf8"));
const packages = new Map();
for (const input of Object.keys(meta.inputs)) {
  const match = /node_modules\/((?:@[^/]+\/)?[^/]+)\//.exec(input);
  if (match) packages.set(match[1], join("node_modules", match[1]));
}
let text = "FormShare's actions editor bundles these packages.\n";
for (const [name, dir] of [...packages].sort((x, y) => x[0].localeCompare(y[0]))) {
  const pkg = JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
  const licence = readdirSync(dir).find(f => /^licen[cs]e/i.test(f));
  if (!licence || !existsSync(join(dir, licence))) {
    console.error("No licence file in " + dir);
    process.exit(1);
  }
  text += "\n" + "=".repeat(78) + "\n" + name + " " + pkg.version + " (" + pkg.license + ")\n" + "=".repeat(78) + "\n\n";
  text += readFileSync(join(dir, licence), "utf8").trim() + "\n";
}
writeFileSync(out, text);
console.log("Wrote " + out + ": " + packages.size + " packages");
