/**
 * Fallback glyph handler that serves pre-built Noto Sans (GoNotoKurrent) PBF
 * glyph ranges for common scripts, and empty PBFs for uncommon/CJK ranges
 * (which MapLibre renders client-side via `localIdeographFontFamily`).
 *
 * All responses are gzip-encoded — both pre-built ranges (stored as .pbf.gz)
 * and empty fallbacks. Fixtures are stored compressed to reduce package size.
 *
 * Covers 80+ scripts including Latin, Cyrillic, Greek, Arabic, Hebrew,
 * Devanagari, Thai, and more. See https://github.com/satbyy/go-noto-universal
 *
 * For use with `createServer({ fallbackGlyph })` from `styled-map-package-api`.
 *
 * @param {string} _fontstack
 * @param {string} range
 * @returns {Response}
 */
export declare function notoGlyphFallback(_fontstack: string, range: string): Response;
