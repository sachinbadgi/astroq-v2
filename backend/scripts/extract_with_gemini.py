import fitz
import google.generativeai as genai
import os
import json
import time

def extract_rules():
    pdf_path = os.path.abspath('reference-docs/Jyotish_Lal Kitab_B.M. Gosvami 1952.pdf')
    out_pdf_path = os.path.abspath('temp_ch16_19.pdf')
    result_path = os.path.abspath('backend/data/gemini_extracted_rules.json')
    
    # 1. Create a sub-PDF with just pages 273-314
    print("Extracting pages 273-314 to temporary PDF...")
    doc = fitz.open(pdf_path)
    # the page index is 0-based; page 273 is likely index 272
    doc2 = fitz.open()
    doc2.insert_pdf(doc, from_page=272, to_page=313)
    doc2.save(out_pdf_path)
    doc.close()
    doc2.close()
    
    # 2. Upload to Gemini
    print("Uploading to Gemini File API...")
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # Optional: Delete previously uploaded file if we want to run again cleanly, but the SDK handles uniqueness via generated names
    myfile = genai.upload_file(out_pdf_path)
    print(f"Uploaded file as: {myfile.name}")
    
    # Wait for processing
    while myfile.state.name == "PROCESSING":
         print(".", end="", flush=True)
         time.sleep(2)
         myfile = genai.get_file(myfile.name)
    print(f"\nFile processing state: {myfile.state.name}")
    
    # 3. Prompt Gemini
    print("Prompting Gemini 1.5 Pro to extract deterministic rules...")
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = """
    You are an expert Astrologer and Data Engineer extracting rules from the Lal Kitab (1952) chapters 16, 17, 18, and 19.
    
    Extract ALL the deterministic rules mentioned in these pages (spanning professions, service, travel, marriage, progeny, money matters, disease, etc).
    Your output must be EXCLUSIVELY a JSON array of objects. No markdown formatting, just pure JSON.
    I need a comprehensive list of EVERY rule. Some pages are tables, please convert every row into a distinct rule. 
    There should be potentially over 100-200 rules extracted from these 42 pages. Be extremely thorough.
    
    Format of each object in the array:
    {
      "domain": "profession (or marriage, health, travel, progeny, wealth, general)",
      "description": "Short human readable description e.g., 'Ketu in H7 -> Auspicious travel'",
      "condition": {
        // Use these condition types:
        // "type": "placement", "planet": "Sun", "houses": [1]
        // "type": "AND", "conditions": [...]
        // "type": "OR", "conditions": [...]
        // "type": "confrontation", "planet_a": "Sun", "planet_b": "Saturn"
        // E.g. for "Sun-Jupiter together in H7": {"type": "AND", "conditions": [{"type": "placement", "planet": "Sun", "houses": [7]}, {"type": "placement", "planet": "Jupiter", "houses": [7]}]}
      },
      "verdict": "Detailed explanation of the astrological result",
      "scale": "minor, moderate, major, extreme",
      "scoring_type": "boost, penalty",
      "source_page": "Page number from the document (e.g. 'Page 296')"
    }
    """
    
    # Note: we might need response_mime_type="application/json" but just instructing pure JSON works.
    response = model.generate_content(
        [myfile, prompt],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    
    print("Got response from Gemini.")
    
    # Format and save
    try:
        rules_json = json.loads(response.text)
        with open(result_path, 'w') as f:
            json.dump(rules_json, f, indent=2)
        print(f"Extracted {len(rules_json)} rules and saved to {result_path}")
    except Exception as e:
        print(f"Failed to parse JSON. Raw output saved. Error: {e}")
        with open(result_path + ".raw.txt", 'w') as f:
            f.write(response.text)

if __name__ == "__main__":
    extract_rules()
