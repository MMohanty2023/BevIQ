from pathlib import Path
from fpdf import FPDF
import ast

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports' / 'BevIQ_Code_Explanation_Hinglish.pdf'
OUT.parent.mkdir(exist_ok=True)

FILES = ['app.py','config.py','run.py','document_rag.py','data_ingestion/normalizer.py','data_ingestion/loader.py','database/db_manager.py','database/mysql_migrator.py','engines/sql_engine.py','engines/vector_engine.py','engines/rag_orchestrator.py','engines/comparison_engine.py','engines/upc_match_engine.py']

def why(line):
    s=line.strip()
    if not s: return 'Blank line: code ko readable banane ke liye.'
    if s.startswith('#'): return 'Comment: developer ka note; Python ise execute nahi karta.'
    if s.startswith('import ') or s.startswith('from '): return 'Import: library/module ke functions yahan available karata hai.'
    if s.startswith('@'): return 'Decorator: neeche wale function ko Flask route ya extra behavior deta hai.'
    if s.startswith('def '): return 'Function: reusable kaam ka block; call hone par body run hoti hai.'
    if s.startswith('class '): return 'Class: related data aur methods ka reusable blueprint.'
    if 'return ' in s: return 'Return: calculated result caller ko wapas bhejta hai.'
    if 'request.' in s: return 'Browser/API request se input, JSON, form ya uploaded file read ho rahi hai.'
    if 'jsonify' in s: return 'Python result ko JSON response bana kar frontend ko bhejta hai.'
    if 'SELECT ' in s.upper() or 'INSERT ' in s.upper() or 'CREATE TABLE' in s.upper(): return 'SQL: database se data read/write ya schema/index tayyar hota hai.'
    if 'pandas' in s.lower() or 'pd.' in s: return 'Pandas: CSV/table data ko DataFrame mein process karta hai.'
    if 'sqlite' in s.lower(): return 'SQLite: local offline file database; fast indexed queries ke liye.'
    if 'requests.' in s: return 'HTTP call: local Ollama API se connect karta hai.'
    if 'pickle' in s: return 'Pickle: vector index object ko disk par save/load karta hai.'
    if 're.' in s: return 'Regex/text cleaning: UPC ya words se pattern extract karta hai.'
    if 'try:' in s or 'except' in s: return 'Error handling: failure ko handle karke app ko crash hone se bachata hai.'
    if 'if __name__' in s: return 'Entry-point guard: file direct run hone par startup code chalata hai.'
    return 'Data flow, configuration, calculation, ya object state update; exact intent surrounding function se samjho.'

def ascii_text(value):
    return str(value).encode('ascii', 'replace').decode('ascii')

