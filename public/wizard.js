// ── State ────────────────────────────────────────────────────
const STORAGE_KEY = 'directa_state';
const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');

const SESSION_ID = (saved && saved.sessionId) || crypto.randomUUID();
let currentStep = (saved && saved.step) || 1;
const TOTAL_STEPS = 11;

const wizardData = (saved && saved.data) || {
  video_type: null,
  goal: null,
  mood: null,
  subject: '',
  environment: '',
  action: '',
  scene_feel: '',
  ref_character: null,
  ref_lighting: null,
  ref_camera: null,
  ref_audio: null,
  lighting: null,
  camera_movement: null,
  shot_type: null,
  depth_of_field: null,
  pace: null,
  duration: '5',
  aspect_ratio: '16:9',
  resolution: '720p',
  fixed_elements: [],
  avoid_elements: [],
  avoid_extra: '',
};

let builtPrompts = null;
let generationId = null;
let generationModel = null;
let pollingTimer = null;

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    sessionId: SESSION_ID,
    step: currentStep,
    data: wizardData,
  }));
}

function clearState() {
  localStorage.removeItem(STORAGE_KEY);
}

// ── Templates ────────────────────────────────────────────────
const TEMPLATES_KEY = 'directa_templates';

function getTemplates() {
  return JSON.parse(localStorage.getItem(TEMPLATES_KEY) || '[]');
}

function saveTemplate(name) {
  const templates = getTemplates();
  templates.push({
    name,
    date: new Date().toLocaleDateString('ar-SA'),
    data: { ...wizardData },
  });
  localStorage.setItem(TEMPLATES_KEY, JSON.stringify(templates));
}

function deleteTemplate(idx) {
  const templates = getTemplates();
  templates.splice(idx, 1);
  localStorage.setItem(TEMPLATES_KEY, JSON.stringify(templates));
}

function loadTemplate(idx) {
  const templates = getTemplates();
  const tpl = templates[idx];
  if (!tpl) return;
  Object.assign(wizardData, tpl.data);
  // Clear refs since they belong to old sessions
  wizardData.ref_character = null;
  wizardData.ref_lighting = null;
  wizardData.ref_camera = null;
  wizardData.ref_audio = null;
  currentStep = 1;
  hide($('#landing-page'));
  show($('#wizard-view'));
  renderStep();
}

// ── API Helper ───────────────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json();
}

// ── DOM Helpers ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }

// ── Progress Bar ─────────────────────────────────────────────
function updateProgress() {
  const pct = ((currentStep) / TOTAL_STEPS) * 100;
  $('#progress-bar').style.width = pct + '%';
  $('#step-counter').textContent = `الخطوة ${currentStep} من ${TOTAL_STEPS}`;
}

// ── Step Rendering ───────────────────────────────────────────
function renderStep() {
  const container = $('#wizard-content');
  container.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'step-card';

  switch (currentStep) {
    case 1: renderStep1(card); break;
    case 2: renderStep2(card); break;
    case 3: renderStep3(card); break;
    case 4: renderStep4(card); break;
    case 5: renderStep5(card); break;
    case 6: renderStep6(card); break;
    case 7: renderStep7(card); break;
    case 8: renderStep8(card); break;
    case 9: renderStep9(card); break;
    case 10: renderStep10(card); break;
    case 11: renderStep11(card); break;
  }

  container.appendChild(card);
  updateProgress();
  updateNav();
  saveState();
}

// ── Navigation ───────────────────────────────────────────────
function updateNav() {
  const backBtn = $('#btn-back');
  const nextBtn = $('#btn-next');

  if (currentStep === 1) {
    hide(backBtn);
  } else {
    show(backBtn);
  }

  if (currentStep === 11) {
    hide(nextBtn);
    hide(backBtn);
    hide($('#nav-buttons'));
  } else {
    show(nextBtn);
    show($('#nav-buttons'));
    nextBtn.disabled = !isStepValid();
  }
}

function isStepValid() {
  switch (currentStep) {
    case 1: return !!wizardData.video_type;
    case 2: return !!wizardData.goal && !!wizardData.mood;
    case 3: return wizardData.subject.trim().length > 0 && wizardData.environment.trim().length > 0;
    case 4: case 5: case 6: case 7: return true; // optional
    case 8: return !!wizardData.lighting && !!wizardData.camera_movement;
    case 9: return !!wizardData.shot_type && !!wizardData.depth_of_field && !!wizardData.pace && !!wizardData.duration && !!wizardData.aspect_ratio && !!wizardData.resolution;
    case 10: return true;
    default: return true;
  }
}

function goNext() {
  if (currentStep < TOTAL_STEPS && isStepValid()) {
    currentStep++;
    renderStep();
  }
}

function goBack() {
  if (currentStep > 1) {
    currentStep--;
    renderStep();
  }
}

// ── Helpers for building step UI ─────────────────────────────
function addQuestion(card, text, hint) {
  const q = document.createElement('div');
  q.className = 'step-question';
  q.textContent = text;
  card.appendChild(q);
  if (hint) {
    const h = document.createElement('div');
    h.className = 'step-hint';
    h.textContent = hint;
    card.appendChild(h);
  }
}

