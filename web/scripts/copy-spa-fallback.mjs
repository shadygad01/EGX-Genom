import { copyFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));

// GitHub Pages has no rewrite rules. Serving the Vite entrypoint as 404.html
// lets React Router handle direct visits to /portfolio, /cases, /market, etc.
await copyFile(`${webRoot}dist/index.html`, `${webRoot}dist/404.html`);
