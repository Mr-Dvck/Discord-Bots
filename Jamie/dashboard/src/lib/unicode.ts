/**
 * Mathematical Sans-Serif Bold — modern bold unicode for Discord channel names.
 * Titles use a capital at the start of each word (and after - / _).
 */

export function toBoldUnicode(text: string): string {
  let out = "";
  for (const ch of text) {
    const o = ch.codePointAt(0) ?? 0;
    if (o >= 0x41 && o <= 0x5a) {
      out += String.fromCodePoint(0x1d5d4 + (o - 0x41));
    } else if (o >= 0x61 && o <= 0x7a) {
      out += String.fromCodePoint(0x1d5ee + (o - 0x61));
    } else if (o >= 0x30 && o <= 0x39) {
      out += String.fromCodePoint(0x1d7ec + (o - 0x30));
    } else {
      out += ch;
    }
  }
  return out;
}

/** Capitalize first letter of title and after space / hyphen / underscore. */
export function titleCaseWords(text: string): string {
  let out = "";
  let capNext = true;
  for (const ch of text) {
    if (capNext && /[a-zA-Z]/.test(ch)) {
      out += ch.toUpperCase();
      capNext = false;
    } else if (ch === " " || ch === "-" || ch === "_") {
      out += ch;
      capNext = true;
    } else if (/[a-zA-Z0-9]/.test(ch)) {
      out += ch.toLowerCase();
      capNext = false;
    } else {
      out += ch;
    }
  }
  return out;
}

export function channelDisplayName(
  name: string,
  opts?: { category?: boolean }
): string {
  let raw = (name || "").trim();
  if (!raw) raw = "Channel";
  if (!opts?.category) {
    raw = raw.replace(/\s+/g, "-");
  }
  for (const ch of raw) {
    const cp = ch.codePointAt(0) ?? 0;
    if (cp >= 0x1d400 && cp <= 0x1d7ff) {
      return raw.slice(0, 100);
    }
  }
  return toBoldUnicode(titleCaseWords(raw)).slice(0, 100);
}
