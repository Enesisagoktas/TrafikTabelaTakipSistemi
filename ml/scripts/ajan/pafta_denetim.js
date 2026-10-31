export const meta = {
  name: 'pafta-denetim',
  description: 'Review pseudo-label contact sheets (one agent per sheet, second opinion for important classes) and emit ret.txt lines',
  phases: [{ title: 'Denetim A' }, { title: 'Denetim B' }],
}

// args: { dir: abs path of <ad>_sozde, sheets: [{file, sinif}], important: [class names], names: [all class names] }
const DESC = {
  caution: 'red-bordered white triangle with a black exclamation mark (other danger)',
  crossroads: 'red-bordered triangle with a black cross / side-road junction symbol',
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
  durak: 'blue rectangle with a bus / bus stop symbol (or white "DURAK" board)',
  demiryolu: 'red-bordered triangle with a steam locomotive or gate symbol, or the St Andrew cross (railway crossing)',
  ada_etrafinda: 'blue circle with three circling arrows (roundabout)',
  isikli_isaret: 'red-bordered triangle with a traffic light symbol',
  keskin_viraj: 'black-and-white (or red-white) chevron arrow board marking a sharp bend',
  devamli_viraj: 'red-bordered triangle with an S-shaped double bend arrow',
  sollama_yasak: 'red-ring circle with two cars side by side, left one red (no overtaking)',
  dusen_kaya: 'red-bordered triangle with falling rocks / rock slope symbol',
  hayvan: 'red-bordered triangle with an animal (cow, deer, sheep) silhouette',
  daralan_yol: 'red-bordered triangle with two lines narrowing (road narrows)',
  dik_egim: 'red-bordered triangle with a slope and a percentage (steep hill)',
  speed40: 'red-ring circle with the number 40', speed60: 'red-ring circle with the number 60',
  hiz_sonu: 'white/grey circle with a number and diagonal black stripes (end of speed limit)',
  yol_calismasi: 'red-bordered triangle (often on yellow background) with a digging worker symbol (road works)',
  kaygan_yol: 'red-bordered triangle with a skidding car symbol (slippery road)',
  diger_levha: 'any OTHER real traffic sign or sign-like post (hazard marker posts, direction boards, info boards) that is not one of the classes above',
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    total_cells: { type: 'number' },
    cells: { type: 'array', items: { type: 'object', properties: {
      no: { type: 'number' }, decision: { type: 'string', enum: ['keep', 'reject', 'relabel'] },
      new_class: { type: 'string' }, note: { type: 'string' },
    }, required: ['no', 'decision'] } },
  },
  required: ['total_cells', 'cells'],
}

const names = args.names
const prompt = (sh) => `You are reviewing pseudo-labels for a Turkish traffic-sign detector. Read the image file with the Read tool:
${args.dir}\\${sh.file}
It is a contact sheet of crops. Every crop is a box that the model predicted as class "${sh.sinif}" = ${DESC[sh.sinif] || sh.sinif}.
Each cell has a YELLOW number at its top-left (the box number) and a RED confidence at its bottom-left. Cells are in row-major order.
Crops include ~40% context around the box, so the sign is in the middle of the cell. Crops come from Turkish roads (dashcam / motorcycle / photo).
For EVERY cell decide:
- keep: the central object truly is a "${sh.sinif}" sign (Turkish KGM design; the same pictogram family as described).
- relabel: it is clearly a different sign from this list (use the exact name): ${names.join(', ')}. Use "diger_levha" for a real traffic sign,
  hazard-marker post or direction/info board that is none of the voiced classes. Use relabel only when you are sure.
- reject: not a traffic sign at all (mirror, dashboard, car part, billboard, shop sign, window, sky, tree, licence plate, text board, blur you cannot identify)
  or a sign whose class you cannot identify. When in doubt, reject — precision matters more than recall.
Speed limits: read the digits carefully; 30/50/70/40/60 look alike at low resolution — if the digits are not legible, reject.
Count the cells first and report total_cells. Return one entry per cell (no missing numbers). Be strict and brief in notes.`

const important = new Set(args.important || [])
const results = await pipeline(args.sheets,
  sh => agent(prompt(sh), { label: `A:${sh.file}`, phase: 'Denetim A', schema: REVIEW_SCHEMA }),
  async (a, sh) => {
    if (!important.has(sh.sinif)) return { sh, a, b: null }
    const b = await agent(prompt(sh), { label: `B:${sh.file}`, phase: 'Denetim B', schema: REVIEW_SCHEMA })
    return { sh, a, b }
  })

// merge: single reviewer -> its decision; two reviewers -> keep only when both keep, relabel only when both agree, else reject
const lines = [], stats = {}
for (const r of results.filter(Boolean)) {
  const { sh, a, b } = r
  if (!a) { lines.push(`${sh.sinif}:*  # A failed`); continue }
  const st = stats[sh.sinif] = stats[sh.sinif] || { keep: 0, reject: 0, relabel: 0, disagree: 0 }
  const A = new Map(a.cells.map(c => [c.no, c]))
  const B = b ? new Map(b.cells.map(c => [c.no, c])) : null
  const n = Math.max(a.total_cells || 0, ...a.cells.map(c => c.no))
  for (let no = 1; no <= n; no++) {
    const ca = A.get(no), cb = B ? B.get(no) : null
    let d = ca ? ca.decision : 'reject', nc = ca && ca.new_class
    if (B) {
      if (!ca || !cb) d = 'reject'
      else if (ca.decision === 'keep' && cb.decision === 'keep') d = 'keep'
      else if (ca.decision === 'relabel' && cb.decision === 'relabel' && ca.new_class === cb.new_class) { d = 'relabel'; nc = ca.new_class }
      else { d = 'reject'; if (ca.decision !== cb.decision) st.disagree++ }
    }
    if (d === 'relabel' && (!nc || !names.includes(nc))) d = 'reject'
    st[d]++
    if (d === 'reject') lines.push(`${sh.sinif}:${no}`)
    else if (d === 'relabel') lines.push(`${sh.sinif}:${no}=${nc}`)
  }
}
return { lines, stats }