function addSectionLabel(card, text) {
  const lbl = document.createElement('div');
  lbl.className = 'section-label';
  lbl.textContent = text;
  card.appendChild(lbl);
}

function addOptionGrid(card, options, field, cols = 2) {
  const grid = document.createElement('div');
  grid.className = 'option-grid';
  if (cols === 1) grid.classList.add('single-col');

  options.forEach(([label, value]) => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    if (wizardData[field] === value) btn.classList.add('selected');
    btn.textContent = label;
    btn.addEventListener('click', () => {
      wizardData[field] = value;
      grid.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      updateNav();
      saveState();
    });
    grid.appendChild(btn);
  });

  card.appendChild(grid);
}

function addTextInput(card, field, label, placeholder, isTextarea = false) {
  const group = document.createElement('div');
  group.className = 'text-input-group';

  const lbl = document.createElement('label');
  lbl.textContent = label;
  group.appendChild(lbl);

  const input = document.createElement(isTextarea ? 'textarea' : 'input');
  input.className = 'text-input';
  input.placeholder = placeholder;
  input.value = wizardData[field] || '';
  input.addEventListener('input', () => {
    wizardData[field] = input.value;
    updateNav();
    saveState();
  });
  group.appendChild(input);

  card.appendChild(group);
  return input;
}

function addUploadZone(card, purpose, icon, text, subText, acceptTypes, refField) {
  const zone = document.createElement('div');
  zone.className = 'upload-zone';
  if (wizardData[refField] && wizardData[refField].url) {
    zone.classList.add('uploaded');
  }
  zone.innerHTML = `
    <div class="upload-icon">${icon}</div>
    <div class="upload-text">${text}</div>
    <div class="upload-sub">${subText}</div>
    <div class="upload-spinner" id="spinner-${purpose}"></div>
    <div class="upload-preview" id="preview-${purpose}">
      <img id="thumb-${purpose}" src="" alt="">
      <span class="upload-filename" id="fname-${purpose}"></span>
      <span class="upload-check">&#10003;</span>
    </div>
  `;

  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = acceptTypes;
  fileInput.style.display = 'none';

  zone.addEventListener('click', (e) => {
    if (e.target.closest('.ref-description') || e.target.closest('.text-input')) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    zone.classList.add('uploading');
    zone.classList.remove('uploaded');
    const spinner = zone.querySelector(`#spinner-${purpose}`);
    spinner.classList.add('visible');
    const preview = zone.querySelector(`#preview-${purpose}`);
    preview.classList.remove('visible');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('purpose', purpose);
      formData.append('session_id', SESSION_ID);

      const result = await api('/api/upload-reference', { method: 'POST', body: formData });

      spinner.classList.remove('visible');
      zone.classList.remove('uploading');
      zone.classList.add('uploaded');

      preview.classList.add('visible');
      const thumb = zone.querySelector(`#thumb-${purpose}`);
      const fname = zone.querySelector(`#fname-${purpose}`);
      fname.textContent = file.name;

      if (file.type.startsWith('image/')) {
        thumb.src = URL.createObjectURL(file);
        thumb.style.display = 'block';
      } else {
        thumb.style.display = 'none';
      }

      if (!wizardData[refField]) wizardData[refField] = {};
      wizardData[refField].url = result.url;
      wizardData[refField].file_type = result.file_type;
      saveState();

    } catch (err) {
      spinner.classList.remove('visible');
      zone.classList.remove('uploading');
      alert('فشل الرفع: ' + err.message);
    }
  });

  card.appendChild(zone);
  card.appendChild(fileInput);

  // Show existing upload
  if (wizardData[refField] && wizardData[refField].url) {
    const preview = zone.querySelector(`#preview-${purpose}`);
    const fname = zone.querySelector(`#fname-${purpose}`);
    preview.classList.add('visible');
    fname.textContent = 'مرفوع';
    const thumb = zone.querySelector(`#thumb-${purpose}`);
    const ft = wizardData[refField].file_type || '';
    if (['png','jpg','jpeg','webp'].includes(ft)) {
      thumb.src = wizardData[refField].url;
      thumb.style.display = 'block';
    } else {
      thumb.style.display = 'none';
    }
  }

  // Description field
  const descGroup = document.createElement('div');
  descGroup.className = 'ref-description';
  const descLabel = document.createElement('label');
  descLabel.textContent = 'صف ما يجب أن يؤخذ من هذا المرجع';
  descLabel.style.cssText = 'display:block;font-size:0.82rem;font-weight:600;margin-top:14px;margin-bottom:6px;';
  descGroup.appendChild(descLabel);

  const descInput = document.createElement('input');
  descInput.className = 'text-input';
  descInput.placeholder = 'وصف اختياري...';
  descInput.value = (wizardData[refField] && wizardData[refField].description) || '';
  descInput.addEventListener('input', () => {
    if (!wizardData[refField]) wizardData[refField] = {};
    wizardData[refField].description = descInput.value;
    saveState();
  });
  descInput.addEventListener('click', (e) => e.stopPropagation());
  descGroup.appendChild(descInput);
  card.appendChild(descGroup);

  // Skip button
  const skip = document.createElement('button');
  skip.className = 'skip-btn';
  skip.textContent = 'تخطي — ليس عندي مرجع';
  skip.addEventListener('click', (e) => {
    e.stopPropagation();
    goNext();
  });
  card.appendChild(skip);
}

