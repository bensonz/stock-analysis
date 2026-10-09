const DATA = __DATA__;
const DETAILS = __DETAILS__;
const STARTING = __STARTING__;
const TRADES = __TRADES__;
const fmtM = v => (v == null ? "—" : Math.round(v).toLocaleString());
const pnlCls = v => (typeof v !== "number" || v === 0) ? "flat" : (v > 0 ? "up" : "down");
const sign = v => (v > 0 ? "+" : "");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pctTxt = v => (v == null ? "—" : `${sign(v)}${v.toFixed(2)}%`);
const BYDATE = {}; DATA.forEach(p => { BYDATE[p.d] = p; });
// The round trip holding `code` on `day` (a code can be traded many times).
function tradeFor(code, day) {
  code = String(code).split(".")[0];
  let best = null;
  for (const [k, t] of Object.entries(TRADES))
    if (t.c === code && t.ed <= day && (!t.xd || day <= t.xd) && (!best || t.ed > best[1].ed)) best = [k, t];
  return best ? best[0] : null;
}
// 组合 day % minus 上证 day %, only over the same span. A pre-15:00 snapshot is
// compared with the 上证 % its own run saw, not with the later close.
const isNoon = p => !!(p.t && p.t < "15:00");
function excess(p) {
  if (p.pr == null) return null;
  if (isNoon(p) && p.iq == null) return null;   // no 上证 for that moment
  const ix = p.iq != null ? p.iq : p.ic;
  if (ix == null || (p.pd && p.ipd && (p.pdi || p.pd) !== p.ipd)) return null;
  return Math.round((p.pr - ix) * 100) / 100;
}
// Σ holding P&L today ÷ yesterday's equity. On a day with no trades and fresh
// marks this equals 组合 day % (cash does not move); a gap means trades,
// a missing quote, or a mark problem — said, not hidden.
function holdingsCheck(det, p) {
  if (!p || p.pr == null || det.equity == null || det.day_pnl == null) return "";
  const hs = det.holdings || [];
  if (!hs.length || hs.some(x => x.d == null || x.v == null)) return "";
  const pnl = hs.reduce((a, x) => a + x.v * x.d / (100 + x.d), 0);
  const c = Math.round(pnl / (det.equity - det.day_pnl) * 10000) / 100;
  // Dividend cash booked since the last snapshot raises equity with no
  // price move: take it out of the gap and name it.
  const gap = Math.round(pnl - det.day_pnl + (det.div_in || 0));
  // Only actions that move cash or shares; RAISE_STOP / HOLD change nothing.
  const trades = (det.actions || []).some(a => TRADE_ACTS[a.a]) || (det.closed || []).length;
  return `<div class="mini">持仓当日贡献合计 <b class="${pnlCls(c)}">${pctTxt(c)}</b> (${sign(pnl)}${fmtM(pnl)}) · 组合 ${pctTxt(p.pr)} (${sign(det.day_pnl)}${fmtM(det.day_pnl)})`
       + (det.div_in ? ` · 含分红到账 ${sign(det.div_in)}${fmtM(det.div_in)}` : "")
       + (Math.abs(gap) > 20 ? ` · 差 ${sign(gap)}${fmtM(gap)}` : "")
       + (Math.abs(gap) > 20
          ? (trades ? "（当日有交易，二者不必相等）"
             : hs.some(x => x.xd != null) ? "（不一致：⚠ 标记的股票账本前值≠行情昨收，常见于除权除息日——分红/送转按除权日记入现金与股数，不计入行情涨跌）"
             : "（不一致：行情或市值时点不同）")
          : " ✓")
       + `</div>`;
}
function cmpHtml(p) {
  const pc = v => `<b class="${pnlCls(v)}">${pctTxt(v)}</b>`;
  const ex = excess(p);
  let h = `<div class="d-cmp">当日 组合 ${pc(p.pr)} · 上证 ${pc(p.ic)} · 超额 ${ex == null ? "—" : pc(ex)}</div>`;
  if (p.k) h += `<div class="mini">上证 开 ${p.k[0].toFixed(2)} 高 ${p.k[1].toFixed(2)} 低 ${p.k[2].toFixed(2)} 收 ${p.k[3].toFixed(2)}</div>`;
  if (p.iq != null)
    h += `<div class="d-note">组合取 ${esc(p.t || "")} 午盘快照，当时上证 ${pctTxt(p.iq)}，收盘 ${pctTxt(p.ic)}；超额按运行时计算</div>`;
  else if (isNoon(p))
    h += `<div class="d-note">组合取 ${esc(p.t)} 午盘快照，该次运行无上证行情——与收盘涨跌不可比，不算超额</div>`;
  if (p.pd && p.ipd && (p.pdi || p.pd) !== p.ipd)
    h += `<div class="d-note">组合较 ${esc(p.pd)} 快照，上证较 ${esc(p.ipd)} 收盘——区间不同，不算超额</div>`;
  return h;
}

