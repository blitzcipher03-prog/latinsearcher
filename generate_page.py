# -*- coding: utf-8 -*-
"""Regenerate blank-web/index.html from wheelock.txt (all page features)."""
import json
import re

DATA = r'C:\Users\blitz\OneDrive\Documents\wheelock.txt'
OUT = r'C:\Users\blitz\Documents\blank-web\index.html'

GEND = {'m': 'm.', 'f': 'f.', 'n': 'n.'}
POS = {'Verb': 'v.', 'Noun': 'n.', 'Adjective': 'adj.', 'Adverb': 'adv.',
       'Pronoun': 'pron.', 'Conjunction': 'conj.', 'Preposition': 'prep.',
       'Interjection': 'interj.'}


def decl_info(t):
    t = t or ''
    if 'Irregular' in t:
        return 'irr.'
    if 'Deponent' in t:
        return 'dep.'
    if 'Impersonal' in t:
        return 'imp.'
    m = re.search(r'((?:1st and 2nd)|[1-5](?:st|nd|rd|th)) (Declension|Conjugation)', t)
    if m:
        base = m.group(1).replace('1st and 2nd', '1st/2nd')
        suffix = 'decl.' if 'Declension' in m.group(0) else 'conj.'
        return base + ' ' + suffix + (' (-iō)' if '-iō' in t else '')
    return ''


PAT = re.compile(r'\((m|f|n)(?:/(?:m|f|n))?\*?\)')


def build_entries(rows):
    entries = []
    for e in rows:
        g = PAT.findall(e['latin'])
        cleaned = PAT.sub('', e['latin']).strip().rstrip(',').strip()
        gender = 'm./f.' if {'m', 'f'} <= set(g) else (GEND.get(g[0], '') if g else '')
        pos_key = (e['part_of_speech'] or '').split(':')[0].strip()
        pa = POS.get(pos_key, '')
        if 'encl' in (e['part_of_speech'] or '').lower():
            pa = 'conj. (encl.)'
        entries.append({
            'latin': cleaned, 'gender': gender, 'english': e['english'],
            'pos': pa, 'decl': decl_info(e['part_of_speech']),
            'ch': e['chapter'] or 0,
            'chapter': f"ch {e['chapter']}" if e['chapter'] is not None else '',
        })
    return entries


def esc(o):
    return json.dumps(o, ensure_ascii=False).replace('</', '<\\/')


