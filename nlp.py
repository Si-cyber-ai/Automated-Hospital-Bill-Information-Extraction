import easyocr
import re
import json
import pandas as pd


# ---------------- OCR ----------------
def extract_text(image_path):
    reader = easyocr.Reader(['en'], gpu=False)  # set True if GPU available
    results = reader.readtext(image_path, detail=0)
    return "\n".join(results)


# ---------------- CLEAN TEXT ----------------
def clean_text(text):
    text = re.sub(r'[^\x00-\x7F₹]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ---------------- HEADER EXTRACTION ----------------
def extract_header_fields(text):
    data = {}

    hospital_match = re.search(r'(.*Hospital)', text)
    data["hospital_name"] = hospital_match.group(1) if hospital_match else "Not Found"

    location_match = re.search(r'(Kochi.*?Kerala)', text)
    data["location"] = location_match.group(1) if location_match else "Not Found"

    invoice_no = re.search(r'Invoice No[:\s]*([A-Z0-9/]+)', text)
    data["invoice_number"] = invoice_no.group(1) if invoice_no else "Not Found"

    invoice_date = re.search(r'Invoice Date[:\s]*(\d{2}-[A-Za-z]{3}-\d{4})', text)
    data["invoice_date"] = invoice_date.group(1) if invoice_date else "Not Found"

    patient = re.search(r'Patient[:\s]*([A-Za-z ]+)', text)
    data["patient_name"] = patient.group(1).strip() if patient else "Not Found"

    admission = re.search(r'Admission[:\s]*(\d{2}-[A-Za-z]{3}-\d{4})', text)
    data["admission_date"] = admission.group(1) if admission else "Not Found"

    discharge = re.search(r'Discharge[:\s]*(\d{2}-[A-Za-z]{3}-\d{4})', text, re.IGNORECASE)
    data["discharge_date"] = discharge.group(1) if discharge else "Not Found"


    return data


# ---------------- ITEM TABLE EXTRACTION ----------------
def extract_items(text):
    items = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        # Skip header lines
        if any(word in line.lower() for word in ["description", "qty", "rate", "total", "grand"]):
            continue

        # Find all numbers (including commas)
        numbers = re.findall(r'[\d,]+', line)

        # We expect at least 2 numbers: rate and total
        if len(numbers) < 2:
            continue

        # Clean numbers
        numbers = [int(n.replace(",", "")) for n in numbers]

        # Assume last = total, second last = rate
        total = numbers[-1]
        rate = numbers[-2]

        # Quantity may or may not exist
        qty = numbers[-3] if len(numbers) >= 3 else None

        # Remove numbers from line to get description
        description = re.sub(r'[\d,]+', '', line).strip(" -")

        # Filter out garbage OCR lines
        if len(description) < 3:
            continue

        items.append({
            "description": description,
            "quantity": qty,
            "rate": rate,
            "total": total
        })

    return items


# ---------------- GRAND TOTAL ----------------
def extract_grand_total(text):
    match = re.search(r'Grand Total[^\d]*([\d,]+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    return "Not Found"

# ---------------- MAIN PROCESS ----------------
def process_hospital_bill(image_path):
    print("🔍 Running OCR...")
    raw_text = extract_text(image_path)
    cleaned_text = clean_text(raw_text)

    header_data = extract_header_fields(cleaned_text)
    items = extract_items(cleaned_text)
    grand_total = extract_grand_total(cleaned_text)

    result = header_data
    result["items"] = items
    result["grand_total"] = grand_total
    result["currency"] = "INR"

    print("\n📦 Structured Output:\n")
    print(json.dumps(result, indent=4))

    # Optional: Save items to CSV
    df = pd.DataFrame(items)
    df.to_csv("hospital_bill_items.csv", index=False)
    print("\n📁 Items saved to hospital_bill_items.csv")


# ---------------- RUN ----------------
if __name__ == "__main__":
    image_path = "/content/Project/hospital_bill.png"  # replace with your image filename
    process_hospital_bill(image_path)