function _isYouTubeUrl(url) {
  return url.includes('youtube.com/') || url.includes('youtu.be/');
}

function addVideoUrlInput(card, refField) {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'margin-top:12px;display:flex;gap:8px;align-items:center;';

  const input = document.createElement('input');
  input.className = 'text-input';
  input.placeholder = 'الصق رابط فيديو مباشر (MP4)...';
  input.dir = 'ltr';
  input.style.flex = '1';

  const btn = document.createElement('button');
  btn.className = 'nav-btn next';
  btn.style.cssText = 'flex:none;padding:10px 16px;font-size:0.8rem;';
  btn.textContent = 'جلب';
  btn.disabled = true;

  // YouTube helper message
  const ytMsg = document.createElement('div');
  ytMsg.className = 'hidden';
  ytMsg.style.cssText = 'margin-top:8px;padding:10px 12px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;font-size:0.78rem;line-height:1.6;color:#999;';
  ytMsg.innerHTML = `
    رابط يوتيوب لا يعمل مباشرة. حمّل المقطع أولاً:<br>
    1. افتح <a href="https://cobalt.tools" target="_blank" style="color:#C9A84C;">cobalt.tools</a> أو <a href="https://ssyoutube.com" target="_blank" style="color:#C9A84C;">ssyoutube.com</a><br>
    2. الصق رابط اليوتيوب وحمّل MP4<br>
    3. ارفع الملف هنا بالزر أعلاه
  `;

  input.addEventListener('input', () => {
    const v = input.value.trim();
    if (_isYouTubeUrl(v)) {
      ytMsg.classList.remove('hidden');
      btn.disabled = true;
    } else {
      ytMsg.classList.add('hidden');
      btn.disabled = !v.startsWith('http');
    }
  });

  btn.addEventListener('click', async () => {
    const url = input.value.trim();
    btn.disabled = true;
    btn.textContent = 'جاري التحميل...';
    input.disabled = true;

    try {
      const result = await api('/api/url-reference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, session_id: SESSION_ID, purpose: refField.replace('ref_', '') }),
      });

      if (!wizardData[refField]) wizardData[refField] = {};
      wizardData[refField].url = result.url;
      wizardData[refField].file_type = result.file_type;
      saveState();

      btn.textContent = '✓ تم';
      btn.style.background = '#2d6a4f';
      input.style.borderColor = '#2d6a4f';
    } catch (err) {
      btn.textContent = 'جلب';
      btn.disabled = false;
      input.disabled = false;
      alert('فشل جلب الفيديو: ' + (err.message || 'خطأ غير معروف'));
    }
  });

  wrapper.appendChild(input);
  wrapper.appendChild(btn);
  card.appendChild(wrapper);
  card.appendChild(ytMsg);
}

function addChipGrid(card, options, field) {
  const grid = document.createElement('div');
  grid.className = 'chip-grid';

  options.forEach(([label, value]) => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    if (wizardData[field].includes(value)) chip.classList.add('selected');
    chip.textContent = label;
    chip.addEventListener('click', () => {
      const idx = wizardData[field].indexOf(value);
      if (idx >= 0) {
        wizardData[field].splice(idx, 1);
        chip.classList.remove('selected');
      } else {
        wizardData[field].push(value);
        chip.classList.add('selected');
      }
      saveState();
    });
    grid.appendChild(chip);
  });

  card.appendChild(grid);
}


// ═════════════════════════════════════════════════════════════
// STEP DEFINITIONS
// ═════════════════════════════════════════════════════════════

function renderStep1(card) {
  addQuestion(card, 'ما نوع الفيديو الذي تريد صناعته؟', 'ابدأ من النتيجة النهائية، وليس من الفكرة');
  addOptionGrid(card, [
    ['🎯 إعلان منتج', 'product_ad'],
    ['🎬 مشهد سينمائي', 'cinematic_scene'],
    ['📱 ريلز / سوشال', 'social_reel'],
    ['👤 UGC Style', 'ugc'],
    ['🔍 عرض منتج قريب', 'product_closeup'],
    ['🎵 فيجوال موسيقي', 'music_visual'],
    ['📖 قصة قصيرة', 'short_story'],
    ['🚀 إعلان إطلاق', 'launch_ad'],
  ], 'video_type');
}

