// Pruebas de los paneles desplegables de la interfaz web.
//   python tests/ui/generar_payload.py && node tests/ui/test_paneles.js
// Ejecuta las funciones reales de pintado contra datos reales de la API.
// Ejecuta las funciones de pintado de la interfaz con datos reales de la API
// y comprueba que producen el HTML esperado. Es la prueba de que los tres
// desplegables funcionan, sin necesidad de abrir un navegador.
const fs = require('fs');
const path = require('path');
const RAIZ = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(RAIZ, 'app/static/index.html'), 'utf8');
const js = html.split('<script>')[1].split('</script>')[0];
async function main(){
const P = JSON.parse(fs.readFileSync(process.argv[2] || '/tmp/payload.json','utf8'));

// Entorno mínimo de navegador
global.location = {protocol:'http:'};
global.document = {
  querySelector: () => ({innerHTML:'', addEventListener(){}, set onclick(v){}, value:'', dataset:{}}),
  querySelectorAll: () => [],
  getElementById: () => ({innerHTML:''}),
  documentElement: {},
};
global.getComputedStyle = () => ({getPropertyValue: () => '#4A6FA5'});
// La interfaz guarda preferencias del usuario; Node no tiene localStorage.
const _almacen = {};
global.localStorage = {
  getItem: k => (k in _almacen ? _almacen[k] : null),
  setItem: (k, v) => { _almacen[k] = String(v); },
  removeItem: k => { delete _almacen[k]; },
};
global.fetch = async () => ({ok:true, json: async () => ({})});

// Las declaraciones let/const dentro de eval no salen de su ámbito, así que
// se exportan explícitamente las que necesitan las pruebas.
eval(js.replace('init();','') + `
  Object.assign(globalThis, {
    WORKS, STATE, IDIOMAS, montarIdiomas, aplicarIdioma,
    pintarDetalle, pedirDetalle, highlight, esc, color, query,
    viewSem, activarParalelos, api, TRAD,
    pintarSecciones, pintarColocaciones, viewPerfil, present0,
    activarBusquedaDePalabra, traducirTodoLoVisible, activarTraduccion,
    viewGuia, sinResultados, viewPanorama, bienvenida, EMBLEMA, hexA, irAPestana, FIELDS, viewAcerca
  });
`);

let fallos = 0;
const chk = (nombre, cond, extra='') => {
  if(cond) console.log('  OK   ' + nombre);
  else { console.log('  FALLO ' + nombre + ' ' + extra); fallos++; }
};

console.log('--- APARICIONES (formas de la palabra) ---');
const f = pintarDetalle('forms', P.forms, P.row);
chk('genera panel', f.includes('class="detail"'));
chk('incluye el titular con el total', f.includes('apariciones, por forma'));
P.forms.results.slice(0,3).forEach(x =>
  chk('muestra la forma "'+x.surface+'"', f.includes('>'+x.surface+'<')));
chk('muestra porcentajes', /\d+(\.\d+)?%/.test(f));
chk('barra proporcional', f.includes('minibar'));

console.log('--- LIBROS ---');
const b = pintarDetalle('books', P.books, P.row);
const conApariciones = P.books.filter(d => d.raw_count > 0);
chk('genera panel', b.includes('class="detail"'));
chk('cuenta libros correctamente',
    b.includes('Aparece en '+conApariciones.length+' de '+P.books.length+' libros'));
conApariciones.slice(0,3).forEach(d =>
  chk('lista el libro "'+d.name+'"', b.includes(d.name)));
chk('no lista libros sin apariciones',
    !P.books.filter(d=>d.raw_count===0).slice(0,1).some(d =>
      b.includes('>'+d.name+'\n')));
chk('ordena por densidad', (() => {
  const nums = [...b.matchAll(/([\d.]+) \/10k/g)].map(m => parseFloat(m[1]));
  return nums.every((v,i) => i===0 || nums[i-1] >= v);
})());

console.log('--- VERSICULOS ---');
const v = pintarDetalle('verses', P.verses, P.row);
chk('genera panel', v.includes('class="detail"'));
chk('incluye referencias', v.includes(P.verses.items[0].ref));
const sinEtiquetas = v.replace(/<[^>]+>/g,'').replace(/&amp;/g,'&');
chk('incluye el texto', sinEtiquetas.includes(P.verses.items[0].text.slice(0,25)));
chk('resalta el termino buscado', v.includes('<mark>'));
chk('explica la diferencia apariciones/versiculos',
    v.includes('aparece más de una vez') || v.includes('una sola vez'));

console.log('--- CASOS LIMITE ---');
chk('sin datos no rompe', pintarDetalle('forms', {results:[]}, P.row) === '');
chk('libros vacios no rompe', pintarDetalle('books', [], P.row) === '');
chk('versiculos vacios no rompe', pintarDetalle('verses', {items:[]}, P.row) === '');
chk('escapa HTML malicioso',
    pintarDetalle('verses', {items:[{ref:'<img src=x onerror=alert(1)>',text:'t',
      division:'d', matched_forms:[], hits:1}]}, P.row).includes('&lt;img'));

// ---------- selector de idioma ----------
console.log('--- SELECTOR DE IDIOMA ---');
{
  let placeholder = '', avisoHTML = '', selHTML = '', selValue = '';
  const elems = {
    '#q':    {set placeholder(v){ placeholder = v; }, get placeholder(){ return placeholder; }},
    '#lang': {set innerHTML(v){ selHTML = v; }, get innerHTML(){ return selHTML; },
              set value(v){ selValue = v; }, get value(){ return selValue; }},
    '#avisoIdioma': {set innerHTML(v){ avisoHTML = v; }, get innerHTML(){ return avisoHTML; }},
  };
  global.document.querySelector = s => elems[s] || {innerHTML:''};

  // Caso real del usuario: cuatro obras, todas en inglés.
  const obras = [
    {id:'kjv', language:'en'}, {id:'tanaj-jps', language:'en'},
    {id:'quran-pickthall', language:'en'}, {id:'gita-arnold', language:'en'},
  ];
  obras.forEach(o => WORKS[o.id] = o);
  montarIdiomas(obras);

  chk('el ingles aparece con el numero de obras', selHTML.includes('4 obras'));
  chk('el espanol se marca como no instalado', selHTML.includes('no instalado'));
  chk('arranca en un idioma que si tiene textos', STATE.lang === 'en');
  chk('placeholder invita a escribir en espanol', placeholder.includes('español'));
  chk('sin aviso cuando hay textos', avisoHTML === '');

  // El usuario cambia a español.
  STATE.lang = 'es';
  aplicarIdioma();
  chk('placeholder cambia al cambiar idioma', placeholder.includes('misericordia'),
      '-> ' + placeholder);
  chk('placeholder cambia de ejemplos', placeholder.includes('misericordia'));
  chk('avisa de que no hay textos en espanol', avisoHTML.includes('No tienes textos'));
  chk('explica como instalarlos', avisoHTML.includes('rv1909'));

  // Y vuelve al inglés.
  STATE.lang = 'en';
  aplicarIdioma();
  chk('el aviso desaparece al volver', avisoHTML === '');
  chk('placeholder vuelve a los ejemplos mixtos', placeholder.includes('pecado'));

  // Con obras en los dos idiomas no debe avisar de nada.
  const mixto = [...obras, {id:'rv1909', language:'es'}];
  mixto.forEach(o => WORKS[o.id] = o);
  montarIdiomas(mixto);
  chk('con corpus mixto cuenta ambos',
      selHTML.includes('4 obras') && selHTML.includes('1 obra'));
  STATE.lang = 'es'; aplicarIdioma();
  chk('con textos en espanol no avisa', avisoHTML === '');
}

// ---------- pestaña de búsqueda por significado ----------
console.log('--- BUSQUEDA POR SIGNIFICADO ---');
{
  let salida = '', consultaSem = '';
  const elems = {
    '#out': {set innerHTML(v){ salida = v; }, get innerHTML(){ return salida; }},
    '#qs':  {get value(){ return consultaSem; }, set value(v){ consultaSem = v; }},
  };
  global.document.querySelector = s => elems[s] || {innerHTML:'', style:{}, value:''};
  global.document.querySelectorAll = () => [];
  global.document.getElementById = () => ({innerHTML:''});
  STATE.tab = 'sem';

  // 1. Sin consulta: debe explicar para qué sirve, no quedarse en blanco.
  consultaSem = '';
  await viewSem();
  chk('sin consulta explica la funcion', salida.includes('Busca ideas, no palabras'));

  // 2. Extra no instalado: mensaje accionable, no un 503 crudo.
  consultaSem = 'perdonar';
  global.fetch = async () => ({ok:false, status:503,
    json: async () => ({detail:'Índice semántico no disponible.'})});
  await viewSem();
  chk('si no esta instalado lo explica', salida.includes('no está instalada'));
  chk('dice como instalarlo', salida.includes('INSTALAR-BUSQUEDA'));

  // 3. Resultados reales.
  const falsos = {query:'perdonar a quien te ha hecho dano', model:'m', caveat:'',
    results:[
      {verse_id:1, ref:'Mateo 6:14', text:'For if ye forgive men their trespasses',
       work_id:'kjv', tradition:'cristianismo', similarity:0.8123},
      {verse_id:2, ref:'Q 42:40', text:'but whoso pardons and does what is right',
       work_id:'quran-pickthall', tradition:'islam', similarity:0.7455},
    ]};
  global.fetch = async () => ({ok:true, json: async () => falsos});
  await viewSem();
  chk('muestra las referencias', salida.includes('Mateo 6:14') && salida.includes('Q 42:40'));
  chk('muestra el texto', salida.includes('forgive men'));
  chk('convierte similitud a porcentaje', salida.includes('81%') && salida.includes('75%'));
  chk('nombra la tradicion en espanol', salida.includes('Cristianismo'));
  chk('incluye el aviso metodologico', salida.includes('no equivalencia doctrinal'));
  chk('ofrece ver otras tradiciones', salida.includes('data-par="1"'));

  // 4. Sin resultados.
  global.fetch = async () => ({ok:true, json: async () => ({query:'x', results:[]})});
  await viewSem();
  chk('sin resultados lo dice claro', salida.includes('supera el umbral'));

  // 5. Seguridad.
  global.fetch = async () => ({ok:true, json: async () => ({query:'x', results:[
    {verse_id:9, ref:'<script>alert(1)</script>', text:'<b>x</b>',
     work_id:'kjv', tradition:'cristianismo', similarity:0.5}]})});
  await viewSem();
  chk('escapa HTML en los resultados',
      salida.includes('&lt;script&gt;') && !salida.includes('<script>alert'));
}

// ---------- vistas nuevas: secciones, colocaciones y perfil ----------
console.log('--- SECCIONES / COLOCACIONES / PERFIL ---');
{
  const cajas = {};
  const nueva = () => ({_h:'', set innerHTML(v){ this._h = v; },
                        get innerHTML(){ return this._h; }});
  ['#seccs','#colocs','#perfilCaja','#out','#q'].forEach(k => cajas[k] = nueva());
  cajas['#q'].value = '';
  global.document.querySelector = k => cajas[k] || nueva();
  global.document.querySelectorAll = () => [];

  // --- secciones ---
  global.fetch = async () => ({ok:true, json: async () => P.sections});
  const filas = [{work_id:'quran-pickthall', workId0:'quran-pickthall',
                  work_title:'Corán (Palmer)', tradition:'islam', raw_count:12}];
  await pintarSecciones(filas);
  const hs = cajas['#seccs'].innerHTML;
  const conDatos = P.sections.results.filter(x => x.total_tokens > 0);
  if(conDatos.length >= 2){
    chk('lista las secciones', conDatos.every(x => hs.includes(x.section)));
    chk('muestra tasas normalizadas', hs.includes('/10k'));
    const sig = conDatos.filter(x => x.significant && x.direction === 'over');
    if(sig.length) chk('destaca la seccion significativa',
                       hs.includes('estadísticamente significativa'));
  }

  // Con una sola sección no debe inventarse una comparación.
  global.fetch = async () => ({ok:true, json: async () =>
    ({results:[{section:'Única', total_tokens:100, raw_count:5, per_10k:500,
                significant:false, direction:'over', divisions:1}]})});
  await pintarSecciones(filas);
  chk('no compara si solo hay una seccion',
      cajas['#seccs'].innerHTML.includes('no tienen partes comparables'));

  // --- colocaciones ---
  global.fetch = async () => ({ok:true, json: async () => P.collocations});
  await pintarColocaciones(filas);
  const hc = cajas['#colocs'].innerHTML;
  if(P.collocations.results.length){
    chk('muestra palabras acompanantes', hc.includes('class="pal"'));
    chk('las hace buscables', hc.includes('data-buscar'));
  }

  global.fetch = async () => ({ok:true, json: async () => ({results:[]})});
  await pintarColocaciones(filas);
  chk('sin colocaciones lo dice', cajas['#colocs'].innerHTML.includes('No hay suficientes'));

  // --- perfil de obra ---
  Object.keys(WORKS).forEach(k => delete WORKS[k]);   // limpiar el estado previo
  WORKS['quran-pickthall'] = {id:'quran-pickthall', title:'Corán', edition:'Palmer',
                           tradition:'islam', language:'en'};
  STATE.obraPerfil = 'quran-pickthall';
  global.fetch = async () => ({ok:true, json: async () => P.distinctive});
  await viewPerfil();
  const hp = cajas['#perfilCaja'].innerHTML;
  if(P.distinctive.results.length){
    chk('muestra vocabulario distintivo', hp.includes('class="pal"'));
    chk('incluye los lemas', hp.includes(P.distinctive.results[0].lemma));
    chk('tamano proporcional al peso', hp.includes('font-size:'));
    chk('explica que no son las mas frecuentes',
        cajas['#out'].innerHTML.includes('más <i>características</i>'));
  }

  global.fetch = async () => ({ok:true, json: async () => ({results:[]})});
  await viewPerfil();
  chk('sin distintivas lo explica',
      cajas['#perfilCaja'].innerHTML.includes('Sin vocabulario'));

  // Los botones de obra deben decir QUE texto es, no solo la edición:
  // «M. Pickthall 1930» por sí solo no identifica el Corán.
  Object.keys(WORKS).forEach(k => delete WORKS[k]);
  WORKS['quran-pickthall'] = {id:'quran-pickthall', title:'Corán',
    edition:'M. Pickthall 1930', tradition:'islam', language:'en'};
  WORKS['kjv'] = {id:'kjv', title:'Biblia', edition:'King James Version',
    tradition:'cristianismo', language:'en'};
  STATE.obraPerfil = 'kjv';
  global.fetch = async () => ({ok:true, json: async () => ({results:[]})});
  await viewPerfil();
  const sel = cajas['#out'].innerHTML;
  chk('el boton nombra la obra', sel.includes('Corán') && sel.includes('Biblia'));
  chk('el boton conserva la edicion',
      sel.includes('M. Pickthall 1930') && sel.includes('King James Version'));
  chk('el boton lleva el color de la tradicion', sel.includes('class="dot"'));

  // Robustez: una obra a la que le falten campos no debe romper la pantalla.
  WORKS['parcial'] = {id:'parcial', tradition:'islam'};
  STATE.obraPerfil = 'parcial';
  global.fetch = async () => ({ok:true, json: async () => ({results:[]})});
  let rompio = false;
  try { await viewPerfil(); } catch(e){ rompio = true; }
  chk('sobrevive a una obra con campos ausentes', !rompio);
  chk('esc tolera null y undefined', esc(null) === '' && esc(undefined) === '');
}

// ---------- búsqueda sin resultados ----------
console.log('--- RESCATE DE BUSQUEDAS EN ESPANOL ---');
{
  let salida = '', valorQ = '';
  const cajas = {
    '#out': {set innerHTML(v){ salida = v; }, get innerHTML(){ return salida; }},
    '#q':   {get value(){ return valorQ; }, set value(v){ valorQ = v; }},
  };
  global.document.querySelector = k => cajas[k] || {innerHTML:'', style:{}, value:''};
  global.document.querySelectorAll = () => [];

  STATE.term = 'pecado';
  STATE.lang = 'en';

  // El caso real: palabra española que SÍ está en el lexicón.
  global.fetch = async () => ({ok:true, json: async () => ({
    original:'pecado',
    campos:[{key:'pecado', label:'Pecado y transgresión', terminos:14}],
    traduccion:'sin',
  })});
  await sinResultados({resolved_stems:['pecado']});

  chk('reconoce que se escribio en espanol', salida.includes('Escribiste'));
  chk('ofrece el campo semantico', salida.includes('Pecado y transgresión'));
  chk('el campo es pulsable', salida.includes('data-campo="pecado"'));
  chk('presenta el campo como la mejor opcion', salida.includes('mejor opción'));
  chk('ofrece tambien la traduccion', salida.includes('data-trad-term="sin"'));
  // «sin» en ingles significa pecado; en espanol significa otra cosa. Sin
  // marcar el idioma, el boton resulta incomprensible.
  chk('marca que la palabra es inglesa', salida.includes('palabra inglesa'));
  chk('explica la equivalencia',
      salida.includes('En inglés') && salida.includes('se dice'));
  chk('destaca visualmente la palabra extranjera', salida.includes('class="ing"'));

  // Palabra sin campo: solo traducción.
  global.fetch = async () => ({ok:true, json: async () => ({
    original:'camello', campos:[], traduccion:'camel',
  })});
  await sinResultados({resolved_stems:['camello']});
  chk('sin campo, ofrece la traduccion', salida.includes('data-trad-term="camel"'));
  chk('sin campo, no habla de conceptos', !salida.includes('mejor opción'));

  // Ni campo ni traducción: no inventarse nada.
  global.fetch = async () => ({ok:true, json: async () => ({
    original:'xyzzy', campos:[], traduccion:null,
  })});
  await sinResultados({resolved_stems:['xyzzy']});
  chk('sin alternativas, mensaje simple', !salida.includes('rescate'));

  // Si el servidor falla, no debe romperse la pantalla.
  global.fetch = async () => { throw new Error('sin red'); };
  await sinResultados({resolved_stems:['algo']});
  chk('si falla la consulta, muestra el mensaje basico',
      salida.includes('Sin resultados'));

  // Si la interfaz y el corpus comparten idioma, no hay nada que rescatar.
  STATE.lang = 'es';
  let llamado = false;
  global.fetch = async () => { llamado = true; return {ok:true, json: async () => ({})}; };
  await sinResultados({resolved_stems:['algo']});
  chk('mismo idioma: no consulta al servidor', !llamado);
  STATE.lang = 'en';
}

// ---------- guía de interpretación ----------
console.log('--- GUIA DE INTERPRETACION ---');
{
  let salida = '';
  global.document.querySelector = k =>
    k === '#out' ? {set innerHTML(v){ salida = v; }, get innerHTML(){ return salida; }}
                 : {innerHTML:'', style:{}, value:''};
  global.document.getElementById = () => null;

  viewGuia();

  chk('explica la normalizacion', salida.includes('10.000 palabras'));
  chk('explica G2', salida.includes('G²'));
  chk('da umbrales concretos', salida.includes('15,1'));
  chk('explica la dispersion', salida.includes('dispersión') || salida.includes('Dispersión'));
  chk('incluye un ejemplo real', salida.includes('17,3') && salida.includes('26,2'));

  // Lo más importante: los límites.
  chk('dice que compara traducciones, no religiones',
      salida.includes('compara traducciones'));
  chk('dice que no mide importancia', salida.includes('No mide importancia'));
  chk('advierte sobre la negacion', salida.includes('No matarás'));
  chk('advierte que no es neutral por ser cuantitativa',
      salida.includes('No es neutral'));
  chk('menciona la sura de las mujeres', salida.includes('Las mujeres'));

  chk('muestra como citar mal y bien',
      salida.includes('class="mal"') && salida.includes('class="bien"'));
  chk('el ejemplo bueno nombra la traduccion concreta',
      salida.includes('Pickthall'));
}


// ---------- panorama, bienvenida y emblemas ----------
console.log('--- PANORAMA / BIENVENIDA / EMBLEMAS ---');
{
  let salida = '', valorQ = '';
  const cajas = {
    '#out': {set innerHTML(v){ salida = v; }, get innerHTML(){ return salida; }},
    '#q':   {get value(){ return valorQ; }, set value(v){ valorQ = v; }},
  };
  global.document.querySelector = k => cajas[k] || {innerHTML:'', style:{}, value:'', click(){}};
  global.document.querySelectorAll = () => [];

  // Emblemas: geometría abstracta, nunca un simbolo religioso real.
  const e1 = EMBLEMA('islam', 20), e2 = EMBLEMA('judaismo', 20);
  chk('el emblema es un svg', e1.includes('<svg') && e1.includes('</svg>'));
  chk('cada tradicion tiene forma propia', e1 !== e2);
  chk('el emblema no usa palabras religiosas',
      !/cross|crescent|star|cruz|luna|estrella/i.test(EMBLEMA('cristianismo')));

  // hexA convierte color de tradicion en transparencia.
  chk('hexA produce rgba', hexA('#3f6491', 0.5).startsWith('rgba('));

  // Bienvenida.
  Object.keys(WORKS).forEach(k => delete WORKS[k]);
  WORKS['kjv'] = {id:'kjv', title:'Biblia', tradition:'cristianismo'};
  WORKS['quran-pickthall'] = {id:'quran-pickthall', title:'Corán', tradition:'islam'};
  const guardaFields = FIELDS.slice();
  FIELDS.length = 0;
  FIELDS.push({key:'misericordia', label:'Misericordia y compasión'},
              {key:'justicia', label:'Justicia y rectitud'});
  bienvenida();
  chk('la bienvenida invita, no queda vacia', salida.includes('cuatro tradiciones'));
  chk('la bienvenida muestra emblemas', salida.includes('<svg'));
  chk('la bienvenida ofrece conceptos de inicio', salida.includes('data-wf'));
  chk('la bienvenida enlaza al panorama', salida.includes('data-goto="panorama"'));

  // Panorama.
  let n = 0;
  global.fetch = async (path) => {
    if(String(path).includes('/frequency')) n++;
    return {ok:true, json: async () => ({results:[
      {work_id:'kjv', per_10k: 11.4, raw_count: 20},
      {work_id:'quran-pickthall', per_10k: 25.0, raw_count: 40},
    ]})};
  };
  await viewPanorama();
  chk('el panorama pide un frequency por concepto', n === FIELDS.length);
  chk('el panorama dibuja la rejilla', salida.includes('class="pano"'));
  chk('el panorama etiqueta los conceptos', salida.includes('Misericordia y compasión'));
  chk('las casillas son pulsables', salida.includes('data-pf'));
  chk('el panorama muestra cifras', salida.includes('25.0'));

  FIELDS.length = 0; guardaFields.forEach(f => FIELDS.push(f));
}


// ---------- acerca de: créditos, contacto, privacidad, atribución ----------
console.log('--- ACERCA DE ---');
{
  let salida = '';
  global.document.querySelector = k =>
    k === '#out' ? {set innerHTML(v){ salida = v; }, get innerHTML(){ return salida; }}
                 : {innerHTML:'', style:{}, value:''};
  // Los elementos del formulario existen en un navegador real; el simulador
  // devuelve objetos mutables para que asignar .onclick no falle.
  global.document.getElementById = () => ({innerHTML:'', value:'', set onclick(f){}});
  Object.keys(WORKS).forEach(k => delete WORKS[k]);
  WORKS['kjv'] = {id:'kjv', title:'Biblia', edition:'King James Version', year:1611,
                  license:'public-domain', source_url:'https://example.org', tradition:'cristianismo'};

  viewAcerca();
  chk('acredita al desarrollador', salida.includes('Guillermo'));
  chk('acredita la asistencia de programacion', salida.includes('Claude'));
  chk('incluye el correo de contacto', salida.includes('ghiguerag@gmail.com'));
  chk('tiene formulario de sugerencias', salida.includes('id="fbMsg"'));
  chk('ofrece enviar por correo y copiar',
      salida.includes('id="fbMail"') && salida.includes('id="fbCopy"'));
  chk('la privacidad es honesta sobre servicios externos',
      salida.includes('servicios externos') || salida.includes('traducción automática'));
  chk('declara la licencia MIT', salida.includes('MIT'));
  chk('atribuye cada texto con su edicion',
      salida.includes('King James Version') && salida.includes('1611'));
  chk('enlaza la fuente del texto', salida.includes('https://example.org'));
}

console.log(fallos ? `\n${fallos} FALLOS` : '\nTodo correcto');
process.exit(fallos ? 1 : 0);
}
main().catch(e => { console.error(e); process.exit(1); });
