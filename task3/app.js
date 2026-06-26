/**
 * Poster Archive App Core JS Logic
 */

// Global State
const DEFAULT_V3_KEY = 'd2e5a7ef6476b797825b7b4a20b72186';

const state = {
  currentYear: 2026,
  currentMonth: 5, // 0-indexed (5 = 6월)
  db: null,
  tmdbApiKey: localStorage.getItem('tmdb_api_key') || '',
  useMock: localStorage.getItem('use_mock') === 'true', // Default false
  records: [], // Array of active viewing records from IndexedDB
  activeDayRecords: [],
  activeRecordIndex: 0
};

// Mock Database Mapping (for demo without API Key)
const MOCK_DB = {
  '기생충': {
    title: '기생충',
    posterPath: 'https://image.tmdb.org/t/p/w500/7c991Gg62hLw7dG5v29o5BoWypw.jpg',
    releaseDate: '2019'
  },
  '오징어 게임': {
    title: '오징어 게임',
    posterPath: 'https://image.tmdb.org/t/p/w500/dJKFT2afGaB9T57n1l5S218VF5D.jpg',
    releaseDate: '2021'
  },
  '인셉션': {
    title: '인셉션',
    posterPath: 'https://image.tmdb.org/t/p/w500/edv5CZvXjA78hxS6v0lGVE284aA.jpg',
    releaseDate: '2010'
  },
  '인터스텔라': {
    title: '인터스텔라',
    posterPath: 'https://image.tmdb.org/t/p/w500/gEU2QthHGvifSv2gDXcSIjghqxs.jpg',
    releaseDate: '2014'
  },
  '글래디에이터': {
    title: '글래디에이터',
    posterPath: 'https://image.tmdb.org/t/p/w500/ty85bCcstzLN77jg5VEwAQ7V3gn.jpg',
    releaseDate: '2000'
  },
  '어벤져스': {
    title: '어벤져스: 엔드게임',
    posterPath: 'https://image.tmdb.org/t/p/w500/or0650h61gZg6uqc24gR7gc5n7t.jpg',
    releaseDate: '2019'
  },
  '라라랜드': {
    title: '라라랜드',
    posterPath: 'https://image.tmdb.org/t/p/w500/kC576m39v73CE9U4cg58t394eVu.jpg',
    releaseDate: '2016'
  },
  '스파이더맨': {
    title: '스파이더맨: 뉴 유니버스',
    posterPath: 'https://image.tmdb.org/t/p/w500/iiZZN643b6RtxO3jzm25G586vJV.jpg',
    releaseDate: '2018'
  },
  '귀멸의 칼날': {
    title: '귀멸의 칼날: 무한열차편',
    posterPath: 'https://image.tmdb.org/t/p/w500/h8Agg2QpjaV1n123f0K9x69s3G3.jpg',
    releaseDate: '2020'
  },
  '센과 치히로의 행방불명': {
    title: '센과 치히로의 행방불명',
    posterPath: 'https://image.tmdb.org/t/p/w500/5t513EaXhP2c05Bst3J22DmgxN8.jpg',
    releaseDate: '2001'
  },
  '범죄도시': {
    title: '범죄도시4',
    posterPath: 'https://image.tmdb.org/t/p/w500/1eByX0zU1Pvxn7H5Y2iJt8uT9eD.jpg',
    releaseDate: '2024'
  },
  '엘리멘탈': {
    title: '엘리멘탈',
    posterPath: 'https://image.tmdb.org/t/p/w500/6oH359jIrR71i28QUBu7n613Ugk.jpg',
    releaseDate: '2023'
  }
};

const DEFAULT_POSTER = 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=500';

// Initialize IndexedDB
function initDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('poster_archive_db', 1);

    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('records')) {
        const store = db.createObjectStore('records', { keyPath: 'id', autoIncrement: true });
        store.createIndex('date', 'date', { unique: false });
        store.createIndex('title', 'title', { unique: false });
      }
    };

    request.onsuccess = (e) => {
      state.db = e.target.result;
      resolve(state.db);
    };

    request.onerror = (e) => {
      console.error('Database opening error:', e.target.error);
      reject(e.target.error);
    };
  });
}

