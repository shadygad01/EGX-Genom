import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildApp } from "./app.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const port = Number(process.env.PORT ?? 3001);
const knowledgeStorePath =
  process.env.KNOWLEDGE_STORE_PATH ??
  path.resolve(__dirname, "../../research/data/knowledge_store.example.json");

const app = buildApp(knowledgeStorePath);

app
  .listen({ port, host: "0.0.0.0" })
  .catch((err) => {
    app.log.error(err);
    process.exit(1);
  });
