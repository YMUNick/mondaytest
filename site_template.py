"""CSS, JS and HTML template for the demo site (docs/index.html). Filled by build_site.py.

Design system (dealt with the design-taste-frontend skill for a software page):
palette "teal on paper", Host Grotesk + JetBrains Mono, sharp radius (4/6/8),
one button pair, one card recipe, a fixed opaque header with a hairline,
400/500 weights only, sentence-case labels, nothing under 13px.
"""

CSS = r"""
:root{
 --bg:#f7f9f8;--surface:#ebf0ee;--paper:#ffffff;--ink:#06525c;--ink-2:#1d5f68;--muted:#2f737d;
 --line:rgba(6,82,92,.14);--line-2:rgba(6,82,92,.24);
 --action:#06525c;--action-ink:#f7f9f8;
 --std:#1b6b43;--std-bg:#dcefe3;--enh:#8a4b00;--enh-bg:#f8e8c8;--high:#b42318;--high-bg:#f9e0dc;
 --code-bg:#052f35;--code-ink:#dff0ee;--code-dim:#8fb9bc;--mark:#fde68a;
 --font-text:"Host Grotesk",system-ui,sans-serif;--font-mono:"JetBrains Mono",ui-monospace,Consolas,monospace;
 --r-sm:4px;--r-md:6px;--r-lg:8px;--btn-h:44px;
 --nav:72px;--padt:96px;--padb:72px;--gut:80px;
 --s-1:4px;--s-2:8px;--s-3:12px;--s-4:16px;--s-5:24px;--s-6:32px;--s-7:48px;--s-8:64px;
 --ease:cubic-bezier(.2,.7,.2,1);
}
:root[data-theme="dark"]{
 --bg:#061b1e;--surface:#0b2a2e;--paper:#0d3034;--ink:#e3efee;--ink-2:#c6dcdc;--muted:#9dbdbf;
 --line:rgba(227,239,238,.14);--line-2:rgba(227,239,238,.26);--action:#7cd0d6;--action-ink:#04262a;
 --std:#86dca9;--std-bg:#143a2a;--enh:#f3c46e;--enh-bg:#3a2c10;--high:#ff9c8f;--high-bg:#401b18;
 --code-bg:#03191c;--code-ink:#d7ebea;--code-dim:#7fa6a9;--mark:#5e4e10;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#061b1e;--surface:#0b2a2e;--paper:#0d3034;--ink:#e3efee;--ink-2:#c6dcdc;--muted:#9dbdbf;
 --line:rgba(227,239,238,.14);--line-2:rgba(227,239,238,.26);--action:#7cd0d6;--action-ink:#04262a;
 --std:#86dca9;--std-bg:#143a2a;--enh:#f3c46e;--enh-bg:#3a2c10;--high:#ff9c8f;--high-bg:#401b18;
 --code-bg:#03191c;--code-ink:#d7ebea;--code-dim:#7fa6a9;--mark:#5e4e10;}}
@media (max-width:639px){:root{--nav:56px;--padt:64px;--padb:48px;--gut:16px}}
@media (min-width:640px) and (max-width:1023px){:root{--gut:32px}}
*{box-sizing:border-box}
html,body{margin:0}
html{scroll-padding-top:calc(var(--nav) + 16px);-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--ink);font:400 16px/1.6 var(--font-text);font-feature-settings:"ss01";
 overflow-wrap:break-word}
h1,h2,h3{font-weight:500;margin:0;letter-spacing:-.02em;line-height:1.12;text-wrap:balance}
h1{font-size:clamp(36px,3.4vw + 12px,62px);letter-spacing:-.035em;max-width:17ch}
h2{font-size:clamp(30px,1.6vw + 22px,44px);letter-spacing:-.03em;max-width:22ch}
h3{font-size:20px;line-height:1.3}
p{margin:0}
a{color:var(--action);text-decoration:none;background:linear-gradient(currentColor,currentColor) 0 100%/100% 1px no-repeat;
 transition:background-size .25s var(--ease)}
a:hover{background-size:0 1px;background-position:100% 100%}
code,.mono{font-family:var(--font-mono);font-size:14px}
:not(pre)>code{background:var(--surface);padding:1px 6px;border-radius:var(--r-sm);font-size:13px}
b,strong{font-weight:500}
.muted{color:var(--muted)}.num{font-variant-numeric:tabular-nums}.nowrap{white-space:nowrap}
.ok{color:var(--std)}.warn{color:var(--high)}.amber{color:var(--enh)}
.small{font-size:14px}
:focus-visible{outline:2px solid var(--action);outline-offset:2px}
.wrap{width:100%;max-width:calc(1280px + 2 * var(--gut));margin:0 auto;padding:0 var(--gut)}
.label{font-size:13px;font-weight:500;color:var(--muted);letter-spacing:0}
.lead{font-size:clamp(17px,.4vw + 15.5px,20px);line-height:1.55;color:var(--ink-2);max-width:56ch}

/* skip link + nav */
.skip-link{position:absolute;left:var(--gut);top:-100px;z-index:30;background:var(--action);color:var(--action-ink);
 padding:10px 16px;border-radius:var(--r-sm);background-image:none}
.skip-link:focus{top:8px}
.nav{position:fixed;inset:0 0 auto 0;height:var(--nav);background:var(--bg);border-bottom:1px solid var(--line);z-index:10}
.nav__in{display:flex;align-items:center;gap:var(--s-5);height:100%}
.brand{display:flex;align-items:center;gap:10px;color:var(--ink);font-size:18px;font-weight:500;letter-spacing:-.01em;
 background:none;white-space:nowrap}
.brand .mark{width:28px;height:28px;border-radius:var(--r-md);background:var(--action);display:grid;place-items:center}
.brand .mark svg{width:16px;height:16px;fill:none;stroke:var(--action-ink);stroke-width:2.2}
.nav__links{display:flex;gap:var(--s-1);margin-left:auto}
.nav__links a{color:var(--ink-2);font-size:15px;font-weight:500;padding:10px 12px;border-radius:var(--r-sm);background:none;
 white-space:nowrap;position:relative;transition:color .2s}
.nav__links a:hover{color:var(--ink)}
.nav__links a[aria-current="true"]::after{content:"";position:absolute;left:12px;right:12px;bottom:4px;height:2px;background:var(--action)}
.nav__end{display:flex;align-items:center;gap:var(--s-2)}
.iconbtn{width:44px;height:44px;border-radius:var(--r-sm);border:1px solid var(--line-2);background:var(--bg);color:var(--ink);
 display:grid;place-items:center;cursor:pointer;transition:background .2s,transform .15s}
.iconbtn:hover{background:var(--surface)}.iconbtn:active{transform:scale(.96)}
.iconbtn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2}
.nav__toggle{display:none}
@media (max-width:1023px){
 .nav__toggle{display:grid}
 .nav__links{position:fixed;inset:var(--nav) 0 0 0;background:var(--bg);flex-direction:column;gap:0;padding:var(--s-2) var(--gut);
  margin:0;visibility:hidden;opacity:0;transition:opacity .2s,visibility 0s .2s;overflow-y:auto}
 .nav__links a{font-size:20px;min-height:56px;display:flex;align-items:center;border-bottom:1px solid var(--line);border-radius:0;padding:0}
 .nav__links a[aria-current="true"]::after{display:none}
 .nav.is-open .nav__links{visibility:visible;opacity:1;transition:opacity .2s}
 .nav__end{margin-left:auto}
}
@media (max-width:519px){.nav .nav__cta{display:none}}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;height:var(--btn-h);padding:0 24px;border-radius:var(--r-sm);
 font:500 16px/1 var(--font-text);cursor:pointer;border:1px solid transparent;background-image:none;white-space:nowrap;
 transition:transform .15s var(--ease),background-color .2s,box-shadow .2s}
.btn:hover{transform:translateY(-1px);background-size:auto}
.btn:active{transform:translateY(0) scale(.98)}
.btn--primary{background:var(--action);color:var(--action-ink)}
.btn--primary:hover{box-shadow:0 6px 16px -8px var(--action)}
.btn--secondary{background:transparent;color:var(--ink);border-color:var(--line-2)}
.btn--secondary:hover{background:var(--surface)}
.btn[disabled]{opacity:.5;cursor:not-allowed;transform:none;box-shadow:none}
.btn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2}
.btn-row{display:flex;flex-wrap:wrap;gap:var(--s-3)}
@media (max-width:639px){.btn-row .btn{flex:1 1 100%}}

/* sections */
main{padding-top:var(--nav)}
section{padding:var(--padt) 0 var(--padb);border-top:1px solid var(--line)}
section.alt{background:var(--surface)}
.sec-head{display:flex;flex-direction:column;gap:var(--s-4);margin-bottom:var(--s-7)}
.sec-head p{max-width:62ch;color:var(--ink-2)}
@media (max-width:639px){.sec-head{margin-bottom:var(--s-6)}}

/* hero */
.hero{border-top:0;padding-top:clamp(48px,6vw,96px)}
.hero__grid{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-7);align-items:start}
@media (min-width:1024px){.hero__grid{grid-template-columns:minmax(0,6fr) minmax(0,5fr);gap:var(--s-8)}}
.hero__copy{display:flex;flex-direction:column;gap:var(--s-5)}
.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;margin:var(--s-3) 0 0;background:var(--line);
 border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden}
@media (min-width:640px){.facts{grid-template-columns:repeat(4,minmax(0,1fr))}}
.facts div{background:var(--bg);padding:14px 16px;display:flex;flex-direction:column-reverse;gap:2px}
.facts dt{font-size:13px;color:var(--muted);font-weight:500}
.facts dd{margin:0;font-size:28px;font-weight:500;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.facts .good dd{color:var(--std)}
[data-enter]>.wrap>*>*{animation:enter .7s var(--ease) both}
[data-enter]>.wrap>*:nth-child(2)>*{animation-delay:.15s}
[data-enter] .hero__copy>*:nth-child(2){animation-delay:.06s}
[data-enter] .hero__copy>*:nth-child(3){animation-delay:.12s}
[data-enter] .hero__copy>*:nth-child(4){animation-delay:.18s}
[data-enter] .hero__copy>*:nth-child(5){animation-delay:.24s}
@keyframes enter{from{opacity:0;transform:translateY(12px)}}

/* app frame (hero) */
.app-frame{background:var(--paper);border:1px solid var(--line-2);border-radius:var(--r-lg);overflow:hidden;
 box-shadow:0 30px 60px -40px rgba(6,82,92,.45)}
.app-frame__bar{display:flex;align-items:center;gap:var(--s-3);padding:10px 14px;border-bottom:1px solid var(--line);background:var(--surface);
 font-size:13px}
.app-frame__bar .dots{display:flex;gap:6px}.app-frame__bar .dots i{width:10px;height:10px;border-radius:50%;background:var(--line-2)}
.app-frame__bar .mono{font-size:13px;color:var(--muted)}
.app-frame__bar .status{margin-left:auto;font-weight:500;color:var(--ink-2);background:var(--bg);border:1px solid var(--line);
 padding:2px 8px;border-radius:var(--r-sm);white-space:nowrap}
.app-frame__body{padding:var(--s-5);display:flex;flex-direction:column;gap:var(--s-4)}
.app-frame__body .who{font-size:20px;font-weight:500;letter-spacing:-.01em}
.app-frame__body blockquote{margin:0;padding:10px 14px;border-left:2px solid var(--action);background:var(--surface);font-size:15px}
.app-frame__body blockquote small{display:block;margin-top:4px;color:var(--std);font-size:13px}
.kv2{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;font-size:15px;margin:0}
.kv2 dt{color:var(--muted);font-size:13px;font-weight:500;padding-top:2px}.kv2 dd{margin:0}

/* pipeline lanes */
.lanes{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-3);counter-reset:st}
@media (min-width:640px){.lanes{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (min-width:1024px){.lanes{grid-template-columns:repeat(4,minmax(0,1fr))}}
.lane{background:var(--paper);border:1px solid var(--line);border-radius:var(--r-lg);padding:var(--s-5);display:flex;flex-direction:column;
 gap:var(--s-2);position:relative;transition:transform .2s var(--ease),border-color .2s}
.lane:hover{transform:translateY(-2px);border-color:var(--line-2)}
.lane::before{counter-increment:st;content:counter(st,decimal-leading-zero);font-family:var(--font-mono);font-size:13px;color:var(--muted)}
.lane p{font-size:15px;color:var(--ink-2)}
.who-tag{position:absolute;top:var(--s-5);right:var(--s-5);font-size:13px;font-weight:500;padding:1px 8px;border-radius:var(--r-sm)}
.who-ai{background:var(--action);color:var(--action-ink)}
.who-code{background:var(--surface);color:var(--ink-2);border:1px solid var(--line)}
.who-people{background:var(--enh-bg);color:var(--enh)}
.principles{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-5);margin-top:var(--s-7)}
@media (min-width:768px){.principles{grid-template-columns:repeat(3,minmax(0,1fr))}}
.principles div{border-top:2px solid var(--action);padding-top:var(--s-4)}
.principles h3{font-size:18px;margin-bottom:6px}
.principles p{color:var(--ink-2)}

/* live runner */
.live{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-4)}
@media (min-width:1024px){.live{grid-template-columns:minmax(0,5fr) minmax(0,7fr);align-items:start}}
.panel-box{border:1px solid var(--line);border-radius:var(--r-lg);background:var(--paper);padding:var(--s-5);margin:0;min-width:0}
.panel-box legend{font-size:13px;font-weight:500;color:var(--muted);padding:0 6px;margin-left:-6px}
.seg{display:inline-flex;flex-wrap:wrap;gap:2px;padding:3px;background:var(--surface);border-radius:var(--r-md);margin:var(--s-2) 0 var(--s-4)}
.seg label{position:relative;cursor:pointer}
.seg input{position:absolute;opacity:0;pointer-events:none}
.seg span{display:flex;align-items:center;min-height:38px;padding:0 14px;border-radius:var(--r-sm);font-size:15px;font-weight:500;color:var(--ink-2);
 transition:background .2s,color .2s}
.seg input:checked+span{background:var(--paper);color:var(--ink);box-shadow:0 1px 2px rgba(6,82,92,.18)}
.seg input:focus-visible+span{outline:2px solid var(--action);outline-offset:1px}
.row2{display:grid;grid-template-columns:minmax(0,1fr);gap:0 var(--s-4)}
@media (min-width:640px){.row2{grid-template-columns:repeat(2,minmax(0,1fr))}}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:var(--s-4);min-width:0}
.field label{font-size:14px;font-weight:500}
.field small{font-size:13px;color:var(--muted)}
.field input,.field textarea{font:400 16px/1.5 var(--font-text);color:var(--ink);background:var(--bg);border:1px solid var(--line-2);
 border-radius:var(--r-sm);padding:11px 12px;min-height:48px;width:100%;transition:border-color .2s,box-shadow .2s}
#api-key,#model{font-family:var(--font-mono);font-size:15px}
.field input:focus,.field textarea:focus{outline:none;border-color:var(--action);box-shadow:0 0 0 3px color-mix(in srgb,var(--action) 22%,transparent)}
.field textarea{resize:vertical}
.help{display:flex;gap:10px;font-size:14px;line-height:1.5;color:var(--ink-2);background:var(--surface);border-radius:var(--r-md);padding:10px 12px}
.help svg{flex:none;width:18px;height:18px;fill:none;stroke:var(--std);stroke-width:2;margin-top:1px}
.help[hidden],[hidden]{display:none!important}
.pick-actions{display:flex;flex-wrap:wrap;gap:var(--s-2);margin-bottom:var(--s-3)}
.picks{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-2);max-height:420px;overflow:auto;padding:2px}
@media (min-width:640px) and (max-width:1023px){.picks{grid-template-columns:repeat(2,minmax(0,1fr))}}
.pick{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line);border-radius:var(--r-md);padding:10px 12px;cursor:pointer;
 font-size:15px;min-height:48px;transition:border-color .2s,background .2s}
.pick:hover{border-color:var(--line-2)}
.pick input{margin-top:3px;width:18px;height:18px;accent-color:var(--action);flex:none}
.pick:has(input:checked){border-color:var(--action);background:color-mix(in srgb,var(--action) 6%,transparent)}
.pick b{display:block;font:400 13px var(--font-mono);color:var(--muted)}
.pick small{display:block;color:var(--muted);font-size:13px}
.run-row{display:flex;flex-wrap:wrap;align-items:center;gap:var(--s-3);margin-top:var(--s-4)}
.form-error{color:var(--high);font-size:14px}
.console{border:1px solid var(--line);border-radius:var(--r-lg);background:var(--paper);min-height:360px;display:flex;flex-direction:column}
.console__head{display:flex;align-items:center;gap:var(--s-3);padding:12px 16px;border-bottom:1px solid var(--line);font-size:14px;font-weight:500}
.console__head .state{margin-left:auto;font-size:13px;color:var(--muted);font-weight:400}
.console__body{padding:var(--s-4) var(--s-5) var(--s-5)}
.empty{color:var(--muted);font-size:15px;padding:var(--s-6) 0;text-align:center}
.progress{height:4px;border-radius:2px;background:var(--surface);overflow:hidden;margin-bottom:var(--s-3)}
.progress div{height:100%;width:0;background:var(--action);transition:width .3s var(--ease)}
.log{list-style:none;margin:0;padding:0;font-size:14px;display:flex;flex-direction:column;gap:6px}
.log li{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.log .t{font-family:var(--font-mono);font-size:13px;color:var(--muted);min-width:36px}
.log .run::before{content:"";display:inline-block;width:10px;height:10px;border:2px solid var(--action);border-right-color:transparent;
 border-radius:50%;animation:spin .8s linear infinite;margin-right:6px;vertical-align:-1px}
@keyframes spin{to{transform:rotate(360deg)}}
.live-summary{display:flex;flex-wrap:wrap;gap:var(--s-2) var(--s-5);align-items:center;margin-top:var(--s-4);padding-top:var(--s-4);
 border-top:1px solid var(--line);font-size:14px}
.live-summary .btn{margin-left:auto;height:40px;font-size:15px;padding:0 16px}

/* chips, tabs, filters */
.chip{min-height:36px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--line-2);background:transparent;color:var(--ink-2);
 font:500 14px var(--font-text);cursor:pointer;transition:background .2s,color .2s,transform .15s}
.chip:hover{background:var(--surface)}.chip:active{transform:scale(.97)}
.chip.is-on,.chip[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip-end{margin-left:auto}
.tabs{display:flex;gap:var(--s-5);border-bottom:1px solid var(--line);margin-bottom:var(--s-5);overflow-x:auto}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;margin-bottom:-1px;padding:12px 0;font:500 16px var(--font-text);
 color:var(--muted);cursor:pointer;white-space:nowrap;min-height:48px}
.tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--action)}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);
 border-radius:var(--r-lg);overflow:hidden;margin-bottom:var(--s-5)}
@media (min-width:768px){.stats{grid-template-columns:repeat(5,minmax(0,1fr))}}
.stat{background:var(--paper);padding:14px 16px;display:flex;flex-direction:column;gap:4px}
@media (max-width:767px){.stat:last-child:nth-child(odd){grid-column:1/-1}}
.stat b{font-size:28px;font-weight:500;letter-spacing:-.02em;line-height:1.1}
.stat span{font-size:13px;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.filters{display:flex;flex-wrap:wrap;gap:var(--s-2);margin-bottom:var(--s-3)}

/* tables */
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--paper)}
.tbl,.b-tbl{width:100%;border-collapse:collapse;font-size:15px}
.tbl th,.tbl td,.b-tbl th,.b-tbl td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:middle}
.tbl tr:last-child td,.b-tbl tr:last-child td{border-bottom:0}
.tbl th,.b-tbl th{font-size:13px;color:var(--muted);font-weight:500;background:var(--surface);white-space:nowrap}
.clickable{min-width:880px}.clickable td:nth-child(2){min-width:180px}
.clickable tbody tr{cursor:pointer;transition:background .15s}
.clickable tbody tr:hover,.clickable tbody tr:focus-visible{background:var(--surface)}
.queue{color:var(--ink-2);min-width:200px}
tr[hidden]{display:none}
.hint{font-size:14px;color:var(--muted);margin-top:var(--s-2)}

/* pills */
.pill{display:inline-flex;align-items:center;gap:6px;padding:2px 9px;border-radius:var(--r-sm);font-size:13px;font-weight:500;white-space:nowrap;line-height:1.5}
.pill i{width:7px;height:7px;border-radius:50%;background:currentColor;flex:none}
.pill-sm{padding:1px 7px}
.pill-standard{color:var(--std);background:var(--std-bg)}
.pill-enhanced{color:var(--enh);background:var(--enh-bg)}
.pill-enhanced i{border-radius:0;width:0;height:0;background:none;border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:7px solid currentColor}
.pill-high{color:var(--high);background:var(--high-bg)}
.pill-high i{border-radius:1px;transform:rotate(45deg)}
.pill-failed{color:var(--muted);background:var(--surface)}

/* case cards (site_render.py) */
.cases{display:flex;flex-direction:column;gap:var(--s-2);margin-top:var(--s-5)}
.case{background:var(--paper);border:1px solid var(--line);border-radius:var(--r-lg);scroll-margin-top:calc(var(--nav) + 16px);
 transition:border-color .2s}
.case:hover{border-color:var(--line-2)}
.case[hidden]{display:none}
.case>summary{cursor:pointer;list-style:none;padding:14px 18px;display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;min-height:56px}
.case>summary::-webkit-details-marker{display:none}
.case>summary::after{content:"";width:8px;height:8px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);
 transform:rotate(45deg);margin-left:var(--s-2);transition:transform .2s}
.case[open]>summary::after{transform:rotate(-135deg)}
.case-id{font-family:var(--font-mono);font-size:13px;color:var(--muted)}
.case-name{font-weight:500}
.case-queue{margin-left:auto;font-size:14px;color:var(--muted)}
.raised{font-size:13px;font-weight:500;color:var(--enh);border:1px solid currentColor;border-radius:var(--r-sm);padding:0 6px}
.case-body{padding:var(--s-2) 18px 18px;border-top:1px solid var(--line)}
.headline{font-size:20px;font-weight:500;letter-spacing:-.01em;margin:var(--s-4) 0 var(--s-1)}
.tierline{display:flex;flex-wrap:wrap;gap:var(--s-3) var(--s-6);padding:12px 14px;margin:var(--s-4) 0 0;background:var(--surface);border-radius:var(--r-md)}
.tierline div{display:flex;flex-direction:column;gap:4px}
.lbl{font-size:13px;color:var(--muted);font-weight:500}
.cols{display:grid;grid-template-columns:minmax(0,1fr);gap:0 var(--s-7)}
@media (min-width:900px){.cols{grid-template-columns:repeat(2,minmax(0,1fr))}}
.cols p{margin:0 0 var(--s-2)}
.cols ul,.cols ol{margin:0;padding-left:20px}
.cols li{margin:4px 0}
h3.k{font-size:13px;font-weight:500;color:var(--muted);margin:var(--s-5) 0 6px;letter-spacing:0}
.flags li{margin:0 0 10px}
.flags q{display:block;color:var(--ink-2);margin:2px 0}
.tag{font-size:13px;color:var(--muted);background:var(--surface);padding:0 6px;border-radius:var(--r-sm)}
.source{margin-top:var(--s-4)}
.source>summary,.out>summary{cursor:pointer;font-size:15px;font-weight:500;color:var(--action);padding:8px 0;list-style:none;
 display:inline-flex;align-items:center;gap:8px;min-height:44px}
.source>summary::-webkit-details-marker,.out>summary::-webkit-details-marker{display:none}
.source>summary::before,.out>summary::before{content:"";width:7px;height:7px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;
 transform:rotate(-45deg);transition:transform .2s}
.source[open]>summary::before,.out[open]>summary::before{transform:rotate(45deg)}
.source p{background:var(--surface);border-radius:var(--r-md);padding:12px 14px;margin:6px 0 0}
mark{background:var(--mark);color:inherit;padding:0 2px;border-radius:2px}
.fine{font-size:13px;color:var(--muted);margin:var(--s-4) 0 0}

/* callouts */
.callout{border:1px solid var(--line);border-left:2px solid var(--action);background:var(--paper);border-radius:var(--r-md);padding:14px 16px;
 margin:var(--s-5) 0;font-size:15px;max-width:80ch}
.callout-warn{border-left-color:var(--enh)}
.callout ul{margin:6px 0;padding-left:20px}

/* evaluation */
.split{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-7)}
@media (min-width:1024px){.split{grid-template-columns:minmax(0,7fr) minmax(0,5fr)}}
.split h3{margin-bottom:var(--s-3)}
.split h3+.tablewrap+h3{margin-top:var(--s-6)}
.timeline{list-style:none;margin:0;padding:0;border-left:1px solid var(--line-2)}
.timeline li{position:relative;padding:0 0 var(--s-5) var(--s-5)}
.timeline li::before{content:"";position:absolute;left:-5px;top:7px;width:9px;height:9px;border-radius:50%;background:var(--bg);border:1px solid var(--line-2)}
.timeline li:last-child::before{background:var(--action);border-color:var(--action)}
.timeline b{display:block;font-family:var(--font-mono);font-size:13px;font-weight:400;color:var(--muted)}

/* board */
.b-group{margin:0 0 var(--s-5)}
.b-title{display:flex;align-items:center;gap:10px;font-weight:500;margin:0 0 var(--s-2)}
.b-title::before{content:"";width:4px;height:18px;border-radius:2px;background:var(--line-2)}
.b-g-high .b-title::before{background:var(--high)}.b-g-enhanced .b-title::before{background:var(--enh)}.b-g-standard .b-title::before{background:var(--std)}
.b-title .muted{font-weight:400;font-size:14px}
.b-tbl{min-width:1080px}
.b-tbl td{padding:9px 14px}
.b-item{font-weight:500;min-width:200px}
.b-status{display:inline-block;padding:3px 10px;border-radius:var(--r-sm);font-size:13px;font-weight:500;white-space:nowrap;color:#fff}
.b-high{background:#c2362b}.b-enhanced{background:#a86200}.b-standard{background:#1d7a4c}.b-review{background:#45707a}
.b-next{min-width:320px;font-size:14px;color:var(--ink-2)}
.clamp{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

/* cli */
.steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr);gap:var(--s-3);counter-reset:cli}
@media (min-width:1024px){.steps{grid-template-columns:repeat(2,minmax(0,1fr))}}
.step{background:var(--paper);border:1px solid var(--line);border-radius:var(--r-lg);padding:var(--s-5);display:flex;flex-direction:column;gap:var(--s-3);min-width:0}
.step h3::before{counter-increment:cli;content:counter(cli) ". ";color:var(--muted)}
.step>p{color:var(--ink-2)}
.cmd{display:flex;align-items:center;gap:var(--s-2);background:var(--code-bg);color:var(--code-ink);border-radius:var(--r-md);padding:4px 4px 4px 14px;min-width:0}
.cmd code{font:400 14px var(--font-mono);flex:1;min-width:0;overflow-x:auto;white-space:nowrap;padding:10px 0;background:none;color:inherit}
.cmd code::before{content:"$ ";color:var(--code-dim)}
.copy{flex:none;display:inline-flex;align-items:center;gap:6px;height:40px;padding:0 12px;border-radius:var(--r-sm);border:0;cursor:pointer;
 background:rgba(255,255,255,.08);color:var(--code-ink);font:500 14px var(--font-text);transition:background .2s,transform .15s}
.copy:hover{background:rgba(255,255,255,.16)}.copy:active{transform:scale(.96)}
.copy svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:2}
pre.term{background:var(--code-bg);color:var(--code-ink);font:400 13px/1.6 var(--font-mono);padding:14px 16px;border-radius:var(--r-md);
 overflow:auto;max-height:420px;margin:6px 0 0;white-space:pre}
.say{display:none;border-left:2px solid var(--enh);padding:6px 0 6px 12px;font-size:15px;color:var(--ink-2)}
.notes-on .say{display:block}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-size:14px;margin:6px 0 0}
.kv dt{color:var(--muted)}.kv dd{margin:0;font-family:var(--font-mono);font-size:13px;word-break:break-word}
.testlist{columns:1;font-size:14px;margin:6px 0 0;padding:0;list-style:none}
@media (min-width:640px){.testlist{columns:2}}
.testlist li{break-inside:avoid;padding:2px 0}

/* phones: tables keep the columns that matter, the cards hold the rest */
.brand{min-height:44px}
@media (max-width:639px){
 .nav__in{gap:var(--s-3)}
 .brand{font-size:16px;gap:8px}
 .seg span{min-height:44px}
 .chip{min-height:44px}
 .clickable,.b-tbl{min-width:0}
 .clickable th:nth-child(n+3):not(:nth-child(5)),.clickable td:nth-child(n+3):not(:nth-child(5)){display:none}
 .clickable td:nth-child(2){min-width:0}
 .b-tbl th:nth-child(n+4),.b-tbl td:nth-child(n+4){display:none}
 .b-item{min-width:0}
 .eval-tbl th:nth-child(2),.eval-tbl td:nth-child(2),.eval-tbl th:nth-child(5),.eval-tbl td:nth-child(5){display:none}
 .tbl th,.tbl td,.b-tbl th,.b-tbl td{padding:10px 12px}
 .tbl .mono,.b-tbl .mono{font-size:13px}
 .case-queue{margin-left:0;flex-basis:100%}
}

/* footer */
footer{border-top:1px solid var(--line);padding:var(--s-7) 0;font-size:14px;color:var(--muted)}
.foot{display:flex;flex-wrap:wrap;gap:var(--s-4) var(--s-7);align-items:flex-start;justify-content:space-between}
.foot p{max-width:62ch;margin:0 0 6px}

@media (prefers-reduced-motion:reduce){
 *,*::before,*::after{animation:none!important;transition:none!important}
}
"""