function renderStep2(card) {
  addQuestion(card, 'ما الهدف؟ وما الإحساس المطلوب؟', 'الهدف يحدد الرسالة — الإحساس يحدد الروح');

  addSectionLabel(card, 'الهدف');
  addOptionGrid(card, [
    ['يبيع ويحوّل', 'sell_convert'],
    ['يثير فضول', 'spark_curiosity'],
    ['يوصل فخامة', 'convey_luxury'],
    ['يبني هوية', 'brand_identity'],
    ['يحكي قصة', 'storytelling'],
    ['يمتع ويطرب', 'entertain'],
  ], 'goal');

  addSectionLabel(card, 'الجو العام');
  addOptionGrid(card, [
    ['فاخر وهادئ', 'luxury_calm'],
    ['حيوي وسريع', 'energetic_fast'],
    ['درامي وعاطفي', 'dramatic_emotional'],
    ['نظيف ومحترف', 'clean_professional'],
    ['دافئ وحميمي', 'warm_intimate'],
    ['قوي وجريء', 'bold_powerful'],
  ], 'mood');
}

function renderStep3(card) {
  addQuestion(card, 'صف المشهد بالكامل', 'الموضوع + المكان + الحركة + الإحساس = تعليمات إخراج حقيقية');
  addTextInput(card, 'subject', 'الموضوع الرئيسي', 'مثال: زجاجة عطر سوداء فاخرة، شاب بملابس سوداء، كوب قهوة...');
  addTextInput(card, 'environment', 'البيئة والمكان', 'مثال: سطح رخامي أسود، مقهى عصري، شارع ممطر ليلاً...');
  addTextInput(card, 'action', 'الحركة داخل المشهد', 'مثال: يمشي بثقة، يد تمسك المنتج وتفتحه، دخان يتصاعد خلف الزجاجة...');
  addTextInput(card, 'scene_feel', 'الإحساس النهائي للمشهد', 'مثال: إحساس إعلان عطر فاخر، أجواء فيلم جريمة حديث، طاقة براند رياضي...');
}

function renderStep4(card) {
  addQuestion(card, 'هل عندك صورة مرجعية للشخصية أو المنتج؟', 'هذا المرجع يثبت الشكل الأساسي — الوجه، العبوة، التفاصيل الجوهرية');
  addUploadZone(card, 'character', '🎭', 'ارفع صورة الشخصية أو المنتج', 'PNG / JPG / WEBP — الحد الأقصى 10MB', 'image/png,image/jpeg,image/webp', 'ref_character');
}

function renderStep5(card) {
  addQuestion(card, 'هل عندك مرجع لنوع الإضاءة التي تريدها؟', 'صورة واحدة تحدد الإضاءة أفضل من مئة كلمة');
  addUploadZone(card, 'lighting', '💡', 'ارفع صورة مرجع الإضاءة', 'PNG / JPG / WEBP', 'image/png,image/jpeg,image/webp', 'ref_lighting');
}

function renderStep6(card) {
  addQuestion(card, 'هل عندك فيديو مرجعي لحركة الكاميرا؟', 'ارفع ملف أو الصق رابط يوتيوب (15 ثانية كحد أقصى)');
  addUploadZone(card, 'camera', '🎥', 'ارفع فيديو مرجع حركة الكاميرا', 'MP4 / MOV / WEBM — الحد الأقصى 50MB', 'video/mp4,video/quicktime,video/webm', 'ref_camera');
  addVideoUrlInput(card, 'ref_camera');
}

function renderStep7(card) {
  addQuestion(card, 'هل عندك مرجع صوتي يعبر عن الإيقاع المطلوب؟', 'الصوت يحدد إيقاع المشهد وسرعة القطع');
  addUploadZone(card, 'audio', '🎵', 'ارفع ملف صوتي مرجعي', 'MP3 / WAV / M4A — الحد الأقصى 20MB', 'audio/mpeg,audio/wav,audio/x-m4a,audio/mp4', 'ref_audio');
}

function renderStep8(card) {
  addQuestion(card, 'حدد الإضاءة وحركة الكاميرا بالضبط', 'هذه هي تعليمات الإخراج الفعلية');

  addSectionLabel(card, 'الإضاءة');
  addOptionGrid(card, [
    ['☀️ طبيعية دافئة', 'natural_warm'],
    ['🌑 جانبية ناعمة', 'soft_side'],
    ['🔵 سينمائية زرقاء', 'cinematic_blue'],
    ['✨ فاخرة معكوسة', 'luxury_reflective'],
    ['🕯️ خافتة درامية', 'dim_dramatic'],
    ['🌟 استوديو نظيفة', 'clean_studio'],
    ['🌅 ذهبية (Golden Hour)', 'golden_hour'],
    ['⚡ نيون حضرية', 'neon_urban'],
  ], 'lighting');

  addSectionLabel(card, 'حركة الكاميرا');
  addOptionGrid(card, [
    ['🔍 اقتراب بطيء — Dolly-in', 'slow_dolly_in'],
    ['🔄 دوران حول الموضوع — Orbit', 'orbit'],
    ['📷 ثابتة — Static', 'static'],
    ['🎥 تتبع من الخلف — Tracking', 'tracking_shot'],
    ['↕️ زاوية منخفضة — Low Angle', 'low_angle_hero'],
    ['🎥 محمولة سينمائية — Handheld', 'handheld_cinematic'],
    ['🔭 اقتراب كاشف — Push-in', 'push_in_reveal'],
    ['⬆️ من الأعلى — Top-down', 'top_down'],
    ['🎯 تغيير بؤري — Rack Focus', 'rack_focus'],
  ], 'camera_movement');
}

