#!/usr/bin/env python3
"""
Surgical Billing Automation - Web Application
Flask-based web server for document extraction and billing
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pytesseract
from surgical_billing_extractor import SurgicalBillingProcessor
from billing_form_generator import BillingFormGenerator

# ============================================================================
# SETUP TESSERACT
# ============================================================================

def setup_tesseract():
    """Find and configure Tesseract-OCR"""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",  # Linux
        "/usr/local/bin/tesseract",  # macOS
    ]

    for path in possible_paths:
        if Path(path).exists():
            pytesseract.pytesseract_cmd = path
            print(f"[✓] Tesseract found at: {path}")
            return True

    print("[!] Tesseract-OCR not found. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    return False

setup_tesseract()

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/surgical_billing_uploads'

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file upload and extraction"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')

        if not files:
            return jsonify({'error': 'No files selected'}), 400

        # Create case folder
        case_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_folder = os.path.join(app.config['UPLOAD_FOLDER'], case_id)
        os.makedirs(case_folder, exist_ok=True)

        # Save files
        saved_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(case_folder, filename)
                file.save(filepath)
                saved_files.append(filename)

        if not saved_files:
            return jsonify({'error': 'No valid files uploaded'}), 400

        # Process files
        processor = SurgicalBillingProcessor()
        data, issues, results = processor.process_patient_folder(case_folder)

        # Generate drafts
        generator = BillingFormGenerator()
        cms1500 = generator.build_cms1500(convert_data_to_dict(data))
        ub04 = generator.build_ub04(convert_data_to_dict(data))

        # Prepare response
        response = {
            'success': True,
            'case_id': case_id,
            'files_processed': saved_files,
            'patient_data': convert_data_to_dict(data),
            'validation_issues': issues,
            'cms1500_draft': cms1500.__dict__,
            'ub04_draft': ub04.__dict__,
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/generate-json', methods=['POST'])
def generate_json():
    """Generate downloadable JSON"""
    try:
        data = request.json

        filename = f"billing_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return jsonify({
            'success': True,
            'filename': filename,
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/health')
def health():
    """Health check endpoint for Railway"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def convert_data_to_dict(data):
    """Convert PatientBillingData to dictionary"""
    return {
        'patient_name': data.patient_name,
        'patient_dob': data.patient_dob,
        'patient_ssn': data.patient_ssn,
        'patient_address': data.patient_address,
        'patient_phone': data.patient_phone,
        'insurance_member_id': data.insurance_member_id,
        'insurance_group_number': data.insurance_group_number,
        'insurance_payer_name': data.insurance_payer_name,
        'insurance_plan_type': data.insurance_plan_type,
        'insurance_deductible': data.insurance_deductible,
        'insurance_coinsurance_pct': data.insurance_coinsurance_pct,
        'procedure_name': data.procedure_name,
        'procedure_date': data.procedure_date,
        'cpt_primary': data.cpt_primary,
        'diagnosis_primary': data.diagnosis_primary,
        'laterality': data.laterality,
        'surgeon_name': data.surgeon_name,
        'surgeon_npi': data.surgeon_npi,
        'facility_name': data.facility_name,
        'facility_npi': data.facility_npi,
        'facility_tax_id': data.facility_tax_id,
        'base_charge': float(data.base_charge),
        'anesthesia_charge': float(data.anesthesia_charge),
        'facility_charge': float(data.facility_charge),
    }

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