JS = r"""
(function(){
 'use strict';
 var root=document.documentElement,THEME='crestview-theme';
 function setTheme(t){if(t)root.setAttribute('data-theme',t);else root.removeAttribute('data-theme')}
 try{var saved=localStorage.getItem(THEME);if(saved)setTheme(saved)}catch(e){}
 document.getElementById('theme').addEventListener('click',function(){
  var dark=root.getAttribute('data-theme')==='dark'||(!root.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches);
  var next=dark?'light':'dark';setTheme(next);try{localStorage.setItem(THEME,next)}catch(e){}
 });

 /* menu (under 1024px) */
 var nav=document.getElementById('nav'),menu=document.getElementById('menu');
 function setMenu(open){nav.classList.toggle('is-open',open);menu.setAttribute('aria-expanded',open?'true':'false');
  menu.setAttribute('aria-label',open?'Close menu':'Open menu');document.body.style.overflow=open?'hidden':''}
 menu.addEventListener('click',function(){setMenu(!nav.classList.contains('is-open'))});
 document.querySelectorAll('#nav-links a').forEach(function(a){a.addEventListener('click',function(){setMenu(false)})});
 document.addEventListener('keydown',function(e){if(e.key==='Escape'&&nav.classList.contains('is-open')){setMenu(false);menu.focus()}});
 matchMedia('(min-width: 1024px)').addEventListener('change',function(m){if(m.matches)setMenu(false)});

 /* current section in the nav */
 var links=[].slice.call(document.querySelectorAll('#nav-links a')),secs=links.map(function(a){return document.querySelector(a.getAttribute('href'))});
 if('IntersectionObserver' in window){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){var i=secs.indexOf(e.target);
   links.forEach(function(l,j){if(i===j)l.setAttribute('aria-current','true');else l.removeAttribute('aria-current')})}})},{rootMargin:'-45% 0px -50% 0px'});
  secs.forEach(function(s){if(s)io.observe(s)});
 }

 /* copy buttons */
 document.querySelectorAll('.copy').forEach(function(b){b.addEventListener('click',function(){
  var label=b.querySelector('span'),t=b.getAttribute('data-copy');
  function done(ok){label.textContent=ok?'Copied':'Select it';setTimeout(function(){label.textContent='Copy'},1600)}
  if(navigator.clipboard)navigator.clipboard.writeText(t).then(function(){done(true)},function(){done(false)});else done(false);
 })});

 /* presenter notes */
 var notes=document.getElementById('notes');
 if(notes)notes.addEventListener('click',function(){var on=document.body.classList.toggle('notes-on');notes.setAttribute('aria-pressed',on?'true':'false')});

 /* results tabs, filters, rows */
 var tabs=[].slice.call(document.querySelectorAll('.tab'));
 function select(t){tabs.forEach(function(o){var on=o===t;o.setAttribute('aria-selected',on?'true':'false');o.tabIndex=on?0:-1;
  document.getElementById(o.getAttribute('aria-controls')).hidden=!on})}
 tabs.forEach(function(t,i){t.addEventListener('click',function(){select(t)});
  t.addEventListener('keydown',function(e){var d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0;if(d){var n=tabs[(i+d+tabs.length)%tabs.length];select(n);n.focus()}})});
 document.querySelectorAll('.panel').forEach(function(p){
  var chips=p.querySelectorAll('[data-filter]');
  chips.forEach(function(c){c.addEventListener('click',function(){
   var f=c.getAttribute('data-filter');
   chips.forEach(function(o){o.setAttribute('aria-pressed',o===c?'true':'false')});
   p.querySelectorAll('tbody tr, .case').forEach(function(el){el.hidden=!(f==='all'||el.getAttribute('data-tier')===f)});
  })});
  var ex=p.querySelector('[data-expand]');
  ex.addEventListener('click',function(){var open=ex.getAttribute('aria-pressed')!=='true';
   p.querySelectorAll('.case:not([hidden])').forEach(function(c){c.open=open});
   ex.setAttribute('aria-pressed',open?'true':'false');ex.textContent=open?'Collapse all':'Expand all'});
  p.querySelectorAll('tbody tr[data-target]').forEach(function(r){
   function go(){var c=document.getElementById(r.getAttribute('data-target'));if(c){c.open=true;c.scrollIntoView({block:'start'});c.querySelector('summary').focus({preventScroll:true})}}
   r.addEventListener('click',go);r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}});
  });
 });

 /* live run: the real pipeline in a Pyodide worker */
 var form=document.getElementById('live-form');
 if(!form)return;
 var MODELS={openai:'gpt-4.1-mini',anthropic:'claude-sonnet-5-5',mock:'mock'};
 var keyIn=document.getElementById('api-key'),modelIn=document.getElementById('model'),
     runBtn=document.getElementById('run-btn'),stopBtn=document.getElementById('stop-btn'),
     err=document.getElementById('form-error'),empty=document.getElementById('console-empty'),state=document.getElementById('console-state'),
     out=document.getElementById('live-out'),log=document.getElementById('log'),bar=document.getElementById('bar'),
     sum=document.getElementById('live-summary'),cards=document.getElementById('live-cards');
 var worker=null,results=[],audit='',t0=0,current=null,lastLine=null;
 function val(n){var c=form.querySelector('input[name="'+n+'"]:checked');return c?c.value:''}
 function syncProvider(){
  var p=val('provider'),mock=p==='mock';
  document.getElementById('key-row').hidden=mock;document.getElementById('key-help').hidden=mock;
  document.getElementById('mock-help').hidden=!mock;
  if(!mock&&(modelIn.value===''||Object.values(MODELS).indexOf(modelIn.value)>=0))modelIn.value=MODELS[p];
  keyIn.placeholder=p==='anthropic'?'sk-ant-...':'sk-...';
 }
 form.querySelectorAll('input[name="provider"]').forEach(function(r){r.addEventListener('change',syncProvider)});
 form.querySelectorAll('input[name="source"]').forEach(function(r){r.addEventListener('change',function(){
  var c=val('source')==='custom';document.getElementById('src-samples').hidden=c;document.getElementById('src-custom').hidden=!c})});
 form.querySelectorAll('[data-pick]').forEach(function(b){b.addEventListener('click',function(){
  var mode=b.getAttribute('data-pick'),demo=['APP-2026-0301','APP-2026-0303','APP-2026-0311'];
  form.querySelectorAll('input[name="sample"]').forEach(function(c){c.checked=mode==='all'||(mode==='demo'&&demo.indexOf(c.value)>=0)});
 })});
 function line(html,cls){
  var li=document.createElement('li'),t=document.createElement('span'),m=document.createElement('span');
  t.className='t';t.textContent=t0?((performance.now()-t0)/1000).toFixed(0)+'s':'';m.innerHTML=html;
  if(cls)m.className=cls;li.appendChild(t);li.appendChild(m);log.appendChild(li);return m;
 }
 function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML}
 function pill(t){return t?'<span class="pill pill-sm pill-'+t+'"><i></i>'+t.charAt(0).toUpperCase()+t.slice(1)+'</span>':'<span class="pill pill-failed">Failed</span>'}
 function busy(on){runBtn.disabled=on;stopBtn.hidden=!on;runBtn.querySelector('span').textContent=on?'Running':'Run the pipeline';
  state.textContent=on?'Running':'Finished'}
 function items(){
  if(val('source')==='custom'){
   var f={client_name:'c-name',client_type:'c-type',estimated_aum:'c-aum',requested_services:'c-services',description:'c-desc'},input={};
   for(var k in f)input[k]=document.getElementById(f[k]).value.trim();
   return [{label:'CUSTOM-001 '+esc(input.client_name||'(no name)'),input:input}];
  }
  return [].map.call(form.querySelectorAll('input[name="sample"]:checked'),function(c){
   return {label:c.value+' '+esc(c.parentNode.querySelector('span').childNodes[1].textContent.trim()),input:{sample_id:c.value}}});
 }
 function onMsg(e){
  var m=e.data;
  if(m.type==='status'){if(lastLine)lastLine.className='';lastLine=line(esc(m.text),'run')}
  else if(m.type==='fatal'){if(lastLine)lastLine.className='';line('<span class="warn">'+esc(m.text)+'</span>');busy(false);state.textContent='Stopped';if(worker){worker.terminate();worker=null}}
  else if(m.type==='start'){if(lastLine){lastLine.className='';lastLine.textContent='Python runtime ready'}
   line('Run <code>'+esc(m.runId)+'</code>, '+m.n+' application'+(m.n>1?'s':'')+', '+esc(current.cfg.provider)+':'+esc(current.cfg.model||'mock')+', prompts v4')}
  else if(m.type==='progress'){bar.style.width=(100*m.i/current.items.length)+'%';lastLine=line(m.label+': risk pre-screen, then onboarding brief','run')}
  else if(m.type==='result'){
   var o=m.out;bar.style.width=(100*(m.i+1)/current.items.length)+'%';if(lastLine)lastLine.className='';
   if(o.error&&!o.html){lastLine.innerHTML=m.label+': <span class="warn">'+esc(o.error)+'</span>'}
   else{
    var raised=o.result&&o.result.final_risk_tier&&o.result.final_risk_tier!==o.result.model_risk_tier;
    lastLine.innerHTML=m.label+': '+pill(o.tier)+(raised?' <span class="raised">raised from '+esc(o.result.model_risk_tier)+'</span>':'')+(o.error?' <span class="warn">'+esc(o.error)+'</span>':'');
    cards.insertAdjacentHTML('beforeend',o.html);results.push(o.result);
    if(results.length===1){var c=cards.lastElementChild;if(c)c.open=true}
   }
  }
  else if(m.type==='done'){
   bar.style.width='100%';audit=m.audit;busy(false);
   var ok=results.filter(function(r){return r.status==='processed'}).length;
   sum.hidden=false;
   sum.innerHTML='<b>'+ok+' of '+current.items.length+' processed</b><span>'+m.seconds.toFixed(0)+' s</span><span>'+m.tokens_in.toLocaleString()+' tokens in, '+m.tokens_out.toLocaleString()+' out</span>'+
    (results.length?'<button type="button" class="btn btn--secondary" id="dl">Download the results</button>':'');
   var dl=document.getElementById('dl');
   if(dl)dl.addEventListener('click',function(){
    [['results.json',JSON.stringify(results,null,2),'application/json'],['audit_log.jsonl',audit,'application/x-ndjson']].forEach(function(f){
     var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([f[1]],{type:f[2]}));a.download=f[0];document.body.appendChild(a);a.click();a.remove()});
   });
  }
 }
 form.addEventListener('submit',function(ev){
  ev.preventDefault();err.textContent='';
  var p=val('provider'),cfg={provider:p,model:p==='mock'?'':modelIn.value.trim(),key:p==='mock'?'':keyIn.value.trim()};
  if(p!=='mock'&&!cfg.key){err.textContent='Paste an API key, or pick "No key".';keyIn.setAttribute('aria-invalid','true');keyIn.focus();return}
  keyIn.removeAttribute('aria-invalid');
  var list=items();
  if(!list.length){err.textContent='Pick at least one application.';return}
  if(val('source')==='custom'&&document.getElementById('c-desc').value.trim().length<20){err.textContent='Write at least 20 characters of application text.';document.getElementById('c-desc').focus();return}
  current={cfg:cfg,items:list};results=[];audit='';log.innerHTML='';cards.innerHTML='';sum.hidden=true;bar.style.width='0';
  empty.hidden=true;out.hidden=false;t0=performance.now();lastLine=null;busy(true);
  if(!worker){worker=new Worker('runner/worker.js');worker.onmessage=onMsg;worker.onerror=function(e){onMsg({data:{type:'fatal',text:e.message||'worker error'}})}}
  worker.postMessage({type:'run',cfg:cfg,items:list});
  if(matchMedia('(max-width: 1023px)').matches)document.getElementById('console').scrollIntoView({block:'start'});
 });
 stopBtn.addEventListener('click',function(){
  if(worker){worker.terminate();worker=null}
  if(lastLine)lastLine.className='';line('<span class="warn">Stopped. Results so far stay here; the next run reloads Python.</span>');busy(false);state.textContent='Stopped';
 });
 syncProvider();
})();
"""

