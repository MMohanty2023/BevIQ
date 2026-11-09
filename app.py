import os
import io
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from config import REPORTS_DIR, MYSQL_PORT, MYSQL_DB, OLLAMA_MODEL, CSV_FILES
from database.db_manager import DBManager, db_manager
from database.mysql_migrator import migrate_data_to_mysql
from engines.sql_engine import sql_engine
from engines.comparison_engine import comparison_engine
from engines.vector_engine import vector_engine
from engines.rag_orchestrator import rag_orchestrator
from data_ingestion.loader import ingest_all_to_sqlite
from document_rag import ingest as ingest_document, list_documents
from engines.upc_match_engine import upc_match_engine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = 'beverage-data-assistant-secret-key-2026'

@app.route('/')
def index():
    return render_template('index.html', ollama_model=OLLAMA_MODEL)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.form if request.form else (request.get_json() or {})
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default-session')
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    try:
        uploaded = None
        if 'file' in request.files and request.files['file'].filename:
            uploaded = ingest_document(request.files['file'], session_id)
        response = rag_orchestrator.route_and_execute(message, session_id=session_id)
        if uploaded:
            response['uploaded_document'] = uploaded
        return jsonify(response)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'answer': f"### ⚠️ Error processing query\n\n`{str(e)}`",
            'source_files': [],
            'record_count': 0,
            'records': [],
            'download_token': None
        }), 500

@app.route('/api/documents', methods=['GET'])
def api_documents():
    return jsonify({'documents': list_documents(request.args.get('session_id', 'default-session'))})

@app.route('/api/upc-audit', methods=['POST'])
def api_upc_audit():
    data = request.get_json() or {}
    category = data.get('category')
    limit = None if data.get('full_review') else max(1, min(int(data.get('limit', 100)), 1000))
    records = upc_match_engine.audit(category, limit)
    import uuid
    token = str(uuid.uuid4())[:8]
    columns = list(records[0].keys()) if records else [
        'category', 'status', 'current_upc', 'suggested_upc', 'alternate_upc',
        'confidence', 'source_file', 'source_row', 'source_brand', 'source_product',
        'source_flavour', 'source_size', 'source_category', 'master_brand',
        'master_product', 'master_size', 'master_row', 'remarks'
    ]
    import pandas as pd
    pd.DataFrame(records, columns=columns).to_csv(REPORTS_DIR / f'report_{token}.csv', index=False)
    return jsonify({'records': records, 'record_count': len(records), 'download_token': token,
                    'columns': columns, 'read_only': True,
                    'message': 'Review-only report. No master product or UPC was changed.'})

@app.route('/api/compare', methods=['POST'])
def api_compare():
    data = request.get_json() or {}
    comp_type = data.get('type', 'all_missing')
    limit = int(data.get('limit', 250))
    search = (data.get('search') or '').strip()[:100]

    try:
        if comp_type == 'all_missing':
            res = comparison_engine.compare_all_missing_in_master(limit_per_category=limit, search=search or None)
        elif comp_type == 'master_vs_beer':
            res = comparison_engine.compare_master_vs_categorization('cat_beer', limit=limit, search=search or None)
        elif comp_type == 'master_vs_rtd':
            res = comparison_engine.compare_master_vs_categorization('cat_rtd', limit=limit, search=search or None)
        elif comp_type == 'master_vs_spirits':
            res = comparison_engine.compare_master_vs_categorization('cat_spirits', limit=limit, search=search or None)
        elif comp_type == 'master_vs_wine':
            res = comparison_engine.compare_master_vs_categorization('cat_wine', limit=limit, search=search or None)
        elif comp_type == 'allbrand_vs_supplier':
            res = comparison_engine.compare_allbrand_vs_supplier(limit=limit)
        elif comp_type == 'beer_vs_rtd':
            res = comparison_engine.compare_beer_vs_rtd(limit=limit)
        elif comp_type == 'duplicate_upcs':
            res = comparison_engine.find_duplicate_upcs_across_all(limit=limit)
        elif comp_type == 'untrained_brands':
            res = comparison_engine.find_untrained_brands(limit=limit, search=search or None)
        else:
            return jsonify({'error': f"Unknown comparison type: {comp_type}"}), 400

        # Create download token
        import uuid, pandas as pd
        token = str(uuid.uuid4())[:8]
        export_records = res.pop('export_records', None)
        if export_records is None:
            export_records = res.get('records')
        if export_records:
            df = pd.DataFrame(export_records)
            df.to_csv(REPORTS_DIR / f"report_{token}.csv", index=False)
        res['download_token'] = token

        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/untrained-dataset', methods=['GET'])