// ---------------- side panel
const dayEl = document.getElementById("day");
let pinned = null;
let latestDay = null;
const ACTION_CN = {OPEN:"开", BUY:"开", SELL:"平", ADD:"加", TRIM:"减", HOLD:"持"};
const OPENS = {OPEN:1, BUY:1, ADD:1};
const TRADE_ACTS = {OPEN:1, BUY:1, ADD:1, SELL:1, TRIM:1};
function unpin() { pinned = null; if (latestDay) renderDay(latestDay); }
function renderDay(d) {
  const det = DETAILS[d];
  if (!det) { dayEl.innerHTML = `<div class='d-date'>${esc(d)}</div><div class='note'>无记录</div>`; return; }
  const pinBtn = pinned ? ` <button id="unpin" title="取消固定 (Esc)">📌 ✕</button>` : "";
  let h = `<div class="d-date">${esc(d)} <span class="chip">${esc(det.slot)}</span>`
        + (det.stale_marks ? ` <span class="chip warn" title="该日快照里的持仓市值早于当日，或无法确定其时点">持仓市值非当日</span>` : "")
        + (det.from_failed_run ? ` <span class="chip warn" title="该数值取自当日一次失败的运行所留下的快照——数值本身可用，但该次运行未走完">来自失败运行</span>` : "")
        + `${pinBtn}</div>`;
  h += `<div class="d-equity">${fmtM(det.equity)}</div>`;
  const dp = det.day_pnl;
  h += `<div class="d-sub"><span class="${pnlCls(dp)}">${dp == null ? "—" : sign(dp) + fmtM(dp)}</span> 较上一快照`
     + ` · 累计 <span class="${pnlCls(det.ret)}">${det.ret == null ? "—" : sign(det.ret) + det.ret + "%"}</span></div>`;
  if (BYDATE[d] && !BYDATE[d].s) h += cmpHtml(BYDATE[d]);
  const trades = (det.actions || []).filter(a => a.a !== "HOLD");
  const hasOpens = trades.some(a => OPENS[a.a]);
  if (trades.length) {
    h += `<h4>当日交易</h4>`;
    for (const a of trades) {
      let size = "";
      if (a.sh) {
        size = `<div class="d-size">${a.sh.toLocaleString()}股`
             + (a.amt ? ` ≈ ${fmtM(a.amt)}` : "")
             + (a.ap ? ` · ${a.ap}%仓位` : "") + `</div>`;
      }
      h += `<div class="d-act"><span class="badge b-${a.a === "SELL" ? "sell" : "open"}">${ACTION_CN[a.a] || esc(a.a)}</span>`
         + ` <b>${esc(a.n)}</b> <span class="muted">${a.p ?? ""}</span>`
         + ` <span class="${pnlCls(a.r)}">${a.r == null ? "" : sign(a.r) + a.r + "%"}</span>`
         + size
         + `<div class="d-note">${esc(a.note)}</div></div>`;
    }
  }
  if (det.closed && det.closed.length) {
    h += `<h4>当日平仓结果</h4>`;
    for (const t of det.closed) {
      h += `<div class="d-row"><b>${esc(t.n)}</b><span class="${pnlCls(t.r)}">${sign(t.r)}${t.r}%</span></div>`
         + `<div class="d-note">${esc(t.why)}</div>`;
    }
  }
  if (det.holdings && det.holdings.length) {
    h += `<h4>持仓 (${det.holdings.length}) <span class="mini">当日最后快照${det.stale_marks ? "(市值非当日)" : ""}</span></h4>`
       + `<div class="d-row mini"><span>市值 (权重)</span><span>当日 · 累计</span></div>`;
    // Every action carries the model's reasoning — not just HOLD. Filtering
    // to HOLD hid 91 of 255 notes (SELL/OPEN/RAISE_STOP), which read as
    // "this row has nothing to say" when it had the most to say.
    const rowNotes = {};
    for (const a of (det.actions || [])) if (a.note) rowNotes[a.c] = {a: a.a, note: a.note};
    let noted = 0;
    for (const p of det.holdings) {
      const size = p.v != null ? `<span class="hv mini">${fmtM(p.v)}${p.w != null ? ` (${p.w}%)` : ""}</span>` : "";
      const rn = rowNotes[p.c];
      if (rn) noted++;
      // Glyph, not the word: the full action name is in the tooltip badge,
      // and "RAISE_STOP" inline pushed the stock code out of the row.
      const glyph = {RAISE_STOP: "⬆", OPEN: "＋", SELL: "✕"}[rn && rn.a] || "";
      const tag = glyph ? ` <span class="act-tag">${glyph}</span>` : "";
      const tk = tradeFor(p.c, d);
      h += `<div class="d-row${rn ? " has-note" : ""}${tk ? " tk" : ""}"${rn ? ` data-note="${esc(rn.note)}" data-act="${esc(rn.a)}"` : ""}${tk ? ` data-tk="${esc(tk)}"` : ""}>`
         + `<span>${esc(p.n)}${tag} <span class="muted">${esc(p.c)}</span>${size}</span>`
         + `<span>${p.xd != null ? `<span class="xd" title="账本前值 ${p.xd} ≠ 行情昨收 ${p.qp}：除权除息日，或前一快照非收盘价。行情涨跌按昨收计，账本按前值计">⚠</span>` : ""}`
         + `<span class="dpct ${pnlCls(p.d)}">${pctTxt(p.d)}</span> · `
         + `<span class="${pnlCls(p.p)}">${p.p == null ? "—" : sign(p.p) + p.p + "%"}</span></span></div>`;
    }
    const chk = holdingsCheck(det, BYDATE[d]);
    if (chk) h += chk;
    // Absence must be visible, not mysterious: 39 of 108 days predate action
    // logging, so no row on them has reasoning to show.
    if (!noted) {
      // Four causes, four sentences. Until 2026-08-21 all of them rendered as
      // "早于决策日志上线", which is true for exactly one date in all history
      // (2026-02-13) and was a fabricated excuse everywhere else.
      const why = {
        run_failed: "该日该时段运行失败，未产生决策记录",
        predates_note_log: "该日有决策但无逐仓理由（早于决策日志上线）",
        unknown: "该日无逐仓决策记录（原因不明）",
      }[det.notes_absent_reason] || "该日无逐仓决策记录";
      h += `<div class="note mini-note">${esc(why)}</div>`;
    }
    else h += `<div class="note mini-note">悬停持仓行查看当日决策理由</div>`;
  } else {
    h += `<div class="note" style="margin-top:8px">空仓 · 100%现金`
       + (hasOpens ? " — 当日开仓于下一快照计入持仓" : "") + `</div>`;
  }
  dayEl.innerHTML = h;
  const btn = document.getElementById("unpin");
  if (btn) btn.addEventListener("click", unpin);
}
document.addEventListener("keydown", ev => { if (ev.key === "Escape" && pinned) unpin(); });

