// The cloud brain for Luma Plus, at the path Anthropic's own client library asks for: /api/luma/brain/v1/messages.
// A Luma at home points the library here with its device sign-in instead of an API key. See api/_lib/luma-cloud.js ("brain").
import { createHandler } from "../../../_lib/luma-cloud.js";
import { makeSupabaseDb } from "../../../_lib/luma-db.js";

const handler = createHandler(() => ({ env: process.env, db: makeSupabaseDb(process.env, fetch), fetch }));

export default function brain(req, res) {
  req.query = { ...(req.query || {}), route: "brain" };
  return handler(req, res);
}

export const config = { maxDuration: 60 }; // a hard ask can think for most of a minute before its first words
