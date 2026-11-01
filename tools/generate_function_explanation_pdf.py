from pathlib import Path
import ast
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "BevIQ_Code_Explanation_Hinglish.pdf"

CORE_FILES = [
    "app.py", "config.py", "run.py", "document_rag.py",
    "data_ingestion/normalizer.py", "data_ingestion/loader.py",
    "database/db_manager.py", "database/mysql_migrator.py",
    "engines/sql_engine.py", "engines/vector_engine.py",
    "engines/rag_orchestrator.py", "engines/comparison_engine.py",
    "engines/upc_match_engine.py",
]

ALL_SCRIPT_FILES = sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in ROOT.rglob("*.py")
    if ".venv" not in path.parts
    and ".pytest_cache" not in path.parts
    and ".superpowers" not in path.parts
    and "__pycache__" not in path.parts
)

EXPLANATIONS = {
    "app.index": "Homepage serve karta hai. Browser ko index.html aur connection/model settings deta hai.",
    "app.api_chat": "Chat ka main API. User ka message/file leta hai, document ingest karta hai aur RAG orchestrator se answer banwata hai.",
    "app.api_documents": "Current session mein upload hue documents ki list frontend ko deta hai.",
    "app.api_upc_audit": "UPC audit chalata hai aur review-only CSV report banata hai; original data change nahi karta.",
    "app.api_compare": "Comparison type dekhkar sahi comparison method choose karta hai aur result export token deta hai.",
    "app.api_stats": "Har dataset ke total rows aur unique UPCs ka dashboard summary deta hai.",
    "app.api_db_status": "MySQL aur Ollama available hain ya nahi, iska status UI ko deta hai.",
    "app.api_configure_db": "Password se MySQL connection test karta hai; request ho to CSV data migrate karta hai.",
    "app.api_rebuild_index": "Database records se local search/vector index dobara banata hai.",
    "app.api_export_csv": "Token se report file locate karke browser ko CSV download karata hai.",
    "config": "Paths, environment settings, database settings, Ollama settings aur 7 CSV files ka schema registry rakhta hai.",
    "run.setup_environment": "Startup se pehle SQLite data ingest aur vector index initialize/verify karta hai.",
    "document_rag._connection": "Document metadata/chunks ke liye SQLite connection, tables aur index banata hai.",
    "document_rag._clean": "Text ke extra spaces aur null values clean karta hai.",
    "document_rag._extract": "PDF, DOCX, TXT, CSV, Excel aur image se readable text nikalta hai.",
    "document_rag._chunks": "Long document ko overlapping chhote parts mein todta hai, taaki search/context manageable rahe.",
    "document_rag.ingest": "Uploaded file save, text extract, chunks create, hash store aur database mein insert karta hai.",
    "document_rag._tokens": "Search query ko comparable lowercase words mein convert karta hai.",
    "document_rag.search": "Session ke document chunks ko word-overlap score se rank karke relevant chunks deta hai.",
    "document_rag.list_documents": "Session ke uploaded documents ka naam/date return karta hai.",
    "data_ingestion.normalizer.normalize_upc": "UPC ko clean 13-digit string banata hai; scientific notation aur leading zero preserve karta hai.",
    "data_ingestion.normalizer.clean_text": "CSV text ko null/extra whitespace se clean karta hai.",
    "data_ingestion.loader.clean_column_name": "Column names ko consistent format mein clean karta hai.",
    "data_ingestion.loader.ingest_csv_to_sqlite": "CSV ko chunks mein read karke normalize aur indexed SQLite table mein load karta hai.",
    "data_ingestion.loader.ingest_all_to_sqlite": "Registry ki saari 7 CSV files ko sequentially SQLite mein load karta hai.",
    "database.db_manager.DBManager.get_sqlite_connection": "Fast offline SQLite connection banata hai, WAL/cache settings ke saath.",
    "database.db_manager.DBManager.get_connection": "MySQL available ho to MySQL, warna SQLite fallback choose karta hai.",
    "database.db_manager.DBManager.query": "SQL execute karke rows ko Python dictionaries ki list mein deta hai.",
    "database.db_manager.DBManager.query_df": "SQL result ko Pandas DataFrame mein convert karta hai.",
    "database.mysql_migrator.migrate_data_to_mysql": "SQLite/CSV data ko MySQL tables mein migrate karta hai, DBeaver access ke liye.",
    "engines.sql_engine.SQLEngine.lookup_upc": "Exact ya alternate UPC ko multiple beverage tables mein search karta hai.",
    "engines.sql_engine.SQLEngine.search_catalog": "Brand/product text ko catalog tables mein search karta hai.",
    "engines.sql_engine.SQLEngine.brand_profile": "Brand ke products, flavours, sizes, suppliers aur categories ka summary banata hai.",
    "engines.sql_engine.SQLEngine.search_supplier": "Supplier ke naam se related products search karta hai.",
    "engines.sql_engine.SQLEngine.count_brands": "SQL se distinct brands ka exact count nikalta hai.",
    "engines.sql_engine.SQLEngine.count_by_category": "Category-wise product counts ke liye GROUP BY use karta hai.",
    "engines.sql_engine.SQLEngine.get_dataset_overview": "Dataset-wise row count aur unique UPC summary deta hai.",
    "engines.vector_engine.LocalVectorIndex.tokenize": "Text ko searchable lowercase tokens mein todta hai.",
    "engines.vector_engine.LocalVectorIndex.build_from_database": "Database rows ka local BM25/TF-IDF style search index banata hai.",
    "engines.vector_engine.LocalVectorIndex.save": "Search index ko disk par pickle file mein save karta hai.",
    "engines.vector_engine.LocalVectorIndex.load": "Saved search index memory mein load karta hai.",
    "engines.vector_engine.LocalVectorIndex.search": "Relevant records ko token scoring ke basis par retrieve karta hai.",
    "engines.rag_orchestrator.RAGOrchestrator.is_ollama_available": "Local Ollama service ko check karta hai.",
    "engines.rag_orchestrator.RAGOrchestrator.query_ollama": "Retrieved context ke saath local LLM ko prompt bhejta hai.",
    "engines.rag_orchestrator.RAGOrchestrator.route_and_execute": "Question ka intent samajhkar SQL, comparison, document, UPC ya vector engine choose karta hai.",
    "engines.rag_orchestrator.RAGOrchestrator._local_general_response": "Ollama unavailable hone par basic offline replies deta hai.",
    "engines.rag_orchestrator.RAGOrchestrator._is_hinglish": "Question Hinglish mein hai ya nahi, approximate detect karta hai.",
    "engines.rag_orchestrator.RAGOrchestrator._extract_brand_guess": "Question se likely brand name identify karta hai.",
    "engines.rag_orchestrator.RAGOrchestrator._format_response": "Answer, records, sources aur download token ko common JSON shape mein pack karta hai.",
    "engines.comparison_engine.ComparisonEngine.compare_master_vs_categorization": "Master aur category sheet ko UPC par compare karke match/missing/mismatch status deta hai.",
    "engines.comparison_engine.ComparisonEngine.compare_allbrand_vs_supplier": "AllBrand aur Supplier data ki supplier integrity compare karta hai.",
    "engines.comparison_engine.ComparisonEngine.compare_beer_vs_rtd": "Beer aur RTD overlap ko business rules se validate karta hai.",
    "engines.comparison_engine.ComparisonEngine.find_duplicate_upcs_across_all": "Sab files mein repeated UPC groups detect karta hai.",
    "engines.comparison_engine.ComparisonEngine.compare_all_missing_in_master": "Category sheets ke UPCs ko master se compare karke missing records deta hai.",
    "engines.upc_match_engine.UPCMatchEngine.audit": "Exact UPC ke baad brand/product/size similarity se possible UPC match suggest karta hai; data write nahi karta.",
}