// Hover reasoning for holding rows. Delegated so it survives every re-render
// of the side panel; native title= was unstyled, ~1s delayed, and clipped the
// 200-char Chinese notes these actually are.
(function() {
  const rt = document.getElementById("rowtip");
  function place(ev) {
    const pad = 14, w = rt.offsetWidth, hgt = rt.offsetHeight;
    let x = ev.clientX - w - pad, y = ev.clientY + pad;
    if (x < 8) x = ev.clientX + pad;                       // flip near left edge
    if (y + hgt > window.innerHeight - 8) y = ev.clientY - hgt - pad;
    rt.style.left = Math.max(8, x) + "px";
    rt.style.top = Math.max(8, y) + "px";
  }
  document.addEventListener("mouseover", ev => {
    const row = ev.target.closest && ev.target.closest(".d-row.has-note");
    if (!row) return;
    // textContent, not innerHTML: dataset gives back the DECODED note, so
    // re-parsing it as HTML would undo the escaping done at render time.
    rt.textContent = "";
    const badge = document.createElement("span");
    badge.className = "rt-act";
    badge.textContent = row.dataset.act || "";
    rt.appendChild(badge);
    rt.appendChild(document.createElement("br"));
    rt.appendChild(document.createTextNode(row.dataset.note || ""));
    rt.style.display = "block";
    place(ev);
  });
  document.addEventListener("mousemove", ev => {
    if (rt.style.display === "block" && ev.target.closest && ev.target.closest(".d-row.has-note")) place(ev);
  });
  document.addEventListener("mouseout", ev => {
    if (ev.target.closest && ev.target.closest(".d-row.has-note")) rt.style.display = "none";
  });
})();