def api_untrained_dataset():
    original_db = getattr(comparison_engine, 'db', None)
    try:
        limit = max(1, min(int(request.args.get('limit', 250)), 50000))
        search = (request.args.get('search') or '').strip()[:100]
        if getattr(db_manager, 'use_mysql', False):
            mysql_ready, _ = db_manager.mysql_schema_status()
            if not mysql_ready and original_db is not None:
                comparison_engine.db = DBManager(use_mysql=False)
        result = comparison_engine.find_untrained_brands(limit=limit, search=search or None)
        result.pop('export_records', None)
        return jsonify({
            'backend': comparison_engine.db.backend_name() if original_db is not None else db_manager.backend_name(),
            **result,
        })
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid untrained dataset limit'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if original_db is not None:
            comparison_engine.db = original_db

@app.route('/api/stats', methods=['GET'])
def api_stats():
    try:
        overview = sql_engine.get_dataset_overview()
        total_records = sum(item['total_rows'] for item in overview)
        total_upcs = sum(item['unique_upcs'] for item in overview)
        return jsonify({
            'total_records': total_records,
            'total_unique_upcs': total_upcs,
            'datasets': overview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/overview', methods=['GET'])
def api_dashboard_overview():
    try:
        overview = sql_engine.get_dataset_overview()
        total_records = sum(int(item.get('total_rows') or 0) for item in overview)
        total_upcs = sum(int(item.get('unique_upcs') or 0) for item in overview)
        return jsonify({
            'backend': db_manager.backend_name(),
            'kpis': {
                'total_records': total_records,
                'total_unique_upcs': total_upcs,
                'dataset_count': len(overview),
            },
            'datasets': overview,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/metrics', methods=['GET'])
def api_dashboard_metrics():
    """Return live category, UPC quality, and Master Brand dashboard metrics."""
    try:
        return jsonify({
            'backend': db_manager.backend_name(),
            **sql_engine.get_dashboard_metrics(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/suppliers', methods=['GET'])
def api_dashboard_suppliers():
    try:
        limit = max(1, min(int(request.args.get('limit', 500)), 500))
        directory_kwargs = {'limit': limit}
        if 'include_records' in request.args:
            directory_kwargs['include_records'] = request.args.get('include_records', '1').lower() in {'1', 'true', 'yes'}
        return jsonify({
            'backend': db_manager.backend_name(),
            **sql_engine.get_supplier_directory(**directory_kwargs),
        })
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a valid number'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/supplier-brand-details', methods=['GET'])
def api_dashboard_supplier_brand_details():
    supplier = (request.args.get('supplier') or '').strip()
    brand = (request.args.get('brand') or '').strip()
    if not supplier or not brand:
        return jsonify({'error': 'supplier and brand are required'}), 400
    try:
        return jsonify({
            'backend': db_manager.backend_name(),
            **sql_engine.get_supplier_brand_details(supplier, brand),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _trained_request_filters():
    filters = {
        'query': (request.args.get('q') or '').strip(),
        'category': (request.args.get('category') or '').strip(),
        'supplier': (request.args.get('supplier') or '').strip(),
        'brand': (request.args.get('brand') or '').strip(),
        'status': (request.args.get('status') or '').strip(),
        'model': (request.args.get('model') or '').strip(),
    }
    for key in ('missing_sku', 'missing_images', 'missing_model_id'):
        filters[key] = request.args.get(key, '').lower() in {'1', 'true', 'yes'}
    for key in ('min_images', 'max_images'):
        value = request.args.get(key)
        if value not in (None, ''):
            filters[key] = max(0, int(value))
    return filters

@app.route('/api/trained-dataset/summary', methods=['GET'])
def api_trained_dataset_summary():
    try:
        return jsonify({'backend': db_manager.backend_name(), **sql_engine.get_trained_dataset_summary(_trained_request_filters())})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid trained dataset filter'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trained-dataset/analytics', methods=['GET'])
def api_trained_dataset_analytics():
    try:
        return jsonify({'backend': db_manager.backend_name(), **sql_engine.get_trained_dataset_analytics(_trained_request_filters())})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid trained dataset filter'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trained-dataset/records', methods=['GET'])
def api_trained_dataset_records():
    try:
        page = max(1, int(request.args.get('page', 1)))
        page_size = max(1, min(int(request.args.get('page_size', 50)), 200))
        return jsonify({'backend': db_manager.backend_name(), **sql_engine.search_trained_brands(
            page=page, page_size=page_size,
            sort_by=request.args.get('sort_by', 'BrandName'), sort_dir=request.args.get('sort_dir', 'asc'),
            **_trained_request_filters(),
        )})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid trained dataset pagination or filter'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trained-dataset/detail/<record_id>', methods=['GET'])
def api_trained_dataset_detail(record_id):
    try:
        payload = sql_engine.get_trained_brand_detail(record_id)
        if not payload.get('record'):
            return jsonify({'error': 'Trained brand record not found'}), 404
        return jsonify({'backend': db_manager.backend_name(), **payload})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trained-dataset/export', methods=['GET'])
def api_trained_dataset_export():
    try:
        filters = _trained_request_filters()
        records = []
        page = 1
        while len(records) < 50000:
            batch = sql_engine.search_trained_brands(page=page, page_size=200, **filters).get('records', [])
            if not batch:
                break
            records.extend(batch)
            page += 1
        token = str(__import__('uuid').uuid4())[:8]
        pd.DataFrame(records[:50000]).to_csv(REPORTS_DIR / f'report_{token}.csv', index=False)
        return jsonify({'download_token': token, 'record_count': len(records[:50000])})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid trained dataset filter'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/master-brands/search', methods=['GET'])
def api_master_brand_search():
    master_id = (request.args.get('id') or '').strip()
    brand = (request.args.get('brand') or '').strip()
    upc = (request.args.get('upc') or '').strip()
    product = (request.args.get('product') or '').strip()
    query = (request.args.get('q') or '').strip()
    if not any((master_id, brand, upc, product, query)):
        return jsonify({'error': 'Provide a Master Brand ID, brand, UPC, product, or search term'}), 400
    try:
        limit = max(1, min(int(request.args.get('limit', 100)), 500))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a valid number'}), 400
    try:
        return jsonify(sql_engine.search_master_brands(
            query=query, master_id=master_id or None, brand=brand or None,
            upc=upc or None, product=product or None, limit=limit,
        ))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/master-brands/export', methods=['GET'])
def api_master_brand_export():
    response = api_master_brand_search()
    if isinstance(response, tuple):
        return response
    if response.status_code != 200:
        return response
    payload = response.get_json()
    token = str(__import__('uuid').uuid4())[:8]
    frame = pd.DataFrame(payload.get('records') or [], columns=payload.get('columns') or None)
    frame.to_csv(REPORTS_DIR / f'report_{token}.csv', index=False)
    return jsonify({**payload, 'download_token': token})

@app.route('/api/dashboard/categories', methods=['GET'])
def api_dashboard_categories():
    try:
        return jsonify({'backend': db_manager.backend_name(), 'categories': sql_engine.count_by_category()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/missing-upc', methods=['GET'])
def api_dashboard_missing_upc():
    try:
        limit = max(1, min(int(request.args.get('limit', 100)), 500))
        search = (request.args.get('search') or '').strip()[:100]
        result = comparison_engine.compare_all_missing_in_master(limit_per_category=limit, search=search or None)
        return jsonify({'backend': db_manager.backend_name(), **result})
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a valid number'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/export/<dataset>', methods=['GET'])
def api_dashboard_export(dataset):
    if dataset not in CSV_FILES:
        return jsonify({'error': f'Unknown dataset: {dataset}'}), 400
    try:
        limit = max(1, min(int(request.args.get('limit', 50000)), 50000))
        table = CSV_FILES[dataset]['table']
        rows = db_manager.query(f"SELECT * FROM `{table}` LIMIT {limit}")
        frame = pd.DataFrame(rows)
        content = frame.to_csv(index=False).encode('utf-8')
        return send_file(io.BytesIO(content), as_attachment=True,
                         download_name=f'beviq_{dataset}.csv', mimetype='text/csv')
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a valid number'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/db-status', methods=['GET'])
def api_db_status():
    database = db_manager.database_status()
    ollama_ok = rag_orchestrator.is_ollama_available()
    return jsonify({
        **database,
        'mysql_port': MYSQL_PORT,
        'mysql_db': MYSQL_DB,
        'ollama_connected': ollama_ok,
        'ollama_model': OLLAMA_MODEL
    })

@app.route('/api/configure-db', methods=['POST'])
def api_configure_db():
    data = request.get_json() or {}
    password = data.get('password', '')
    migrate = data.get('migrate', False)

    db_manager.mysql_password = password
    ok, msg = db_manager.test_mysql_connection(password=password)

    if not ok:
        db_manager.set_mysql_backend(True)
        return jsonify({'success': False, 'message': msg}), 400

    db_manager.set_mysql_backend(True)

    if migrate:
        mig_ok, mig_msg = migrate_data_to_mysql(
            password=password,
            replace_existing=bool(data.get('replace_existing', False)),
        )
        return jsonify({'success': mig_ok, 'message': mig_msg, 'backend': db_manager.backend_name()})

    return jsonify({'success': True, 'message': f"Connected to MySQL on port {MYSQL_PORT} successfully!",
                    'backend': db_manager.backend_name()})

@app.route('/api/rebuild-index', methods=['POST'])
def api_rebuild_index():
    try:
        count = vector_engine.build_from_database(limit_per_table=10000)
        return jsonify({'success': True, 'indexed_documents': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-csv/<token>', methods=['GET'])
def api_export_csv(token):
    csv_file = REPORTS_DIR / f"report_{token}.csv"
    if not csv_file.exists():
        return "Report file not found or expired", 404
    return send_file(csv_file, as_attachment=True, download_name=f"beverage_report_{token}.csv", mimetype="text/csv")

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"Starting BevIQ on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
