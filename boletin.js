const routeNow = document.querySelector('#routeNow');
const routeMeta = document.querySelector('#routeMeta');
const routeSummary = document.querySelector('#routeSummary');
const routeList = document.querySelector('#routeList');
const routePlay = document.querySelector('#routePlay');
const routePause = document.querySelector('#routePause');
const routeStop = document.querySelector('#routeStop');
const routeStatus = document.querySelector('#routeStatus');
const routeProgress = document.querySelector('#routeProgress');
const routeEdition = document.querySelector('#routeEdition');
const routeDuration = document.querySelector('#routeDuration');

let bulletin = [];
let currentIndex = 0;
let started = false;
let stopped = true;

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'\"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[char]));
}

function contextText(category) {
  const copy = {
    'Argentina': 'Puede afectar condiciones de operación, costos, normativa o decisiones de empresas transportistas en Argentina.',
    'Región': 'Puede impactar corredores internacionales, fronteras, puertos y movimientos de carga dentro de Sudamérica.',
    'Camiones': 'Es relevante para renovación de flota, tecnología, productividad y costo total de operación.',
    'Remolques': 'Incide en configuraciones, productividad e implementos utilizados por el transporte regional.',
    'Logística': 'Aporta información para planificación, distribución, productividad y gestión de cadenas de suministro.',
    'Economía': 'Tasas, combustible, tarifas y actividad económica modifican costos por kilómetro y decisiones de inversión.',
    'Rutas y normativa': 'Los cambios regulatorios y de infraestructura pueden modificar circulación y planificación operativa.'
  };
  return copy[category] || 'Es información relevante para decisiones operativas y comerciales del transporte.';
}

function selectBulletin(items) {
  const selected = [];
  const categories = new Set();
  for (const item of items) {
    if (!categories.has(item.category)) {
      selected.push(item);
      categories.add(item.category);
    }
    if (selected.length >= 7) break;
  }
  for (const item of items) {
    if (!selected.includes(item)) selected.push(item);
    if (selected.length >= 8) break;
  }
  return selected.slice(0, 8);
}

function speechFor(item, index) {
  return [
    `Noticia ${index + 1} de ${bulletin.length}.`,
    item.title,
    item.summary || '',
    'Por qué importa.',
    contextText(item.category),
    `Fuente: ${item.source || 'fuente identificada'}.`
  ].filter(Boolean).join(' ');
}

function chooseVoice() {
  const voices = window.speechSynthesis.getVoices();
  return voices.find(voice => voice.lang.toLowerCase() === 'es-ar')
    || voices.find(voice => voice.lang.toLowerCase().startsWith('es-'))
    || voices.find(voice => voice.lang.toLowerCase().startsWith('es'))
    || null;
}

function updateCurrent() {
  const item = bulletin[currentIndex];
  if (!item) {
    routeNow.textContent = 'Boletín finalizado';
    routeMeta.textContent = '';
    routeSummary.textContent = 'Terminaste la edición actual del Boletín de Ruta.';
    routeProgress.style.width = '100%';
    document.querySelectorAll('.route-item').forEach(node => node.classList.remove('active'));
    return;
  }
  routeNow.textContent = item.title;
  routeMeta.textContent = `${item.category || 'Actualidad'} · ${item.source || 'Fuente identificada'} · ${currentIndex + 1} de ${bulletin.length}`;
  routeSummary.textContent = item.summary || 'Información seleccionada por el radar regional de Stylo Camión.';
  routeProgress.style.width = `${Math.round((currentIndex / bulletin.length) * 100)}%`;
  document.querySelectorAll('.route-item').forEach((node, index) => node.classList.toggle('active', index === currentIndex));
}

function setStatus(text) { routeStatus.textContent = text; }

function speakCurrent() {
  if (!bulletin.length || currentIndex >= bulletin.length) {
    finishBulletin();
    return;
  }
  window.speechSynthesis.cancel();
  updateCurrent();
  const item = bulletin[currentIndex];
  const utterance = new SpeechSynthesisUtterance(speechFor(item, currentIndex));
  const voice = chooseVoice();
  utterance.voice = voice;
  utterance.lang = voice?.lang || 'es-AR';
  utterance.rate = 0.95;
  utterance.onstart = () => {
    stopped = false;
    setStatus(`Reproduciendo noticia ${currentIndex + 1} de ${bulletin.length}`);
  };
  utterance.onend = () => {
    if (stopped) return;
    currentIndex += 1;
    currentIndex >= bulletin.length ? finishBulletin() : speakCurrent();
  };
  utterance.onerror = () => {
    setStatus('No se pudo continuar la lectura en este dispositivo.');
    stopped = true;
  };
  window.speechSynthesis.speak(utterance);
}

