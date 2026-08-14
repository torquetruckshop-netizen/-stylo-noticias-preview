const items=[
{category:'Argentina',source:'Transporte Mundial',title:'Faltan conductores de camión: un problema que ya condiciona al transporte argentino.',summary:'La falta de choferes vuelve a poner en discusión capacitación, renovación generacional y productividad de las flotas.'},
{category:'Logística',source:'Infobae',title:'Infraestructura, tecnología y capacitación marcan la agenda logística.',summary:'Los tres ejes aparecen cada vez más conectados en las decisiones de empresas y operadores.'},
{category:'Rutas',source:'Vialidad Nacional',title:'Antes de salir, revisar el estado de las rutas nacionales.',summary:'La información oficial de transitabilidad permite anticipar cortes, restricciones y cambios de recorrido.'},
{category:'Clima',source:'Servicio Meteorológico Nacional',title:'Las alertas meteorológicas también forman parte de la operación.',summary:'Tormentas, nieve, viento y otros fenómenos pueden modificar tiempos, seguridad y planificación de un viaje.'},
{category:'Hitos',source:'Infobae Movant',title:'Stylo Camión y la digitalización del transporte.',summary:'La entrevista a Francisco Spoturno forma parte de la historia documentada del proyecto y de su mirada sobre tecnología y confianza.'}
];

const now=document.querySelector('#routeNow');
const meta=document.querySelector('#routeMeta');
const summary=document.querySelector('#routeSummary');
const list=document.querySelector('#routeList');
const play=document.querySelector('#routePlay');
const pause=document.querySelector('#routePause');
const stop=document.querySelector('#routeStop');
const status=document.querySelector('#routeStatus');
const progress=document.querySelector('#routeProgress');
const edition=document.querySelector('#routeEdition');
const duration=document.querySelector('#routeDuration');
let index=0;let started=false;let stopped=true;

edition.textContent=new Intl.DateTimeFormat('es-AR',{weekday:'long',day:'numeric',month:'long'}).format(new Date());
duration.textContent=`${items.length} bloques · aproximadamente 2 minutos.`;

function renderList(){list.innerHTML=items.map((item,i)=>`<article class="route-item${i===index?' active':''}"><span class="route-number">${String(i+1).padStart(2,'0')}</span><div><h3>${item.title}</h3><div class="meta">${item.category} · ${item.source}</div></div></article>`).join('')}
function renderCurrent(){const item=items[index];if(!item){now.textContent='Boletín finalizado';meta.textContent='';summary.textContent='Terminaste la edición de prueba.';progress.style.width='100%';document.querySelectorAll('.route-item').forEach(n=>n.classList.remove('active'));return}now.textContent=item.title;meta.textContent=`${item.category} · ${item.source} · ${index+1} de ${items.length}`;summary.textContent=item.summary;progress.style.width=`${Math.round(index/items.length*100)}%`;renderList()}
function voice(){const voices=speechSynthesis.getVoices();return voices.find(v=>v.lang.toLowerCase()==='es-ar')||voices.find(v=>v.lang.toLowerCase().startsWith('es'))||null}
function textFor(item,i){return `Noticia ${i+1} de ${items.length}. ${item.title} ${item.summary} Fuente: ${item.source}.`}
function speak(){if(index>=items.length){finish();return}speechSynthesis.cancel();renderCurrent();const u=new SpeechSynthesisUtterance(textFor(items[index],index));const v=voice();if(v)u.voice=v;u.lang=v?.lang||'es-AR';u.rate=.95;u.onstart=()=>{stopped=false;status.textContent=`Reproduciendo bloque ${index+1} de ${items.length}`};u.onend=()=>{if(stopped)return;index++;index>=items.length?finish():speak()};u.onerror=()=>{status.textContent='La voz no pudo continuar en este dispositivo.';stopped=true};speechSynthesis.speak(u)}
function start(){if(!('speechSynthesis'in window)){status.textContent='La lectura por voz no está disponible en este navegador.';return}if(speechSynthesis.paused){speechSynthesis.resume();pause.textContent='Pausar';return}if(index>=items.length)index=0;stopped=false;if(!started){started=true;const intro=new SpeechSynthesisUtterance(`Boletín de Ruta Stylo Camión. Vista previa con ${items.length} bloques. Información para el transporte de Argentina y Sudamérica.`);const v=voice();if(v)intro.voice=v;intro.lang=v?.lang||'es-AR';intro.rate=.95;intro.onend=()=>{if(!stopped)speak()};speechSynthesis.cancel();speechSynthesis.speak(intro)}else{speak()}}
function togglePause(){if(!('speechSynthesis'in window))return;if(speechSynthesis.paused){speechSynthesis.resume();pause.textContent='Pausar';status.textContent='Reproducción reanudada'}else if(speechSynthesis.speaking){speechSynthesis.pause();pause.textContent='Reanudar';status.textContent='Boletín pausado'}}
function reset(){if('speechSynthesis'in window)speechSynthesis.cancel();index=0;started=false;stopped=true;pause.textContent='Pausar';status.textContent='Detenido. Listo para comenzar desde el inicio.';renderCurrent()}
function finish(){if('speechSynthesis'in window)speechSynthesis.cancel();stopped=true;index=items.length;renderCurrent();status.textContent='Boletín finalizado.'}
play.addEventListener('click',start);pause.addEventListener('click',togglePause);stop.addEventListener('click',reset);window.addEventListener('beforeunload',()=>{'speechSynthesis'in window&&speechSynthesis.cancel()});renderCurrent();