function renderStep9(card) {
  addQuestion(card, 'نوع اللقطة والتفاصيل التقنية', '');

  addSectionLabel(card, 'نوع اللقطة');
  addOptionGrid(card, [
    ['🌍 لقطة واسعة — Wide', 'wide'],
    ['🧍 لقطة كاملة — Full', 'full'],
    ['👤 لقطة متوسطة — Medium', 'medium'],
    ['🔍 لقطة قريبة — Close-up', 'closeup'],
    ['🔬 ماكرو — Extreme Close-up', 'macro'],
    ['🎬 من واسعة لقريبة — Wide to Close', 'wide_to_close'],
  ], 'shot_type');

  addSectionLabel(card, 'عمق الميدان');
  addOptionGrid(card, [
    ['🌸 ضحل — خلفية ضبابية', 'shallow_dof'],
    ['🎯 متوسط', 'medium_dof'],
    ['🏔️ عميق — كل شيء واضح', 'deep_dof'],
  ], 'depth_of_field');

  addSectionLabel(card, 'الإيقاع والسرعة');
  addOptionGrid(card, [
    ['🐌 بطيء ومدروس', 'slow_paced'],
    ['⚖️ متوسط ومتوازن', 'medium_paced'],
    ['⚡ سريع وحيوي', 'fast_paced'],
  ], 'pace');

  addSectionLabel(card, 'مدة الفيديو');
  addOptionGrid(card, [
    ['5 ثوانٍ', '5'],
    ['10 ثوانٍ', '10'],
    ['15 ثانية', '15'],
  ], 'duration');

  addSectionLabel(card, 'أبعاد الفيديو');
  addOptionGrid(card, [
    ['🖥️ أفقي — 16:9', '16:9'],
    ['📱 عمودي — 9:16', '9:16'],
    ['⬜ مربع — 1:1', '1:1'],
    ['🎬 سينمائي عريض — 21:9', '21:9'],
  ], 'aspect_ratio');

  addSectionLabel(card, 'الدقة');
  addOptionGrid(card, [
    ['720p — جودة عالية', '720p'],
    ['480p — أسرع', '480p'],
  ], 'resolution');
}

function renderStep10(card) {
  addQuestion(card, 'ما الذي يجب أن يبقى ثابتاً؟', 'الثوابت هي DNA المشهد — اختر العناصر التي لا يجب أن تتغير');

  addSectionLabel(card, 'يجب أن يثبت');
  addChipGrid(card, [
    ['هوية الشخصية / الشكل', 'identity'],
    ['شكل المنتج / العبوة', 'product_shape'],
    ['ألوان المشهد', 'colors'],
    ['نوع الإضاءة', 'lighting_style'],
    ['المكان / الخلفية', 'background'],
    ['الملابس', 'clothing'],
    ['الشعار أو العلامة التجارية', 'logo'],
    ['النبرة العامة', 'tone'],
  ], 'fixed_elements');

  addTextInput(card, 'avoid_extra', 'ملاحظات إضافية', 'أي تعليمات أو تفاصيل إضافية تريد إضافتها...', true);
}

// ── Step 11: Review ──────────────────────────────────────────

