export const meta = {
  name: 'svg-esleme',
  description: 'Map official Turkish road-sign drawings (contact sheets) to the 38 model classes with two independent readers; keep only agreements',
  phases: [{ title: 'Okuma A' }, { title: 'Okuma B' }],
}
const NAMES = ['caution','crossroads','dangerousleft','dangerousright','donotturnleft','donotturnright','giveway','keepleft','keepright','noentry','nostopping','nouturn','pedestrian_info','pedestrian_risk','priorityroad','schoolpassing','speed30','speed50','speed70','stop','kasis','durak','demiryolu','ada_etrafinda','isikli_isaret','keskin_viraj','devamli_viraj','sollama_yasak','dusen_kaya','hayvan','daralan_yol','dik_egim','speed40','speed60','hiz_sonu','yol_calismasi','kaygan_yol','diger_levha']
const DESC = {
  caution: 'red-bordered white triangle with a black exclamation mark (other danger)',
  crossroads: 'red-bordered triangle with a black cross / side-road junction symbol (uncontrolled junction)',
  dangerousleft: 'red-bordered triangle, single bend arrow curving LEFT',
  dangerousright: 'red-bordered triangle, single bend arrow curving RIGHT',
  donotturnleft: 'red-ring circle, left-turn arrow crossed by red bar',
  donotturnright: 'red-ring circle, right-turn arrow crossed by red bar',
  giveway: 'inverted red-bordered white triangle (yield)',
  keepleft: 'blue circle, white arrow pointing down-left (keep left)',
  keepright: 'blue circle, white arrow pointing down-right (keep right)',
  noentry: 'red circle with a horizontal white bar',
  nostopping: 'blue circle with red ring and red X (no stopping)',
  nouturn: 'red-ring circle, U-turn arrow crossed by red bar',
  pedestrian_info: 'blue square, white pedestrian on crossing stripes (crossing ahead info)',
  pedestrian_risk: 'red-bordered triangle, black pedestrian figure (pedestrian danger)',
  priorityroad: 'yellow diamond inside white diamond (priority road)',
  schoolpassing: 'red-bordered triangle, two children figures (school crossing)',
  speed30: 'red-ring circle with the number 30', speed50: 'red-ring circle with the number 50', speed70: 'red-ring circle with the number 70',
  stop: 'red octagon with STOP / DUR',
  kasis: 'red-bordered triangle with a bump symbol (speed hump)',
  durak: 'blue rectangle with a bus / bus stop symbol',
  demiryolu: 'red-bordered triangle with a steam locomotive or gate symbol, or the St Andrew cross (railway crossing)',
  ada_etrafinda: 'blue circle with three circling arrows (roundabout)',
  isikli_isaret: 'red-bordered triangle with a traffic light symbol',
  keskin_viraj: 'black-and-white (or red-white) chevron arrow board marking a sharp bend',
  devamli_viraj: 'red-bordered triangle with an S-shaped double bend arrow (either direction)',
  sollama_yasak: 'red-ring circle with two cars side by side, left one red (no overtaking)',
  dusen_kaya: 'red-bordered triangle with falling rocks / rock slope symbol',
  hayvan: 'red-bordered triangle with an animal (cow, deer, sheep) silhouette',
  daralan_yol: 'red-bordered triangle with two lines narrowing (road narrows, any side)',
  dik_egim: 'red-bordered triangle with a slope and a percentage (steep hill, up or down)',
  speed40: 'red-ring circle with the number 40', speed60: 'red-ring circle with the number 60',
  hiz_sonu: 'white/grey circle with a number and diagonal black stripes (end of speed limit, any number)',
  yol_calismasi: 'red-bordered triangle (often on yellow background) with a digging worker symbol (road works)',
  kaygan_yol: 'red-bordered triangle with a skidding car symbol (slippery road)',
  diger_levha: 'any OTHER real, current Turkish traffic sign (information, prohibition, mandatory, direction or service sign) that is not one of the classes above',
}
const SCHEMA = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: {
  no: { type: 'number' }, cls: { type: 'string' }, sure: { type: 'boolean' } }, required: ['no', 'cls'] } } }, required: ['items'] }
const prompt = (sh) => `Use the Read tool on the image ${args.dir}\\${sh.file}. It is a contact sheet of official Turkish road-sign drawings (Wikimedia Commons SVG renders), 8 cells per row, row-major.
Each cell shows one drawing; under the cell a RED number (the drawing number) and the file title in black. Numbers on this sheet run ${sh.start}..${sh.end} (${sh.end - sh.start + 1} cells).
Also Read ${args.dir}\\liste.csv: data row N (after the header line) is drawing number N; columns dosya,baslik,kategori,lisans,yazar,sayfa. Use the title (KGM code like T-10, TT-29-50, B-12b, YBT-20) together with what you SEE.
For EVERY number ${sh.start}..${sh.end} output one entry: cls = the model class the drawing depicts, from this exact list: ${NAMES.join(', ')}.
Class definitions: ${JSON.stringify(DESC)}.
Use cls="none" when the drawing is NOT a current, plain traffic sign: titles containing "1952" (historic 1952 standard) or "(old)", text-only boards, route-number shields, place-name/junction-name boards (Kavşak İsim Levhası), telephone/service pictogram boards, "Kural levha", anything unclear.
Rules: speed-limit red circles (TT-29-30/50/70/80/90, YBTT-29-50) -> speed30/speed50/speed70 by the digits; 40 -> speed40; 60 -> speed60; other digits (80, 90) -> diger_levha. End-of-speed-limit (TT-33-xx, grey stripes) -> hiz_sonu for ANY number. Chevron bend boards -> keskin_viraj. Slope up or down -> dik_egim. Any animal -> hayvan. Any road-narrows variant -> daralan_yol. Locomotive triangle, gate triangle and crossbuck -> demiryolu. Yellow-background temporary variants (YB-, YBT-, YBTT-) keep the class of their pictogram (e.g. YBT-20 exclamation -> caution). Mandatory blue arrows that are not keep-left/keep-right/roundabout -> diger_levha. Priority-road END sign (diamond with black stripes) -> diger_levha, not priorityroad.
Set sure=false when the title and the drawing disagree or you cannot see the pictogram clearly. Return entries for all ${sh.end - sh.start + 1} numbers, nothing else.`
const results = await pipeline(args.sheets,
  sh => agent(prompt(sh), { label: `A:${sh.file}`, phase: 'Okuma A', schema: SCHEMA }),
  async (a, sh) => ({ sh, a, b: await agent(prompt(sh), { label: `B:${sh.file}`, phase: 'Okuma B', schema: SCHEMA }) }))
const map = {}, dis = [], stats = {}
for (const r of results.filter(Boolean)) {
  if (!r.a || !r.b) { dis.push(`${r.sh.file}: a reader failed`); continue }
  const B = new Map(r.b.items.map(i => [i.no, i]))
  for (const ia of r.a.items) {
    const ib = B.get(ia.no)
    if (!ib) { dis.push(`${ia.no}: B missing`); continue }
    if (ia.cls === ib.cls && ia.cls !== 'none' && ia.sure !== false && ib.sure !== false) { map[ia.no] = ia.cls; stats[ia.cls] = (stats[ia.cls] || 0) + 1 }
    else if (ia.cls !== ib.cls) dis.push(`${ia.no}: A=${ia.cls} B=${ib.cls}`)
    else if (ia.cls !== 'none') dis.push(`${ia.no}: ${ia.cls} unsure`)
  }
}
log(`${Object.keys(map).length} drawings mapped; ${dis.length} disagreements/unsure`)
return { map, stats, disagreements: dis }