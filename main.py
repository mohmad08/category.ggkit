"""Локальный тренажёр для подготовки к квалификационной категории.

Запуск: python main.py
Затем откройте http://127.0.0.1:8000
"""

import json
import re
import zipfile
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
QUESTION = re.compile(r"^(\d{1,4})\.\s*(.+)")
ANSWER = re.compile(r"(\d{1,2})\.\s*")


def paragraph_data(paragraph):
    """Возвращает текст абзаца и признак, что в нём есть жирный фрагмент."""
    runs = paragraph.findall(".//w:r", NS)
    chunks, marks = [], []
    for run in runs:
        value = "".join(node.text or "" for node in run.findall(".//w:t", NS))
        is_bold = run.find(".//w:rPr/w:b", NS) is not None
        chunks.append(value); marks.extend([is_bold] * len(value))
    raw = "".join(chunks).replace("\u00a0", " ")
    left = len(raw) - len(raw.lstrip()); right = len(raw.rstrip())
    return raw.strip(), any(marks), marks[left:right]


def split_options(text, bold_marks):
    """Документы иногда хранят несколько вариантов в одном абзаце."""
    matches = list(ANSWER.finditer(text))
    if not matches:
        return []
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[match.end():end].strip()
        if value:
            # В слитых абзацах верный вариант выделен жирным лишь в своих runs.
            result.append({"id": int(match.group(1)), "text": value,
                           "correct": any(bold_marks[match.start():end])})
    return result


def parse_docx(path, category):
    xml = zipfile.ZipFile(path).read("word/document.xml")
    body = ET.fromstring(xml).find(".//w:body", NS)
    questions, current = [], None
    for p in body.findall("w:p", NS):
        text, bold, bold_marks = paragraph_data(p)
        if not text:
            continue
        found = QUESTION.match(text)
        # Вопросы заканчиваются вопросительным знаком/двоеточием. Варианты — тоже с цифры,
        # поэтому отличаем их по наличию уже открытого вопроса и короткому номеру варианта.
        is_new_question = found and (current is None or text.endswith(("?", ":")))
        if is_new_question:
            if current and current["options"]:
                questions.append(current)
            current = {"id": f"{category}-{found.group(1)}", "number": int(found.group(1)),
                       "question": found.group(2), "instruction": "", "options": [], "source": ""}
            continue
        if not current:
            continue
        if text.startswith("(Выберите"):
            current["instruction"] = text.strip("()")
        elif text.startswith("(") and text.endswith(")"):
            current["source"] = text.strip("()")
        else:
            current["options"].extend(split_options(text, bold_marks))
    if current and current["options"]:
        questions.append(current)
    # Оставляем только полноценно распознанные задания с правильным ответом.
    return [q for q in questions if len(q["options"]) >= 2 and any(o["correct"] for o in q["options"])]


def load_questions():
    return {
        "first": parse_docx(ROOT / "СПО ПЕРВАЯ КАТЕГОРИЯ.docx", "first"),
        "highest": parse_docx(ROOT / "СПО ВЫСШАЯ КАТЕГОРИЯ.docx", "highest"),
    }


