import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_mock_documents(output_dir: Path) -> list:
    """Generate realistic synthetic candidate document images for testing."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    # 1. Class 10 Marksheet (Gold Standard)
    img_10 = Image.new("RGB", (800, 1000), color=(250, 250, 245))
    draw = ImageDraw.Draw(img_10)
    draw.rectangle([20, 20, 780, 980], outline=(0, 51, 102), width=4)
    draw.text((250, 50), "CENTRAL BOARD OF SECONDARY EDUCATION", fill=(0, 51, 102))
    draw.text((320, 80), "CLASS X MARKS STATEMENT 2017", fill=(0, 0, 0))
    
    draw.text((60, 150), "Candidate Name: ROHAN KUMAR SHARMA", fill=(0, 0, 0))
    draw.text((60, 190), "Father's Name  : RAJESH SHARMA", fill=(0, 0, 0))
    draw.text((60, 230), "Mother's Name  : SUNITA SHARMA", fill=(0, 0, 0))
    draw.text((60, 270), "Date of Birth  : 14/08/2001 (14TH AUGUST TWO THOUSAND ONE)", fill=(0, 0, 0))
    draw.text((60, 310), "Roll No / ID   : CBSE/10/2017/889210", fill=(0, 0, 0))
    
    # Marks Table mock
    draw.rectangle([60, 360, 740, 700], outline=(100, 100, 100), width=2)
    draw.text((80, 380), "SUBJECT              MAX MARKS    MARKS OBTAINED    RESULT", fill=(0, 0, 0))
    draw.line([60, 410, 740, 410], fill=(100, 100, 100), width=1)
    draw.text((80, 430), "ENGLISH COMM.           100             088           PASS", fill=(0, 0, 0))
    draw.text((80, 470), "MATHEMATICS             100             092           PASS", fill=(0, 0, 0))
    draw.text((80, 510), "SCIENCE                 100             085           PASS", fill=(0, 0, 0))
    draw.text((80, 550), "SOCIAL SCIENCE          100             087           PASS", fill=(0, 0, 0))
    draw.text((80, 590), "HINDI COURSE-A          100             090           PASS", fill=(0, 0, 0))
    draw.text((80, 650), "RESULT: PASS    AGGREGATE: 88.4%", fill=(0, 100, 0))
    
    path_10 = output_dir / "class_10_marksheet.jpg"
    img_10.save(path_10)
    generated_files.append(path_10)

    # 2. Class 12 Marksheet (With slight name variation "Rohan K. Sharma")
    img_12 = Image.new("RGB", (800, 1000), color=(250, 250, 250))
    draw = ImageDraw.Draw(img_12)
    draw.rectangle([20, 20, 780, 980], outline=(120, 0, 0), width=4)
    draw.text((250, 50), "CENTRAL BOARD OF SECONDARY EDUCATION", fill=(120, 0, 0))
    draw.text((300, 80), "SENIOR SCHOOL CERTIFICATE (CLASS XII) 2019", fill=(0, 0, 0))
    
    draw.text((60, 150), "Candidate Name: ROHAN K. SHARMA", fill=(0, 0, 0))
    draw.text((60, 190), "Father's Name  : RAJESH SHARMA", fill=(0, 0, 0))
    draw.text((60, 230), "Date of Birth  : 14/08/2001", fill=(0, 0, 0))
    draw.text((60, 270), "Roll No        : CBSE/12/2019/554109", fill=(0, 0, 0))
    
    path_12 = output_dir / "class_12_marksheet.jpg"
    img_12.save(path_12)
    generated_files.append(path_12)

    # 3. Aadhaar Card
    img_id = Image.new("RGB", (700, 450), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_id)
    draw.rectangle([10, 10, 690, 440], outline=(200, 50, 50), width=3)
    draw.text((220, 30), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill=(200, 50, 50))
    draw.text((280, 60), "GOVERNMENT OF INDIA", fill=(0, 0, 0))
    
    draw.text((50, 140), "Name : ROHAN KUMAR SHARMA", fill=(0, 0, 0))
    draw.text((50, 180), "DOB  : 14/08/2001", fill=(0, 0, 0))
    draw.text((50, 220), "Gender : MALE", fill=(0, 0, 0))
    draw.text((50, 260), "S/O : RAJESH SHARMA", fill=(0, 0, 0))
    draw.text((200, 350), "9988 7766 5544", fill=(0, 0, 150))
    
    path_id = output_dir / "aadhaar_card.jpg"
    img_id.save(path_id)
    generated_files.append(path_id)

    # 4. OBC-NCL Certificate (With issue date & FY)
    img_obc = Image.new("RGB", (800, 1000), color=(255, 253, 240))
    draw = ImageDraw.Draw(img_obc)
    draw.rectangle([20, 20, 780, 980], outline=(0, 100, 0), width=4)
    draw.text((260, 50), "FORM OF CERTIFICATE TO BE PRODUCED BY OTHER BACKWARD CLASSES", fill=(0, 100, 0))
    draw.text((300, 80), "GOVERNMENT OF RAJASTHAN - OFFICE OF THE TEHSILDAR", fill=(0, 0, 0))
    
    draw.text((60, 160), "Certificate No : OBC/NCL/2023/4491", fill=(0, 0, 0))
    draw.text((60, 200), "Date of Issue  : 10/04/2023", fill=(0, 0, 0))
    draw.text((60, 240), "Financial Year : 2023-2024", fill=(0, 0, 0))
    draw.text((60, 300), "This is to certify that ROHAN SHARMA, son of RAJESH SHARMA", fill=(0, 0, 0))
    draw.text((60, 340), "belongs to the OBC Category and does NOT belong to Creamy Layer.", fill=(0, 0, 0))
    draw.text((450, 850), "Issuing Authority: TEHSILDAR, JAIPUR", fill=(0, 0, 0))
    
    path_obc = output_dir / "obc_ncl_certificate.jpg"
    img_obc.save(path_obc)
    generated_files.append(path_obc)

    # 5. Passport Photo
    img_photo = Image.new("RGB", (400, 500), color=(200, 220, 240))
    draw = ImageDraw.Draw(img_photo)
    # Draw simple synthetic face silhouette
    draw.ellipse([120, 100, 280, 300], fill=(240, 190, 160)) # Face
    draw.rectangle([100, 300, 300, 500], fill=(40, 40, 120))  # Shirt/Suit
    draw.ellipse([150, 170, 180, 200], fill=(30, 30, 30))     # Eye L
    draw.ellipse([220, 170, 250, 200], fill=(30, 30, 30))     # Eye R
    draw.arc([170, 220, 230, 260], start=0, end=180, fill=(100, 40, 40), width=3) # Smile
    
    path_photo = output_dir / "passport_photo.jpg"
    img_photo.save(path_photo)
    generated_files.append(path_photo)

    # 6. Candidate Signature
    img_sig = Image.new("RGB", (600, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_sig)
    # Draw synthetic signature stroke
    draw.line([(50, 150), (120, 80), (180, 170), (240, 100), (320, 160), (420, 70), (520, 180)], fill=(0, 0, 150), width=4)
    draw.line([(100, 160), (500, 160)], fill=(0, 0, 150), width=2)
    
    path_sig = output_dir / "signature.jpg"
    img_sig.save(path_sig)
    generated_files.append(path_sig)

    return generated_files

if __name__ == "__main__":
    out = Path(__file__).parent / "sample_documents"
    files = generate_mock_documents(out)
    print(f"Generated {len(files)} synthetic candidate test documents in: {out}")
