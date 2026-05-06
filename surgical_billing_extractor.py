#!/usr/bin/env python3
"""
Surgical Center Billing Automation - Data Extraction & Validation
Extracts billing data from scanned surgical documents, validates, and flags uncertainties.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
from PIL import Image
import difflib

# ============================================================================
# DATA SCHEMA
# ============================================================================

@dataclass
class PatientBillingData:
    """Complete billing data for a surgical procedure"""
    # Patient demographics
    patient_name: str = ""
    patient_dob: str = ""
    patient_ssn: str = ""
    patient_address: str = ""
    patient_phone: str = ""

    # Insurance
    insurance_member_id: str = ""
    insurance_group_number: str = ""
    insurance_payer_name: str = ""
    insurance_plan_type: str = ""  # PPO, POS, etc.
    insurance_deductible: str = ""
    insurance_deductible_met: str = ""
    insurance_coinsurance_pct: str = ""

    # Procedure
    procedure_name: str = ""
    procedure_date: str = ""
    procedure_time: str = ""
    cpt_primary: str = ""
    cpt_secondary: List[str] = None
    diagnosis_primary: str = ""
    diagnosis_secondary: List[str] = None
    laterality: str = ""  # L/R/Bilateral

    # Provider
    surgeon_name: str = ""
    surgeon_npi: str = ""
    anesthesiologist_name: str = ""
    facility_name: str = ""
    facility_npi: str = ""
    facility_tax_id: str = ""

    # Charges
    base_charge: float = 0.0
    anesthesia_charge: float = 0.0
    facility_charge: float = 0.0
    modifier_bilateral: bool = False
    modifier_staged: bool = False

    # Source documents
    source_files: List[str] = None
    extraction_date: str = ""

    def __post_init__(self):
        if self.cpt_secondary is None:
            self.cpt_secondary = []
        if self.diagnosis_secondary is None:
            self.diagnosis_secondary = []
        if self.source_files is None:
            self.source_files = []
        if not self.extraction_date:
            self.extraction_date = datetime.now().isoformat()


@dataclass
class ExtractionResult:
    """Result of field extraction with confidence scoring"""
    field_name: str
    extracted_value: str
    confidence: float  # 0.0-1.0
    source_document: str
    is_uncertain: bool = False
    notes: str = ""
    flagged_for_review: bool = False


# ============================================================================
# OCR & TEXT EXTRACTION
# ============================================================================

class SurgicalDocumentOCR:
    """Handles OCR extraction from PDF and image documents"""

    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.pytesseract_cmd = tesseract_path

    def extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using both text extraction and OCR"""
        text_content = ""

        # Try pdfplumber first (faster, works on PDFs with text layer)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text_content += extracted_text + "\n"
        except:
            pass

        # If no text extracted, fall back to OCR via images
        if not text_content.strip():
            try:
                images = convert_from_path(pdf_path, dpi=200)
                for image in images:
                    text_content += pytesseract.image_to_string(image) + "\n"
            except Exception as e:
                print(f"OCR failed for {pdf_path}: {e}")

        return text_content

    def extract_from_image(self, image_path: str) -> str:
        """Extract text from image file"""
        try:
            image = Image.open(image_path)
            return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"OCR failed for {image_path}: {e}")
            return ""


# ============================================================================
# FIELD EXTRACTION & PATTERN MATCHING
# ============================================================================

