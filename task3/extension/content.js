// content.js
// Injected into Netflix and TVING history pages to export viewing history

(function() {
  console.log('[Poster Archive Exporter] content.js loaded');

  // 1. Helper: Format Date object to YYYY-MM-DD
  function formatDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  // 2. Helper: Convert TVING relative dates or formats to YYYY-MM-DD
  function parseTvingDate(dateStr) {
    if (!dateStr) return '';
    const cleanStr = dateStr.trim();
    const now = new Date();

    if (cleanStr.includes('오늘') || cleanStr.includes('방금') || cleanStr.includes('시간 전') || cleanStr.includes('분 전')) {
      return formatDate(now);
    }
    if (cleanStr.includes('어제')) {
      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      return formatDate(yesterday);
    }

    // Matches "n일 전"
    const relativeDaysMatch = cleanStr.match(/(\d+)\s*일\s*전/);
    if (relativeDaysMatch) {
      const daysAgo = parseInt(relativeDaysMatch[1]);
      const targetDate = new Date(now);
      targetDate.setDate(now.getDate() - daysAgo);
      return formatDate(targetDate);
    }

    // Matches "YYYY.MM.DD"
    const yyyymmddMatch = cleanStr.match(/(\d{4})[./-](\d{1,2})[./-](\d{1,2})/);
    if (yyyymmddMatch) {
      return `${yyyymmddMatch[1]}-${yyyymmddMatch[2].padStart(2, '0')}-${yyyymmddMatch[3].padStart(2, '0')}`;
    }

    // Matches "MM.DD" (assumes current year)
    const mmddMatch = cleanStr.match(/^(\d{1,2})[./-](\d{1,2})$/);
    if (mmddMatch) {
      return `${now.getFullYear()}-${mmddMatch[1].padStart(2, '0')}-${mmddMatch[2].padStart(2, '0')}`;
    }

    // Standard date parsing fallback
    const parsed = new Date(cleanStr);
    if (!isNaN(parsed.getTime())) {
      return formatDate(parsed);
    }

    return '';
  }

  // 3. Helper: Generate and trigger download of CSV
  function downloadCSV(records, filename) {
    if (records.length === 0) {
      alert('시청 기록 데이터를 찾지 못했습니다. 로그인되어 있는지, 내역이 표시되어 있는지 확인하세요.');
      return;
    }

    // CSV Header matching Poster Archive parser
    let csvContent = 'Title,Date\n';
    records.forEach(row => {
      // Escape double quotes inside title
      const escapedTitle = row.title.replace(/"/g, '""');
      csvContent += `"${escapedTitle}","${row.date}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // 4. Inject Export Button in Page UI
  function injectExporterButton() {
    if (document.getElementById('poster-archive-exporter-btn')) return;

    const btn = document.createElement('button');
    btn.id = 'poster-archive-exporter-btn';
    btn.innerText = '🎟️ Poster Archive용 CSV 내보내기';
    
    // Style with Lpalo Children's Storybook theme
    btn.style.position = 'fixed';
    btn.style.top = '24px';
    btn.style.right = '24px';
    btn.style.zIndex = '2147483647'; // Always on top
    btn.style.backgroundColor = '#ef724f'; // Ember Orange
    btn.style.color = '#ffffff';
    btn.style.border = '2px solid #000000';
    btn.style.borderRadius = '47px';
    btn.style.padding = '12px 24px';
    btn.style.fontFamily = "'Pretendard', sans-serif";
    btn.style.fontSize = '15px';
    btn.style.fontWeight = 'bold';
    btn.style.cursor = 'pointer';
    btn.style.transition = 'transform 0.1s ease, background-color 0.1s ease';

    btn.addEventListener('mouseenter', () => {
      btn.style.backgroundColor = '#ace2df'; // Mint Wash
      btn.style.color = '#000000';
      btn.style.transform = 'scale(1.05)';
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.backgroundColor = '#ef724f';
      btn.style.color = '#ffffff';
      btn.style.transform = 'scale(1)';
    });

    btn.addEventListener('click', handleExportClick);
    document.body.appendChild(btn);
  }

  // 5. Exporter click handler
  function handleExportClick() {
    const host = window.location.hostname;
    
    if (host.includes('netflix.com')) {
      exportNetflixHistory();
    } else if (host.includes('tving.com')) {
      exportTvingHistory();
    }
  }

  // 6. Netflix Scraper Logic
  function exportNetflixHistory() {
    // Try to click Netflix's built-in "Download all" button if visible
    const downloadAllLink = document.querySelector('a[href*="download=true"], a.download-all-link, a[data-uia="download-all-link"]');
    if (downloadAllLink) {
      console.log('[Poster Exporter] Netflix download link found, clicking it...');
      downloadAllLink.click();
      return;
    }

    // Scrape DOM fallback if link is not found
    console.log('[Poster Exporter] Netflix download link not found, scraping DOM...');
    const rows = document.querySelectorAll('.retableRow, ul.viewingactivity-list > li');
    const records = [];

    rows.forEach(row => {
      // Netflix Title Selector
      const titleEl = row.querySelector('.col.title a, .title a, .col.title');
      const dateEl = row.querySelector('.col.date, .date');
      
      if (titleEl && dateEl) {
        const titleText = titleEl.innerText.trim();
        const dateText = dateEl.innerText.trim();
        
        // Parse date
        const parsedDate = new Date(dateText);
        if (titleText && !isNaN(parsedDate.getTime())) {
          records.push({
            title: titleText,
            date: formatDate(parsedDate)
          });
        }
      }
    });

    downloadCSV(records, `netflix_viewing_history_${formatDate(new Date())}.csv`);
  }

  // 7. TVING Scraper Logic
  function exportTvingHistory() {
    console.log('[Poster Exporter] Scraping TVING DOM...');
    // TVING watch history cards selector
    // Based on TVING's common history list item DOM layout (usually anchor wrapper containing title div and relative watch date/time info)
    const cards = document.querySelectorAll('a[href*="/movie/"], a[href*="/vod/"], li[class*="history"], div[class*="HistoryCard"], a[class*="history"]');
    const records = [];

    // Fallback: search broad elements if strict elements are not matches
    const targetElements = cards.length > 0 ? cards : document.querySelectorAll('div.card, li.card, div[class*="card"], li[class*="card"]');
    
    targetElements.forEach(element => {
      // Find Title: usually holds title class or has inline text containing movie/drama name
      const titleEl = element.querySelector('strong, h3, h4, span[class*="title"], div[class*="title"], strong[class*="title"], span[class*="name"], div[class*="name"]');
      // Find Watch Time/Date
      const dateEl = element.querySelector('span[class*="date"], div[class*="date"], span[class*="time"], div[class*="time"], span[class*="History"], p[class*="History"]');

      if (titleEl) {
        const titleText = titleEl.innerText.trim();
        // TVING often puts dates or "오늘", "어제" in these containers
        const rawDateText = dateEl ? dateEl.innerText.trim() : '오늘'; // default to today if not specified
        const cleanDate = parseTvingDate(rawDateText);
        
        if (titleText && cleanDate) {
          records.push({
            title: titleText,
            date: cleanDate
          });
        }
      }
    });

    // Fallback: If still empty, search all text nodes or broad anchors
    if (records.length === 0) {
      console.log('[Poster Exporter] Strict selectors returned empty. Trying broad DOM selectors...');
      // Look for any anchor tag that has both title-like text and relative-date text
      const allAnchors = document.querySelectorAll('a[href*="/movie/"], a[href*="/vod/"]');
      allAnchors.forEach(a => {
        const titleText = a.innerText.trim().split('\n')[0]; // First line is usually title
        let rawDate = '오늘';
        
        // Find sibling or nested element containing date strings
        const textContent = a.innerText;
        const relativeMatches = textContent.match(/오늘|어제|일\s*전|\d{4}\.\d{2}\.\d{2}/);
        if (relativeMatches) {
          rawDate = relativeMatches[0];
        }
        
        const cleanDate = parseTvingDate(rawDate);
        if (titleText && cleanDate && titleText.length > 1) {
          records.push({
            title: titleText,
            date: cleanDate
          });
        }
      });
    }

    // Deduplicate records on the same day with same title
    const uniqueRecords = [];
    const seen = new Set();
    records.forEach(r => {
      const key = `${r.title}||${r.date}`;
      if (!seen.has(key)) {
        seen.add(key);
        uniqueRecords.push(r);
      }
    });

    downloadCSV(uniqueRecords, `tving_viewing_history_${formatDate(new Date())}.csv`);
  }

  // 8. Inject check loop (since SPA pages load dynamically)
  setInterval(injectExporterButton, 1000);
  injectExporterButton();

})();