async function renderStep11(card) {
  addQuestion(card, 'مراجعة Directa', '');

  // Loading state
  const loader = document.createElement('div');
  loader.className = 'building-prompt';
  loader.innerHTML = '<div class="gen-animation">🎬</div><div>Directa يبني الرؤية<span class="dots">...</span></div>';
  card.appendChild(loader);

  try {
    const result = await api('/api/build-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wizard_data: wizardData }),
    });
    builtPrompts = result;
  } catch (err) {
    loader.innerHTML = `<div class="error-card"><h3>خطأ</h3><p>${err.message}</p></div>`;
    return;
  }

  // Remove loader, show review
  loader.remove();

  const reviewLabel = document.createElement('div');
  reviewLabel.className = 'review-label';
  reviewLabel.textContent = 'نظرة Directa — البرومبت النهائي';
  card.appendChild(reviewLabel);

  const reviewCard = document.createElement('div');
  reviewCard.className = 'review-card';
  reviewCard.id = 'review-prompt-display';
  reviewCard.textContent = builtPrompts.arabic_prompt;
  card.appendChild(reviewCard);

  // References thumbnails
  const refs = [];
  const refLabels = {
    ref_character: 'الشخصية',
    ref_lighting: 'الإضاءة',
    ref_camera: 'الكاميرا',
    ref_audio: 'الصوت',
  };
  for (const [key, label] of Object.entries(refLabels)) {
    if (wizardData[key] && wizardData[key].url) {
      refs.push({ ...wizardData[key], purpose: key.replace('ref_', ''), label });
    }
  }

  if (refs.length > 0) {
    const refsContainer = document.createElement('div');
    refsContainer.className = 'review-refs';
    refs.forEach(ref => {
      const item = document.createElement('div');
      item.className = 'review-ref-item';
      const ft = ref.file_type || '';
      if (['png','jpg','jpeg','webp'].includes(ft)) {
        item.innerHTML = `<img src="${ref.url}" alt="${ref.label}"><div class="review-ref-label">${ref.label}</div>`;
      } else {
        item.innerHTML = `<div style="width:64px;height:64px;background:#1a1a1a;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">📎</div><div class="review-ref-label">${ref.label}</div>`;
      }
      refsContainer.appendChild(item);
    });
    card.appendChild(refsContainer);
  }

  // English prompt preview
  const enLabel = document.createElement('div');
  enLabel.className = 'review-label';
  enLabel.style.marginTop = '16px';
  enLabel.textContent = 'البرومبت الفعلي (يُرسل لـ fal.ai)';
  card.appendChild(enLabel);

  const enCard = document.createElement('div');
  enCard.className = 'review-card';
  enCard.style.direction = 'ltr';
  enCard.style.textAlign = 'left';
  enCard.style.fontSize = '0.78rem';
  enCard.style.color = '#888';
  enCard.textContent = builtPrompts.english_prompt;
  card.appendChild(enCard);

  // Edit toggle for Arabic
  const editToggle = document.createElement('span');
  editToggle.className = 'edit-toggle';
  editToggle.textContent = 'تعديل البرومبت العربي';
  let editOpen = false;
  const editArea = document.createElement('textarea');
  editArea.className = 'text-input hidden';
  editArea.style.minHeight = '120px';
  editArea.value = builtPrompts.arabic_prompt;
  editArea.addEventListener('input', () => {
    builtPrompts.arabic_prompt = editArea.value;
    reviewCard.textContent = editArea.value;
  });

  editToggle.addEventListener('click', () => {
    editOpen = !editOpen;
    if (editOpen) {
      show(editArea);
      editToggle.textContent = 'إخفاء التعديل';
    } else {
      hide(editArea);
      editToggle.textContent = 'تعديل البرومبت العربي';
    }
  });

  card.appendChild(editToggle);
  card.appendChild(editArea);

  // Duration display
  const durLabel = document.createElement('div');
  durLabel.style.cssText = 'font-size:0.82rem;color:#888;margin-top:12px;';
  durLabel.textContent = `المدة: ${wizardData.duration || '5'} ثوانٍ`;
  card.appendChild(durLabel);

  // Save as template button
  const saveTemplateBtn = document.createElement('button');
  saveTemplateBtn.className = 'skip-btn';
  saveTemplateBtn.style.marginTop = '12px';
  saveTemplateBtn.textContent = '💾 حفظ كقالب';
  saveTemplateBtn.addEventListener('click', () => {
    const name = prompt('اسم القالب:');
    if (!name) return;
    saveTemplate(name);
    saveTemplateBtn.textContent = '✓ تم الحفظ';
    saveTemplateBtn.disabled = true;
  });
  card.appendChild(saveTemplateBtn);

  // Generate button
  const genBtn = document.createElement('button');
  genBtn.className = 'generate-btn';
  genBtn.textContent = '⚡ ابدأ التوليد';
  genBtn.addEventListener('click', () => startGeneration(genBtn));
  card.appendChild(genBtn);

  // Back button for step 11
  const backBtn = document.createElement('button');
  backBtn.className = 'nav-btn back';
  backBtn.textContent = 'رجوع';
  backBtn.style.marginTop = '10px';
  backBtn.addEventListener('click', goBack);
  card.appendChild(backBtn);
}


// ── Generation ───────────────────────────────────────────────

async function startGeneration(btn) {
  btn.disabled = true;
  btn.textContent = 'جاري الإرسال...';

  const references = [];
  const refKeys = ['ref_character', 'ref_lighting', 'ref_camera', 'ref_audio'];
  refKeys.forEach(key => {
    if (wizardData[key] && wizardData[key].url) {
      references.push({
        purpose: key.replace('ref_', ''),
        url: wizardData[key].url,
        file_type: wizardData[key].file_type || '',
      });
    }
  });

  try {
    const result = await api('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: SESSION_ID,
        wizard_data: wizardData,
        english_prompt: builtPrompts.english_prompt,
        arabic_prompt: builtPrompts.arabic_prompt,
        references,
        duration: wizardData.duration || '5',
        aspect_ratio: wizardData.aspect_ratio || '16:9',
        resolution: wizardData.resolution || '720p',
      }),
    });

    generationId = result.generation_id;
    generationModel = result.model;
    showGenerationScreen();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = '⚡ ابدأ التوليد';
    alert('خطأ: ' + err.message);
  }
}

const GEN_MESSAGES = [
  'Directa يبني المشهد...',
  'يضع الإضاءة في مكانها...',
  'الكاميرا تجد موقعها...',
  'يرسم التفاصيل الدقيقة...',
  'اللمسات الأخيرة...',
];