ICON = ("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E"
        "%3Crect%20width='32'%20height='32'%20rx='6'%20fill='%2306525c'/%3E"
        "%3Cpath%20d='M16%206l8%204v5c0%205-3.4%209.2-8%2010-4.6-.8-8-5-8-10v-5z'%20fill='none'%20stroke='%23f7f9f8'%20stroke-width='2.2'/%3E"
        "%3Cpath%20d='M12.5%2015.5l2.5%202.5%204.5-4.5'%20fill='none'%20stroke='%23f7f9f8'%20stroke-width='2.2'/%3E%3C/svg%3E")

PAGE = """<!doctype html>
<html lang="en" data-radius="sharp">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Crestview AI intake: risk pre-screen for client onboarding</title>
<meta name="description" content="A working proof of concept that pre-screens wealth-management client applications with AI, applies the escalation policy in code and routes every case to a person on monday.com.">
<meta name="theme-color" content="#f7f9f8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#061b1e" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:title" content="Crestview AI intake: risk pre-screen for client onboarding">
<meta property="og:description" content="Run the real pipeline in your browser, read every pre-screen with its quoted evidence, and see how it scores against hand-labelled tiers.">
<meta name="twitter:card" content="summary">
<link rel="icon" href="{icon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Host+Grotesk:wght@400..500&family=JetBrains+Mono:wght@400..500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<!-- Deal (design-taste-frontend): kind software; palette teal-on-paper; type host (Host Grotesk + JetBrains Mono); radius sharp; buttons solid; no photographs, effects or scroll moments: this is a working tool page. -->
<header class="nav" id="nav">
 <div class="wrap nav__in">
  <a class="skip-link" href="#top">Skip to content</a>
  <a class="brand" href="#top"><span class="mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3l7 3.5v4.5c0 4.4-3 8.1-7 9-4-.9-7-4.6-7-9V6.5z"/><path d="M9 12l2.2 2.2L15.5 10"/></svg></span><span>Crestview AI intake</span></a>
  <nav class="nav__links" id="nav-links" aria-label="Sections">
   <a href="#how">Pipeline</a><a href="#live">Live run</a><a href="#results">Results</a><a href="#evaluation">Evaluation</a><a href="#board">Board</a><a href="#cli">CLI</a>
  </nav>
  <div class="nav__end">
   <button class="iconbtn" id="theme" type="button" aria-label="Switch between light and dark theme"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 13.4A8 8 0 1 1 10.6 4a6.3 6.3 0 0 0 9.4 9.4z"/></svg></button>
   <a class="btn btn--primary nav__cta" href="#live">Run the pipeline</a>
   <button class="iconbtn nav__toggle" id="menu" type="button" aria-expanded="false" aria-controls="nav-links" aria-label="Open menu"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
  </div>
 </div>
</header>

<main id="top">
<section class="hero" data-enter aria-labelledby="hero-title">
 <div class="wrap hero__grid">
  <div class="hero__copy">
   <p class="label">Proof of concept for Crestview Capital Group on monday.com</p>
   <h1 id="hero-title">AI risk pre&#8209;screen for wealth&#8209;client onboarding</h1>
   <p class="lead">An AI model reads each application, quotes its evidence and drafts the onboarding brief. Code applies the escalation policy and picks the compliance queue. A person makes every decision.</p>
   <div class="btn-row">
    <a class="btn btn--primary" href="#live">Run the pipeline <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>
    <a class="btn btn--secondary" href="#results">See the results</a>
   </div>
   <dl class="facts">
    <div class="good"><dt>missed high-risk cases</dt><dd>{missed}</dd></div>
    <div><dt>sample set within the label</dt><dd>{g_ok}/{g_total}</dd></div>
    <div><dt>edge cases, incl. injection</dt><dd>{e_ok}/{e_total}</dd></div>
    <div><dt>for {n_golden} applications</dt><dd>~{seconds} s</dd></div>
   </dl>
  </div>
  <div class="hero__visual">{hero_case}</div>
 </div>
</section>

<section id="how" class="alt" aria-labelledby="how-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="how-title">How the pipeline sets a risk tier</h2>
  <p>Two model calls per application, wrapped in code that owns the policy, the routing and the checks.</p></div>
  <ol class="lanes">
   <li class="lane"><span class="who-tag who-code">Code</span><h3>Validates the row</h3><p>Reads &ldquo;$1,200,000&rdquo;, &ldquo;35M&rdquo; and mixed dates. Bad rows are reported, never fatal.</p></li>
   <li class="lane"><span class="who-tag who-code">Code</span><h3>Sets a rules floor</h3><p>Shell companies, nominee directors, PEPs and injected instructions set a minimum tier.</p></li>
   <li class="lane"><span class="who-tag who-ai">AI</span><h3>Quotes the evidence</h3><p>Fills a fact checklist and lists each red flag with a verbatim quote.</p></li>
   <li class="lane"><span class="who-tag who-code">Code</span><h3>Applies the policy</h3><p>Final tier is the highest of rules, policy and model. Low confidence moves it up.</p></li>
   <li class="lane"><span class="who-tag who-code">Code</span><h3>Picks the queue</h3><p>A fixed map from the final tier chooses the compliance queue, never the model.</p></li>
   <li class="lane"><span class="who-tag who-ai">AI</span><h3>Drafts the brief</h3><p>Client profile, risk note and owner-tagged next steps, written from the final tier.</p></li>
   <li class="lane"><span class="who-tag who-code">Code</span><h3>Checks the brief</h3><p>The first step must go to compliance. &ldquo;Approved&rdquo; or &ldquo;cleared&rdquo; is flagged.</p></li>
   <li class="lane"><span class="who-tag who-people">People</span><h3>Decides on the board</h3><p>One monday.com item per client, grouped by tier, waiting for a named reviewer.</p></li>
  </ol>
  <div class="principles">
   <div><h3>AI can raise a tier, never clear one</h3><p>Rules and policy set floors the model cannot go below. Every record waits for human review.</p></div>
   <div><h3>Every flag carries its quote</h3><p>Quotes are checked against the application, and every tier change records its reason.</p></div>
   <div><h3>Application text is data</h3><p>An instruction hidden in an application becomes a red flag, not a command.</p></div>
  </div>
 </div>
</section>

<section id="live" aria-labelledby="live-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="live-title">Live run in your browser</h2>
  <p>The same <code>pipeline.py</code>, rules and v4 prompts run as Python in this page. Only the model call differs: your browser sends it straight to the provider.</p></div>
  <div class="live">
   <form id="live-form" novalidate>
    <fieldset class="panel-box"><legend>Model</legend>
     <div class="seg" role="radiogroup" aria-label="Model provider">
      <label><input type="radio" name="provider" value="openai" checked><span>OpenAI</span></label>
      <label><input type="radio" name="provider" value="anthropic"><span>Anthropic</span></label>
      <label><input type="radio" name="provider" value="mock"><span>No key</span></label>
     </div>
     <div class="row2" id="key-row">
      <div class="field"><label for="api-key">API key</label>
       <input id="api-key" name="api-key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-..." aria-describedby="key-help form-error"></div>
      <div class="field"><label for="model">Model</label>
       <input id="model" name="model" type="text" autocomplete="off" spellcheck="false" value="gpt-4.1-mini"></div>
     </div>
     <p class="help" id="key-help"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
     <span>The key stays in this tab and goes only to the provider you pick. Nothing is stored. Use a key with a spending limit; with gpt-4.1-mini all 15 applications cost a few cents.</span></p>
     <p class="help" id="mock-help" hidden><span>No model is called. Tiers come from the deterministic rules alone, so you can watch the plumbing. This is not AI output.</span></p>
    </fieldset>
    <fieldset class="panel-box" style="margin-top:12px"><legend>Applications</legend>
     <div class="seg" role="radiogroup" aria-label="Application source">
      <label><input type="radio" name="source" value="samples" checked><span>Sample set</span></label>
      <label><input type="radio" name="source" value="custom"><span>Your own</span></label>
     </div>
     <div id="src-samples">
      <div class="pick-actions"><button type="button" class="chip" data-pick="demo">Pick 3 demo cases</button><button type="button" class="chip" data-pick="all">Pick all 15</button><button type="button" class="chip" data-pick="none">Clear</button></div>
      <div class="picks">{live_samples}</div>
     </div>
     <div id="src-custom" hidden>
      <div class="row2">
       <div class="field"><label for="c-name">Client name</label><input id="c-name" name="c-name" value="Northgate Holdings Ltd"></div>
       <div class="field"><label for="c-type">Client type</label><input id="c-type" name="c-type" value="Corporate"></div>
       <div class="field"><label for="c-aum">Estimated AUM</label><input id="c-aum" name="c-aum" value="$60M" aria-describedby="aum-help"><small id="aum-help">60000000, $60,000,000 or 60M</small></div>
       <div class="field"><label for="c-services">Requested services</label><input id="c-services" name="c-services" value="Discretionary portfolio management"></div>
      </div>
      <div class="field"><label for="c-desc">Application text</label>
       <textarea id="c-desc" name="c-desc" rows="6">Holding company incorporated in the British Virgin Islands in 2025. Ownership is held through two nominee directors; the client says the ultimate beneficial owner prefers to remain private. Funds of $60M will come from the sale of a trading business, documents to follow. The client wants the account open by Friday.</textarea></div>
     </div>
    </fieldset>
    <div class="run-row">
     <button type="submit" class="btn btn--primary" id="run-btn"><span>Run the pipeline</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
     <button type="button" class="btn btn--secondary" id="stop-btn" hidden>Stop the run</button>
     <p class="form-error" id="form-error" role="alert"></p>
    </div>
   </form>
   <div class="console" id="console" role="region" aria-labelledby="console-title">
    <div class="console__head"><span id="console-title">Run output</span><span class="state" id="console-state">Idle</span></div>
    <div class="console__body">
     <p class="empty" id="console-empty">Pick a model and applications, then run. Python loads in about 10 seconds the first time; each application takes 5 to 10 seconds.</p>
     <div id="live-out" hidden>
      <div class="progress" aria-hidden="true"><div id="bar"></div></div>
      <ol class="log" id="log" aria-live="polite"></ol>
      <div class="live-summary" id="live-summary" hidden></div>
      <div class="cases" id="live-cards"></div>
     </div>
    </div>
   </div>
  </div>
 </div>
</section>

<section id="results" class="alt" aria-labelledby="results-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="results-title">Pre-screen results from the last run</h2>
  <p>Every card is an AI pre-screen waiting for human review, never a compliance decision. Open one to read its reasoning and quoted evidence.</p></div>
  <div class="tabs" role="tablist" aria-label="Result sets">
   <button class="tab" role="tab" id="tab-golden" aria-controls="panel-golden" aria-selected="true" tabindex="0">Sample applications ({n_golden})</button>
   <button class="tab" role="tab" id="tab-edge" aria-controls="panel-edge" aria-selected="false" tabindex="-1">Edge cases ({n_edge})</button>
  </div>
  {panel_golden}
  {panel_edge}
 </div>
</section>

<section id="evaluation" aria-labelledby="eval-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="eval-title">Accuracy against hand-labelled tiers</h2>
  <p>Each application has an acceptable tier range. A miss means a high-risk client placed lower; that number must stay at 0.</p></div>
  <div class="stats" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr))">
   <div class="stat"><b class="num ok">{missed}</b><span>missed high-risk</span></div>
   <div class="stat"><b class="num">{g_ok}/{g_total}</b><span>sample set (model alone {g_model}/{g_total})</span></div>
   <div class="stat"><b class="num">{e_ok}/{e_total}</b><span>edge set (model alone {e_model}/{e_total})</span></div>
   <div class="stat"><b class="num">{over}</b><span>over-escalated, the safe error</span></div>
  </div>
  {over_note}
  <div class="split">
   <div><h3>Sample set</h3>{g_table}<h3>Edge cases</h3>{e_table}</div>
   <div><h3>Prompt versions</h3>
    <ol class="timeline">
     <li><b>v1</b>Baseline. Eastbridge caught only by the rules floor; high-risk cases sent to the wrong queue.</li>
     <li><b>v2</b>Application text treated as data, routing set by code. Still missed the prompt-injection case.</li>
     <li><b>v3</b>Escalation policy moved from the prompt into code. Injection caught; &ldquo;pressure&rdquo; read too broadly.</li>
     <li><b>v4, current</b>&ldquo;Pressure&rdquo; narrowed; a pending board resolution counts as missing information.</li>
    </ol>
    <p class="callout">The model reads and quotes well but applies multi-condition rules unreliably, and its tier can change between runs at temperature 0. So the model extracts facts and code applies the policy.</p>
   </div>
  </div>
 </div>
</section>

<section id="board" class="alt" aria-labelledby="board-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="board-title">The monday.com board after a run</h2>
  <p>One group per tier, one item per client, 12 columns, and the full reasoning posted as an item update. Built from the same data the dry run sends.</p></div>
  {board}
  <p class="callout">Writes are idempotent: each one first finds the item by Application ID, then updates or creates it. The pipeline only ever writes &ldquo;Awaiting human review&rdquo;.</p>
  <details class="out"><summary>Show the dry-run log ({n_dry} GraphQL calls, nothing sent)</summary><pre class="term">{dry}</pre></details>
 </div>
</section>

<section id="cli" aria-labelledby="cli-title">
 <div class="wrap">
  <div class="sec-head"><h2 id="cli-title">Command-line demo in four steps</h2>
  <p>Run these from the project folder with an <code>OPENAI_API_KEY</code> set. Each step keeps the output of the last real run as a fallback.</p>
  <div><button type="button" class="chip" id="notes" aria-pressed="false">Show presenter notes</button></div></div>
  <ol class="steps">
   <li class="step"><h3>Run the pipeline</h3>
    <p>Both AI stages with guardrails for {n_golden} applications, then every monday.com request printed instead of sent.</p>
    {cmd_pipeline}
    <p class="say">&ldquo;Two model calls per client, four clients at a time. Re-running never duplicates an item: every write looks it up by Application ID first.&rdquo;</p>
    <details class="out"><summary>Show the last run's metadata</summary>
     <dl class="kv"><dt>Run</dt><dd>{run_id} ({run_date})</dd><dt>Model</dt><dd>{provider}:{model}</dd>
     <dt>Prompts</dt><dd>{prompts}</dd><dt>Model calls</dt><dd>{calls} ({retries} retried)</dd>
     <dt>Tokens</dt><dd>{tokens_in} in, {tokens_out} out</dd><dt>Wall time</dt><dd>~{seconds} s, 4 workers</dd></dl></details>
   </li>
   <li class="step"><h3>Score it against the labels</h3>
    <p>Compares each final tier with its labelled range and exits with an error on any missed high-risk case, so it can gate CI.</p>
    {cmd_eval}
    <p class="say">&ldquo;Over-escalation costs reviewer time. Under-escalation is the failure we cannot accept, so it fails the build.&rdquo;</p>
    <details class="out"><summary>Show the output</summary><pre class="term">{g_eval_text}</pre></details>
   </li>
   <li class="step"><h3>Open one case in the report</h3>
    <p>Each card shows the reasoning, the quoted evidence, every guardrail action and the onboarding brief.</p>
    {cmd_one}
    <p class="say">{say_case}</p>
   </li>
   <li class="step"><h3>Run the tests</h3>
    <p>{n_tests} offline tests with a mock model: messy rows, rules, policy, guardrails, brief checks, retries and the dry run.</p>
    {cmd_test}
    <details class="out"><summary>Show the tests ({test_tail})</summary><ul class="testlist">{test_list}</ul></details>
   </li>
  </ol>
 </div>
</section>
</main>

<footer>
 <div class="wrap foot">
  <div><p><b>Crestview AI intake</b>, a proof of concept for the monday.com Forward Deployed Engineer exercise.</p>
  <p>Crestview Capital Group is fictional and every application is synthetic sample data. Built from the repository's own outputs on {built}.</p></div>
  <p><a href="{repo}">Read the source on GitHub</a></p>
 </div>
</footer>
<script>{js}</script>
</body>
</html>
"""
