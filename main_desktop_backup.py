"""AI Quiz Generator 2.0 - desktop launcher and secure Python bridge."""
from __future__ import annotations
import base64, json, os, random, re, sys, threading, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
HISTORY_FILE = DATA / "history.json"

try:
    import webview
except ImportError:
    webview = None
try:
    from groq import Groq
except ImportError:
    Groq = None
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document
except ImportError:
    Document = None

OFFLINE_BANK = {
 "python": [
  {"question":"Which keyword defines a function in Python?","options":["func","define","def","function"],"answer_index":2,"explanation":"Python uses the def keyword to define a function."},
  {"question":"What is the result of len([2, 4, 6])?","options":["2","3","4","6"],"answer_index":1,"explanation":"The list contains three elements."},
  {"question":"Which collection stores key-value pairs?","options":["tuple","set","dictionary","string"],"answer_index":2,"explanation":"A dictionary maps unique keys to values."},
  {"question":"Which value represents the absence of a value in Python?","options":["undefined","null","None","void"],"answer_index":2,"explanation":"None is Python's null-like singleton."},
  {"question":"What does list.append(x) do?","options":["Sorts the list","Adds x to the end","Removes x","Copies the list"],"answer_index":1,"explanation":"append adds one item at the end of a list."},
  {"question":"Which block handles an exception?","options":["catch","except","error","rescue"],"answer_index":1,"explanation":"Python exception handling uses try and except."},
  {"question":"What is the type of 3.14?","options":["int","str","float","bool"],"answer_index":2,"explanation":"Decimal numeric literals are floats by default."},
  {"question":"Which operator tests equality?","options":["=","==","!=","=>"],"answer_index":1,"explanation":"== compares values; = assigns a value."},
 ],
 "physics": [
  {"question":"What is the SI unit of force?","options":["Joule","Watt","Newton","Pascal"],"answer_index":2,"explanation":"Force is measured in newtons (N)."},
  {"question":"Which quantity is the rate of change of velocity?","options":["Momentum","Acceleration","Displacement","Impulse"],"answer_index":1,"explanation":"Acceleration is the change in velocity per unit time."},
  {"question":"What is the SI unit of work?","options":["Newton","Joule","Watt","Tesla"],"answer_index":1,"explanation":"One joule is one newton-metre of work."},
  {"question":"Near Earth's surface, gravitational acceleration is approximately?","options":["3.8 m/s²","6.7 m/s²","9.8 m/s²","12.8 m/s²"],"answer_index":2,"explanation":"The standard approximate value is 9.8 m/s²."},
  {"question":"Which is a vector quantity?","options":["Mass","Time","Speed","Velocity"],"answer_index":3,"explanation":"Velocity has both magnitude and direction."},
 ],
 "biology": [
  {"question":"Which organelle is known as the powerhouse of the cell?","options":["Nucleus","Mitochondrion","Ribosome","Golgi apparatus"],"answer_index":1,"explanation":"Mitochondria generate much of the cell's ATP."},
  {"question":"What molecule carries genetic information?","options":["ATP","DNA","Glucose","Lipid"],"answer_index":1,"explanation":"DNA stores hereditary information in most organisms."},
  {"question":"What is the process plants use to make glucose from light?","options":["Respiration","Fermentation","Photosynthesis","Transpiration"],"answer_index":2,"explanation":"Photosynthesis converts light energy into chemical energy."},
  {"question":"Which blood cells primarily transport oxygen?","options":["Platelets","Red blood cells","White blood cells","Plasma cells"],"answer_index":1,"explanation":"Hemoglobin in red blood cells binds oxygen."},
 ]
}

