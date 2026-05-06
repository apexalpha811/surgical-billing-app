#!/usr/bin/env python3
"""
Billing Form Generator
Creates draft CMS-1500 (professional) and UB-04 (facility) billing forms.
"""

import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CMS1500Draft:
    """CMS-1500 Professional Billing Form (837P EDI)"""
    # Claim identification
    claim_id: str = ""
    submission_date: str = ""
    claim_type: str = "1"  # 1=Medical, 2=Dental, 3=Vision, etc.

    # Insurance (Box 1-13)
    patient_full_name: str = ""
    patient_dob: str = ""
    patient_sex: str = ""
    insured_name: str = ""
    insured_dob: str = ""
    insurance_plan_name: str = ""
    member_id: str = ""
    group_number: str = ""

    # Patient info (Box 10)
    claim_codes: List[str] = None  # A-L for various conditions

    # Condition codes
    condition_codes: List[str] = None

    # Diagnosis (Box 21)
    diagnosis_1: str = ""
    diagnosis_2: str = ""
    diagnosis_3: str = ""
    diagnosis_4: str = ""
    diagnosis_5: str = ""
    diagnosis_6: str = ""
    diagnosis_7: str = ""
    diagnosis_8: str = ""

    # Diagnosis pointer (links diagnosis to service lines)
    diagnosis_pointer: List[str] = None

    # Service lines (Box 24)
    service_lines: List['ServiceLine'] = None

    # Provider (Box 31-33)
    rendering_provider_name: str = ""
    rendering_provider_npi: str = ""
    billing_provider_name: str = ""
    billing_provider_npi: str = ""
    billing_provider_tin: str = ""

    # Claim amounts
    total_charge: float = 0.0
    total_paid: float = 0.0
    patient_responsibility: float = 0.0

    def __post_init__(self):
        if self.claim_codes is None:
            self.claim_codes = []
        if self.condition_codes is None:
            self.condition_codes = []
        if self.diagnosis_pointer is None:
            self.diagnosis_pointer = []
        if self.service_lines is None:
            self.service_lines = []
        if not self.submission_date:
            self.submission_date = datetime.now().strftime("%m%d%Y")


@dataclass
class ServiceLine:
    """Individual service line item (Box 24)"""
    line_number: int = 0
    service_date_start: str = ""
    service_date_end: str = ""
    cpt_code: str = ""
    modifier_1: str = ""
    modifier_2: str = ""
    modifier_3: str = ""
    modifier_4: str = ""
    diagnosis_pointer: str = ""
    charge: float = 0.0
    unit_count: float = 1.0
    place_of_service: str = "24"  # 24=ASC
    emergency: bool = False
    epsd: bool = False  # Eligible for Participation


@dataclass
class UB04Draft:
    """UB-04 Facility Billing Form (837I EDI)"""
    # Claim identification
    claim_id: str = ""
    submission_date: str = ""
    statement_covers_from: str = ""
    statement_covers_to: str = ""

    # Provider info (FL 1-5)
    facility_name: str = ""
    facility_address: str = ""
    facility_city: str = ""
    facility_state: str = ""
    facility_zip: str = ""
    facility_npi: str = ""
    facility_ein: str = ""
    facility_type_code: str = "71"  # 71=ASC, 80=Facility

    # Insurance info (FL 8-10)
    insurance_group_name: str = ""
    insurance_group_id: str = ""

    # Patient info (FL 11-23)
    patient_name: str = ""
    patient_address: str = ""
    patient_city: str = ""
    patient_state: str = ""
    patient_zip: str = ""
    patient_dob: str = ""
    patient_sex: str = ""

    # Admission info
    admission_date: str = ""
    admission_type: str = "7"  # 7=Outpatient
    admission_source: str = ""
    discharge_date: str = ""
    discharge_status: str = "01"  # 01=Discharged to home

    # Diagnosis codes (FL 67-75)
    principal_diagnosis: str = ""
    secondary_diagnosis_1: str = ""
    secondary_diagnosis_2: str = ""
    secondary_diagnosis_3: str = ""
    secondary_diagnosis_4: str = ""
    secondary_diagnosis_5: str = ""
    secondary_diagnosis_6: str = ""
    secondary_diagnosis_7: str = ""
    secondary_diagnosis_8: str = ""

    # Procedure codes (FL 74)
    principal_procedure: str = ""
    principal_procedure_date: str = ""
    secondary_procedure_1: str = ""
    secondary_procedure_2: str = ""

    # Revenue codes (FL 42)
    revenue_codes: List['RevenueCode'] = None

    # Totals
    total_charges: float = 0.0
    total_non_covered: float = 0.0
    patient_responsibility: float = 0.0

    def __post_init__(self):
        if self.revenue_codes is None:
            self.revenue_codes = []
        if not self.submission_date:
            self.submission_date = datetime.now().strftime("%m%d%Y")