// IndexedDB Accessors
function getAllRecordsFromDB() {
  return new Promise((resolve, reject) => {
    const transaction = state.db.transaction(['records'], 'readonly');
    const store = transaction.objectStore(transaction.objectStoreNames[0]);
    const request = store.getAll();

    request.onsuccess = (e) => {
      resolve(e.target.result);
    };

    request.onerror = (e) => {
      reject(e.target.error);
    };
  });
}

function saveRecordToDB(record) {
  return new Promise((resolve, reject) => {
    const transaction = state.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore(transaction.objectStoreNames[0]);
    
    // Clean record properties before saving
    const dataToSave = {
      title: record.title,
      date: record.date,
      posterPath: record.posterPath || DEFAULT_POSTER,
      rating: parseInt(record.rating) || 0,
      review: record.review || '',
      companions: record.companions || ''
    };
    if (record.id) {
      dataToSave.id = record.id;
    }

    const request = store.put(dataToSave);

    request.onsuccess = (e) => {
      resolve(e.target.result); // Returns id
    };

    request.onerror = (e) => {
      reject(e.target.error);
    };
  });
}

function deleteRecordFromDB(id) {
  return new Promise((resolve, reject) => {
    const transaction = state.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore(transaction.objectStoreNames[0]);
    const request = store.delete(id);

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = (e) => {
      reject(e.target.error);
    };
  });
}

function clearAllRecordsFromDB() {
  return new Promise((resolve, reject) => {
    const transaction = state.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore(transaction.objectStoreNames[0]);
    const request = store.clear();

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = (e) => {
      reject(e.target.error);
    };
  });
}

// Helper: Format Date object to YYYY-MM-DD
function formatDateString(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// Title Parsing Engine (Clean title before searching TMDB)
function cleanContentTitle(rawTitle) {
  if (!rawTitle) return '';
  let cleaned = rawTitle.trim();

  // 1. Remove brackets content: [런닝맨], (기생충) 등
  cleaned = cleaned.replace(/\[[^\]]*\]/g, '');
  cleaned = cleaned.replace(/\([^)]*\)/g, '');

  // 2. Split by typical delimiters like ':' or '-' or '/'
  // Netflix often uses formats like: "Title: Season X: Episode Y"
  if (cleaned.includes(':')) {
    const parts = cleaned.split(':');
    cleaned = parts[0];
  } else if (cleaned.includes('-')) {
    // Check if it looks like Title - Episode
    const parts = cleaned.split('-');
    cleaned = parts[0];
  }

  // 3. Remove episode, season indicators: "시즌 1", "2화", "1부", "Season 2", "Episode 3"
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

