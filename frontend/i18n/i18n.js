/* ==============================================================================
   CTAS (Coastal Threat Alert System) - Multilingual i18n Engine
   Supported Languages: English, Hindi, Tamil, Malayalam, Bengali, Odia, Gujarati, Konkani
   ============================================================================== */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CTAS_i18n = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const STORAGE_KEY = 'ctas_language';
  const DEFAULT_LANG = 'en';

  const LANGUAGES = {
    en: { name: 'English', native: 'English', flag: '🌐' },
    hi: { name: 'Hindi', native: 'हिन्दी', flag: '🇮🇳' },
    ta: { name: 'Tamil', native: 'தமிழ்', flag: '🇮🇳' },
    ml: { name: 'Malayalam', native: 'മലയാളം', flag: '🇮🇳' },
    bn: { name: 'Bengali', native: 'বাংলা', flag: '🇮🇳' },
    or: { name: 'Odia', native: 'ଓଡ଼ିଆ', flag: '🇮🇳' },
    gu: { name: 'Gujarati', native: 'ગુજરાતી', flag: '🇮🇳' },
    kok: { name: 'Konkani', native: 'कोंकणी', flag: '🇮🇳' }
  };

  let currentLang = DEFAULT_LANG;
  const translationCache = {};

  // Fetch a translation file with in-memory caching and offline resilience
  async function loadTranslations(lang) {
    if (translationCache[lang]) {
      return translationCache[lang];
    }

    try {
      const res = await fetch(`/frontend/i18n/${lang}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      translationCache[lang] = data;
      return data;
    } catch (err) {
      console.warn(`[CTAS i18n] Failed to load /frontend/i18n/${lang}.json, falling back:`, err);
      // If language fails and isn't English, fallback to English
      if (lang !== DEFAULT_LANG) {
        return await loadTranslations(DEFAULT_LANG);
      }
      return {};
    }
  }

  // Deep key lookup (e.g. 'nav.home')
  function getNestedValue(obj, keyPath) {
    if (!obj || !keyPath) return null;
    const parts = keyPath.split('.');
    let cur = obj;
    for (const part of parts) {
      if (cur && typeof cur === 'object' && part in cur) {
        cur = cur[part];
      } else {
        return null;
      }
    }
    return cur;
  }

  // Programmatic translation lookup
  function t(keyPath, fallback = '') {
    const activeData = translationCache[currentLang];
    const enData = translationCache[DEFAULT_LANG];

    let val = getNestedValue(activeData, keyPath);
    if (val === null || val === undefined) {
      val = getNestedValue(enData, keyPath);
    }
    return val !== null && val !== undefined ? val : (fallback || keyPath);
  }

  // Scan and translate DOM elements with data-i18n attributes
  function translateDOM(rootElement = document) {
    // 1. innerText / innerHTML
    rootElement.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const translation = t(key);
      if (translation && translation !== key) {
        // If string contains HTML (e.g., icons, emphasis), use innerHTML, else textContent
        if (translation.includes('<') && translation.includes('>')) {
          el.innerHTML = translation;
        } else {
          el.textContent = translation;
        }
      }
    });

    // 2. Placeholders
    rootElement.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      const translation = t(key);
      if (translation && translation !== key) {
        el.setAttribute('placeholder', translation);
      }
    });

    // 3. Titles / Tooltips
    rootElement.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const key = el.getAttribute('data-i18n-title');
      const translation = t(key);
      if (translation && translation !== key) {
        el.setAttribute('title', translation);
      }
    });

    // 4. Aria Labels
    rootElement.querySelectorAll('[data-i18n-aria]').forEach((el) => {
      const key = el.getAttribute('data-i18n-aria');
      const translation = t(key);
      if (translation && translation !== key) {
        el.setAttribute('aria-label', translation);
      }
    });

    // Update html lang attribute
    document.documentElement.lang = currentLang;
  }

  // Switch language
  async function setLanguage(lang) {
    if (!LANGUAGES[lang]) {
      console.warn(`[CTAS i18n] Unsupported language "${lang}", defaulting to "${DEFAULT_LANG}"`);
      lang = DEFAULT_LANG;
    }

    currentLang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) {}

    // Preload both requested language and English master
    await Promise.all([loadTranslations(DEFAULT_LANG), loadTranslations(lang)]);

    translateDOM();
    updateSelectorUI();

    // Dispatch global event for components to react
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang, meta: LANGUAGES[lang] } }));
  }

  // Create unified glassmorphic Language Selector component
  function createLanguageSelector() {
    const wrap = document.createElement('div');
    wrap.className = 'ctas-lang-selector-wrap';
    wrap.style.cssText = `
      position: relative;
      display: inline-flex;
      align-items: center;
      margin-left: 8px;
      margin-right: 8px;
    `;

    wrap.innerHTML = `
      <div style="
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.18);
        padding: 5px 10px;
        border-radius: 20px;
        backdrop-filter: blur(8px);
        transition: all 0.25s ease;
      ">
        <span style="font-size: 14px;">🌐</span>
        <select id="ctas-lang-dropdown" style="
          background: transparent;
          border: none;
          color: #EDEAFB;
          font-family: inherit;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
          outline: none;
          padding-right: 4px;
        ">
          ${Object.entries(LANGUAGES).map(([code, info]) => `
            <option value="${code}" style="background: #130B20; color: #EDEAFB;">
              ${info.native} (${code.toUpperCase()})
            </option>
          `).join('')}
        </select>
      </div>
    `;

    const select = wrap.querySelector('#ctas-lang-dropdown');
    select.value = currentLang;

    select.addEventListener('change', (e) => {
      setLanguage(e.target.value);
    });

    return wrap;
  }

  function updateSelectorUI() {
    document.querySelectorAll('#ctas-lang-dropdown').forEach((sel) => {
      sel.value = currentLang;
    });
  }

  // Auto-mount selector to placeholders or nav
  function autoMountSelector() {
    const existing = document.querySelector('.ctas-lang-selector-wrap');
    if (existing) return;

    // Check specific container
    const placeholder = document.getElementById('ctas-language-selector') || document.querySelector('.ctas-language-selector');
    if (placeholder) {
      placeholder.appendChild(createLanguageSelector());
      return;
    }

    // Default: mount into #header-actions or .nav-bar or body top
    const headerActions = document.getElementById('header-actions');
    if (headerActions) {
      headerActions.prepend(createLanguageSelector());
      return;
    }

    const navBar = document.querySelector('.nav-bar') || document.querySelector('.ai-controls');
    if (navBar) {
      navBar.appendChild(createLanguageSelector());
      return;
    }
  }

  // Initialize
  async function init() {
    let savedLang = DEFAULT_LANG;
    try {
      savedLang = localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
    } catch (e) {}

    await setLanguage(savedLang);
    autoMountSelector();
  }

  // Hook into DOMContentLoaded
  if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', () => init());
    } else {
      init();
    }
  }

  return {
    LANGUAGES,
    currentLang: () => currentLang,
    t,
    setLanguage,
    translateDOM,
    createLanguageSelector,
    autoMountSelector,
    init
  };
});