PAGE = r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Категория — тренажёр</title><style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:wght@700&display=swap');
:root{--ink:#1c2b28;--muted:#67736f;--cream:#f7f5ef;--paper:#fffefa;--line:#e5e4dc;--mint:#dff1e8;--green:#197a56;--coral:#e8755c;--shadow:0 16px 44px #18382b12}*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font-family:Manrope,Arial,sans-serif}.top{max-width:1160px;margin:auto;padding:24px 28px;display:flex;align-items:center;justify-content:space-between}.logo{font-weight:800;font-size:19px;letter-spacing:-.8px}.logo i{font-style:normal;color:var(--green)}.progress{font-size:13px;color:var(--muted);display:flex;gap:10px;align-items:center}.dot{width:8px;height:8px;border-radius:50%;background:#b8c4be}.dot.on{background:var(--green)}main{max-width:1104px;margin:36px auto 80px;padding:0 28px}.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:42px;align-items:end;margin:44px 0 52px}.eyebrow{font-size:12px;color:var(--green);font-weight:800;letter-spacing:1.5px;text-transform:uppercase}.hero h1{font:700 clamp(40px,5.4vw,70px)/1.05 'Playfair Display',serif;letter-spacing:-2.5px;margin:13px 0 18px}.hero p{color:var(--muted);line-height:1.7;max-width:570px;margin:0}.stat{background:#dcefe5;border-radius:22px;padding:27px 30px}.stat b{display:block;font:700 48px/1 'Playfair Display',serif;color:var(--green)}.stat span{font-size:14px;color:#426258}.choice{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.card{border:1px solid var(--line);background:var(--paper);border-radius:20px;padding:27px;cursor:pointer;text-align:left;transition:.2s;box-shadow:0 4px 18px #243f3505}.card:hover{transform:translateY(-3px);box-shadow:var(--shadow);border-color:#aad1bf}.card .icon{font-size:29px}.card h2{font-size:20px;margin:26px 0 8px}.card p{margin:0;color:var(--muted);font-size:14px;line-height:1.5}.screen{display:none}.screen.active{display:block}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.back{border:0;background:transparent;color:var(--muted);font:600 14px Manrope;cursor:pointer;padding:7px 0}.category{font-size:13px;color:var(--green);font-weight:800}.mode-switch{display:flex;background:#ebece7;padding:4px;border-radius:11px;gap:3px}.mode-switch button{border:0;background:transparent;padding:8px 12px;border-radius:8px;cursor:pointer;font:600 12px Manrope;color:var(--muted)}.mode-switch .selected{background:white;color:var(--ink);box-shadow:0 1px 4px #00000012}.quiz{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(22px,4vw,44px);box-shadow:var(--shadow)}.meta{display:flex;justify-content:space-between;color:var(--muted);font-size:13px}.bar{height:5px;background:#e6ebe6;border-radius:9px;margin:13px 0 33px;overflow:hidden}.bar i{display:block;background:var(--green);height:100%;border-radius:9px;transition:.25s}.instruction{font-size:12px;font-weight:700;color:var(--green);letter-spacing:.5px;margin:0 0 12px}.question{font:700 clamp(24px,3.3vw,37px)/1.25 'Playfair Display',serif;margin:0 0 29px;max-width:850px}.options{display:grid;gap:10px}.option{display:flex;align-items:flex-start;gap:14px;width:100%;border:1px solid var(--line);background:#fff;padding:16px;border-radius:13px;text-align:left;color:var(--ink);font:500 15px/1.45 Manrope;cursor:pointer}.option:hover{border-color:#91bea9}.letter{flex:0 0 26px;height:26px;border-radius:50%;background:#f0f2ee;text-align:center;padding-top:3px;color:var(--muted);font-size:12px;font-weight:700}.option.chosen{border-color:var(--green);background:#f2fbf6}.option.correct{border-color:#43a675;background:#edfaf2}.option.wrong{border-color:#e68d7c;background:#fff1ee}.actions{display:flex;justify-content:space-between;align-items:center;margin-top:28px}.hint{color:var(--muted);font-size:12px}.primary{border:0;background:var(--green);color:#fff;border-radius:11px;padding:13px 20px;font:700 14px Manrope;cursor:pointer}.primary:disabled{opacity:.38;cursor:not-allowed}.primary:hover:not(:disabled){background:#126445}.result{text-align:center;padding:30px 10px}.result b{display:block;font:700 70px/1 'Playfair Display',serif;color:var(--green)}.result h2{font:700 30px 'Playfair Display',serif;margin:12px 0}.result p{color:var(--muted)}.review{margin-top:28px;text-align:left}.review details{border-top:1px solid var(--line);padding:12px 0;color:var(--muted);font-size:13px}.review summary{cursor:pointer;color:var(--ink);font-weight:700}.source{margin-top:20px;color:var(--muted);font-size:12px;line-height:1.5}@media(max-width:650px){.top,main{padding-left:18px;padding-right:18px}.hero,.choice{grid-template-columns:1fr}.hero{gap:23px;margin-top:22px}.hero h1{letter-spacing:-1.7px}.stat{padding:20px}.toolbar{align-items:flex-start;gap:12px}.mode-switch{flex-wrap:wrap}.quiz{padding:22px}.actions{gap:10px}.hint{display:none}}
/* Design system: an exam workbook, not a generic dashboard. */
:root{--ink:#172a45;--muted:#637185;--paper:#fffefa;--cream:#eef3f7;--line:#b8c8d9;--green:#147a5b;--coral:#e9573f;--blue:#315c9b;--shadow:none}
*{box-sizing:border-box}body{background:var(--cream);font-family:Onest,Arial,sans-serif;background-image:linear-gradient(#dce5ee 1px,transparent 1px);background-size:100% 36px}.top{max-width:1200px;padding:23px 32px;border-bottom:2px solid var(--ink)}.logo{font-size:18px;letter-spacing:-.7px;color:var(--ink)}.logo i{color:var(--coral)}.progress{font-size:12px;font-weight:600;color:var(--ink);text-transform:none}.dot{width:9px;height:9px;border-radius:0;background:var(--coral)}main{max-width:1140px;margin:0 auto 80px;padding:0 32px}.hero{grid-template-columns:1fr 275px;gap:50px;align-items:stretch;margin:0;padding:70px 0 48px;border-bottom:1px solid var(--line)}.eyebrow{font-size:13px;color:var(--blue);font-weight:700;letter-spacing:0;text-transform:none;margin-bottom:25px}.hero h1{font:700 clamp(44px,6vw,82px)/.98 'PT Serif',Georgia,serif;letter-spacing:-3.5px;margin:0 0 24px;color:var(--ink)}.hero p{font-size:16px;max-width:540px;color:#43536a;line-height:1.65}.stat{border:2px solid var(--ink);border-radius:0;background:var(--paper);box-shadow:8px 8px 0 var(--coral);padding:24px 25px;display:flex;flex-direction:column;justify-content:center;position:relative}.stat:before{content:'ПРОВЕРКА';position:absolute;right:-13px;top:16px;transform:rotate(90deg);font-size:9px;letter-spacing:1.6px;color:var(--coral);font-weight:700}.stat span{font-size:12px;font-weight:700;color:var(--blue)}.stat b{font:700 67px/.95 'PT Serif',Georgia,serif;color:var(--ink);margin:10px 0}.stat small{font-size:12px;color:var(--muted)}.choice{grid-template-columns:1fr;gap:0;margin:38px 0 0;border-top:2px solid var(--ink)}.card{display:grid;grid-template-columns:72px 1fr auto;gap:22px;align-items:center;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent;padding:25px 12px;text-align:left;box-shadow:none}.card:hover{transform:none;box-shadow:none;border-color:var(--ink);background:#e3edf8}.card .icon{font:700 29px/1 'PT Serif',Georgia,serif;color:var(--coral);border-right:1px solid var(--line);padding:5px 15px 5px 0}.card h2{font:700 27px 'PT Serif',Georgia,serif;margin:0 0 4px;color:var(--ink)}.card p{font-size:14px;margin:0;color:var(--muted)}.card strong{font-size:13px;color:var(--blue);border-bottom:2px solid var(--coral);padding-bottom:4px}.home-note{font-size:12px;color:var(--muted);margin:24px 0}.toolbar{margin:35px 0 19px;border-bottom:1px solid var(--line);padding-bottom:13px}.back{font-family:Onest,Arial,sans-serif;color:var(--blue);font-weight:700}.mode-switch{background:transparent;border:1px solid var(--line);padding:2px;border-radius:0;gap:0}.mode-switch button{border-radius:0;font-family:Onest,Arial,sans-serif;padding:8px 13px}.mode-switch .selected{background:var(--ink);color:white;box-shadow:none}.quiz{border:2px solid var(--ink);border-radius:0;background:var(--paper);box-shadow:10px 10px 0 #c7d7e8;padding:clamp(22px,4vw,48px);position:relative}.quiz:before{content:'БИЛЕТ';position:absolute;top:0;right:0;background:var(--coral);color:white;padding:6px 13px;font-size:10px;font-weight:700;letter-spacing:.8px}.meta{font-size:12px;font-weight:700;color:var(--blue)}.bar{height:3px;background:#d9e3ec;border-radius:0;margin:14px 0 34px}.bar i{background:var(--coral);border-radius:0}.instruction{font-size:12px;font-weight:700;color:var(--blue);letter-spacing:0;margin-bottom:14px}.question{font:700 clamp(26px,3.5vw,42px)/1.24 'PT Serif',Georgia,serif;color:var(--ink);letter-spacing:-.6px}.options{gap:0;border-top:1px solid var(--line)}.option{border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent;padding:16px 8px;font-family:Onest,Arial,sans-serif}.option:hover{border-color:var(--ink);background:#f0f5fa}.letter{border-radius:0;background:#dce8f3;color:var(--blue);font-size:12px;padding-top:5px}.option.chosen{border-color:var(--blue);background:#e7f0fa}.option.correct{border-color:var(--green);background:#e7f5ee}.option.wrong{border-color:var(--coral);background:#fff0ed}.primary{border-radius:0;background:var(--ink);font-family:Onest,Arial,sans-serif;padding:14px 21px}.primary:hover:not(:disabled){background:var(--blue)}.source{border-left:3px solid var(--coral);padding-left:11px}.result b,.result h2{font-family:'PT Serif',Georgia,serif;color:var(--ink)}.result b{color:var(--coral)}.review details{border-color:var(--line)}button:focus-visible{outline:3px solid #f2b33d;outline-offset:3px}@media(prefers-reduced-motion:reduce){*{transition:none!important}}@media(max-width:650px){.top,main{padding-left:18px;padding-right:18px}.hero{grid-template-columns:1fr;padding:42px 0 34px;gap:27px}.hero h1{letter-spacing:-2px}.stat{min-height:160px;box-shadow:6px 6px 0 var(--coral)}.card{grid-template-columns:48px 1fr;gap:13px}.card .icon{font-size:22px}.card h2{font-size:23px}.card strong{grid-column:2;justify-self:start}.toolbar{align-items:center}.quiz{box-shadow:6px 6px 0 #c7d7e8}.question{letter-spacing:-.3px}}
/* Restore the original visual theme. */
:root{--ink:#1c2b28;--muted:#67736f;--cream:#f7f5ef;--paper:#fffefa;--line:#e5e4dc;--mint:#dff1e8;--green:#197a56;--coral:#e8755c;--shadow:0 16px 44px #18382b12}body{margin:0;background:var(--cream);color:var(--ink);font-family:Manrope,Arial,sans-serif;background-image:none}.top{max-width:1160px;margin:auto;padding:24px 28px;border-bottom:0}.logo{font-weight:800;font-size:19px;letter-spacing:-.8px}.logo i{color:var(--green)}.progress{font-size:13px;color:var(--muted);font-weight:400}.dot{width:8px;height:8px;border-radius:50%;background:#b8c4be}main{max-width:1104px;margin:36px auto 80px;padding:0 28px}.hero{grid-template-columns:1.2fr .8fr;gap:42px;align-items:end;margin:44px 0 52px;padding:0;border-bottom:0}.eyebrow{font-size:12px;color:var(--green);font-weight:800;letter-spacing:1.5px;text-transform:uppercase;margin:0}.hero h1{font:700 clamp(40px,5.4vw,70px)/1.05 'Playfair Display',serif;letter-spacing:-2.5px;margin:13px 0 18px;color:var(--ink)}.hero p{font-size:16px;color:var(--muted);line-height:1.7;max-width:570px;margin:0}.stat{background:#dcefe5;border:0;border-radius:22px;box-shadow:none;padding:27px 30px;display:block}.stat:before{display:none}.stat b{display:block;font:700 48px/1 'Playfair Display',serif;color:var(--green);margin:0}.stat span{font-size:14px;font-weight:400;color:#426258}.stat small{display:none}.choice{grid-template-columns:repeat(2,1fr);gap:18px;margin:0;border:0}.card{display:block;border:1px solid var(--line);border-radius:20px;background:var(--paper);padding:27px;cursor:pointer;text-align:left;box-shadow:0 4px 18px #243f3505}.card:hover{transform:translateY(-3px);box-shadow:var(--shadow);border-color:#aad1bf;background:var(--paper)}.card .icon{font:400 29px/1 Manrope;color:var(--ink);border:0;padding:0}.card h2{font:700 20px Manrope;margin:26px 0 8px;color:var(--ink)}.card p{margin:0;color:var(--muted);font-size:14px;line-height:1.5}.toolbar{margin:0 0 24px;border:0;padding:0}.back{font-family:Manrope;color:var(--muted);font-weight:600}.mode-switch{display:flex;background:#ebece7;border:0;padding:4px;border-radius:11px;gap:3px}.mode-switch button{border-radius:8px;font-family:Manrope;padding:8px 12px}.mode-switch .selected{background:#fff;color:var(--ink);box-shadow:0 1px 4px #00000012}.quiz{border:1px solid var(--line);border-radius:22px;background:var(--paper);box-shadow:var(--shadow);padding:clamp(22px,4vw,44px)}.quiz:before{display:none}.meta{font-size:13px;font-weight:400;color:var(--muted)}.bar{height:5px;background:#e6ebe6;border-radius:9px;margin:13px 0 33px}.bar i{background:var(--green);border-radius:9px}.instruction{font-size:12px;font-weight:700;color:var(--green);letter-spacing:.5px;margin:0 0 12px}.question{font:700 clamp(24px,3.3vw,37px)/1.25 'Playfair Display',serif;color:var(--ink);letter-spacing:0}.options{gap:10px;border:0}.option{border:1px solid var(--line);border-radius:13px;background:#fff;padding:16px;font-family:Manrope}.option:hover{border-color:#91bea9;background:#fff}.letter{border-radius:50%;background:#f0f2ee;color:var(--muted);padding-top:3px}.option.chosen{border-color:var(--green);background:#f2fbf6}.option.correct{border-color:#43a675;background:#edfaf2}.option.wrong{border-color:#e68d7c;background:#fff1ee}.primary{border-radius:11px;background:var(--green);font-family:Manrope;padding:13px 20px}.primary:hover:not(:disabled){background:#126445}.source{border:0;padding:0}.result b,.result h2{font-family:'Playfair Display',serif;color:var(--green)}.result b{color:var(--green)}@media(max-width:650px){.top,main{padding-left:18px;padding-right:18px}.hero,.choice{grid-template-columns:1fr}.hero{gap:23px;margin-top:22px;padding:0}.hero h1{letter-spacing:-1.7px}.stat{padding:20px}.toolbar{align-items:flex-start;gap:12px}.quiz{box-shadow:var(--shadow)}.question{letter-spacing:0}}
.credits{margin:70px 0 0;text-align:center;color:#87928d;font-size:12px;letter-spacing:.2px}.credits b{color:var(--green);font-weight:800}</style></head><body><header class="top"><div class="logo">категория<i>•</i>практика</div><div class="progress" id="total"></div></header><main>
<section id="home" class="screen active"><div class="hero"><div><div class="eyebrow">Тренажёр для педагогов СПО</div><h1>Уверенно к новой категории.</h1><p>Читайте вопросы с правильными ответами или проверьте себя в режиме экзамена. Прогресс сохраняется в этом браузере.</p></div><div class="stat"><b id="count">—</b><span>вопросов в базе</span></div></div><div class="choice"><button class="card" onclick="start('first')"><div class="icon">Ⅰ</div><h2>Первая категория</h2><p>Изучение и тестирование по банку вопросов для первой категории.</p></button><button class="card" onclick="start('highest')"><div class="icon">Ⅱ</div><h2>Высшая категория</h2><p>Подготовка к квалификационному испытанию на высшую категорию.</p></button></div></section>
<section id="practice" class="screen"><div class="toolbar"><button class="back" onclick="home()">← К выбору категории</button><div class="mode-switch"><button id="learnBtn" onclick="setMode('learn')">Изучать</button><button id="testBtn" onclick="setMode('test')">Проверить себя</button></div></div><div class="quiz" id="quiz"></div></section><footer class="credits">by <b>M_08</b> from <b>GGKIT</b></footer></main><script>
let bank={},category='',mode='learn',list=[],index=0,answers={},revealed={};const letters='АБВГДЕЖЗ';
fetch('/api/questions').then(r=>r.json()).then(d=>{bank=d;let n=d.first.length+d.highest.length;document.querySelector('#count').textContent=n;document.querySelector('#total').innerHTML='<span class="dot on"></span> '+n+' вопросов';});
function start(c){category=c;mode='learn';list=[...bank[c]];index=0;answers={};revealed={};document.querySelector('#home').classList.remove('active');document.querySelector('#practice').classList.add('active');render()}
function home(){document.querySelector('#practice').classList.remove('active');document.querySelector('#home').classList.add('active')}
function setMode(m){mode=m;index=0;answers={};revealed={};list=mode==='test'?[...bank[category]].sort(()=>Math.random()-.5).slice(0,Math.min(80,bank[category].length)):[...bank[category]];render()}
function pick(id){let q=list[index],multi=q.instruction.toLowerCase().includes('все'),a=answers[q.id]||[];if(revealed[q.id])return;answers[q.id]=multi?(a.includes(id)?a.filter(x=>x!==id):[...a,id]):[id];render()}
function next(){let q=list[index];if(mode==='learn'&&!revealed[q.id]){revealed[q.id]=true;render();return}if(index<list.length-1){index++;render()}else result()}
function render(){let q=list[index],selected=answers[q.id]||[],learn=mode==='learn',shown=!!revealed[q.id],multi=q.instruction.toLowerCase().includes('все');document.querySelector('#learnBtn').className=mode==='learn'?'selected':'';document.querySelector('#testBtn').className=mode==='test'?'selected':'';let opts=q.options.map(o=>{let cl='option';if(selected.includes(o.id))cl+=' chosen';if(learn&&shown){if(o.correct)cl+=' correct';else if(selected.includes(o.id))cl+=' wrong'}return `<button class="${cl}" onclick="pick(${o.id})"><span class="letter">${letters[o.id-1]||o.id}</span><span>${o.text}</span></button>`}).join('');let disabled=mode==='test'?!selected.length:(!shown&&!selected.length);let label=mode==='learn'&&!shown?'Проверить ответ':index===list.length-1?'Завершить':'Далее →';let hint=learn?(shown?'Правильные варианты отмечены зелёным.':'Выберите '+(multi?'все подходящие варианты':'вариант')+' и проверьте ответ.'):'Выберите вариант и переходите дальше';document.querySelector('#quiz').innerHTML=`<div class="meta"><span>${category==='first'?'Первая':'Высшая'} категория</span><span>${index+1} из ${list.length}</span></div><div class="bar"><i style="width:${(index+1)/list.length*100}%"></i></div><p class="instruction">${q.instruction||'Выберите ответ'}</p><h1 class="question">${q.question}</h1><div class="options">${opts}</div>${learn&&shown?'<p class="source">Источник: '+q.source+'</p>':''}<div class="actions"><span class="hint">${hint}</span><button class="primary" ${disabled?'disabled':''} onclick="next()">${label}</button></div>`}
function result(){let score=0,wrong=[];list.forEach(q=>{let got=(answers[q.id]||[]).sort().join(','),ok=q.options.filter(o=>o.correct).map(o=>o.id).sort().join(',');if(got===ok)score++;else wrong.push(q)});let pct=Math.round(score/list.length*100),passed=score>=56;document.querySelector('#quiz').innerHTML=`<div class="result"><b>${pct}%</b><h2>${score} из ${list.length} верно</h2><p>${passed?'Тест сдан: набрано не менее 56 правильных ответов.':'Тест не сдан: для зачёта нужно минимум 56 правильных ответов из 80.'}</p><button class="primary" onclick="setMode('test')">Пройти ещё раз</button>${wrong.length?'<div class="review"><h3>Повторить ошибки</h3>'+wrong.map(q=>'<details><summary>'+q.question+'</summary><p>Правильный ответ: '+q.options.filter(o=>o.correct).map(o=>o.text).join('; ')+'</p></details>').join('')+'</div>':''}</div>`}
</script></body></html>'''


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/questions":
            data = json.dumps(QUESTIONS, ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        elif self.path in ("/", "/index.html"):
            data = PAGE.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        else: self.send_error(404)
    def log_message(self, *_): pass


if __name__ == "__main__":
    QUESTIONS = load_questions()
    print(f"Загружено: первая — {len(QUESTIONS['first'])}, высшая — {len(QUESTIONS['highest'])}.")
    print("Откройте http://127.0.0.1:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
else:
    QUESTIONS = load_questions()