function showGenerationScreen() {
  const container = $('#wizard-content');
  hide($('#nav-buttons'));

  container.innerHTML = `
    <div class="step-card gen-screen">
      <div class="gen-animation">🎬</div>
      <div class="gen-message" id="gen-msg">${GEN_MESSAGES[0]}</div>
      <div class="gen-progress-track">
        <div class="gen-progress-fill" id="gen-progress"></div>
      </div>
      <div class="gen-english" id="gen-english">${builtPrompts.english_prompt}</div>
    </div>
  `;

  let msgIdx = 0;
  const msgTimer = setInterval(() => {
    msgIdx = (msgIdx + 1) % GEN_MESSAGES.length;
    const el = document.getElementById('gen-msg');
    if (el) el.textContent = GEN_MESSAGES[msgIdx];
  }, 3000);

  pollStatus(msgTimer);
}

async function pollStatus(msgTimer) {
  if (pollingTimer) clearInterval(pollingTimer);

  pollingTimer = setInterval(async () => {
    try {
      const result = await api(`/api/status/${generationId}`);
      const progressEl = document.getElementById('gen-progress');
      if (progressEl) progressEl.style.width = (result.progress || 0) + '%';

      if (result.status === 'done' && result.video_url) {
        clearInterval(pollingTimer);
        clearInterval(msgTimer);
        showVideoResult(result.video_url);
      } else if (result.status === 'error') {
        clearInterval(pollingTimer);
        clearInterval(msgTimer);
        showError(result.error || 'حدث خطأ أثناء التوليد');
      }
    } catch (err) {
      // Keep polling on network errors
    }
  }, 3000);
}

function showVideoResult(videoUrl) {
  const container = $('#wizard-content');
  container.innerHTML = `
    <div class="step-card video-result">
      <video src="${videoUrl}" autoplay loop muted playsinline controls></video>
      <div class="result-actions">
        <a href="${videoUrl}" download class="result-btn primary">⬇️ تحميل الفيديو</a>
        <button class="result-btn" id="btn-regenerate">🔄 أعد التوليد</button>
        <button class="result-btn" id="btn-edit-regen">✏️ تعديل وإعادة</button>
        <button class="result-btn" id="btn-new">🆕 مشروع جديد</button>
      </div>
    </div>
  `;

  document.getElementById('btn-regenerate').addEventListener('click', async () => {
    const references = [];
    const refKeys = ['ref_character', 'ref_lighting', 'ref_camera', 'ref_audio'];
    refKeys.forEach(key => {
      if (wizardData[key] && wizardData[key].url) {
        references.push({
          purpose: key.replace('ref_', ''),
          url: wizardData[key].url,
          file_type: wizardData[key].file_type || '',
        });
      }
    });
    try {
      const result = await api('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: SESSION_ID,
          wizard_data: wizardData,
          english_prompt: builtPrompts.english_prompt,
          arabic_prompt: builtPrompts.arabic_prompt,
          references,
          duration: wizardData.duration || '5',
        aspect_ratio: wizardData.aspect_ratio || '16:9',
        resolution: wizardData.resolution || '720p',
        }),
      });
      generationId = result.generation_id;
      generationModel = result.model;
      showGenerationScreen();
    } catch (err) {
      alert('خطأ: ' + err.message);
    }
  });

  document.getElementById('btn-edit-regen').addEventListener('click', () => {
    currentStep = 11;
    show($('#nav-buttons'));
    renderStep();
  });

  document.getElementById('btn-new').addEventListener('click', () => {
    // Reset wizard data
    Object.keys(wizardData).forEach(k => {
      if (Array.isArray(wizardData[k])) wizardData[k] = [];
      else if (typeof wizardData[k] === 'string') wizardData[k] = '';
      else wizardData[k] = null;
    });
    builtPrompts = null;
    generationId = null;
    currentStep = 1;
    clearState();
    show($('#nav-buttons'));
    renderStep();
  });
}

function showError(errorMsg) {
  const container = $('#wizard-content');
  container.innerHTML = `
    <div class="step-card">
      <div class="error-card">
        <h3>حدث خطأ</h3>
        <p>${errorMsg}</p>
        <button class="result-btn" id="btn-retry" style="display:inline-block;margin:0 4px;">🔄 إعادة المحاولة</button>
        <button class="result-btn" id="btn-back-edit" style="display:inline-block;margin:0 4px;">✏️ تعديل وإعادة</button>
      </div>
    </div>
  `;

  document.getElementById('btn-retry').addEventListener('click', async () => {
    const references = [];
    const refKeys = ['ref_character', 'ref_lighting', 'ref_camera', 'ref_audio'];
    refKeys.forEach(key => {
      if (wizardData[key] && wizardData[key].url) {
        references.push({
          purpose: key.replace('ref_', ''),
          url: wizardData[key].url,
          file_type: wizardData[key].file_type || '',
        });
      }
    });
    try {
      const result = await api('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: SESSION_ID,
          wizard_data: wizardData,
          english_prompt: builtPrompts.english_prompt,
          arabic_prompt: builtPrompts.arabic_prompt,
          references,
          duration: wizardData.duration || '5',
        aspect_ratio: wizardData.aspect_ratio || '16:9',
        resolution: wizardData.resolution || '720p',
        }),
      });
      generationId = result.generation_id;
      generationModel = result.model;
      showGenerationScreen();
    } catch (err) {
      alert('خطأ: ' + err.message);
    }
  });

  document.getElementById('btn-back-edit').addEventListener('click', () => {
    currentStep = 11;
    show($('#nav-buttons'));
    renderStep();
  });
}