// ---------------- charts
(function() {
  const svg = document.getElementById("chart"), tip = document.getElementById("tip");
  const bars = document.getElementById("bars"), cmp = document.getElementById("cmp");
  if (!DATA.length) { svg.outerHTML = "<div class='empty'>暂无快照数据</div>"; return; }
  const IDXBASE = __IDXBASE__;
  const hasIdx = DATA.some(p => p.i != null);
  // Right gutter only widens when there is a second axis to put in it.
  const W = 960, H = 340, L = 74, R = (hasIdx && IDXBASE) ? 56 : 16, T = 18, B = 30;
  const iw = W - L - R, ih = H - T - B;
  // Right axis = the SAME gridlines relabelled in index points. The candles are
  // rebased (index_t / index_base x STARTING), so equity value v corresponds to
  // index level v / STARTING x IDXBASE exactly. Deliberately NOT an independent
  // scale: the whole point of the overlay is "did we beat 上证", and giving each
  // series its own range lets any pair of lines be made to look correlated or
  // divergent by choosing limits. One scale, two readings.
  const showIdxAxis = hasIdx && IDXBASE;
  const toIdx = v => v / STARTING * IDXBASE;
  const toEq = v => v / IDXBASE * STARTING;
  const MIN_PX_FOR_LABELS = 34;   // below this the % strip can't fit "+0.79%"
  let V = DATA, x, y, idxHidden = false;

  function draw(n) {
    V = n ? DATA.slice(-n) : DATA;
    const es = V.map(p => p.e);
    if (hasIdx) V.forEach(p => {
      if (p.i != null) es.push(p.i);
      if (showIdxAxis && p.k) es.push(toEq(p.k[1]), toEq(p.k[2]));
    });
    es.push(STARTING);   // the 0% baseline stays on screen in every range
    let lo = Math.min(...es), hi = Math.max(...es);
    const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
    const slot = iw / Math.max(V.length, 1);
    x = i => L + slot * (i + 0.5);   // centred in its own slot, so candles never clip
    y = v => T + (hi - v) / (hi - lo) * ih;
    const bw = Math.max(1.5, Math.min(16, slot * 0.6));
    const S = [];
    for (let g = 0; g <= 4; g++) {
      const v = lo + (hi - lo) * g / 4, yy = y(v);
      S.push(`<line x1="${L}" y1="${yy}" x2="${W - R}" y2="${yy}" stroke="#eef1f5"/>`);
      S.push(`<text x="${L - 8}" y="${yy + 4}" text-anchor="end" font-size="11" fill="#8a93a2">${Math.round(v).toLocaleString()}</text>`);
      if (showIdxAxis)
        S.push(`<text x="${W - R + 8}" y="${yy + 4}" font-size="11" fill="#c08a2e">${toIdx(v).toFixed(0)}</text>`);
    }
    if (showIdxAxis) {
      S.push(`<text x="${W - R + 8}" y="${T - 6}" font-size="10" fill="#c08a2e">上证</text>`);
      S.push(`<text x="${L - 8}" y="${T - 6}" text-anchor="end" font-size="10" fill="#8a93a2">净值</text>`);
    }
    const step = Math.max(1, Math.round(V.length / 8));
    for (let i = 0; i < V.length; i += step)
      S.push(`<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#8a93a2">${V[i].d.slice(5)}</text>`);
    S.push(`<line x1="${L}" y1="${y(STARTING)}" x2="${W - R}" y2="${y(STARTING)}" stroke="#9aa3b2" stroke-dasharray="5 4"/>`);
    const pts = V.map((p, i) => `${x(i).toFixed(1)},${y(p.e).toFixed(1)}`).join(" ");
    const tone = V[V.length - 1].e >= STARTING ? "212,58,58" : "26,156,98";
    S.push(`<polygon points="${x(0)},${y(STARTING)} ${pts} ${x(V.length - 1)},${y(STARTING)}" fill="rgba(${tone},0.07)"/>`);
    // 上证 daily candles, only on dates with a real bar — never forward-filled.
    // A date with only a settled close (kline not built yet) gets a flat tick.
    if (showIdxAxis) {
      const C = [];
      V.forEach((p, i) => {
        const cx = x(i).toFixed(1);
        if (p.k) {
          const [o, h, l, c] = p.k.map(toEq), col = p.k[3] >= p.k[0] ? "#d43a3a" : "#1a9c62";
          const top = y(Math.max(o, c)), hgt = Math.max(1, Math.abs(y(o) - y(c)));
          C.push(`<line x1="${cx}" y1="${y(h).toFixed(1)}" x2="${cx}" y2="${y(l).toFixed(1)}" stroke="${col}" stroke-width="1"/>`
               + `<rect x="${(x(i) - bw / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${bw.toFixed(1)}" height="${hgt.toFixed(1)}" fill="${col}" fill-opacity="0.55" stroke="${col}" stroke-width="0.8"/>`);
        } else if (p.kc != null) {
          const yy = y(toEq(p.kc)).toFixed(1);
          C.push(`<line x1="${(x(i) - bw / 2).toFixed(1)}" y1="${yy}" x2="${(x(i) + bw / 2).toFixed(1)}" y2="${yy}" stroke="#c08a2e" stroke-width="2"/>`);
        }
      });
      S.push(`<g id="idxline"${idxHidden ? ' style="display:none"' : ""}>${C.join("")}</g>`);
    }
    const solidFrom = (V[0].s && V.length > 1) ? 1 : 0;
    if (solidFrom)
      S.push(`<line x1="${x(0)}" y1="${y(V[0].e)}" x2="${x(1)}" y2="${y(V[1].e)}" stroke="#3b6ea5" stroke-width="2" stroke-dasharray="6 5"/>`);
    const solidPts = V.slice(solidFrom).map((p, i) => `${x(i + solidFrom).toFixed(1)},${y(p.e).toFixed(1)}`).join(" ");
    S.push(`<polyline points="${solidPts}" fill="none" stroke="#3b6ea5" stroke-width="2"/>`);
    if (slot >= MIN_PX_FOR_LABELS)
      V.forEach((p, i) => { if (!p.s) S.push(`<circle cx="${x(i)}" cy="${y(p.e)}" r="2.2" fill="#3b6ea5"/>`); });
    S.push(`<circle id="dot" r="4" fill="#3b6ea5" stroke="#fff" stroke-width="1.5" style="display:none"/>`);
    S.push(`<line id="guide" y1="${T}" y2="${T + ih}" stroke="#c3cad4" stroke-dasharray="3 3" style="display:none"/>`);
    svg.innerHTML = S.join("");

    // daily pnl bars (shared x)
    if (bars) {
      const BH = 96, BT = 6, BB = 4, bih = BH - BT - BB;
      const ps = V.map(p => p.p).filter(v => typeof v === "number");
      const mx = Math.max(1, ...ps.map(Math.abs));
      const by = v => BT + (mx - v) / (2 * mx) * bih;
      const BS = [`<line x1="${L}" y1="${by(0)}" x2="${W - R}" y2="${by(0)}" stroke="#e4e8ee"/>`,
                  `<text x="${L - 8}" y="${by(mx) + 8}" text-anchor="end" font-size="10" fill="#8a93a2">+${fmtM(mx)}</text>`,
                  `<text x="${L - 8}" y="${by(-mx)}" text-anchor="end" font-size="10" fill="#8a93a2">-${fmtM(mx)}</text>`];
      V.forEach((p, i) => {
        if (typeof p.p !== "number") return;
        const yy = by(Math.max(p.p, 0)), hh = Math.abs(by(p.p) - by(0)) || 0.5;
        BS.push(`<rect x="${(x(i) - bw / 2).toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" fill="${p.p >= 0 ? "#d43a3a" : "#1a9c62"}" opacity="0.8"/>`);
      });
      bars.innerHTML = BS.join("");
    }

    // day-% strip: 组合 / 上证 / 超额 per column, only when it can be read
    if (cmp) {
      const rows = [["组合", 15], ["上证", 33], ["超额", 51]];
      const CS = rows.map(([t, yy]) => `<text x="${L - 8}" y="${yy}" text-anchor="end" font-size="10.5" fill="#8a93a2">${t}</text>`);
      if (slot < MIN_PX_FOR_LABELS) {
        CS.length = 0;
        CS.push(`<text x="${W / 2}" y="33" text-anchor="middle" font-size="11.5" fill="#8a93a2">逐日涨跌需更窄的范围——切换到「近20日」，或悬停查看</text>`);
      } else {
        const cell = (v, yy, i, extra) => v == null
          ? `<text x="${x(i)}" y="${yy}" text-anchor="middle" font-size="10.5" fill="#b4bcc8">—</text>`
          : `<text x="${x(i)}" y="${yy}" text-anchor="middle" font-size="10.5" fill="${v > 0 ? "#d43a3a" : v < 0 ? "#1a9c62" : "#1c2330"}">${sign(v)}${v.toFixed(2)}${extra || ""}</text>`;
        V.forEach((p, i) => {
          if (p.s) return;
          CS.push(cell(p.pr, 15, i, isNoon(p) ? "*" : ""), cell(p.ic, 33, i), cell(excess(p), 51, i, p.iq != null ? "*" : ""));
        });
      }
      cmp.innerHTML = CS.join("");
    }
    const dot = svg.querySelector("#dot"), guide = svg.querySelector("#guide");
    svg.onmouseleave = () => {
      dot.style.display = "none"; guide.style.display = "none"; tip.style.display = "none";
      if (!pinned) renderDay(DATA[DATA.length - 1].d);
    };
    svg.onmousemove = ev => {
      const i = idxFromEvent(ev), p = V[i];
      dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(p.e)); dot.style.display = "";
      guide.setAttribute("x1", x(i)); guide.setAttribute("x2", x(i)); guide.style.display = "";
      tip.innerHTML = tipHtml(p);
      tip.style.display = "block";
      // flip left near the right edge so the multi-line tip stays on screen
      const left = ev.clientX + 14 + tip.offsetWidth > window.innerWidth ? ev.clientX - 14 - tip.offsetWidth : ev.clientX + 14;
      tip.style.left = Math.max(4, left) + "px"; tip.style.top = (ev.clientY - 12) + "px";
      if (!pinned) renderDay(p.d);
    };
  }

  function idxFromEvent(ev) {
    const r = svg.getBoundingClientRect();
    const mx = (ev.clientX - r.left) * W / r.width;
    const slot = iw / Math.max(V.length, 1);
    return Math.max(0, Math.min(V.length - 1, Math.floor((mx - L) / slot)));
  }

  function tipHtml(p) {
    if (p.s) return `${p.d} · ${fmtM(p.e)} · 组合起始(初始资金)`;
    let h = `<b>${p.d}</b>${p.t ? ` · ${isNoon(p) ? "午盘" : ""}快照 ${p.t}` : ""}`
          + `<br>组合 ${fmtM(p.e)} · ${pctTxt(p.pr)}${p.pd ? ` <span class="tm">较 ${p.pd.slice(5)}</span>` : ""}`;
    if (p.k) h += `<br>上证 开 ${p.k[0].toFixed(2)} 高 ${p.k[1].toFixed(2)} 低 ${p.k[2].toFixed(2)} 收 ${p.k[3].toFixed(2)}`;
    else if (p.kc != null) h += `<br>上证 收 ${p.kc.toFixed(2)} <span class="tm">(仅实时收盘价，无日K)</span>`;
    else if (hasIdx) h += `<br>上证 当日无日K`;
    if (p.ic != null) h += ` · ${pctTxt(p.ic)}${p.ipd ? ` <span class="tm">较 ${p.ipd.slice(5)}</span>` : ""}`;
    if (p.iq != null) h += `<br>运行时上证 ${pctTxt(p.iq)} <span class="tm">(快照早于收盘)</span>`;
    else if (isNoon(p)) h += `<br><span class="tm">快照早于收盘，运行时无上证行情</span>`;
    const ex = excess(p);
    h += `<br>超额 ${ex == null ? "—" : pctTxt(ex)}${p.iq != null && ex != null ? ` <span class="tm">按运行时上证</span>` : ""}`;
    return h;
  }

  // range selector
  const rangeEl = document.getElementById("range");
  let n = 20;
  try { const v = localStorage.getItem("site.range"); if (v != null) n = +v; } catch (e) {}
  function setRange(k) {
    n = k;
    if (rangeEl) rangeEl.querySelectorAll("button").forEach(b => b.classList.toggle("on", +b.dataset.n === n));
    try { localStorage.setItem("site.range", String(n)); } catch (e) {}
    draw(n && n < DATA.length ? n : 0);
  }
  if (rangeEl) rangeEl.addEventListener("click", ev => {
    const b = ev.target.closest("button"); if (b) setRange(+b.dataset.n);
  });

  // legend toggle
  const lg = document.getElementById("lg-idx");
  if (lg && hasIdx) lg.addEventListener("click", () => {
    idxHidden = !idxHidden;
    const el = svg.querySelector("#idxline");
    if (el) el.style.display = idxHidden ? "none" : "";
    lg.classList.toggle("off", idxHidden);
  });

  svg.addEventListener("click", ev => {
    const d = V[idxFromEvent(ev)].d;
    pinned = (pinned === d) ? null : d;
    renderDay(pinned || d);
  });
  setRange(n);
  latestDay = DATA[DATA.length - 1].d;
  renderDay(latestDay);
})();

