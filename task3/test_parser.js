// Unit tests for CSV parser, Title Cleaner, and Date parser
const assert = require('assert');

// 1. Title Cleaning Engine Logic (Copied from app.js)
function cleanContentTitle(rawTitle) {
  if (!rawTitle) return '';
  let cleaned = rawTitle.trim();

  // 1. Remove brackets content: [런닝맨], (기생충) 등
  cleaned = cleaned.replace(/\[[^\]]*\]/g, '');
  cleaned = cleaned.replace(/\([^)]*\)/g, '');

  // 2. Split by typical delimiters like ':' or '-' or '/'
  if (cleaned.includes(':')) {
    const parts = cleaned.split(':');
    cleaned = parts[0];
  } else if (cleaned.includes('-')) {
    const parts = cleaned.split('-');
    cleaned = parts[0];
  }

  // 3. Remove episode, season indicators
  const indicators = [
    /\s시즌\s?\d+/gi,
    /\s\d+화/g,
    /\s\d+부/g,
    /\sseason\s?\d+/gi,
    /\sepisode\s?\d+/gi,
    /\spart\s?\d+/gi
  ];
  indicators.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '');
  });

  return cleaned.trim();
}

// 2. Flexible Date Parser Logic (Copied from app.js)
function parseDateFlexible(dateStr) {
  if (!dateStr) return '';
  
  const yyyymmdd = dateStr.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (yyyymmdd) {
    return `${yyyymmdd[1]}-${yyyymmdd[2].padStart(2, '0')}-${yyyymmdd[3].padStart(2, '0')}`;
  }

  const mdy = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (mdy) {
    let year = mdy[3];
    if (year.length === 2) {
      year = '20' + year;
    }
    return `${year}-${mdy[1].padStart(2, '0')}-${mdy[2].padStart(2, '0')}`;
  }

  const d = new Date(dateStr);
  if (!isNaN(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
  return '';
}

// 3. Robust CSV Parser (Copied from app.js)
function parseCSV(text) {
  const lines = [];
  let row = [""];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    const next = text[i+1];

    if (c === '"') {
      if (inQuotes && next === '"') {
        row[row.length - 1] += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (c === ',' && !inQuotes) {
      row.push('');
    } else if ((c === '\r' || c === '\n') && !inQuotes) {
      if (c === '\r' && next === '\n') {
        i++;
      }
      lines.push(row);
      row = [''];
    } else {
      row[row.length - 1] += c;
    }
  }
  if (row.length > 1 || row[0] !== '') {
    lines.push(row);
  }
  return lines;
}

// --- Run Tests ---
console.log('--- Running Parsers Unit Tests ---');

// Test Suite 1: Title cleaning
try {
  assert.strictEqual(cleanContentTitle('오징어 게임: 시즌 1: 1화 무궁화 꽃이 피던 날'), '오징어 게임');
  assert.strictEqual(cleanContentTitle('[넷플릭스] 기생충 (Parasite)'), '기생충');
  assert.strictEqual(cleanContentTitle('귀멸의 칼날: 무한열차편: 2화'), '귀멸의 칼날');
  assert.strictEqual(cleanContentTitle('인셉션'), '인셉션');
  assert.strictEqual(cleanContentTitle('슬기로운 의사생활: 3화'), '슬기로운 의사생활');
  console.log('✔ Title Cleaning Tests Passed!');
} catch (e) {
  console.error('✘ Title Cleaning Tests Failed:', e.message);
  process.exit(1);
}

// Test Suite 2: Flexible Date parsing
try {
  assert.strictEqual(parseDateFlexible('2026-06-01'), '2026-06-01');
  assert.strictEqual(parseDateFlexible('2026/6/5'), '2026-06-05');
  assert.strictEqual(parseDateFlexible('2026.06.10'), '2026-06-10');
  assert.strictEqual(parseDateFlexible('6/17/26'), '2026-06-17');
  assert.strictEqual(parseDateFlexible('06/17/2026 14:05:00'), '2026-06-17');
  console.log('✔ Date Parsing Tests Passed!');
} catch (e) {
  console.error('✘ Date Parsing Tests Failed:', e.message);
  process.exit(1);
}

// Test Suite 3: CSV parsing
try {
  const sampleCSV = 'Title,Date\n"오징어 게임, 시즌 1",2026-06-05\n기생충,2026-06-01\n';
  const parsed = parseCSV(sampleCSV);
  assert.strictEqual(parsed.length, 3); // headers + 2 rows
  assert.strictEqual(parsed[1][0], '오징어 게임, 시즌 1');
  assert.strictEqual(parsed[2][0], '기생충');
  console.log('✔ CSV Parsing Tests Passed!');
} catch (e) {
  console.error('✘ CSV Parsing Tests Failed:', e.message);
  process.exit(1);
}

console.log('--- All Unit Tests Successfully Passed! ---');
