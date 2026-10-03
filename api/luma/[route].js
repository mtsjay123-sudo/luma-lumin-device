// Luma Cloud routes: /api/luma/<route>. See api/_lib/luma-cloud.js.
import { createHandler } from "../_lib/luma-cloud.js";
import { makeSupabaseDb } from "../_lib/luma-db.js";

export default createHandler(() => ({ env: process.env, db: makeSupabaseDb(process.env, fetch), fetch }));
