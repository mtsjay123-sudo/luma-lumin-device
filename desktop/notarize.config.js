// The Mac build with an Apple Developer ID: signed with the certificate in CSC_LINK,
// hardened runtime on, and notarized by Apple (APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD /
// APPLE_TEAM_ID). Then macOS opens Luma with no warning. Without those, CI makes the
// ad-hoc signed build from package.json instead.
const base = require("./package.json").build;
const { identity, ...mac } = base.mac; // let electron-builder find the Developer ID certificate

module.exports = { ...base, mac: { ...mac, hardenedRuntime: true, notarize: true } };