@dataclass
class RevenueCode:
    """Revenue code line item (FL 42)"""
    revenue_code: str = ""
    description: str = ""
    hcpcs_code: str = ""
    units: float = 1.0
    unit_rate: float = 0.0
    charge: float = 0.0


class BillingFormGenerator:
    """Generate CMS-1500 and UB-04 billing forms from extracted data"""

    def __init__(self):
        self.place_of_service_map = {
            '11': 'Office',
            '12': 'Patient Home',
            '21': 'Inpatient Hospital',
            '22': 'Outpatient Hospital',
            '24': 'Ambulatory Surgical Center',
            '25': 'Patient Enclave',
            '26': 'Hospice',
            '31': 'Skilled Nursing Facility',
            '99': 'Other',
        }

        self.cpt_asc_bundle_map = {
            # Common ASC procedures
            '29881': {'description': 'Knee Arthroscopy', 'base_charge': 4500, 'anesthesia': 800},
            '29882': {'description': 'Knee Arthroscopy - meniscus', 'base_charge': 5200, 'anesthesia': 850},
            '29883': {'description': 'Knee Arthroscopy - chondro', 'base_charge': 5800, 'anesthesia': 900},
            '29884': {'description': 'Knee Arthroscopy - patellofem', 'base_charge': 6200, 'anesthesia': 950},
            '20610': {'description': 'Ankle Injection', 'base_charge': 800, 'anesthesia': 250},
            '64447': {'description': 'Nerve Block', 'base_charge': 1200, 'anesthesia': 400},
        }

    def build_cms1500(self, patient_data: Dict) -> CMS1500Draft:
        """Build a CMS-1500 form from extracted patient data"""
        form = CMS1500Draft()

        # Basic info
        form.claim_id = patient_data.get('chart_id', '')
        form.patient_full_name = patient_data.get('patient_name', '')
        form.patient_dob = patient_data.get('patient_dob', '')
        form.patient_sex = patient_data.get('patient_sex', 'U')

        # Insurance
        form.insured_name = patient_data.get('patient_name', '')
        form.insured_dob = patient_data.get('patient_dob', '')
        form.insurance_plan_name = patient_data.get('insurance_payer_name', '')
        form.member_id = patient_data.get('insurance_member_id', '')
        form.group_number = patient_data.get('insurance_group_number', '')

        # Diagnosis
        form.diagnosis_1 = patient_data.get('diagnosis_primary', '')
        form.diagnosis_2 = patient_data.get('diagnosis_secondary_1', '') if isinstance(patient_data.get('diagnosis_secondary'), list) else ''

        # Provider
        form.rendering_provider_name = patient_data.get('surgeon_name', '')
        form.rendering_provider_npi = patient_data.get('surgeon_npi', '')
        form.billing_provider_tin = patient_data.get('facility_tax_id', '')

        # Service lines
        cpt_code = patient_data.get('cpt_primary', '')
        if cpt_code:
            service_line = ServiceLine(
                line_number=1,
                service_date_start=patient_data.get('procedure_date', ''),
                service_date_end=patient_data.get('procedure_date', ''),
                cpt_code=cpt_code,
                modifier_1='-50' if patient_data.get('laterality') == 'Bilateral' else '',
                diagnosis_pointer='1',
                charge=patient_data.get('base_charge', 0.0),
                place_of_service='24',  # ASC
            )
            form.service_lines.append(service_line)

        # Totals
        form.total_charge = patient_data.get('base_charge', 0.0) + patient_data.get('anesthesia_charge', 0.0)

        return form

    def build_ub04(self, patient_data: Dict) -> UB04Draft:
        """Build a UB-04 form from extracted patient data"""
        form = UB04Draft()

        # Facility info
        form.facility_name = patient_data.get('facility_name', 'Culver City Surgical Specialists')
        form.facility_npi = patient_data.get('facility_npi', '')
        form.facility_ein = patient_data.get('facility_tax_id', '')

        # Patient info
        form.patient_name = patient_data.get('patient_name', '')
        form.patient_dob = patient_data.get('patient_dob', '')
        form.patient_sex = patient_data.get('patient_sex', 'U')

        # Insurance
        form.insurance_group_name = patient_data.get('insurance_payer_name', '')
        form.insurance_group_id = patient_data.get('insurance_group_number', '')

        # Admission (outpatient/same-day)
        form.admission_date = patient_data.get('procedure_date', '')
        form.discharge_date = patient_data.get('procedure_date', '')
        form.admission_type = '7'  # Outpatient

        # Diagnosis
        form.principal_diagnosis = patient_data.get('diagnosis_primary', '')
        form.secondary_diagnosis_1 = patient_data.get('diagnosis_secondary_1', '') if isinstance(patient_data.get('diagnosis_secondary'), list) else ''

        # Procedures
        form.principal_procedure = patient_data.get('cpt_primary', '')
        form.principal_procedure_date = patient_data.get('procedure_date', '')

        # Revenue codes - map CPT to revenue codes
        # Revenue codes: 250=Surgery, 270=Anesthesia, 290=Misc charges
        cpt = patient_data.get('cpt_primary', '')

        if cpt:
            # Surgery revenue
            surgery_rev = RevenueCode(
                revenue_code='250',
                description=f"Surgery - CPT {cpt}",
                hcpcs_code=cpt,
                units=1.0,
                charge=patient_data.get('base_charge', 0.0)
            )
            form.revenue_codes.append(surgery_rev)

            # Anesthesia revenue
            if patient_data.get('anesthesia_charge', 0) > 0:
                anesthesia_rev = RevenueCode(
                    revenue_code='270',
                    description='Anesthesia Services',
                    hcpcs_code='',
                    units=1.0,
                    charge=patient_data.get('anesthesia_charge', 0.0)
                )
                form.revenue_codes.append(anesthesia_rev)

            # Facility revenue
            if patient_data.get('facility_charge', 0) > 0:
                facility_rev = RevenueCode(
                    revenue_code='290',
                    description='Facility/Other Charges',
                    units=1.0,
                    charge=patient_data.get('facility_charge', 0.0)
                )
                form.revenue_codes.append(facility_rev)

        # Totals
        form.total_charges = (patient_data.get('base_charge', 0.0) +
                              patient_data.get('anesthesia_charge', 0.0) +
                              patient_data.get('facility_charge', 0.0))

        return form

    def format_cms1500_text(self, form: CMS1500Draft) -> str:
        """Format CMS-1500 as readable text"""
        lines = [
            "=" * 80,
            "CMS-1500 CLAIM FORM - PROFESSIONAL BILLING",
            "=" * 80,
            f"\nClaim ID: {form.claim_id}",
            f"Submission Date: {form.submission_date}\n",

            "PATIENT INFORMATION:",
            f"  Name: {form.patient_full_name}",
            f"  DOB: {form.patient_dob}",
            f"  Sex: {form.patient_sex}\n",

            "INSURANCE INFORMATION:",
            f"  Payer: {form.insurance_plan_name}",
            f"  Member ID: {form.member_id}",
            f"  Group Number: {form.group_number}\n",

            "DIAGNOSIS CODES:",
            f"  1: {form.diagnosis_1}",
            f"  2: {form.diagnosis_2}\n",

            "PROVIDER INFORMATION:",
            f"  Rendering Provider: {form.rendering_provider_name}",
            f"  Provider NPI: {form.rendering_provider_npi}",
            f"  Billing Provider TIN: {form.billing_provider_tin}\n",

            "SERVICE LINES:",
            "-" * 80,
        ]

        for line in form.service_lines:
            lines.append(
                f"  Line {line.line_number}: {line.cpt_code} {line.modifier_1} "
                f"Date: {line.service_date_start} "
                f"Charge: ${line.charge:,.2f} "
                f"POS: {line.place_of_service}"
            )

        lines.extend([
            "-" * 80,
            f"\nTOTAL CHARGE: ${form.total_charge:,.2f}",
            f"Total Paid by Insurance: ${form.total_paid:,.2f}",
            f"Patient Responsibility: ${form.patient_responsibility:,.2f}",
            "\n⚠️  IMPORTANT NOTES:",
            "  • This is a DRAFT form for review only",
            "  • All fields must be verified before submission",
            "  • Missing or incorrect information must be corrected",
            "  • This form is NOT ready for submission without human review",
            "=" * 80,
        ])

        return "\n".join(lines)

    def format_ub04_text(self, form: UB04Draft) -> str:
        """Format UB-04 as readable text"""
        lines = [
            "=" * 80,
            "UB-04 CLAIM FORM - FACILITY BILLING",
            "=" * 80,
            f"\nClaim ID: {form.claim_id}",
            f"Submission Date: {form.submission_date}",
            f"Statement Covers: {form.statement_covers_from} to {form.statement_covers_to}\n",

            "FACILITY INFORMATION:",
            f"  Name: {form.facility_name}",
            f"  NPI: {form.facility_npi}",
            f"  EIN/Tax ID: {form.facility_ein}\n",

            "PATIENT INFORMATION:",
            f"  Name: {form.patient_name}",
            f"  DOB: {form.patient_dob}",
            f"  Sex: {form.patient_sex}",
            f"  Address: {form.patient_address}\n",

            "ADMISSION INFORMATION:",
            f"  Admission Date: {form.admission_date}",
            f"  Discharge Date: {form.discharge_date}",
            f"  Type: {'Outpatient' if form.admission_type == '7' else 'Inpatient'}\n",

            "DIAGNOSIS CODES:",
            f"  Principal: {form.principal_diagnosis}",
            f"  Secondary 1: {form.secondary_diagnosis_1}\n",

            "PROCEDURES:",
            f"  Principal: {form.principal_procedure}",
            f"  Date: {form.principal_procedure_date}\n",

            "REVENUE CODES & CHARGES:",
            "-" * 80,
            f"{'Code':<8} {'Description':<35} {'Units':>8} {'Charge':>12}",
            "-" * 80,
        ]

        for rev in form.revenue_codes:
            lines.append(
                f"{rev.revenue_code:<8} {rev.description:<35} {rev.units:>8.1f} ${rev.charge:>11,.2f}"
            )

        lines.extend([
            "-" * 80,
            f"\nTOTAL CHARGES: ${form.total_charges:,.2f}",
            f"Patient Responsibility: ${form.patient_responsibility:,.2f}",
            "\n⚠️  IMPORTANT NOTES:",
            "  • This is a DRAFT form for review only",
            "  • All fields must be verified before submission",
            "  • Revenue codes may require adjustment based on actual services",
            "  • Insurance auth numbers must be verified",
            "  • This form is NOT ready for submission without human review",
            "=" * 80,
        ])

        return "\n".join(lines)