def catalog(path):
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    found = []

    def visit(nodes, owner=""):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = owner + node.name
                found.append((name, node.lineno))
                visit(node.body, name + ".")
            elif isinstance(node, ast.ClassDef):
                name = owner + node.name
                found.append((name, node.lineno))
                visit(node.body, name + ".")

    visit(tree.body)
    return found


class Guide(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(35, 75, 125)
            self.cell(0, 7, "BevIQ Function-wise Project Explanation", align="R")
            self.ln(5)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def cover_title(self, text, size=16):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(25, 65, 120)
        self.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def heading(self, text):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(180, 80, 20)
        self.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def para(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(35, 35, 35)
        self.multi_cell(0, 4.8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def item(self, name, purpose):
        self.set_font("Courier", "B", 8)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 4, name, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(55, 55, 55)
        self.multi_cell(0, 4.5, "Kyun / kaam: " + purpose, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


def explanation_for(rel, name):
    key = rel.replace("\\", ".").replace("/", ".").removesuffix(".py") + "." + name
    if key in EXPLANATIONS:
        return EXPLANATIONS[key]
    if name in EXPLANATIONS:
        return EXPLANATIONS[name]
    if name.split(".")[-1] == "__init__":
        return "Object initialize karta hai; default state/settings set karta hai."
    return "Reusable operation; surrounding class/module ke data par ek specific processing step karta hai."


def script_summary(rel):
    name = Path(rel).stem.lower()
    if rel.startswith("tests/"):
        return "Automated test script: project ke behavior ko assert karke regression pakadta hai."
    if rel.startswith("tools/"):
        if "pdf" in name:
            return "Documentation helper script: project explanation/report PDF generate karta hai."
        if "match" in name or "upc" in name:
            return "Analysis helper script: UPC cleanup, matching ya missing-UPC audit ke liye."
        if "compare" in name or "check" in name:
            return "Analysis helper script: datasets/categories ke beech validation ya comparison ke liye."
        if "profile" in name or "analysis" in name or "inspect" in name:
            return "Data inspection script: CSV structure, counts, columns aur data quality samajhne ke liye."
        return "One-time/supporting tool: development ya data-analysis ka specific helper kaam karta hai."
    if name == "app":
        return "Flask web application entry module: API routes aur browser requests handle karta hai."
    return "Project ka Python module: related data-processing ya application logic ko organize karta hai."


def build():
    pdf = Guide("P", "mm", "A4")
    pdf.set_auto_page_break(True, 15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.cover_title("BevIQ / beverage_db\nFunction-wise Explanation", 16)
    pdf.para("Yeh PDF line-by-line explanation nahi hai. Iska focus sirf yeh hai: project mein kaunse functions/classes hain, har ek ka kaam kya hai, aur woh kyun use hua hai. Hinglish mein simple study notes diye gaye hain.")

    pdf.heading("1. Project ka overall flow")
    pdf.para("User browser mein question deta hai -> app.py Flask request receive karta hai -> RAG orchestrator intent decide karta hai -> SQL/comparison/document/UPC/vector engine ka function run hota hai -> result JSON mein frontend ko milta hai -> HTML/JavaScript result dikhate hain.")
    pdf.para("Main source of truth database/CSV comparison hai. Ollama sirf optional natural-language answer banata hai; exact count ya UPC match ka decision SQL/business logic karta hai.")

    pdf.heading("2. app.py: functions aur unka reason")
    for name in ["index", "api_chat", "api_documents", "api_upc_audit", "api_compare", "api_stats", "api_db_status", "api_configure_db", "api_rebuild_index", "api_export_csv"]:
        pdf.item(name + "()", explanation_for("app.py", name))
    pdf.para("app.py mein Flask route decorators ka matlab hai ki browser ke alag URLs ko alag Python functions handle karenge. GET generally data/read ke liye aur POST user input/action ke liye use hua hai.")

    pdf.add_page()
    pdf.heading("3. Baaki core Python files")
    for rel in CORE_FILES[1:]:
        pdf.heading(rel)
        entries = catalog(ROOT / rel)
        for name, line in entries:
            short = name.split(".")[-1]
            display = f"{name}()  [source line {line}]" if short not in {name} else f"{name}  [source line {line}]"
            pdf.item(display, explanation_for(rel, name))
        if rel == "config.py":
            pdf.para("Config file mein functions bahut kam hain; yahan variables/dictionaries ka use isliye hai taaki paths, credentials, model aur CSV column mapping ek central jagah se control ho.")

    pdf.add_page()
    pdf.heading("4. Tools, tests aur frontend ka role")
    pdf.item("tools/*.py", "One-time analysis, profiling, UPC matching, supplier/beer-RTD checks aur PDF generation ke helper scripts. Main web app ka runtime flow in sab par depend nahi karta.")
    pdf.item("tests/*.py", "Automated checks: endpoints, RAG routing, UPC matching, database behavior aur read-only audit verify karte hain.")
    pdf.item("templates/index.html", "Browser page ka structure aur JavaScript interaction. API calls karta hai aur returned JSON ko chat/table/report link mein dikhata hai.")
    pdf.item("README.md", "Human documentation: setup, features, database connection aur sample questions batata hai.")
    pdf.item("requirements.txt", "Python dependencies ki list; installation ke liye.")

    pdf.add_page()
    pdf.heading("5. All Python scripts: function/class catalog")
    pdf.para("Neeche project ke har Python script ka naam diya gaya hai. Har script ke andar defined function/class ka simple purpose diya hai. Yeh section source lines ko repeat nahi karta; sirf reusable blocks ka role samjhata hai.")
    for rel in ALL_SCRIPT_FILES:
        if rel in CORE_FILES:
            continue
        pdf.heading(rel)
        pdf.para(script_summary(rel))
        path = ROOT / rel
        try:
            entries = catalog(path)
        except (SyntaxError, UnicodeDecodeError) as exc:
            pdf.item("Module", f"Script parse nahi ho paya ({type(exc).__name__}); file ka purpose upar diya gaya hai.")
            continue
        if not entries:
            pdf.item("Module-level code", "Is script mein named function/class nahi hai; top-level statements direct run hote hain.")
        for name, line in entries:
            pdf.item(f"{name} [source line {line}]", explanation_for(rel, name))

    pdf.heading("6. Kaunsi language kis liye use hui?")
    pdf.item("Python", "Backend ka main language: Flask API, CSV processing, UPC cleaning, SQLite/MySQL queries, comparison logic, document extraction, RAG routing aur Ollama call.")
    pdf.item("HTML", "Webpage ka structure: chat box, buttons, tabs, tables, upload control.")
    pdf.item("CSS", "Dashboard ka look: colors, layout, spacing, cards, buttons, badges aur responsive design.")
    pdf.item("JavaScript", "Browser-side behavior: fetch() se API call, FormData se file upload, JSON ko chat/table mein render karna; page reload ki zarurat nahi.")
    pdf.item("SQL", "Exact database work: SELECT, COUNT, JOIN, GROUP BY, duplicate aur missing-record checks.")
    pdf.item("JSON", "Frontend aur Python backend ke beech response format: answer, records, sources, counts, download token.")
    pdf.item("CSV", "Original beverage datasets aur generated reports ka storage/exchange format.")
    pdf.item("Markdown", "Chat answers mein headings, bullets aur tables ko readable banane ke liye.")
    pdf.item(".env", "Machine-specific settings jaise MySQL password/host aur Ollama configuration ko source code se bahar rakhne ke liye.")
    pdf.item("Pickle", "Local search/vector index ko disk par save karke next startup par reuse karne ke liye.")

    pdf.heading("7. Interview-style one-line explanation")
    pdf.para("BevIQ ek local beverage data assistant hai. Python/Flask request handle karta hai, CSV data SQLite/MySQL mein indexed hota hai, SQL exact answers deta hai, comparison engine sheets ke differences nikalta hai, UPC engine conservative matching karta hai, document RAG uploaded files search karta hai, aur HTML/CSS/JavaScript browser mein result dikhate hain.")
    pdf.output(str(OUT))
    print(OUT)


if __name__ == "__main__":
    build()
