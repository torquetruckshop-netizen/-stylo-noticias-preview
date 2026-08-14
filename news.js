const grid = document.querySelector('#newsGrid');
const updated = document.querySelector('#newsUpdated');

function esc(value='') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function fmtDate(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 'Actualización reciente';
  return new Intl.DateTimeFormat('es-AR', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'}).format(d);
}

async function loadNews() {
  try {
    const response = await fetch(`data/news.json?v=${Date.now()}`, {cache:'no-store'});
    if (!response.ok) throw new Error('Feed no disponible');
    const data = await response.json();
    const items = Array.isArray(data.items) ? data.items.slice(0, 6) : [];
    if (!items.length) throw new Error('Sin noticias');

    updated.textContent = `Actualizado ${fmtDate(data.updated_at)}`;
    grid.innerHTML = items.map((item, index) => `
      <a class="radar-card${index === 0 ? ' lead-card' : ''}" href="${esc(item.url)}" target="_blank" rel="noopener">
        <div class="radar-meta"><span>${esc(item.category || 'Actualidad')}</span><span>${esc(item.source || 'Fuente identificada')}</span></div>
        <h3>${esc(item.title)}</h3>
        <p>${esc(item.summary || 'Información seleccionada por el radar regional de Stylo Camión.')}</p>
        <small>${fmtDate(item.published_at)}</small>
      </a>`).join('');
  } catch (error) {
    updated.textContent = 'Actualización pendiente';
    grid.innerHTML = '<article class="radar-card lead-card"><div class="radar-meta"><span>STYLO CAMIÓN</span><span>RADAR</span></div><h3>El radar automático está actualizando las noticias.</h3><p>Volvé a ingresar en unos minutos.</p></article>';
  }
}

loadNews();