def main():
    """Example usage"""
    generator = BillingFormGenerator()

    # Sample data from extraction
    sample_data = {
        'chart_id': 'CASE-2026-0506-001',
        'patient_name': 'John Smith',
        'patient_dob': '03/15/1965',
        'patient_sex': 'M',
        'insurance_payer_name': 'UnitedHealthcare',
        'insurance_member_id': 'UHC123456789',
        'insurance_group_number': 'GRP987654',
        'diagnosis_primary': 'M17.11',
        'diagnosis_secondary': [],
        'surgeon_name': 'Dr. Paul Brody',
        'surgeon_npi': '1234567890',
        'facility_name': 'Culver City Surgical Specialists',
        'facility_npi': '1922138817',
        'facility_tax_id': '51-0552740',
        'cpt_primary': '29881',
        'procedure_date': '05/06/2026',
        'laterality': 'Right',
        'base_charge': 4500.0,
        'anesthesia_charge': 800.0,
        'facility_charge': 2200.0,
    }

    # Build forms
    cms1500 = generator.build_cms1500(sample_data)
    ub04 = generator.build_ub04(sample_data)

    # Output
    print(generator.format_cms1500_text(cms1500))
    print("\n\n")
    print(generator.format_ub04_text(ub04))

    # Export as JSON
    output = {
        'cms1500_draft': asdict(cms1500),
        'ub04_draft': asdict(ub04),
        'generated_at': datetime.now().isoformat(),
    }

    output_file = Path('billing_drafts.json')
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n✅ Billing drafts exported to {output_file}")


if __name__ == "__main__":
    main()
