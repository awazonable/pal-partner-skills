// 表示言語（現状 ja 固定。en へ切替可能な形にしておく）
export const LANG = 'ja';

// { ja, en } 形式のローカライズ文字列から表示文字列を取り出す。
// 文字列がそのまま渡された場合はそのまま返す。
export function t(localized, lang = LANG) {
  if (localized == null) return '';
  if (typeof localized === 'string') return localized;
  return localized[lang] || localized.ja || localized.en || '';
}
