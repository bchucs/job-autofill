// Job Application Auto-Fill - Popup Script

document.addEventListener('DOMContentLoaded', async () => {
  const loadingEl = document.getElementById('loading');
  const noProfileEl = document.getElementById('noProfile');
  const noFieldsEl = document.getElementById('noFields');
  const mainContentEl = document.getElementById('mainContent');
  const fieldListEl = document.getElementById('fieldList');
  const fileUploadsEl = document.getElementById('fileUploads');
  const fileListEl = document.getElementById('fileList');
  const fillBtn = document.getElementById('fillBtn');
  const resultsEl = document.getElementById('results');
  const refreshBtn = document.getElementById('refreshBtn');
  const settingsBtn = document.getElementById('settingsBtn');
  const setupBtn = document.getElementById('setupBtn');
  const llmStatusEl = document.getElementById('llmStatus');
  const llmStatusTextEl = document.getElementById('llmStatusText');
  const cacheInfoEl = document.getElementById('cacheInfo');
  const llmModeToggle = document.getElementById('llmModeToggle');

  let llmAvailable = false;
  let useLLMMode = true;
  let currentLLMMapping = null;
  let currentFields = [];
  let currentFileUploads = [];

  // Set up button event listeners first (before any early returns)
  refreshBtn.addEventListener('click', () => {
    analyzePage();
  });

  settingsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Clear cache button
  const clearCacheBtn = document.getElementById('clearCacheBtn');
  clearCacheBtn.addEventListener('click', async () => {
    const response = await chrome.runtime.sendMessage({ action: 'clearLLMCache' });
    alert(`Cleared ${response.cleared} cached mappings`);
    analyzePage();
  });

  if (setupBtn) {
    setupBtn.addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
  }

  // LLM mode toggle
  llmModeToggle.addEventListener('change', async (e) => {
    useLLMMode = e.target.checked;
    await chrome.storage.local.set({ useLLMMode });

    if (useLLMMode && llmAvailable) {
      llmStatusEl.style.display = 'flex';
    } else {
      llmStatusEl.style.display = 'none';
    }

    // Re-analyze when mode changes
    analyzePage();
  });

  // Load saved LLM mode preference
  const { useLLMMode: savedMode } = await chrome.storage.local.get(['useLLMMode']);
  if (savedMode !== undefined) {
    useLLMMode = savedMode;
    llmModeToggle.checked = useLLMMode;
  }

  // Check LLM server status
  async function checkLLMStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'checkLLMStatus' });
      llmAvailable = response?.available || false;

      if (llmAvailable) {
        llmStatusEl.className = 'llm-status active';
        llmStatusTextEl.textContent = 'LLM: Ready';
        if (useLLMMode) {
          llmStatusEl.style.display = 'flex';
        }
      } else {
        llmStatusEl.className = 'llm-status inactive';
        llmStatusTextEl.textContent = 'LLM: Server offline';
        llmStatusEl.style.display = useLLMMode ? 'flex' : 'none';
      }
    } catch (e) {
      llmAvailable = false;
      llmStatusEl.className = 'llm-status error';
      llmStatusTextEl.textContent = 'LLM: Error';
    }
  }

  // Check if profile exists
  const { profile } = await chrome.storage.sync.get(['profile']);

  if (!profile || !profile.first_name) {
    loadingEl.style.display = 'none';
    noProfileEl.style.display = 'block';
    return;
  }

  // Check LLM status then analyze page
  await checkLLMStatus();
  analyzePage();

  async function analyzePage() {
    loadingEl.style.display = 'flex';
    mainContentEl.style.display = 'none';
    noFieldsEl.style.display = 'none';
    resultsEl.style.display = 'none';
    currentLLMMapping = null;

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      // Check if content script is already loaded, inject only if needed
      try {
        await chrome.tabs.sendMessage(tab.id, { action: 'ping' });
        // Script is already loaded
      } catch (e) {
        // Script not loaded, inject it
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
          });
          // Wait for script to initialize
          await new Promise(resolve => setTimeout(resolve, 100));
        } catch (injectError) {
          console.log('Script injection note:', injectError.message);
        }
      }

      if (useLLMMode && llmAvailable) {
        // LLM mode: Extract all fields for LLM matching
        const extractResponse = await chrome.tabs.sendMessage(tab.id, { action: 'extractFieldsForLLM' });

        if (!extractResponse || extractResponse.fields.length === 0) {
          loadingEl.style.display = 'none';
          noFieldsEl.style.display = 'block';
          return;
        }

        currentFields = extractResponse.fields;

        // Get LLM mapping from background worker
        loadingEl.querySelector('span').textContent = 'Matching fields with AI...';

        const mappingResponse = await chrome.runtime.sendMessage({
          action: 'getLLMMapping',
          fields: extractResponse.fields,
          url: extractResponse.url
        });

        if (mappingResponse.success) {
          currentLLMMapping = mappingResponse.mapping;

          if (mappingResponse.fromCache) {
            cacheInfoEl.textContent = '(cached)';
          } else {
            cacheInfoEl.textContent = '';
          }

          // Display fields with their mapped values
          displayLLMFields(extractResponse.fields, mappingResponse.mapping, profile);
        } else {
          // LLM failed, fall back to regex
          console.warn('LLM matching failed:', mappingResponse.error);
          llmStatusEl.className = 'llm-status error';
          llmStatusTextEl.textContent = 'LLM: ' + (mappingResponse.error || 'Error');
          await fallbackToRegex(tab);
          return;
        }
      } else {
        // Regex mode
        await fallbackToRegex(tab);
        return;
      }

      loadingEl.style.display = 'none';
      mainContentEl.style.display = 'block';

    } catch (error) {
      console.error('Error analyzing page:', error);
      loadingEl.style.display = 'none';
      noFieldsEl.style.display = 'block';
      noFieldsEl.innerHTML = `
        <p style="color: #c53030; margin-bottom: 10px;">Could not connect to page.</p>
        <p style="font-size: 12px; color: #666;">Please refresh the Workday page and try again.</p>
        <button id="retryBtn" style="margin-top: 10px; padding: 8px 16px; cursor: pointer;">Refresh Page & Retry</button>
      `;
      document.getElementById('retryBtn')?.addEventListener('click', async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        await chrome.tabs.reload(tab.id);
        window.close();
      });
    }
  }

  async function fallbackToRegex(tab) {
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'analyze' });

    loadingEl.style.display = 'none';

    if (!response || (response.fields.length === 0 && response.fileUploads.length === 0)) {
      noFieldsEl.style.display = 'block';
      return;
    }

    currentFields = response.fields;
    currentFileUploads = response.fileUploads;
    displayFields(response.fields, response.fileUploads);
    mainContentEl.style.display = 'block';
  }

  function displayLLMFields(fields, mapping, profile) {
    fieldListEl.innerHTML = '';
    let hasFieldsToFill = false;

    fields.forEach(field => {
      const profileKey = mapping[field.selector];
      const value = profileKey ? getProfileValueByKey(profile, profileKey) : null;

      const item = document.createElement('div');
      item.className = 'field-item';

      const label = document.createElement('span');
      label.className = 'field-label';
      label.textContent = formatLabel(field.label || field.name || field.id || '(unknown)');
      label.title = field.label || field.selector;

      const valueEl = document.createElement('span');
      valueEl.className = 'field-value' + (value ? '' : ' missing');

      if (value) {
        valueEl.textContent = truncate(value, 25);
        valueEl.title = value;
        hasFieldsToFill = true;
      } else if (profileKey) {
        valueEl.textContent = `${profileKey} (empty)`;
        valueEl.title = `Mapped to ${profileKey} but no value in profile`;
      } else {
        valueEl.textContent = 'No match';
        valueEl.title = 'Could not match this field to any profile key';
      }

      item.appendChild(label);
      item.appendChild(valueEl);
      fieldListEl.appendChild(item);
    });

    // Update button state
    fillBtn.disabled = !hasFieldsToFill;
    fillBtn.textContent = hasFieldsToFill ? 'Fill Form' : 'No fields to fill';
  }

  function displayFields(fields, fileUploads) {
    fieldListEl.innerHTML = '';

    fields.forEach(field => {
      const item = document.createElement('div');
      item.className = 'field-item';

      const label = document.createElement('span');
      label.className = 'field-label';
      label.textContent = formatLabel(field.label);
      label.title = field.label;

      const value = document.createElement('span');
      value.className = 'field-value' + (field.hasValue ? '' : ' missing');
      value.textContent = field.hasValue ? truncate(field.value, 25) : 'Not set';
      value.title = field.value || 'No value configured';

      item.appendChild(label);
      item.appendChild(value);
      fieldListEl.appendChild(item);
    });

    if (fileUploads.length > 0) {
      fileUploadsEl.style.display = 'block';
      fileListEl.innerHTML = '';

      fileUploads.forEach(upload => {
        const item = document.createElement('div');
        item.className = 'file-item';

        const label = document.createElement('span');
        label.textContent = formatLabel(upload.label);

        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = upload.type;

        item.appendChild(label);
        item.appendChild(badge);
        fileListEl.appendChild(item);
      });
    }

    // Update button state
    const hasFieldsToFill = fields.some(f => f.hasValue);
    fillBtn.disabled = !hasFieldsToFill;
    if (!hasFieldsToFill) {
      fillBtn.textContent = 'No fields to fill';
    }
  }

  // Helper to get profile value by dot-notation key (mirror of content.js logic)
  function getProfileValueByKey(profile, key) {
    if (key.includes('.')) {
      const [parent, child] = key.split('.');

      if (parent === 'address') {
        return profile.address?.[child] || null;
      }
      if (parent === 'education') {
        const edu = profile.education?.[0];
        if (!edu) return null;

        if (child === 'school') return edu.school;
        if (child === 'degree') return edu.degree;
        if (child === 'major') return edu.major;
        if (child === 'gpa') return edu.gpa;
        if (child === 'end_year') return edu.graduation_date?.split('-')[0] || null;
        if (child === 'start_year') return edu.start_date?.split('-')[0] || null;
        return null;
      }
      if (parent === 'high_school') {
        return profile.high_school?.[child] || null;
      }
      if (parent === 'test_scores') {
        return profile.test_scores?.[child] || null;
      }
      return null;
    }

    if (key === 'full_name') {
      if (profile.first_name && profile.last_name) {
        return `${profile.first_name} ${profile.last_name}`;
      }
      return null;
    }

    if (key === 'authorized_to_work') return profile.authorized_to_work ? 'Yes' : 'No';
    if (key === 'requires_sponsorship') return profile.requires_sponsorship ? 'Yes' : 'No';
    if (key === 'applied_before') return profile.applied_before ? 'Yes' : 'No';
    if (key === 'other_offers') return profile.other_offers ? 'Yes' : 'No';

    if (key === 'skills') {
      const skills = profile.skills || profile.programming_languages;
      if (Array.isArray(skills)) {
        return skills.filter(s =>
          /python|java|javascript|typescript|c\+\+|c#|go|rust|ruby|sql|html|css|bash|ocaml/i.test(s)
        ).join(', ');
      }
      return null;
    }

    return profile[key] || null;
  }

  function formatLabel(label) {
    // Clean up label text
    return label
      .replace(/[*:]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 30);
  }

  function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
  }

  // Fill button click
  fillBtn.addEventListener('click', async () => {
    fillBtn.disabled = true;
    fillBtn.textContent = 'Filling...';

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      let response;

      if (useLLMMode && currentLLMMapping) {
        // Use LLM mapping to fill
        response = await chrome.tabs.sendMessage(tab.id, {
          action: 'fillWithMapping',
          mapping: currentLLMMapping
        });
      } else {
        // Use regex-based filling
        response = await chrome.tabs.sendMessage(tab.id, { action: 'fill' });
      }

      displayResults(response.results);
      fillBtn.textContent = 'Done!';

      setTimeout(() => {
        fillBtn.textContent = 'Fill Again';
        fillBtn.disabled = false;
      }, 2000);

    } catch (error) {
      console.error('Error filling form:', error);
      fillBtn.textContent = 'Error - Try Again';
      fillBtn.disabled = false;
    }
  });

  function displayResults(results) {
    resultsEl.style.display = 'block';
    resultsEl.innerHTML = '';

    if (results.filled.length > 0) {
      const filledTitle = document.createElement('div');
      filledTitle.className = 'section-title';
      filledTitle.textContent = `Filled ${results.filled.length} fields`;
      resultsEl.appendChild(filledTitle);

      results.filled.forEach(item => {
        const el = document.createElement('div');
        el.className = 'result-item filled';
        el.innerHTML = `<span class="checkmark">&#10003;</span> ${formatLabel(item.label)}`;
        resultsEl.appendChild(el);
      });
    }

    if (results.errors && results.errors.length > 0) {
      const errorTitle = document.createElement('div');
      errorTitle.className = 'section-title';
      errorTitle.style.color = '#c53030';
      errorTitle.textContent = `Errors`;
      resultsEl.appendChild(errorTitle);

      results.errors.forEach(item => {
        const el = document.createElement('div');
        el.className = 'result-item error';
        el.textContent = `X ${formatLabel(item.label || item.selector)}: ${item.reason}`;
        resultsEl.appendChild(el);
      });
    }
  }

});