// ---------------- position history (click a position)
(function() {
  const modal = document.getElementById("posmodal"), body = document.getElementById("pm-body");
  if (!modal) return;
  const ACT = {OPEN:"开仓", BUY:"开仓", ADD:"加仓", TRIM:"减仓", SELL:"平仓", HOLD:"持有",
               RAISE_STOP:"上移止损", DIVIDEND:"分红", BONUS_SHARES:"送转"};
  const ACT_CLS = {OPEN:"open", BUY:"open", ADD:"open", SELL:"sell", TRIM:"sell"};

  function chart(t) {
    const B = t.bars;
    if (!B.length) return `<div class="empty">无K线：${esc(t.bars_missing || "价格库中无该股数据")}</div>`;
    const W = 860, H = 300, L = 56, R = 104, T = 14, BOT = 26, iw = W - L - R, ih = H - T - BOT;
    const vals = B.flatMap(b => [b[2], b[3]]);
    for (const v of [t.ep, t.xp, t.tp, ...t.stops.map(s => s[1])]) if (typeof v === "number") vals.push(v);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.12 || 1; lo -= pad; hi += pad;   // room for 买/卖 markers
    const slot = iw / B.length, bw = Math.max(1.5, Math.min(12, slot * 0.62));
    const x = i => L + slot * (i + 0.5), y = v => T + (hi - v) / (hi - lo) * ih;
    const idx = {}; B.forEach((b, i) => { idx[b[0]] = i; });
    // date → slot index; a date between bars (holiday) snaps to the next bar
    const at = d => { if (d in idx) return idx[d]; const i = B.findIndex(b => b[0] > d); return i < 0 ? B.length - 1 : i; };
    const S = [];
    for (let g = 0; g <= 4; g++) {
      const v = lo + (hi - lo) * g / 4;
      S.push(`<line x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}" stroke="#eef1f5"/>`
           + `<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="#8a93a2">${v.toFixed(2)}</text>`);
    }
    const step = Math.max(1, Math.round(B.length / 8));
    for (let i = 0; i < B.length; i += step)
      S.push(`<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#8a93a2">${B[i][0].slice(5)}</text>`);
    // holding window shading
    const i0 = at(t.ed), i1 = t.xd ? at(t.xd) : B.length - 1;
    S.push(`<rect x="${x(i0) - slot / 2}" y="${T}" width="${(i1 - i0 + 1) * slot}" height="${ih}" fill="#3b6ea5" fill-opacity="0.05"/>`);
    B.forEach((b, i) => {
      const [, o, h, l, c] = b, col = c >= o ? "#d43a3a" : "#1a9c62";
      S.push(`<line x1="${x(i)}" y1="${y(h)}" x2="${x(i)}" y2="${y(l)}" stroke="${col}"/>`
           + `<rect x="${x(i) - bw / 2}" y="${y(Math.max(o, c))}" width="${bw}" height="${Math.max(1, Math.abs(y(o) - y(c)))}" fill="${col}" fill-opacity="${i >= i0 && i <= i1 ? 0.75 : 0.3}" stroke="${col}" stroke-width="0.8"/>`);
    });
    // Right-edge labels are collected and laid out together: equal values
    // merge into one label ("成本/止损 19.29" — the breakeven stop), close
    // values are pushed apart so no two overlap.
    const labels = [];
    const label = (v, col, name) => { if (typeof v === "number") labels.push({v, col, name}); };
    const hline = (v, col, name, dash) => {
      if (typeof v !== "number") return;
      S.push(`<line x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}" stroke="${col}" stroke-width="1.3" ${dash ? `stroke-dasharray="${dash}"` : ""}/>`);
      label(v, col, name);
    };
    hline(t.ep, "#3b6ea5", "成本", "5 4");
    hline(t.tp, "#c08a2e", "目标", "2 3");
    // stop: a step line through the KNOWN levels only (older RAISE_STOPs lack new_stop)
    t.stops.forEach((s, k) => {
      const nx = k + 1 < t.stops.length ? x(at(t.stops[k + 1][0])) : x(i1) + slot / 2;
      S.push(`<line x1="${x(at(s[0])) - slot / 2}" y1="${y(s[1])}" x2="${nx}" y2="${y(s[1])}" stroke="#7a4fc0" stroke-width="1.6"/>`);
      if (k + 1 === t.stops.length) label(s[1], "#7a4fc0", "止损");
    });
    const merged = [];
    for (const lb of labels.sort((a, b) => b.v - a.v)) {
      const same = merged.find(m => Math.abs(m.v - lb.v) < 1e-6);
      if (same) same.parts.push(lb); else merged.push({v: lb.v, parts: [lb]});
    }
    const LGAP = 13, ytop = T + 4, ybot = T + ih + 4;
    const ys = merged.map(m => y(m.v) + 4);
    for (let k = 1; k < ys.length; k++) ys[k] = Math.max(ys[k], ys[k - 1] + LGAP);
    if (ys.length && ys[ys.length - 1] > ybot) {
      ys[ys.length - 1] = ybot;
      for (let k = ys.length - 2; k >= 0; k--) ys[k] = Math.min(ys[k], ys[k + 1] - LGAP);
    }
    merged.forEach((m, k) => {
      const names = m.parts.map(p => `<tspan fill="${p.col}">${p.name}</tspan>`).join("/");
      S.push(`<text x="${W - R + 4}" y="${Math.max(ytop, ys[k])}" font-size="10.5" fill="${m.parts[0].col}">${names} ${m.v}</text>`);
    });
    // trade markers sit just OUTSIDE their day's bar (买/加 under the low,
    // 卖/减 above the high) so they never cover the candle they mark
    const mark = (d, px, up, col, text) => {
      if (!d) return;
      const i = at(d), b = B[i];
      const tip = b ? (up ? y(b[3]) + 3 : y(b[2]) - 3) : (typeof px === "number" ? y(px) : null);
      if (tip == null) return;
      const dy = up ? 9 : -9;
      S.push(`<path d="M${x(i)},${tip} l-5,${dy} h10 z" fill="${col}"/>`
           + `<text x="${x(i)}" y="${tip + dy + (up ? 11 : -3)}" text-anchor="middle" font-size="10.5" font-weight="600" fill="${col}">${text}</text>`);
    };
    mark(t.ed, t.ep, true, "#d43a3a", "买");
    for (const e of t.ev) if ((e.a === "ADD" || e.a === "TRIM") && e.px) mark(e.d, e.px, e.a === "ADD", e.a === "ADD" ? "#d43a3a" : "#1a9c62", e.a === "ADD" ? "加" : "减");
    if (t.xd) mark(t.xd, t.xp, false, "#1a9c62", "卖");
    return `<svg viewBox="0 0 ${W} ${H}" class="pm-chart">${S.join("")}</svg>`;
  }

  function open(k) {
    const t = TRADES[k];
    if (!t) return;
    const days = t.xd ? `${esc(t.ed)} → ${esc(t.xd)}` : `${esc(t.ed)} 起持有中`;
    let h = `<div class="pm-head"><b>${esc(t.n)}</b> <span class="muted">${esc(t.c)}</span> `
          + `<span class="chip">${days}</span> `
          + `<span class="${pnlCls(t.r)}"><b>${t.r == null ? "—" : sign(t.r) + t.r + "%"}</b></span>`
          + `${t.sec ? ` <span class="muted">· ${esc(t.sec)}</span>` : ""}</div>`;
    h += `<div class="mini">成本 ${t.ep ?? "—"}${t.xp != null ? ` · 卖出 ${t.xp}` : ""}${t.sh ? ` · ${t.sh.toLocaleString()}股` : ""}`
       + `${t.cs != null ? ` · 最终止损 ${t.cs}` : ""}${t.tp != null ? ` · 目标 ${t.tp}` : ""} · 日K不复权（与账本一致）</div>`;
    h += chart(t);
    h += `<div class="pm-scroll">`;
    if (t.th) h += `<div class="pm-sec"><h4>建仓理由</h4><div class="d-note">${esc(t.th)}</div></div>`;
    if (t.why) h += `<div class="pm-sec"><h4>离场原因</h4><div class="d-note">${esc(t.why)}</div></div>`;
    h += `<div class="pm-sec"><h4>逐日记录 (${t.ev.length})</h4>`;
    for (const e of t.ev.slice().reverse()) {
      h += `<div class="pm-ev"><span class="pm-d">${esc(e.d)} <span class="muted">${esc(e.s)}</span></span>`
         + `<span class="badge b-${ACT_CLS[e.a] || "hold"}">${esc(ACT[e.a] || e.a)}</span>`
         + ` <span class="muted">${e.px ?? ""}</span>`
         + `${e.r != null ? ` <span class="${pnlCls(e.r)}">${sign(e.r)}${e.r}%</span>` : ""}`
         + `${e.st != null ? ` <span class="muted">止损→${e.st}</span>` : ""}`
         + `${e.note ? `<div class="d-note">${esc(e.note)}</div>` : ""}</div>`;
    }
    body.innerHTML = h + `</div></div>`;
    modal.hidden = false;
    body.querySelector(".pm-scroll").scrollTop = 0;
  }
  const close = () => { modal.hidden = true; };
  document.getElementById("pm-x").addEventListener("click", close);
  modal.addEventListener("click", ev => { if (ev.target === modal) close(); });
  document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !modal.hidden) { close(); ev.stopPropagation(); } }, true);
  document.addEventListener("click", ev => {
    const el = ev.target.closest && ev.target.closest("[data-tk]");
    if (el) open(el.dataset.tk);
  });
})();