JS = r'''
var input=document.getElementById('search');
var posSel=document.getElementById('pos');
var declSel=document.getElementById('decl');
var declWrap=document.getElementById('declWrap');
var chapIn=document.getElementById('chapter');
var list=document.getElementById('list');
var FULLPOS={'v.':'verb','n.':'noun','adj.':'adjective','adv.':'adverb','pron.':'pronoun','conj.':'conjunction','conj. (encl.)':'conjunction (enclitic)','prep.':'preposition','interj.':'interjection'};

function nrm(s){ return s.toLowerCase().replace(/ā/g,'a').replace(/ē/g,'e').replace(/ī/g,'i').replace(/ō/g,'o').replace(/ū/g,'u').replace(/ȳ/g,'y'); }
function tokensIn(hay,q){ var h=nrm(hay); return nrm(q).split(/\s+/).filter(Boolean).every(function(t){return h.indexOf(t)!==-1;}); }
function latinTokens(s){ return nrm(s).split(/[^a-z]+/).filter(function(x){return x;}); }
function exactLatin(e,q){ var tl=latinTokens(e.latin); return q.toLowerCase().split(/\s+/).filter(Boolean).every(function(t){return tl.indexOf(t)!==-1;}); }
function fillPairs(sel,pairs){ sel.innerHTML='<option value="">All</option>'+pairs.map(function(p){return '<option value="'+p[0]+'">'+p[1]+'</option>';}).join(''); }
function fill(sel,opts){ fillPairs(sel,opts.map(function(o){return [o,o];})); }
function declOptions(pos){
  var m=[];
  ENTRIES.forEach(function(e){ if((!pos||e.pos===pos)&&e.decl&&m.indexOf(e.decl)===-1) m.push(e.decl); });
  return m;
}
function refreshDecl(){
  var pos=posSel.value;
  var show=(pos===''||pos==='n.'||pos==='v.'||pos==='adj.');
  declWrap.style.display=show?'':'none';
  if(!show){ declSel.value=''; return; }
  var opts=declOptions(pos), prev=declSel.value;
  if(opts.length){ fill(declSel,opts); declSel.value=(prev&&opts.indexOf(prev)!==-1)?prev:''; }
  else{ fill(declSel,[]); }
}
function getChap(){ var v=parseInt(chapIn.value,10); return (v>=1&&v<=40)?v:0; }
function passes(e){
  return (!posSel.value||e.pos===posSel.value)
      && (!declSel.value||e.decl===declSel.value)
      && (!getChap()||e.ch===getChap());
}
function line(e){ return ['<span style="font-style:italic;">'+e.latin+'</span>',e.gender,e.english,e.pos,e.chapter,e.decl].filter(function(x){return x;}).join(', '); }
function render(listArr){ list.innerHTML=listArr.map(line).join('<br>\n'); }
function nearest(pool,q){
  var lower=q.toLowerCase(), toks=lower.split(/\s+/), best=null, bestScore=-1;
  pool.forEach(function(e){
    var eng=e.english.toLowerCase(), score=0;
    if(eng.indexOf(lower)!==-1) score+=50;
    toks.forEach(function(t){ if(t&&eng.indexOf(t)!==-1) score+=10; });
    score-=Math.min(eng.length,200)/200;
    if(score>bestScore){bestScore=score;best=e;}
  });
  return bestScore>0?best:null;
}
function renderSplit(exact,similar){
  var a=exact.map(line), b=similar.map(line);
  if(a.length&&b.length){ list.innerHTML=a.join('<br>\n')+'<div style="height:10px;"></div>'+b.join('<br>\n'); }
  else if(a.length){ render(exact); }
  else { render(similar); }
}
function update(){
  var q=input.value.trim(), chap=getChap();
  var pool=ENTRIES.filter(passes);
  if(!q){ render(pool); return; }
  var lower=q.toLowerCase();
  if(lower==='to'){ render(pool); return; }  // lone 'to' filters nothing
  // "to X" => search only verbs' english by the stem after 'to'
  if(/^to\s+\S+/.test(lower)){
    // verb pool: tagged verbs + any entry whose English starts with 'to ' (covers untagged verbs)
    var vpool=posSel.value?pool:pool.filter(function(e){return e.pos==='v.'||e.english.toLowerCase().indexOf('to ')==0;});
    var stem=lower.replace(/^to\s+/,'').trim();
    var vtoks=stem.split(/\s+/).filter(Boolean);
    function vKey(s){ return s.toLowerCase().replace(/^to\s+/,''); }
    function vAliases(k){ return k.split(/[;,]/).map(function(a){return a.trim();}); }
    function vScore(en){
      var k=vKey(en), s=0;
      if(stem&&k.indexOf(stem)!==-1) s+=100;
      vAliases(k).forEach(function(a){ if(stem&&a===stem) s+=60; });
      vtoks.forEach(function(t){ if(t&&k.indexOf(t)!==-1) s+=20; });
      s-=Math.min(en.length,200)/200;
      return s;
    }
    function vExact(e){ var k=vKey(e.english); return stem&&(k.indexOf(stem)!==-1||vAliases(k).indexOf(stem)!==-1); }
    var scored=vpool.map(function(e){return {e:e,s:vScore(e.english)};})
      .filter(function(x){return x.s>0;})
      .sort(function(a,b){return b.s-a.s;});
    var exact=scored.filter(function(x){return vExact(x.e);}).map(function(x){return x.e;});
    var similar=scored.filter(function(x){return !vExact(x.e);}).map(function(x){return x.e;});
    renderSplit(exact,similar);
    return;
  }
  var lat=pool.filter(function(e){ return tokensIn(e.latin,q); });
  if(lat.length){
    var exact=lat.filter(function(e){ return exactLatin(e,q); });
    var sim=lat.filter(function(e){ return exactLatin(e,q)===false; });
    renderSplit(exact,sim);
    return;
  }
  var lower=q.toLowerCase();
  var toks=lower.split(/\s+/);
  function engScore(en){
    var s=0, e=en.toLowerCase();
    if(e.indexOf(lower)!==-1) s+=100;          // exact/substring of full phrase
    toks.forEach(function(t){ if(t&&e.indexOf(t)!==-1) s+=20; });
    s-=Math.min(e.length,200)/200;            // shorter defs win ties
    return s;
  }
  var scored=pool.map(function(e){ return {e:e,s:engScore(e.english)}; })
    .filter(function(x){ return x.s>0; })
    .sort(function(a,b){ return b.s-a.s; });  // closest first
  var exact=scored.filter(function(x){ return x.e.english.toLowerCase().indexOf(lower)!==-1; }).map(function(x){ return x.e; });
  var similar=scored.filter(function(x){ return x.e.english.toLowerCase().indexOf(lower)===-1; }).map(function(x){ return x.e; });
  renderSplit(exact,similar);
}
posSel.addEventListener('change',function(){ refreshDecl(); update(); });
declSel.addEventListener('change',update);
chapIn.addEventListener('input',update);
input.addEventListener('input',update);
fillPairs(posSel,(function(){var m=[],seen={};ENTRIES.forEach(function(e){if(e.pos&&!seen[e.pos]){seen[e.pos]=1;m.push([e.pos,FULLPOS[e.pos]||e.pos]);}});return m;})());
refreshDecl();
update();
'''

