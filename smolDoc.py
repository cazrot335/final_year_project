import time
import torch
import os
from PIL import Image
from pdf2image import convert_from_path
from transformers import AutoProcessor, AutoModelForImageTextToText
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument

# --- 1. SETUP MODEL & DEVICE ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "ds4sd/SmolDocling-256M-preview"

print(f"Using Device: {DEVICE}")
print(f"Loading model: {model_id}...")

processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForImageTextToText.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
    device_map="auto" if DEVICE == "cuda" else None,
    trust_remote_code=True
)

def parse_resume_pdf(pdf_path):
    # --- 2. PDF TO IMAGE (Target Page 1) ---
    start_time = time.time()
    try:
        images = convert_from_path(pdf_path, dpi=200)
        image = images[0].convert("RGB")
    except Exception as e:
        return {"error": f"PDF Conversion Error: {e}"}

    conv_time = time.time() - start_time

    # --- 3. MODEL INFERENCE ---
    # Standard prompt for SmolDocling structured output
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": "convert the document to docling."}
            ]
        }
    ]

    inf_start = time.time()
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False,
            use_cache=True,
            eos_token_id=processor.tokenizer.eos_token_id,
            pad_token_id=processor.tokenizer.pad_token_id,
        )

    # Decode and clean hallucinations (The "User/Assistant" filter)
    prompt_len = inputs.input_ids.shape[1]
    raw_output = processor.batch_decode(generated_ids[:, prompt_len:], skip_special_tokens=True)[0]

    # We strip everything after "User:" or "Assistant:" to keep only the structural tags
    clean_doctags = raw_output.split("User:")[0].split("Assistant:")[0].strip()

    inf_time = time.time() - inf_start

    # --- 4. MARKDOWN CONVERSION ---
    try:
        # Pass the clean tags and the original image to the Docling parser
        doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([clean_doctags], [image])
        # Removed: print(f"DEBUG: DocTagsDocument has {len(doctags_doc.doc_tags_pairs)} tag-image pairs.") # New debug print
        doc = DoclingDocument(name="Resume_Analysis")
        doc.load_from_doctags(doctags_doc)
        print(f"DEBUG: DoclingDocument elements count: {len(doc.elements) if hasattr(doc, 'elements') else 'N/A'}") # Added debug print
        markdown_output = doc.export_to_markdown()
    except Exception as e:
        markdown_output = f"Structure Parser Error: {e}\n\nRAW TAGS:\n{clean_doctags[:500]}"

    total_time = time.time() - start_time

    return {
        "markdown": markdown_output,
        "raw_tags": clean_doctags,
        "metrics": {
            "pdf_to_img": f"{conv_time:.2f}s",
            "inference": f"{inf_time:.2f}s",
            "total": f"{total_time:.2f}s"
        }
    }

# --- 5. RUN TEST ---
pdf_file = "my_resume.pdf"

if os.path.exists(pdf_file):
    print("Processing resume...")
    result = parse_resume_pdf(pdf_file)

    if "error" in result:
        print(result["error"])
    else:
        print("\n" + "="*40)
        print("STRUCTURED MARKDOWN OUTPUT")
        print("="*40)
        print(result["markdown"])

        print("\n" + "="*40)
        print("RAW DOCTAGS OUTPUT") # Added for debugging
        print("="*40)
        print(result["raw_tags"])

        print("\n" + "="*40)
        print("PERFORMANCE METRICS")
        print("="*40)
        for k, v in result["metrics"].items():
            print(f"{k}: {v}")
else:
    print(f"Error: '{pdf_file}' not found. Please upload your resume to the sidebar.")