function startBulletin() {
  if (!bulletin.length) return;
  if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
    setStatus('La lectura por voz no está disponible en este navegador.');
    return;
  }
  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
    routePause.textContent = 'Pausar';
    setStatus(`Reproduciendo noticia ${currentIndex + 1} de ${bulletin.length}`);
    return;
  }
  if (currentIndex >= bulletin.length) currentIndex = 0;
  stopped = false;
  if (!started) {
    started = true;
    window.speechSynthesis.cancel();
    const intro = new SpeechSynthesisUtterance(`Boletín de Ruta Stylo Camión. Edición de ${bulletin.length} noticias. Información seleccionada para el transporte de Argentina y Sudamérica.`);
    const voice = chooseVoice();
    intro.voice = voice;
    intro.lang = voice?.lang || 'es-AR';
    intro.rate = 0.95;
    intro.onstart = () => setStatus('Iniciando Boletín de Ruta');
    intro.onend = () => { if (!stopped) speakCurrent(); };
    intro.onerror = () => speakCurrent();
    window.speechSynthesis.speak(intro);
    return;
  }
  speakCurrent();
}

function togglePause() {
  if (!('speechSynthesis' in window)) return;
  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
    routePause.textContent = 'Pausar';
    setStatus(`Reproduciendo noticia ${Math.min(currentIndex + 1, bulletin.length)} de ${bulletin.length}`);
  } else if (window.speechSynthesis.speaking) {
    window.speechSynthesis.pause();
    routePause.textContent = 'Reanudar';
    setStatus('Boletín pausado');
  }
}

function stopBulletin() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  stopped = true;
  started = false;
  currentIndex = 0;
  routePause.textContent = 'Pausar';
  updateCurrent();
  setStatus('Detenido. Listo para comenzar desde el inicio.');
}

function finishBulletin() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  stopped = true;
  currentIndex = bulletin.length;
  updateCurrent();
  setStatus('Boletín finalizado.');
}

function estimateMinutes(items) {
  const words = items.reduce((total, item, index) => total + speechFor(item, index).split(/\s+/).length, 0) + 25;
  return Math.max(1, Math.ceil(words / 145));
}

function renderPlaylist() {
  routeList.innerHTML = bulletin.map((item, index) => `
    <article class="route-item${index === currentIndex ? ' active' : ''}">
      <span class="route-number">${String(index + 1).padStart(2, '0')}</span>
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <div class="meta">${escapeHtml(item.category || 'Actualidad')} · ${escapeHtml(item.source || 'Fuente identificada')}</div>
      </div>
    </article>`).join('');
}

async function loadBulletin() {
  routePlay.disabled = true;
  routePause.disabled = true;
  routeStop.disabled = true;
  try {
    const response = await fetch(`data/news.json?v=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Feed no disponible');
    const payload = await response.json();
    const items = Array.isArray(payload.items) ? payload.items : [];
    bulletin = selectBulletin(items);
    if (!bulletin.length) throw new Error('Sin noticias');

    const updated = payload.updated_at ? new Date(payload.updated_at) : new Date();
    routeEdition.textContent = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }).format(updated);
    routeDuration.textContent = `${bulletin.length} noticias · aproximadamente ${estimateMinutes(bulletin)} min de audio.`;
    currentIndex = 0;
    updateCurrent();
    renderPlaylist();

    const speechAvailable = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
    routePlay.disabled = !speechAvailable;
    routePause.disabled = !speechAvailable;
    routeStop.disabled = !speechAvailable;
    setStatus(speechAvailable ? 'Listo para iniciar.' : 'La lectura por voz no está disponible en este navegador.');
  } catch (error) {
    routeNow.textContent = 'Boletín temporalmente no disponible';
    routeSummary.textContent = 'No pudimos cargar la selección automática. Volvé a Noticias y probá nuevamente en unos minutos.';
    routeList.innerHTML = '<div class="route-loading">No hay una edición disponible en este momento.</div>';
    routeEdition.textContent = 'Sin edición';
    routeDuration.textContent = 'Actualización pendiente.';
    setStatus('No se pudo cargar el boletín.');
  }
}

routePlay.addEventListener('click', startBulletin);
routePause.addEventListener('click', togglePause);
routeStop.addEventListener('click', stopBulletin);
window.addEventListener('beforeunload', () => {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
});
loadBulletin();