CONTROLS = ('<span><strong>search:</strong> <input type="text" id="search" name="search"></span> '
            '<span><strong>pos:</strong> <select id="pos"></select></span> '
            '<span id="declWrap"><strong>decl/conj:</strong> <select id="decl"></select></span> '
            '<span><strong>chapter:</strong> <input type="number" id="chapter" min="1" max="40" style="width:60px;"></span>')


def sort_key(e):
    # alphabetize ignoring macrons/case (chapter still primary)
    s = e['latin'].lower().replace('ā', 'a').replace('ē', 'e').replace('ī', 'i')
    s = s.replace('ō', 'o').replace('ū', 'u').replace('ȳ', 'y')
    return (e['ch'], s)


def main():
    rows = [json.loads(ln) for ln in open(DATA, encoding='utf-8').read().splitlines() if ln.strip()]
    entries = build_entries(rows)
    entries.sort(key=sort_key)
    html = ('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n'
            '<title>Wheelock Vocabulary</title>\n'
            '<style>\n'
            '  @media (max-width: 700px) {\n'
            '    body { margin:0; }\n'
            '    #controls { padding:10px; display:flex; flex-direction:column; align-items:stretch; gap:8px; }\n'
            '    #controls > span { display:flex; align-items:center; gap:8px; }\n'
            '    #controls input[type=text], #controls input[type=number], #controls select {\n'
            '      font-size:16px; min-height:40px; padding:6px; box-sizing:border-box; }\n'
            '    #search { flex:1; }\n'
            '    #list { font-size:12px; }\n'
            '    h1 { font-size:20px; }\n'
            '  }\n'
            '</style>\n</head>\n'
            '<body style="background:#ffffff; margin:0;">\n'
            '<h1 style="padding:10px 0 0 10px; margin:0;">Wheelock Latin Vocabulary Search</h1>\n'
            '<div id="controls" style="padding:10px 0 0 10px;">' + CONTROLS + '</div>\n'
            '<div id="list" style="padding:10px;"></div>\n'
            '<div style="position:fixed; bottom:10px; right:10px; font-size:12px; color:#555;">'
            '(This vocabulary is pulled directly from Wheelock\'s Latin and three other sources! '
            'It is 99% right but please report if some entries are wrong!)</div>\n'
            '<script>\nvar ENTRIES=' + esc(entries) + ';\n' + JS + '</script>\n</body>\n</html>')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'generated {len(entries)} entries -> {OUT}')


if __name__ == '__main__':
    main()