class BillingFieldExtractor:
    """Extracts specific billing fields from OCR text"""

    def __init__(self):
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[str, List[str]]:
        """Define regex patterns for each billing field"""
        return {
            # Patient demographics
            'patient_name': [
                r'PATIENT\s*:?\s*([A-Z][a-zA-Z\s]+)',
                r'Patient Name\s*:?\s*([A-Za-z\s]+)',
                r'Name\s*(?:Last|First).*?([A-Z][a-zA-Z\s]+)',
            ],
            'patient_dob': [
                r'D\.O\.B\.?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'Date of Birth\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'DOB\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'patient_ssn': [
                r'SSN\s*:?\s*(\d{3}[-]?\d{2}[-]?\d{4})',
                r'Social Security\s*:?\s*(\d{3}[-]?\d{2}[-]?\d{4})',
                r'Seguro Social\s*:?\s*(\d{3}[-]?\d{2}[-]?\d{4})',
            ],
            'insurance_member_id': [
                r'Member ID\s*:?\s*([A-Z0-9]+)',
                r'Member\s*(?:ID|#)\s*:?\s*([A-Z0-9]+)',
                r'Policy\s*(?:ID|Number)\s*:?\s*([A-Z0-9]+)',
            ],
            'insurance_group_number': [
                r'Group\s*(?:#|Number)\s*:?\s*([A-Z0-9]+)',
                r'Group\s*:?\s*([A-Z0-9]+)',
            ],
            'cpt_primary': [
                r'CPT\s*(?:Code|#)\s*:?\s*(\d{5})',
                r'Procedure Code\s*:?\s*(\d{5})',
                r'CPT\s*1\s*:?\s*(\d{5})',
            ],
            'procedure_date': [
                r'Surgery Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'Date of Service\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'Date of Procedure\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'surgeon_name': [
                r'Surgeon\s*:?\s*([A-Z][a-zA-Z\s]+)',
                r'Physician\s*/\s*Surgeon\s*:?\s*([A-Z][a-zA-Z\s]+)',
            ],
            'surgeon_npi': [
                r'Surgeon NPI\s*:?\s*(\d{10})',
                r'NPI\s*:?\s*(\d{10})',
            ],
            'facility_tax_id': [
                r'Tax ID\s*:?\s*(\d{2}[-]?\d{7})',
                r'EIN\s*:?\s*(\d{2}[-]?\d{7})',
            ],
            'facility_npi': [
                r'Facility NPI\s*:?\s*(\d{10})',
                r'NPI\s*1922138817',
            ],
            'diagnosis_primary': [
                r'Diagnosis\s*(?:Primary|1)\s*:?\s*([A-Z]\d{2}\.?\d*[A-Z]*)',
                r'ICD-10.*?:\s*([A-Z]\d{2}\.?\d*[A-Z]*)',
            ],
            'insurance_deductible': [
                r'deductible\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
                r'Deductible.*?\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            ],
        }

    def extract_fields(self, text: str, doc_type: str) -> Dict[str, ExtractionResult]:
        """Extract all relevant fields from OCR text"""
        results = {}

        for field_name, patterns in self.patterns.items():
            value = ""
            confidence = 0.0
            matched_pattern = None

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Take longest match (usually most complete)
                    value = max(matches, key=len)
                    confidence = min(0.95, 0.7 + (len(matches) * 0.1))
                    matched_pattern = pattern
                    break

            is_uncertain = confidence < 0.7
            flagged = is_uncertain or not value

            results[field_name] = ExtractionResult(
                field_name=field_name,
                extracted_value=value,
                confidence=confidence,
                source_document=doc_type,
                is_uncertain=is_uncertain,
                flagged_for_review=flagged,
                notes=f"Matched pattern: {matched_pattern}" if value else "No match found"
            )

        return results


# ============================================================================
# VALIDATION & CONFLICT RESOLUTION
# ============================================================================

class BillingDataValidator:
    """Validates and reconciles extracted billing data"""

    def __init__(self):
        self.issues = []

    def validate_patient_data(self, data: PatientBillingData) -> List[str]:
        """Validate patient demographics"""
        issues = []

        if not data.patient_name:
            issues.append("Missing patient name")
        if not data.patient_dob:
            issues.append("Missing date of birth")
        if not data.patient_phone and not data.patient_address:
            issues.append("Missing contact information (phone/address)")

        # Validate format
        if data.patient_dob and not re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', data.patient_dob):
            issues.append(f"Invalid DOB format: {data.patient_dob}")

        if data.patient_ssn and not re.match(r'\d{3}-?\d{2}-?\d{4}', data.patient_ssn):
            issues.append(f"Invalid SSN format: {data.patient_ssn}")

        return issues

    def validate_insurance_data(self, data: PatientBillingData) -> List[str]:
        """Validate insurance information"""
        issues = []

        if not data.insurance_member_id:
            issues.append("Missing member ID (CRITICAL for billing)")
        if not data.insurance_payer_name:
            issues.append("Missing payer name")
        if not data.insurance_group_number:
            issues.append("Missing group number")

        return issues

    def validate_procedure_data(self, data: PatientBillingData) -> List[str]:
        """Validate procedure/diagnosis information"""
        issues = []

        if not data.cpt_primary:
            issues.append("Missing primary CPT code (CRITICAL for billing)")
        elif not re.match(r'^\d{5}', data.cpt_primary):
            issues.append(f"Invalid CPT format: {data.cpt_primary}")

        if not data.diagnosis_primary:
            issues.append("Missing primary diagnosis code")

        if not data.procedure_date:
            issues.append("Missing date of service")
        elif not re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', data.procedure_date):
            issues.append(f"Invalid procedure date format: {data.procedure_date}")

        return issues

    def validate_provider_data(self, data: PatientBillingData) -> List[str]:
        """Validate provider information"""
        issues = []

        if not data.surgeon_name:
            issues.append("Missing surgeon name")
        if not data.surgeon_npi:
            issues.append("Missing surgeon NPI")
        elif not re.match(r'^\d{10}', data.surgeon_npi):
            issues.append(f"Invalid NPI format: {data.surgeon_npi}")

        if not data.facility_npi:
            issues.append("Missing facility NPI")
        if not data.facility_tax_id:
            issues.append("Missing facility tax ID")

        return issues

    def validate_all(self, data: PatientBillingData) -> Dict[str, List[str]]:
        """Run all validations"""
        return {
            'patient': self.validate_patient_data(data),
            'insurance': self.validate_insurance_data(data),
            'procedure': self.validate_procedure_data(data),
            'provider': self.validate_provider_data(data),
        }


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

class SurgicalBillingProcessor:
    """Main orchestrator for billing data extraction and validation"""

    def __init__(self, tesseract_path: Optional[str] = None):
        self.ocr = SurgicalDocumentOCR(tesseract_path)
        self.extractor = BillingFieldExtractor()
        self.validator = BillingDataValidator()
        self.extraction_results = []

    def process_patient_folder(self, folder_path: str) -> PatientBillingData:
        """Process all documents in a folder for a single patient/case"""
        folder = Path(folder_path)
        data = PatientBillingData()
        data.source_files = []

        # Find all PDF and image files
        files = list(folder.glob("*.pdf")) + list(folder.glob("*.pdf")) + \
                list(folder.glob("*.png")) + list(folder.glob("*.jpg"))

        print(f"Processing {len(files)} documents from {folder_path}")

        for file_path in files:
            print(f"  → {file_path.name}")
            data.source_files.append(str(file_path))

            # Extract text
            if file_path.suffix.lower() == '.pdf':
                text = self.ocr.extract_from_pdf(str(file_path))
            else:
                text = self.ocr.extract_from_image(str(file_path))

            # Identify document type and extract fields
            doc_type = self._identify_document_type(file_path.name, text)
            field_results = self.extractor.extract_fields(text, doc_type)
            self.extraction_results.extend(field_results.values())

            # Merge extracted fields into data (highest confidence wins)
            self._merge_fields(data, field_results)

        # Validate all data
        validation_issues = self.validator.validate_all(data)

        return data, validation_issues, self.extraction_results

    def _identify_document_type(self, filename: str, text: str) -> str:
        """Identify document type based on filename and content"""
        filename_lower = filename.lower()

        if 'scheduling' in filename_lower:
            return 'surgery_scheduling'
        elif 'intake' in filename_lower or 'registration' in filename_lower:
            return 'patient_intake'
        elif 'insurance' in filename_lower or 'verification' in filename_lower:
            return 'insurance_verification'
        elif 'confirmation' in filename_lower or 'checklist' in filename_lower:
            return 'facility_confirmation'
        elif 'consent' in filename_lower or 'authorization' in filename_lower:
            return 'surgical_consent'
        elif 'physician' in filename_lower or 'orders' in filename_lower:
            return 'physician_orders'
        else:
            return 'unknown'

    def _merge_fields(self, data: PatientBillingData, field_results: Dict[str, ExtractionResult]):
        """Merge extracted fields into patient data (highest confidence wins)"""
        for field_name, result in field_results.items():
            if result.extracted_value and result.confidence > 0.5:
                current_value = getattr(data, field_name, "")
                # Only update if empty or new value has higher confidence
                if not current_value:
                    setattr(data, field_name, result.extracted_value)


def main():
    """Example usage"""
    processor = SurgicalBillingProcessor()

    # Process sample folder
    sample_folder = "/sessions/epic-blissful-ride/mnt/culver"
    data, issues, results = processor.process_patient_folder(sample_folder)

    print("\n" + "="*60)
    print("EXTRACTED BILLING DATA")
    print("="*60)
    print(json.dumps(asdict(data), indent=2, default=str))

    print("\n" + "="*60)
    print("VALIDATION ISSUES")
    print("="*60)
    for category, issue_list in issues.items():
        if issue_list:
            print(f"\n{category.upper()}:")
            for issue in issue_list:
                print(f"  ⚠️  {issue}")

    print("\n" + "="*60)
    print("FIELD EXTRACTION DETAILS")
    print("="*60)
    for result in results:
        if result.flagged_for_review:
            print(f"🚩 {result.field_name} (confidence: {result.confidence:.0%})")
            print(f"   Value: {result.extracted_value}")
            print(f"   Source: {result.source_document}")


if __name__ == "__main__":
    main()