class QuizAPI:
    def __init__(self):
        self.material_text = ""
        self.material_name = ""
        self.last_quiz = []
        self.started_at = None

    def get_status(self):
        return {"ai_available": bool(Groq and os.getenv("GROQ_API_KEY")),
                "groq_package": bool(Groq), "openai_package": bool(Groq), "pdf_support": bool(PdfReader), "docx_support": bool(Document),
                "material_loaded": bool(self.material_text), "material_name": self.material_name,
                "history": self._history()[:5]}

    def _history(self):
        try: return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception: return []

    def load_material(self, filename, encoded):
        try:
            raw = base64.b64decode(encoded)
            suffix = Path(filename).suffix.lower()
            if suffix == ".txt": text = raw.decode("utf-8", errors="replace")
            elif suffix == ".pdf":
                if not PdfReader: return {"ok":False,"error":"PDF support is missing. Run: py -m pip install pypdf"}
                import io
                reader = PdfReader(io.BytesIO(raw))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)
            elif suffix == ".docx":
                if not Document: return {"ok":False,"error":"DOCX support is missing. Run: py -m pip install python-docx"}
                import io
                doc = Document(io.BytesIO(raw))
                parts = [p.text for p in doc.paragraphs]
                for table in doc.tables:
                    for row in table.rows: parts.append(" | ".join(cell.text for cell in row.cells))
                text = "\n".join(parts)
            else: return {"ok":False,"error":"Please upload a PDF, DOCX, or TXT file."}
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if len(text) < 80: return {"ok":False,"error":"Not enough readable text was found in this file."}
            self.material_text, self.material_name = text, Path(filename).name
            return {"ok":True,"name":self.material_name,"characters":len(text),"words":len(text.split())}
        except Exception as e: return {"ok":False,"error":f"Could not read file: {e}"}

    def clear_material(self):
        self.material_text, self.material_name = "", ""
        return {"ok":True}

    def generate_quiz(self, topic, count, difficulty, language, source_mode):
        topic = (topic or "").strip()
        count = max(5, min(20, int(count or 10)))
        material_mode = source_mode == "material"
        if material_mode and not self.material_text:
            return {"ok":False,"error":"Upload study material first, or switch to Topic mode."}
        if not material_mode and not topic:
            return {"ok":False,"error":"Enter a topic to start your quiz."}
        if not Groq or not os.getenv("GROQ_API_KEY"):
            if material_mode:
                return {"ok":False,"error":"Strict source-only mode needs a Groq API key. Add GROQ_API_KEY to your .env file, then restart the app. No outside questions will be substituted."}
            key = next((k for k in OFFLINE_BANK if k in topic.lower()), None)
            if not key:
                return {"ok":False,"error":"AI is not configured, and the offline bank only covers Python, Physics, and Biology. Set GROQ_API_KEY in your .env file to generate quizzes on any topic."}
            qs = random.sample(OFFLINE_BANK[key], min(count, len(OFFLINE_BANK[key])))
            quiz = {"title":f"{topic.title()} Quick Challenge", "questions":qs, "source":"Offline question bank"}
        else:
            try:
                client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=90.0, max_retries=1)
                if material_mode:
                    # Split into overlapping chunks so later sections are not silently discarded.
                    text = self.material_text
                    max_chars = 24000
                    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars-1200)]
                    chosen = chunks[:min(4, len(chunks))]
                    source = "\n\n--- MATERIAL SECTION ---\n\n".join(chosen)
                    instruction = ("STRICT SOURCE-ONLY MODE. Every question, correct answer, and explanation must be supported by the supplied study material. Do not use outside knowledge or fill gaps. If the source cannot support the requested number, return only supported questions. Include source_evidence as a short exact quote from the material for every question.\nSTUDY MATERIAL:\n" + source)
                    label = self.material_name
                else:
                    instruction = f"Create accurate multiple-choice questions about this topic: {topic}. Use broadly accepted knowledge."
                    label = topic
                prompt = f'''{instruction}\n\nDifficulty: {difficulty}. Language: {language}. Requested questions: {count}.\nReturn ONLY valid JSON with this schema: {{"title":"short title","questions":[{{"question":"...","options":["A","B","C","D"],"answer_index":0,"explanation":"...","source_evidence":"..."}}]}}. answer_index must be 0-3. Avoid duplicate questions. Keep all content in the requested language.''' 
                response = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role":"system","content":"You create rigorous, clear educational quizzes. Follow source restrictions exactly and output valid JSON only."},{"role":"user","content":prompt}], temperature=0.35, response_format={"type":"json_object"})
                data = json.loads(response.choices[0].message.content)
                quiz = {"title":data.get("title") or f"{label} Challenge", "questions":data.get("questions",[]), "source":f"Study material: {label}" if material_mode else f"AI-generated: {label}"}
                quiz["questions"] = self._validate(quiz["questions"], material_mode)
                if len(quiz["questions"]) < 1: return {"ok":False,"error":"The generator could not create any valid questions from the source. Try a clearer or shorter document."}
            except Exception as e:
                return {"ok":False,"error":f"Quiz generation failed: {e}"}
        self.last_quiz = quiz["questions"]
        self.started_at = time.time()
        return {"ok":True,"quiz":quiz}

    def _validate(self, questions, strict):
        valid, seen = [], set()
        source_lower = self.material_text.lower() if strict else ""
        for q in questions:
            try:
                question = str(q["question"]).strip()
                options = [str(x).strip() for x in q["options"]]
                idx = int(q["answer_index"])
                expl = str(q.get("explanation", "")).strip()
                evidence = str(q.get("source_evidence", "")).strip()
                norm = re.sub(r"\W+", "", question.lower())
                if not question or norm in seen or len(options) != 4 or len(set(options)) < 4 or idx not in range(4): continue
                if strict and (not evidence or evidence.lower() not in source_lower): continue
                seen.add(norm)
                item = {"question":question,"options":options,"answer_index":idx,"explanation":expl}
                if evidence: item["source_evidence"] = evidence
                valid.append(item)
            except Exception: continue
        return valid

    def save_result(self, title, score, total, elapsed, answers):
        history = self._history()
        item = {"title":str(title),"score":int(score),"total":int(total),"percent":round(100*int(score)/max(1,int(total))),"date":datetime.now().strftime("%d %b %Y · %I:%M %p"),"elapsed":int(elapsed)}
        history.insert(0,item); HISTORY_FILE.write_text(json.dumps(history[:50],indent=2),encoding="utf-8")
        return {"ok":True,"result":item,"history":history[:5]}

    def get_history(self): return self._history()[:30]


def main():
    if webview is None:
        print("Missing dependency: pywebview. Install requirements with: py -m pip install -r requirements.txt")
        input("Press Enter to exit...")
        return
    api = QuizAPI()
    html = (ROOT / "ui" / "index.html").resolve().as_uri()
    webview.create_window("AI Quiz Generator 2.0", html, js_api=api, width=1420, height=900, min_size=(1080,700), background_color="#0a0c12")
    webview.start(debug=False)

if __name__ == "__main__":
    main()
