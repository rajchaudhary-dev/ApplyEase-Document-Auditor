import os
from pathlib import Path
from PIL import Image, ImageDraw

def generate_mock_gazette_pdf(output_path: Path) -> Path:
    """Generate a multi-page synthetic recruitment gazette PDF for testing."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pages = []

    # Page 1: Header, Notification Metadata, Key Dates, Vacancy Breakdown
    p1 = Image.new("RGB", (850, 1100), color=(255, 255, 255))
    d1 = ImageDraw.Draw(p1)
    d1.rectangle([30, 30, 820, 1070], outline=(0, 51, 102), width=4)
    d1.text((220, 60), "UNION PUBLIC SERVICE COMMISSION", fill=(0, 51, 102))
    d1.text((250, 90), "EXAMINATION NOTICE NO. 04/2026-ASO", fill=(0, 0, 0))
    d1.text((280, 115), "DATED: 01ST MARCH 2026", fill=(0, 0, 0))
    
    d1.text((60, 180), "1. RECRUITMENT NOTIFICATION DETAILS", fill=(0, 51, 102))
    d1.text((60, 210), "Post Name       : ASSISTANT SECTION OFFICER (ASO)", fill=(0, 0, 0))
    d1.text((60, 235), "Department      : Central Secretariat Service (CSS)", fill=(0, 0, 0))
    d1.text((60, 260), "Advt Number     : ADVT-UPSC/2026/ASO-99", fill=(0, 0, 0))
    d1.text((60, 285), "Total Vacancies : 450 (UR: 180, OBC: 120, EWS: 45, SC: 68, ST: 37)", fill=(0, 0, 0))

    d1.text((60, 340), "2. IMPORTANT DATES", fill=(0, 51, 102))
    d1.text((60, 370), "Online Registration Start Date : 05/03/2026", fill=(0, 0, 0))
    d1.text((60, 395), "Online Registration Last Date  : 15/04/2026 (Till 18:00 Hrs)", fill=(0, 0, 0))
    d1.text((60, 420), "Crucial Date for Age & Qualif  : 01/08/2026", fill=(0, 0, 0))
    d1.text((60, 445), "Last Date for Fee Deposit      : 16/04/2026", fill=(0, 0, 0))
    d1.text((60, 470), "Preliminary Examination Date    : 20/06/2026", fill=(0, 0, 0))

    d1.text((60, 520), "3. APPLICATION FEE", fill=(0, 51, 102))
    d1.text((60, 550), "General / OBC / EWS Male Candidates : Rs. 500/-", fill=(0, 0, 0))
    d1.text((60, 575), "SC / ST / PwBD / Female Candidates  : NIL (Exempted)", fill=(0, 0, 0))
    d1.text((60, 600), "Mode of Payment                     : Net Banking, Credit/Debit Card, UPI", fill=(0, 0, 0))

    pages.append(p1)

    # Page 2: Age Criteria, Relaxations, Educational Qualifications, Upload Specs
    p2 = Image.new("RGB", (850, 1100), color=(255, 255, 255))
    d2 = ImageDraw.Draw(p2)
    d2.rectangle([30, 30, 820, 1070], outline=(0, 51, 102), width=4)

    d2.text((60, 60), "4. AGE LIMIT AND RELAXATIONS (AS ON 01/08/2026)", fill=(0, 51, 102))
    d2.text((60, 95), "Minimum Age Limit : 21 Years (Candidate must not be born after 01/08/2005)", fill=(0, 0, 0))
    d2.text((60, 120), "Maximum Age Limit : 30 Years (Candidate must not be born before 02/08/1996)", fill=(0, 0, 0))
    d2.text((60, 150), "Category-wise Upper Age Relaxation:", fill=(0, 0, 0))
    d2.text((80, 180), "- Other Backward Classes (OBC-NCL) : +3 Years (Max Age: 33)", fill=(0, 0, 0))
    d2.text((80, 205), "- Scheduled Castes (SC) / ST        : +5 Years (Max Age: 35)", fill=(0, 0, 0))
    d2.text((80, 230), "- Persons with Benchmark Disabilities: +10 Years", fill=(0, 0, 0))
    d2.text((80, 255), "- Ex-Servicemen                     : +5 Years", fill=(0, 0, 0))

    d2.text((60, 310), "5. EDUCATIONAL QUALIFICATIONS", fill=(0, 51, 102))
    d2.text((60, 345), "Mandatory Qualification : Bachelor's Degree in any discipline from a recognized University.", fill=(0, 0, 0))
    d2.text((60, 370), "Minimum Percentage      : 60% aggregate or equivalent CGPA in Graduation.", fill=(0, 0, 0))
    d2.text((60, 395), "Experience Requirement  : No prior work experience is required (Freshers Eligible).", fill=(0, 0, 0))

    d2.text((60, 450), "6. RESERVATION & CERTIFICATE CLAUSES", fill=(0, 51, 102))
    d2.text((60, 480), "OBC-NCL Clause : Certificate must be issued on or after 01/04/2025 covering Financial Year 2025-2026.", fill=(0, 0, 0))
    d2.text((60, 505), "EWS Clause     : Certificate must be valid for Financial Year 2025-2026 based on FY 2024-2025 income.", fill=(0, 0, 0))

    d2.text((60, 560), "7. UPLOAD ASSET SPECIFICATIONS", fill=(0, 51, 102))
    d2.text((60, 590), "Passport Photograph : 200x230 pixels, JPEG format, file size between 20KB and 50KB.", fill=(0, 0, 0))
    d2.text((60, 615), "Candidate Signature : 140x60 pixels, JPEG format, file size between 10KB and 20KB.", fill=(0, 0, 0))
    d2.text((60, 640), "Document Certificates: JPEG or PDF format, maximum file size 300KB.", fill=(0, 0, 0))

    pages.append(p2)

    # Save as multi-page PDF
    pages[0].save(output_path, "PDF", save_all=True, append_images=pages[1:])
    return output_path

if __name__ == "__main__":
    out_file = Path(__file__).parent / "sample_gazettes" / "upsc_aso_2026_gazette.pdf"
    generate_mock_gazette_pdf(out_file)
    print(f"Generated synthetic recruitment gazette PDF: {out_file}")