// TMDB API / Mock search interface
async function searchContentPoster(title) {
  const cleanedTitle = cleanContentTitle(title);
  if (!cleanedTitle) {
    return { title: title, posterPath: DEFAULT_POSTER, releaseDate: '' };
  }

  // A. Use Mock Data ONLY if useMock is explicitly checked
  if (state.useMock) {
    const keys = Object.keys(MOCK_DB);
    const matchedKey = keys.find(k => cleanedTitle.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(cleanedTitle.toLowerCase()));
    if (matchedKey) {
      return MOCK_DB[matchedKey];
    }
  }

  // B. Real TMDB API search (Supports v4 Bearer Token or Fallback v3 API Key)
  try {
    let searchUrl = '';
    let headers = { accept: 'application/json' };
    
    if (state.tmdbApiKey) {
      if (state.tmdbApiKey.length === 32) {
        searchUrl = `https://api.themoviedb.org/3/search/multi?api_key=${state.tmdbApiKey}&query=${encodeURIComponent(cleanedTitle)}&include_adult=false&language=ko-KR&page=1`;
      } else {
        searchUrl = `https://api.themoviedb.org/3/search/multi?query=${encodeURIComponent(cleanedTitle)}&include_adult=false&language=ko-KR&page=1`;
        headers['Authorization'] = `Bearer ${state.tmdbApiKey.replace('Bearer ', '')}`;
      }
    } else {
      searchUrl = `https://api.themoviedb.org/3/search/multi?api_key=${DEFAULT_V3_KEY}&query=${encodeURIComponent(cleanedTitle)}&include_adult=false&language=ko-KR&page=1`;
    }

    const response = await fetch(searchUrl, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (data.results && data.results.length > 0) {
      const hit = data.results.find(item => item.poster_path && (item.media_type === 'movie' || item.media_type === 'tv')) || data.results[0];
      const name = hit.title || hit.name || hit.original_title || hit.original_name;
      const posterPath = hit.poster_path ? `https://image.tmdb.org/t/p/w500${hit.poster_path}` : DEFAULT_POSTER;
      const releaseDate = hit.release_date || hit.first_air_date || '';
      return {
        title: name,
        posterPath: posterPath,
        releaseDate: releaseDate.substring(0, 4)
      };
    }
  } catch (error) {
    console.error('TMDB API search error:', error);
  }

  // Fallback to Mock if API search failed and key was missing
  if (!state.tmdbApiKey) {
    const keys = Object.keys(MOCK_DB);
    const matchedKey = keys.find(k => cleanedTitle.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(cleanedTitle.toLowerCase()));
    if (matchedKey) {
      return MOCK_DB[matchedKey];
    }
  }

  // Absolute fallback
  return { title: cleanedTitle, posterPath: DEFAULT_POSTER, releaseDate: '' };
}

// Parse CSV content (Robust custom parsing)
function parseCSV(text) {
  const lines = [];
  let row = [""];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    const next = text[i+1];

    if (c === '"') {
      if (inQuotes && next === '"') {
        // Escaped quote
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

// Parse date string flexibly and output YYYY-MM-DD
function parseDateFlexible(dateStr) {
  if (!dateStr) return '';
  
  // Format: "YYYY-MM-DD"
  const yyyymmdd = dateStr.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (yyyymmdd) {
    return `${yyyymmdd[1]}-${yyyymmdd[2].padStart(2, '0')}-${yyyymmdd[3].padStart(2, '0')}`;
  }

  // Format: "M/D/YY" (Typical US Netflix format) or "M/D/YYYY"
  const mdy = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (mdy) {
    let year = mdy[3];
    if (year.length === 2) {
      year = '20' + year; // Assumes 20xx
    }
    return `${year}-${mdy[1].padStart(2, '0')}-${mdy[2].padStart(2, '0')}`;
  }

  // Direct Date parsing fallback
  const d = new Date(dateStr);
  if (!isNaN(d.getTime())) {
    return formatDateString(d);
  }
  return '';
}

// Process uploaded CSV file
async function processCSVFile(file) {
  const text = await file.text();
  const parsedRows = parseCSV(text);
  if (parsedRows.length <= 1) {
    alert('CSV 파일 형식이 올바르지 않거나 데이터가 없습니다.');
    return;
  }

  const headers = parsedRows[0].map(h => h.trim().toLowerCase());
  
  // Find Title & Date column indices
  let titleIdx = headers.findIndex(h => h.includes('title') || h.includes('작품') || h.includes('제목'));
  let dateIdx = headers.findIndex(h => h.includes('date') || h.includes('시간') || h.includes('날짜') || h.includes('일시'));

  // Default fallbacks if header matches fail
  if (titleIdx === -1) titleIdx = 0;
  if (dateIdx === -1) dateIdx = 1;

  let loadedCount = 0;
  let errorCount = 0;

  for (let i = 1; i < parsedRows.length; i++) {
    const row = parsedRows[i];
    if (row.length <= Math.max(titleIdx, dateIdx)) continue;

    const rawTitle = row[titleIdx];
    const rawDate = row[dateIdx];

    if (!rawTitle || !rawDate) continue;

    const cleanDate = parseDateFlexible(rawDate.trim());
    if (!cleanDate) {
      errorCount++;
      continue;
    }

    // Call TMDB/Mock search
    const movieInfo = await searchContentPoster(rawTitle);
    
    // Save to Database
    await saveRecordToDB({
      title: rawTitle.trim(),
      date: cleanDate,
      posterPath: movieInfo.posterPath,
      rating: 0,
      review: '',
      companions: ''
    });
    loadedCount++;
  }

  alert(`업로드 완료! 성공적으로 ${loadedCount}개의 시청 기록을 가져왔습니다.${errorCount > 0 ? ` (날짜 오류 제외: ${errorCount}개)` : ''}`);
  await loadAndRender();
}

// Load records from Database and Draw Calendar
async function loadAndRender() {
  state.records = await getAllRecordsFromDB();
  renderCalendar();
  updateStats();
}

function updateStats() {
  const currentMonthStr = `${state.currentYear}-${String(state.currentMonth + 1).padStart(2, '0')}`;
  const monthlyRecords = state.records.filter(r => r.date.startsWith(currentMonthStr));
  document.getElementById('total-watched-count').textContent = monthlyRecords.length;
}

// Draw Calendar Grid
function renderCalendar() {
  const calendarDays = document.getElementById('calendar-days');
  calendarDays.innerHTML = '';

  // Update Header Month label
  document.getElementById('current-month-year').textContent = `${state.currentYear}년 ${state.currentMonth + 1}월`;

  // First day of current month
  const firstDay = new Date(state.currentYear, state.currentMonth, 1);
  const startDayOfWeek = firstDay.getDay(); // 0 is Sunday
  
  // Total days in current month
  const totalDays = new Date(state.currentYear, state.currentMonth + 1, 0).getDate();

  // Total days in previous month
  const prevMonthTotalDays = new Date(state.currentYear, state.currentMonth, 0).getDate();

  // 42 cells grid (6 weeks)
  const cells = [];

  // 1. Previous Month days padding
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    cells.push({
      dateStr: '',
      dayNum: prevMonthTotalDays - i,
      isCurrentMonth: false
    });
  }

  // 2. Current Month days
  for (let i = 1; i <= totalDays; i++) {
    const d = new Date(state.currentYear, state.currentMonth, i);
    cells.push({
      dateStr: formatDateString(d),
      dayNum: i,
      isCurrentMonth: true
    });
  }

  // 3. Next Month days padding
  let nextPaddingCount = 42 - cells.length;
  for (let i = 1; i <= nextPaddingCount; i++) {
    cells.push({
      dateStr: '',
      dayNum: i,
      isCurrentMonth: false
    });
  }

  const todayStr = formatDateString(new Date());

  // Render cells to DOM
  cells.forEach(cell => {
    const dayCell = document.createElement('div');
    dayCell.classList.add('day-cell');
    
    if (!cell.isCurrentMonth) {
      dayCell.classList.add('other-month');
    } else {
      if (cell.dateStr === todayStr) {
        dayCell.classList.add('today');
      }
      dayCell.dataset.date = cell.dateStr;
    }

    // Day number badge
    const dayNumDiv = document.createElement('div');
    dayNumDiv.classList.add('day-number');
    dayNumDiv.textContent = cell.dayNum;
    dayCell.appendChild(dayNumDiv);

    // Empty cell manual add button overlay icon
    if (cell.isCurrentMonth) {
      const addIcon = document.createElement('i');
      addIcon.classList.add('fa-solid', 'fa-circle-plus', 'day-cell-add-icon');
      dayCell.appendChild(addIcon);
    }

    // Filter records for this cell date
    if (cell.isCurrentMonth && cell.dateStr) {
      const dayRecords = state.records.filter(r => r.date === cell.dateStr);

      if (dayRecords.length > 0) {
        dayCell.classList.add('has-poster');
        
        const stackContainer = document.createElement('div');
        stackContainer.classList.add('poster-stack');

        // Show up to 3 posters stacked
        dayRecords.slice(0, 3).forEach(rec => {
          const img = document.createElement('img');
          img.classList.add('poster-stamp');
          img.src = rec.posterPath;
          img.alt = rec.title;
          stackContainer.appendChild(img);
        });

        // Add badge for multiple watch count (Top Right)
        if (dayRecords.length > 1) {
          const badge = document.createElement('div');
          badge.classList.add('multiple-badge');
          badge.textContent = `+${dayRecords.length}`;
          dayCell.appendChild(badge);
        }

        // Add badge for star ratings (Bottom Right)
        // Shows 5-star style rating indicator
        const ratedRec = dayRecords.find(r => r.rating > 0);
        if (ratedRec) {
          const ratingBadge = document.createElement('div');
          ratingBadge.classList.add('rating-badge');
          
          let starsHTML = '';
          for (let i = 1; i <= 5; i++) {
            if (i <= ratedRec.rating) {
              starsHTML += '<i class="fa-solid fa-star"></i>';
            } else {
              starsHTML += '<i class="fa-regular fa-star"></i>';
            }
          }
          ratingBadge.innerHTML = starsHTML;
          dayCell.appendChild(ratingBadge);
        }

        dayCell.appendChild(stackContainer);

        // Click on cell with posters -> Open detail modal with pager navigation
        dayCell.addEventListener('click', (e) => {
          e.stopPropagation();
          state.activeDayRecords = dayRecords;
          state.activeRecordIndex = 0;
          openDetailModal(dayRecords[0]);
        });
      } else {
        // Click on empty cell -> Open manual search modal for this date
        dayCell.addEventListener('click', () => {
          openManualAddModal(cell.dateStr);
        });
      }
    }

    calendarDays.appendChild(dayCell);
  });
}

// Modal Toggle Functions
function showModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.add('active');
}

function hideModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.remove('active');
}

// Star Rating UI Controller
function setupStarRating() {
  const stars = document.querySelectorAll('.rating-star');
  const ratingInput = document.getElementById('detail-rating');

  stars.forEach(star => {
    star.addEventListener('click', () => {
      const val = parseInt(star.dataset.value);
      ratingInput.value = val;
      updateStarsUI(val);
    });
  });
}

function updateStarsUI(val) {
  const stars = document.querySelectorAll('.rating-star');
  stars.forEach(star => {
    const starVal = parseInt(star.dataset.value);
    if (starVal <= val) {
      star.classList.add('active');
    } else {
      star.classList.remove('active');
    }
  });
}

// Open Detailed Edit Modal
function openDetailModal(record) {
  if (!record) return;

  document.getElementById('detail-record-id').value = record.id;
  document.getElementById('detail-date').value = record.date;
  document.getElementById('detail-display-date').value = record.date;
  document.getElementById('detail-title').value = record.title;
  document.getElementById('detail-poster-img').src = record.posterPath;
  
  const ratingVal = record.rating || 0;
  document.getElementById('detail-rating').value = ratingVal;
  updateStarsUI(ratingVal);

  document.getElementById('detail-review').value = record.review || '';
  document.getElementById('detail-companions').value = record.companions || '';

  // Paging indicator update
  const total = state.activeDayRecords.length;
  const idx = state.activeRecordIndex;
  document.getElementById('detail-page-indicator').textContent = `${idx + 1} / ${total}`;

  // Enable/disable page navigation buttons
  const prevBtn = document.getElementById('btn-detail-prev');
  const nextBtn = document.getElementById('btn-detail-next');
  prevBtn.disabled = (idx === 0);
  nextBtn.disabled = (idx === total - 1);

  showModal('modal-record-detail');
}

// Open Manual Add Search Modal
function openManualAddModal(dateStr) {
  document.getElementById('manual-target-date').value = dateStr;
  document.getElementById('manual-search-input').value = '';
  document.getElementById('manual-search-results').innerHTML = '<p class="search-info-text">추가할 콘텐츠 제목을 검색해보세요.</p>';
  showModal('modal-manual-add');
}

// Manual TMDB Search
async function performManualSearch() {
  const query = document.getElementById('manual-search-input').value.trim();
  const resultsContainer = document.getElementById('manual-search-results');
  
  if (!query) {
    resultsContainer.innerHTML = '<p class="search-info-text">검색어를 입력해주세요.</p>';
    return;
  }

  resultsContainer.innerHTML = '<p class="search-info-text"><i class="fa-solid fa-spinner fa-spin"></i> 검색 중...</p>';

  const targetDate = document.getElementById('manual-target-date').value;

  // A. Mock Search (Only when useMock is enabled and no API key available)
  if (state.useMock && !state.tmdbApiKey) {
    const keys = Object.keys(MOCK_DB);
    const matches = keys.filter(k => k.toLowerCase().includes(query.toLowerCase()));
    
    if (matches.length > 0) {
      resultsContainer.innerHTML = '';
      matches.forEach(key => {
        const item = MOCK_DB[key];
        const card = createSearchResultCard(item.title, item.posterPath, item.releaseDate, targetDate);
        resultsContainer.appendChild(card);
      });
    } else {
      resultsContainer.innerHTML = '';
      const card = createSearchResultCard(query, DEFAULT_POSTER, '신규 등록', targetDate);
      resultsContainer.appendChild(card);
    }
    return;
  }

  // B. Real TMDB Search (Supports v4 Bearer or Fallback v3 key)
  try {
    let searchUrl = '';
    let headers = { accept: 'application/json' };
    
    if (state.tmdbApiKey) {
      if (state.tmdbApiKey.length === 32) {
        searchUrl = `https://api.themoviedb.org/3/search/multi?api_key=${state.tmdbApiKey}&query=${encodeURIComponent(query)}&include_adult=false&language=ko-KR&page=1`;
      } else {
        searchUrl = `https://api.themoviedb.org/3/search/multi?query=${encodeURIComponent(query)}&include_adult=false&language=ko-KR&page=1`;
        headers['Authorization'] = `Bearer ${state.tmdbApiKey.replace('Bearer ', '')}`;
      }
    } else {
      searchUrl = `https://api.themoviedb.org/3/search/multi?api_key=${DEFAULT_V3_KEY}&query=${encodeURIComponent(query)}&include_adult=false&language=ko-KR&page=1`;
    }

    const response = await fetch(searchUrl, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.results && data.results.length > 0) {
      resultsContainer.innerHTML = '';
      // Show up to 9 results
      data.results.slice(0, 9).forEach(hit => {
        if (hit.media_type !== 'movie' && hit.media_type !== 'tv') return;
        
        const name = hit.title || hit.name || hit.original_title || hit.original_name;
        const posterPath = hit.poster_path ? `https://image.tmdb.org/t/p/w500${hit.poster_path}` : DEFAULT_POSTER;
        const releaseYear = (hit.release_date || hit.first_air_date || '').substring(0, 4) || 'N/A';
        
        const card = createSearchResultCard(name, posterPath, releaseYear, targetDate);
        resultsContainer.appendChild(card);
      });
      
      if (resultsContainer.children.length === 0) {
        resultsContainer.innerHTML = '<p class="search-info-text">검색 결과가 없습니다.</p>';
      }
    } else {
      resultsContainer.innerHTML = '<p class="search-info-text">검색 결과가 없습니다.</p>';
    }
  } catch (error) {
    console.error('Manual TMDB Search Error:', error);
    resultsContainer.innerHTML = '<p class="search-info-text">검색 중 오류가 발생했습니다.</p>';
  }
}

// Create Card for Search Results UI
function createSearchResultCard(title, posterUrl, subtext, dateStr) {
  const card = document.createElement('div');
  card.classList.add('search-result-item');
  
  const img = document.createElement('img');
  img.src = posterUrl;
  img.alt = title;
  
  const titleDiv = document.createElement('div');
  titleDiv.classList.add('item-title');
  titleDiv.textContent = title;

  const subP = document.createElement('span');
  subP.style.fontSize = '0.7rem';
  subP.style.color = 'var(--text-muted)';
  subP.textContent = subtext ? `(${subtext})` : '';

  card.appendChild(img);
  card.appendChild(titleDiv);
  card.appendChild(subP);

  card.addEventListener('click', async () => {
    // Select this item and insert to DB directly
    await saveRecordToDB({
      title: title,
      date: dateStr,
      posterPath: posterUrl,
      rating: 0,
      review: '',
      companions: ''
    });
    hideModal('modal-manual-add');
    await loadAndRender();
  });

  return card;
}

// Export All IndexedDB Data as JSON Backup
async function backupData() {
  const records = await getAllRecordsFromDB();
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(records, null, 2));
  const dlAnchorElem = document.createElement('a');
  dlAnchorElem.setAttribute("href", dataStr);
  dlAnchorElem.setAttribute("download", `poster_archive_backup_${formatDateString(new Date())}.json`);
  dlAnchorElem.click();
}

