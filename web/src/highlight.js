// highlight.js — minimal, dependency-free syntax highlighting for the three
// languages we show (cobol, python, bash). One ordered regex per language;
// matches are wrapped in <span class="tok-*">, everything else is escaped.
// Good enough to read like code on a CRT, not a full grammar.

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Each language is a single regex with named groups; the first group that
// matches names the token class. Ordering inside the alternation = precedence.
const GRAMMARS = {
  python: /(?<comment>#[^\n]*)|(?<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")|(?<keyword>\b(?:from|import|def|return|class|if|else|elif|for|while|in|with|as|None|True|False|lambda|raise|try|except)\b)|(?<builtin>\b(?:Decimal|ROUND_HALF_UP|float|round|str|int|json|pytest|quantize|strip)\b)|(?<number>\b\d+\.?\d*\b)/g,
  cobol: /(?<comment>^.{0,6}\*[^\n]*)|(?<string>'[^'\n]*'|"[^"\n]*")|(?<keyword>\b(?:IDENTIFICATION|PROGRAM-ID|DATA|DIVISION|WORKING-STORAGE|SECTION|PROCEDURE|PIC|VALUE|COMP-3|MOVE|COMPUTE|ROUNDED|ACCEPT|DISPLAY|FUNCTION|NUMVAL|STOP|RUN|TO)\b)|(?<builtin>\b(?:WS-[A-Z0-9-]+|MAIN-PARA)\b)|(?<number>\b\d+\.?\d*\b)/gm,
  bash: /(?<comment>#[^\n]*)|(?<string>'[^'\n]*'|"[^"\n]*")|(?<keyword>\b(?:cobc|pytest|git|grep|wc|cat|echo|python3?|add|commit)\b)|(?<flag>(?:^|\s)-{1,2}[A-Za-z][\w-]*)|(?<number>\b\d+\.?\d*\b)/gm,
};

/** Return highlighted HTML for `code` in `lang`. Falls back to escaped text. */
export function highlight(code, lang) {
  const src = code ?? '';
  const re = GRAMMARS[lang];
  if (!re) return escapeHtml(src);

  let out = '';
  let last = 0;
  re.lastIndex = 0;
  let m;
  while ((m = re.exec(src)) !== null) {
    if (m.index === re.lastIndex) { re.lastIndex++; continue; } // avoid zero-width loop
    out += escapeHtml(src.slice(last, m.index));
    const groups = m.groups || {};
    const cls = Object.keys(groups).find((k) => groups[k] != null);
    // `flag` may include a leading space we want to keep outside the span.
    const token = m[0];
    if (cls === 'flag' && /^\s/.test(token)) {
      out += escapeHtml(token[0]) + `<span class="tok-builtin">${escapeHtml(token.slice(1))}</span>`;
    } else {
      out += `<span class="tok-${cls}">${escapeHtml(token)}</span>`;
    }
    last = re.lastIndex;
  }
  out += escapeHtml(src.slice(last));
  return out;
}