def function_catalog(path):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
    except SyntaxError:
        return []
    items = []
    def visit(nodes, owner=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ''
                purpose = doc.splitlines()[0] if doc else node.name.replace('_', ' ').capitalize() + ': reusable operation.'
                items.append((owner + node.name, node.lineno, purpose))
                visit(node.body, owner + node.name + ' -> ')
            elif isinstance(node, ast.ClassDef):
                items.append((owner + node.name, node.lineno, 'Class: related data aur methods ka reusable blueprint.'))
                visit(node.body, owner + node.name + ' -> ')
    visit(tree.body)
    return items

DETAILS = {
    'app.index': 'Root browser page serve karta hai. render_template() index.html ko config values ke saath HTML response banata hai.',
    'app.api_chat': 'Main chat endpoint. Form/JSON message aur optional file leta hai, document_rag.ingest() se file store karta hai, phir rag_orchestrator.route_and_execute() call karke JSON answer deta hai.',
    'app.api_documents': 'Current browser session ke uploaded documents list karta hai; chat UI ko document history dene ke liye.',
    'app.api_upc_audit': 'Read-only UPC audit chalata hai, records ko CSV report mein save karta hai aur download token return karta hai.',
    'app.api_compare': 'Comparison type ke basis par comparison_engine ka correct method select karta hai; result ko CSV export token ke saath JSON banata hai.',
    'app.api_stats': 'Har dataset ka row count aur unique UPC count nikal kar dashboard metrics return karta hai.',
    'app.api_db_status': 'MySQL connectivity aur Ollama availability check karke UI status badges ke liye data return karta hai.',
    'app.api_configure_db': 'User ke MySQL password se connection test karta hai; optional migration start karta hai.',
    'app.api_rebuild_index': 'SQLite records se persistent local vector/BM25 index dobara build karta hai.',
    'app.api_export_csv': 'Generated report token validate karke CSV file browser ko download karata hai.',
    'config': 'Configuration module paths, environment variables, database settings, Ollama settings aur seven CSV datasets ka schema registry rakhta hai.',
    'run.setup_environment': 'Startup bootstrap: SQLite missing ho to ingestion chalata hai, vector index missing ho to build karta hai, phir Flask server ready karta hai.',
    'document_rag._connection': 'Document metadata aur chunks ke liye SQLite connection/table/index create karta hai.',
    'document_rag._extract': 'PDF/DOCX/TXT/CSV/XLSX/image extension ke hisaab se text extract karta hai.',
    'document_rag._chunks': 'Long text ko overlapping chunks mein todta hai taaki retrieval aur LLM context manageable rahe.',
    'document_rag.ingest': 'Uploaded file validate/save, text extraction/chunking, hash generation aur document chunks database insert karta hai.',
    'document_rag.search': 'Session ke chunks ko query-token overlap score se rank karke top relevant document context return karta hai.',
    'database.db_manager.DBManager.get_sqlite_connection': 'SQLite WAL, cache aur performance pragmas ke saath local connection banata hai.',
    'database.db_manager.DBManager.get_connection': 'MySQL available ho to MySQL, warna SQLite fallback choose karta hai.',
    'database.db_manager.DBManager.query': 'SQL execute karke rows ko dictionaries ki list mein return karta hai; engines ka common database interface.',
    'database.db_manager.DBManager.query_df': 'SQL result ko Pandas DataFrame mein return karta hai.',
    'data_ingestion.normalizer.normalize_upc': 'Scientific notation, UPC= prefix, decimal aur missing leading zero clean karke UPC ko string rakhta hai.',
    'data_ingestion.normalizer.clean_text': 'Null values aur extra whitespace ko clean karta hai.',
    'data_ingestion.loader.ingest_csv_to_sqlite': 'CSV ko chunks mein read, normalize, source row metadata add aur indexed SQLite table mein append karta hai.',
    'data_ingestion.loader.ingest_all_to_sqlite': 'Config registry ke saare seven CSV datasets sequentially ingest karta hai.',
    'engines.sql_engine.SQLEngine.lookup_upc': 'Normalized UPC ko AIMaster, AllBrand, Beer, RTD, Spirits aur Wine tables mein exact/alternate match karta hai.',
    'engines.sql_engine.SQLEngine.search_catalog': 'Brand/product text ko sabhi catalog sheets mein search karke common result shape banata hai.',
    'engines.sql_engine.SQLEngine.brand_profile': 'Ek brand ke flavours, sizes, suppliers, origins, categories aur UPC summary banata hai.',
    'engines.sql_engine.SQLEngine.search_supplier': 'Supplier name ke basis par AIMaster products search karta hai.',
    'engines.sql_engine.SQLEngine.count_brands': 'Requested table mein distinct normalized brands ka exact SQL count deta hai.',
    'engines.sql_engine.SQLEngine.count_by_category': 'Master, Beer aur RTD categories ka GROUP BY aggregation deta hai.',
    'engines.sql_engine.SQLEngine.get_dataset_overview': 'Har configured table ka total row aur unique UPC metric return karta hai.',
    'engines.vector_engine.LocalVectorIndex.tokenize': 'Search text ko lowercase alphanumeric tokens mein convert karta hai.',
    'engines.vector_engine.LocalVectorIndex.build_from_database': 'Selected database rows ka BM25 document index, metadata, document frequency aur lengths build karta hai.',
    'engines.vector_engine.LocalVectorIndex.save': 'Index state ko pickle file mein persist karta hai.',
    'engines.vector_engine.LocalVectorIndex.load': 'Saved pickle index ko memory mein load karta hai.',
    'engines.vector_engine.LocalVectorIndex.search': 'BM25-style TF/IDF score se top relevant beverage records retrieve karta hai.',
    'engines.rag_orchestrator.RAGOrchestrator.is_ollama_available': 'Local Ollama /api/tags endpoint ko short cache ke saath check karta hai.',
    'engines.rag_orchestrator.RAGOrchestrator.query_ollama': 'Prompt, model aur system instruction ko local Ollama /api/generate endpoint par bhejta hai.',
    'engines.rag_orchestrator.RAGOrchestrator.route_and_execute': 'User intent classify karke normal chat, SQL, document RAG, comparison, UPC audit, brand search ya vector retrieval ka correct route select karta hai.',
    'engines.rag_orchestrator.RAGOrchestrator._local_general_response': 'Ollama unavailable hone par greetings, help, joke aur basic Hinglish/English replies deta hai.',
    'engines.rag_orchestrator.RAGOrchestrator._is_hinglish': 'Lightweight language markers se Hinglish response choose karta hai.',
    'engines.rag_orchestrator.RAGOrchestrator._extract_brand_guess': 'Question words hata kar actual multi-word brand name nikalta hai.',
    'engines.rag_orchestrator.RAGOrchestrator._format_response': 'Answer, records, sources, CSV token aur read-only flag ko frontend-friendly response shape mein pack karta hai.',
    'engines.comparison_engine.ComparisonEngine.compare_master_vs_categorization': 'UPC join karke Exact, Partial, Mismatch aur Missing statuses classify karta hai.',
    'engines.comparison_engine.ComparisonEngine.compare_allbrand_vs_supplier': 'SupplierCode join karke official supplier name integrity check karta hai.',
    'engines.comparison_engine.ComparisonEngine.compare_beer_vs_rtd': 'Overlapping Beer/RTD UPCs ko NON RTD, FAB/seltzer verification aur mismatch rules se validate karta hai.',
    'engines.comparison_engine.ComparisonEngine.find_duplicate_upcs_across_all': 'Multiple source files mein same UPC groups find karta hai.',
    'engines.comparison_engine.ComparisonEngine.compare_all_missing_in_master': 'Beer, Wine, RTD aur Spirits ke UPCs ko Master se compare karke missing samples aur summary banata hai.',
    'engines.upc_match_engine.UPCMatchEngine.audit': 'AllBrand candidates ke against exact UPC, alternate UPC, product/brand/size similarity check karta hai; source data modify nahi karta.',
}

class Guide(FPDF):
    def header(self):
        if self.page_no()>1:
            self.set_font('Helvetica','B',8); self.set_text_color(40,80,130); self.cell(0,7,'BevIQ Code Explanation - Hinglish',align='R'); self.ln(5)
    def footer(self):
        self.set_y(-12); self.set_font('Helvetica','',8); self.set_text_color(100,100,100); self.cell(0,8,f'Page {self.page_no()}',align='C')
    def heading(self,t,size=14):
        self.set_font('Helvetica','B',size); self.set_text_color(25,65,120); self.multi_cell(0,8,t); self.ln(2)
    def p(self,t):
        self.set_font('Helvetica','',9); self.set_text_color(30,30,30); self.multi_cell(0,4.8,t); self.ln(1)

def build():
    pdf=Guide('P','mm','A4'); pdf.set_auto_page_break(True,15); pdf.set_margins(15,15,15); pdf.add_page()
    pdf.heading('BevIQ / beverage_db\nCode Explanation Study Guide',16)
    pdf.p('Yeh separate study PDF hai. Project ke source code mein koi feature add ya change nahi kiya gaya. Hinglish mein file-by-file, function-by-function aur line-by-line reading guide diya gaya hai.')
    pdf.heading('1. Project ko ek line mein samjho',12)
    pdf.p('Browser question bhejta hai -> Flask app.py receive karta hai -> rag_orchestrator intent decide karta hai -> SQL/comparison/document/vector/UPC engine data nikalta hai -> optional Ollama language answer banata hai -> JSON frontend ko milta hai -> index.html chat/table dikhata hai.')
    for t in ['Flask: web server aur REST API routes.','SQLite: offline local indexed database; CSV ko har query par scan nahi karna padta.','MySQL: optional DBeaver/shared database; SQLite fallback available hai.','RAG: relevant records/chunks retrieve karke unke basis par answer.','Ollama: local LLM; optional conversational synthesis, exact truth source nahi.','Vector index: yahan BM25-style token scoring hai; FAISS/dense embeddings nahi.','UPC normalization: scientific notation/decimal/prefix se clean 13-digit string, leading zero safe.']:
        pdf.p('- '+t)
    pdf.heading('2. RAG aur Ollama kyun?',12)
    pdf.p('RAG ka matlab Retrieval Augmented Generation hai: pehle apne database/document se relevant context, phir us context par answer. Exact UPC, count aur comparison code/SQL se calculate hote hain. Ollama local llama3.2 jaise model ko call karta hai, taaki retrieved facts ko natural English/Hinglish mein explain kiya ja sake. Ollama down ho tab deterministic offline answer available rehta hai.')
    pdf.heading('3. Core source files: line-by-line',12)
    for rel in FILES:
        path=ROOT/rel
        if not path.exists(): continue
        pdf.add_page(); pdf.heading('File: '+rel,12); pdf.p('Pehle source line padho, phir uski explanation. Blank lines bhi include hain taaki original numbering follow ho.')
        for n,line in enumerate(path.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            if pdf.get_y()>270: pdf.add_page()
            pdf.set_font('Courier','',7); pdf.set_text_color(20,20,20); pdf.multi_cell(0,3.4,ascii_text(f'{n:4}: {line.replace(chr(9),"    ")[:220]}'),new_x='LMARGIN',new_y='NEXT')
            if pdf.get_y()>270: pdf.add_page()
            pdf.set_font('Helvetica','I',7.3); pdf.set_text_color(80,80,80); pdf.multi_cell(0,3.4,ascii_text('     '+why(line)),new_x='LMARGIN',new_y='NEXT')
    pdf.add_page(); pdf.heading('4. Tools, frontend aur tests ka purpose',12)
    pdf.p('tools/inspect_data.py delimiter, columns aur row count inspect karta hai. deep_data_analysis.py UPC duplicates/scientific notation/overlap nikalta hai. beer_rtd_check.py cross-category overlap dekhta hai. supplier_check.py supplier code integrity check karta hai. full_profile.py dataset profiling JSON banata hai. missing_upc_matcher.py aur v2/v3/v4 conservative fuzzy product matching aur reports ke iterations hain. generate_project_pdf scripts documentation PDF banate hain. tests/ endpoint, RAG routing, UPC matching, cached Ollama status aur read-only behavior verify karte hain.')
    pdf.p('templates/index.html browser UI hai: chat form FormData bhejta hai, comparison buttons API call karte hain, returned records ko table/status badge/CSV link mein render karta hai. Frontend backend ki business logic nahi karta; backend result ka presentation karta hai.')
    pdf.add_page(); pdf.heading('5. Complete function and class catalog',12)
    pdf.p('Yeh quick revision index hai. Project ke Python files se saare classes aur functions nikale gaye hain. Detailed source line explanation upar file sections mein hai.')
    all_files = FILES + [str(p.relative_to(ROOT)) for p in (ROOT / 'tools').glob('*.py') if p.name != Path(__file__).name] + [str(p.relative_to(ROOT)) for p in (ROOT / 'tests').glob('*.py')]
    seen = set()
    for rel in all_files:
        if rel in seen or not (ROOT / rel).exists():
            continue
        seen.add(rel)
        entries = function_catalog(ROOT / rel)
        if not entries:
            continue
        pdf.set_font('Helvetica','B',10); pdf.set_text_color(180,80,20); pdf.multi_cell(0,6,ascii_text(rel),new_x='LMARGIN',new_y='NEXT')
        for name, line, purpose in entries:
            if pdf.get_y()>270: pdf.add_page()
            pdf.set_font('Courier','B',7.5); pdf.set_text_color(25,25,25); pdf.multi_cell(0,3.8,ascii_text(f'Line {line}: {name}'),new_x='LMARGIN',new_y='NEXT')
            lookup_name = name.replace(' -> ', '.')
            module_name = rel.replace('\\', '.').replace('/', '.').rsplit('.py', 1)[0]
            detailed = DETAILS.get(lookup_name) or DETAILS.get(module_name + '.' + lookup_name) or DETAILS.get(rel.rsplit('.', 1)[0]) or purpose
            pdf.set_font('Helvetica','',8); pdf.set_text_color(55,55,55); pdf.multi_cell(0,4.2,ascii_text('Purpose / Why: '+detailed),new_x='LMARGIN',new_y='NEXT')
    pdf.add_page(); pdf.heading('6. Kaunsi language kyun use hui?',12)
    pdf.p('Python: main backend language. Flask routes, CSV cleaning, UPC normalization, database queries, RAG routing, BM25 scoring, document extraction aur Ollama API calls Python mein hain. Python choose hua kyunki pandas, Flask, SQLite, PDF/DOCX readers aur AI ecosystem strong hai; data-heavy logic readable rehta hai.')
    pdf.p('HTML: templates/index.html browser ka structure banata hai - header, chat box, tabs, buttons, tables aur upload controls. HTML decide karta hai page par kaunse elements exist karenge.')
    pdf.p('CSS: index.html ke style section mein colors, dark dashboard layout, cards, buttons, responsive grid, badges aur scrolling tables define hote hain. CSS ka kaam appearance hai, business/data logic nahi.')
    pdf.p('JavaScript: browser-side interaction handle karta hai. fetch() se /api/chat, /api/compare aur export endpoints call hote hain; FormData file upload karta hai; returned JSON ko chat bubbles aur tables mein convert karta hai. Isse page reload ke bina live UI milti hai.')
    pdf.p('SQL: SQLite aur MySQL tables se exact search, COUNT, JOIN, GROUP BY, duplicate audit aur missing-record comparison ke liye. SQL deterministic hai, isliye exact UPC/count ke liye LLM se better hai.')
    pdf.p('JSON: frontend-backend communication format. Flask jsonify() se answer, records, source_files, record_count aur download_token browser ko milte hain. JSON config/analysis reports mein bhi use hua hai.')
    pdf.p('CSV: original business datasets ka storage format. Pipe (|) aur comma delimiters alag files mein hain; loader delimiter config se read karta hai. CSV reports user download kar sakta hai.')
    pdf.p('Markdown: assistant answers headings, bullets, tables aur code formatting ke liye banata hai. Frontend ka parseSimpleMarkdown() us text ko HTML presentation mein badalta hai.')
    pdf.p(' .env simple KEY=VALUE settings rakhta hai. requirements.txt Python dependencies ka manifest hai. Pickle binary format persistent local vector index save karne ke liye use hua hai.')
    pdf.heading('7. Languages ka combined request flow',12)
    pdf.p('HTML form + JavaScript FormData -> Flask/Python route -> Python RAG/SQL engine -> SQLite SQL result -> Python JSON response -> JavaScript JSON parsing -> HTML table + CSS styling. Agar wording natural banani ho aur Ollama online ho, Python retrieved context ko local LLM ko bhejta hai; final answer Markdown mein aata hai.')
    pdf.heading('8. Kisi ko explain karne ka ready answer',12)
    pdf.p('BevIQ local beverage intelligence application hai. CSV files pehle normalize hokar SQLite tables aur indexes banti hain. Flask browser/API requests leta hai. RAG orchestrator query ko route karta hai: exact lookup ke liye SQL, cross-file gap ke liye comparison engine, uploaded PDF ke liye document chunks, product UPC review ke liye UPC match engine, aur fuzzy catalog retrieval ke liye BM25 vector engine. Ollama optional local LLM hai jo retrieved facts ko conversational answer mein likhta hai. Isliye app offline/private, traceable source-row based aur CSV-exportable hai.')
    pdf.output(str(OUT)); print(OUT)

if __name__=='__main__': build()