// Restore Data from JSON file
async function restoreData(file) {
  try {
    const text = await file.text();
    const importedRecords = JSON.parse(text);
    if (!Array.isArray(importedRecords)) {
      alert('올바른 JSON 백업 형식이 아닙니다.');
      return;
    }

    let restoreCount = 0;
    for (const record of importedRecords) {
      if (record.title && record.date) {
        await saveRecordToDB(record);
        restoreCount++;
      }
    }
    alert(`복원 성공! ${restoreCount}개의 기록이 추가되었습니다.`);
    await loadAndRender();
  } catch (error) {
    console.error('Restore Error:', error);
    alert('데이터 복원 실패. JSON 형식을 확인하세요.');
  }
}

// Register Listeners
function setupEventListeners() {
  // Navigation Month Control
  document.getElementById('btn-prev-month').addEventListener('click', async () => {
    state.currentMonth--;
    if (state.currentMonth < 0) {
      state.currentMonth = 11;
      state.currentYear--;
    }
    renderCalendar();
    updateStats();
  });

  document.getElementById('btn-next-month').addEventListener('click', async () => {
    state.currentMonth++;
    if (state.currentMonth > 11) {
      state.currentMonth = 0;
      state.currentYear++;
    }
    renderCalendar();
    updateStats();
  });

  // Settings Modal Open
  document.getElementById('btn-settings').addEventListener('click', () => {
    document.getElementById('tmdb-api-key').value = state.tmdbApiKey;
    document.getElementById('toggle-mock-search').checked = state.useMock;
    showModal('modal-settings');
  });

  // Close modals clicking X or overlay
  document.querySelectorAll('.close-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      hideModal(btn.dataset.modal);
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
      hideModal(e.target.id);
    }
  });

  // Save Settings
  document.getElementById('tmdb-api-key').addEventListener('input', (e) => {
    state.tmdbApiKey = e.target.value.trim();
    localStorage.setItem('tmdb_api_key', state.tmdbApiKey);
  });

  document.getElementById('toggle-mock-search').addEventListener('change', (e) => {
    state.useMock = e.target.checked;
    localStorage.setItem('use_mock', state.useMock);
  });

  // CSV Drag-and-Drop / Upload Trigger
  const csvDropzone = document.getElementById('csv-dropzone');
  const csvInput = document.getElementById('csv-upload-input');

  csvInput.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
      await processCSVFile(e.target.files[0]);
    }
  });

  csvDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    csvDropzone.style.borderColor = 'var(--neon-pink)';
    csvDropzone.style.background = 'rgba(236, 72, 153, 0.08)';
  });

  csvDropzone.addEventListener('dragleave', () => {
    csvDropzone.style.borderColor = '';
    csvDropzone.style.background = '';
  });

  csvDropzone.addEventListener('drop', async (e) => {
    e.preventDefault();
    csvDropzone.style.borderColor = '';
    csvDropzone.style.background = '';
    
    if (e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.csv')) {
        await processCSVFile(file);
      } else {
        alert('CSV 파일만 지원됩니다.');
      }
    }
  });

  // Record Detail Modal Save Form
  document.getElementById('record-detail-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('detail-record-id').value;
    const cleanId = id ? parseInt(id) : null;
    
    const updatedRecord = {
      id: cleanId,
      title: document.getElementById('detail-title').value,
      date: document.getElementById('detail-display-date').value,
      posterPath: document.getElementById('detail-poster-img').src,
      rating: parseInt(document.getElementById('detail-rating').value),
      review: document.getElementById('detail-review').value.trim(),
      companions: document.getElementById('detail-companions').value.trim()
    };

    await saveRecordToDB(updatedRecord);
    hideModal('modal-record-detail');
    await loadAndRender();
  });

  // Record Detail Modal Delete (Handles paginated UI state)
  document.getElementById('btn-delete-record').addEventListener('click', async () => {
    const id = document.getElementById('detail-record-id').value;
    if (id && confirm('이 콘텐츠 시청 기록을 삭제하시겠습니까?')) {
      const deletedId = parseInt(id);
      await deleteRecordFromDB(deletedId);
      
      // Filter out deleted record from active navigation stack
      state.activeDayRecords = state.activeDayRecords.filter(r => r.id !== deletedId);

      if (state.activeDayRecords.length > 0) {
        // Shift active index if out of bounds
        if (state.activeRecordIndex >= state.activeDayRecords.length) {
          state.activeRecordIndex = state.activeDayRecords.length - 1;
        }
        openDetailModal(state.activeDayRecords[state.activeRecordIndex]);
      } else {
        hideModal('modal-record-detail');
      }
      await loadAndRender();
    }
  });

  // Detail Modal Navigation
  document.getElementById('btn-detail-prev').addEventListener('click', () => {
    if (state.activeRecordIndex > 0) {
      state.activeRecordIndex--;
      openDetailModal(state.activeDayRecords[state.activeRecordIndex]);
    }
  });

  document.getElementById('btn-detail-next').addEventListener('click', () => {
    if (state.activeRecordIndex < state.activeDayRecords.length - 1) {
      state.activeRecordIndex++;
      openDetailModal(state.activeDayRecords[state.activeRecordIndex]);
    }
  });

  // Manual Add Modal Trigger Search
  document.getElementById('btn-manual-search').addEventListener('click', performManualSearch);
  document.getElementById('manual-search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      performManualSearch();
    }
  });

  // Backup & Restore Events
  document.getElementById('btn-backup').addEventListener('click', backupData);
  
  const restoreTriggerBtn = document.getElementById('btn-restore-trigger');
  const restoreFileInput = document.getElementById('restore-file-input');
  
  restoreTriggerBtn.addEventListener('click', () => {
    restoreFileInput.click();
  });

  restoreFileInput.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
      await restoreData(e.target.files[0]);
    }
  });

  // Clear Database
  document.getElementById('btn-clear-data').addEventListener('click', async () => {
    console.log('초기화 버튼 클릭됨');
    try {
      if (confirm('경고: 달력의 모든 콘텐츠 시청 기록이 영구히 삭제됩니다. 정말 진행하시겠습니까?')) {
        console.log('사용자가 확인을 누름. 초기화 진행...');
        await clearAllRecordsFromDB();
        console.log('IndexedDB 초기화 성공');
        alert('모든 데이터가 초기화되었습니다.');
        hideModal('modal-settings');
        await loadAndRender();
        console.log('데이터 렌더링 완료');
      } else {
        console.log('사용자가 취소를 누름');
      }
    } catch (err) {
      console.error('초기화 중 오류 발생:', err);
      alert('초기화 중 오류가 발생했습니다: ' + err.message);
    }
  });
}

// App Entry Point
window.addEventListener('DOMContentLoaded', async () => {
  // Set current month to matching real today month on init
  const today = new Date();
  state.currentYear = today.getFullYear();
  state.currentMonth = today.getMonth();

  // If local storage doesn't have the API key, set user's key as the default
  if (!localStorage.getItem('tmdb_api_key')) {
    localStorage.setItem('tmdb_api_key', 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwYzE4ZWUwMzY3N2M5OWRhNThmNzdlMDAxODQ4NmMyYSIsIm5iZiI6MTc4MTY3NDYyNC44MzksInN1YiI6IjZhMzIzMjgwNzFiY2E1NjUxMjM4OTcxNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McMofZ3Ce4vpD6JlvJgAIb33M8k54ubNyM-p-tEjCUE');
  }
  if (localStorage.getItem('use_mock') === null) {
    localStorage.setItem('use_mock', 'false');
  }

  try {
    await initDB();
    setupStarRating();
    setupEventListeners();
    await loadAndRender();
  } catch (error) {
    console.error('Failed to initialize Poster Calendar Application:', error);
  }
});
