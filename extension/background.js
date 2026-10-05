// Job Application Auto-Fill - Background Service Worker

const SERVER_URL = 'http://localhost:8765';
const CACHE_KEY_PREFIX = 'llm_cache_';
const CACHE_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

// Profile keys that the LLM can map to
const PROFILE_KEYS = [
  'first_name', 'last_name', 'full_name', 'email', 'phone', 'phone_country_code',
  'address.street', 'address.city', 'address.state', 'address.zip', 'address.country',
  'linkedin', 'github', 'portfolio',
  'education.school', 'education.degree', 'education.major', 'education.gpa',
  'education.start_year', 'education.start_month', 'education.end_year', 'education.end_month',
  'education.graduation_date',
  'high_school.name', 'high_school.graduation',
  'test_scores.sat', 'test_scores.act',
  'experience.0.title', 'experience.0.company', 'experience.0.location',
  'experience.0.description', 'experience.0.start_date', 'experience.0.end_date',
  'experience.1.title', 'experience.1.company', 'experience.1.location',
  'experience.1.description', 'experience.1.start_date', 'experience.1.end_date',
  'experience.2.title', 'experience.2.company', 'experience.2.location',
  'experience.2.description', 'experience.2.start_date', 'experience.2.end_date',
  'authorized_to_work', 'requires_sponsorship', 'citizenship',
  'applied_before', 'other_offers',
  'gender', 'race_ethnicity', 'veteran_status', 'disability_status',
  'skills',
  'interview_code_of_conduct', 'privacy_statement', 'pursuing_further_education'
];

// Generate a fingerprint for caching based on URL and field structure
function generateCacheKey(url, fields) {
  const fieldFingerprint = fields
    .map(f => `${f.selector}:${f.label}:${f.type}`)
    .sort()
    .join('|');
  const hash = simpleHash(fieldFingerprint);
  // Use URL pathname (ignore query params which may change)
  const urlPath = new URL(url).pathname;
  return `${CACHE_KEY_PREFIX}${urlPath}_${hash}`;
}

function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}

// Check cache for existing mapping
async function getCachedMapping(cacheKey) {
  const result = await chrome.storage.local.get([cacheKey]);
  if (result[cacheKey]) {
    const cached = result[cacheKey];
    if (Date.now() - cached.timestamp < CACHE_EXPIRY_MS) {
      return cached.mapping;
    }
    // Cache expired, remove it
    await chrome.storage.local.remove([cacheKey]);
  }
  return null;
}

// Save mapping to cache
async function cacheMapping(cacheKey, mapping) {
  await chrome.storage.local.set({
    [cacheKey]: {
      mapping,
      timestamp: Date.now()
    }
  });
}

// Call local server to get LLM field mapping
async function getLLMMapping(fields) {
  const response = await fetch(`${SERVER_URL}/match-fields`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      profile_keys: PROFILE_KEYS,
      fields: fields
    })
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Server error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  return data.mapping;
}

// Check if server is running
async function checkServerStatus() {
  try {
    const response = await fetch(`${SERVER_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return response.ok;
  } catch (e) {
    return false;
  }
}

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkLLMStatus') {
    checkServerStatus().then(isRunning => {
      sendResponse({ available: isRunning });
    });
    return true;
  }

  if (request.action === 'getLLMMapping') {
    const { fields, url } = request;

    (async () => {
      try {
        // Check cache first
        const cacheKey = generateCacheKey(url, fields);
        const cachedMapping = await getCachedMapping(cacheKey);

        if (cachedMapping) {
          sendResponse({
            success: true,
            mapping: cachedMapping,
            fromCache: true
          });
          return;
        }

        // Call LLM server
        const mapping = await getLLMMapping(fields);

        // Cache the result
        await cacheMapping(cacheKey, mapping);

        sendResponse({
          success: true,
          mapping: mapping,
          fromCache: false
        });
      } catch (error) {
        console.error('LLM mapping error:', error);
        sendResponse({
          success: false,
          error: error.message
        });
      }
    })();

    return true; // Keep channel open for async response
  }

  if (request.action === 'clearLLMCache') {
    (async () => {
      const all = await chrome.storage.local.get(null);
      const cacheKeys = Object.keys(all).filter(k => k.startsWith(CACHE_KEY_PREFIX));
      await chrome.storage.local.remove(cacheKeys);
      sendResponse({ cleared: cacheKeys.length });
    })();
    return true;
  }
});