// ── History ──────────────────────────────────────────────────

async function showHistory() {
  hide($('#wizard-view'));
  const panel = $('#history-panel');
  panel.classList.add('visible');

  panel.innerHTML = `
    <span class="history-back" id="history-back-btn">→ رجوع لـ Directa</span>
    <div class="step-question">مشاريعي</div>
    <div id="history-content"><div class="building-prompt">جاري التحميل<span class="dots">...</span></div></div>
  `;

  document.getElementById('history-back-btn').addEventListener('click', hideHistory);

  try {
    const items = await api('/api/history');
    const content = document.getElementById('history-content');

    if (!items || items.length === 0) {
      content.innerHTML = '<div class="history-empty">لا توجد مشاريع سابقة</div>';
      return;
    }

    const grid = document.createElement('div');
    grid.className = 'history-grid';

    items.forEach(item => {
      const el = document.createElement('div');
      el.className = 'history-item';

      const statusClass = item.status || 'pending';
      const statusLabel = { done: 'مكتمل', processing: 'قيد التوليد', error: 'خطأ', pending: 'في الانتظار' }[statusClass] || statusClass;

      let mediaHtml;
      if (item.video_url && item.status === 'done') {
        mediaHtml = `<video src="${item.video_url}" muted playsinline preload="metadata"></video>`;
      } else {
        mediaHtml = `<div class="history-placeholder">🎬</div>`;
      }

      const date = item.created_at ? new Date(item.created_at).toLocaleDateString('ar-SA') : '';
      const prompt = item.arabic_prompt || '';

      el.innerHTML = `
        ${mediaHtml}
        <div class="history-meta">
          <div class="history-date">${date}</div>
          <div class="history-prompt">${prompt}</div>
          <span class="history-status ${statusClass}">${statusLabel}</span>
          <button class="history-delete-btn" data-id="${item.id}">حذف</button>
        </div>
      `;

      // Click to view result
      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('history-delete-btn')) return;
        if (item.status === 'done' && item.video_url) {
          hideHistory();
          generationId = item.id;
          showVideoResult(item.video_url);
        }
      });

      // Delete button
      el.querySelector('.history-delete-btn').addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('حذف هذا المشروع؟')) return;
        try {
          await api(`/api/generation/${item.id}`, { method: 'DELETE' });
          el.remove();
        } catch (err) {
          alert('فشل الحذف');
        }
      });

      grid.appendChild(el);
    });

    content.innerHTML = '';
    content.appendChild(grid);
  } catch (err) {
    document.getElementById('history-content').innerHTML =
      `<div class="error-card"><h3>خطأ</h3><p>${err.message}</p></div>`;
  }
}

function hideHistory() {
  show($('#wizard-view'));
  $('#history-panel').classList.remove('visible');
}


// ── Landing Page ─────────────────────────────────────────────

function startWizard() {
  hide($('#landing-page'));
  show($('#wizard-view'));
  renderStep();
}

function renderTemplatesOnLanding() {
  const container = document.getElementById('landing-templates');
  if (!container) return;
  const templates = getTemplates();
  if (templates.length === 0) {
    container.innerHTML = '';
    return;
  }
  let html = '<div class="section-label" style="text-align:center;margin-top:32px;">القوالب المحفوظة</div><div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:10px;">';
  templates.forEach((tpl, i) => {
    html += `<button class="chip template-chip" data-idx="${i}">${tpl.name}<span class="template-delete" data-idx="${i}" style="margin-right:6px;color:#666;cursor:pointer;"> ✕</span></button>`;
  });
  html += '</div>';
  container.innerHTML = html;

  container.querySelectorAll('.template-chip').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (e.target.classList.contains('template-delete')) {
        e.stopPropagation();
        const idx = parseInt(e.target.dataset.idx);
        deleteTemplate(idx);
        renderTemplatesOnLanding();
        return;
      }
      loadTemplate(parseInt(btn.dataset.idx));
    });
  });
}


// ── Init ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-start').addEventListener('click', startWizard);
  document.getElementById('landing-history').addEventListener('click', () => {
    hide($('#landing-page'));
    show($('#wizard-view'));
    renderStep();
    showHistory();
  });
  document.getElementById('btn-next').addEventListener('click', goNext);
  document.getElementById('btn-back').addEventListener('click', goBack);
  document.getElementById('history-link').addEventListener('click', (e) => {
    e.preventDefault();
    showHistory();
  });

  renderTemplatesOnLanding();

  // Restore saved state — skip landing if wizard was in progress
  if (saved && saved.step > 1) {
    hide($('#landing-page'));
    show($('#wizard-view'));
    renderStep();
  }
});
