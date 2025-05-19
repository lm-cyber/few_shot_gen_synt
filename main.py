from module.layout import Layout
from module.ocr import OCR
from module.llm import GENERATE_TEXT  
from module.pdf_gen import generate_pdf_from_layout_data
from module.config import anonymize_text_tokens
from module.helper import filter_contained_boxes
from module.anonymize import anonymize_text
from reportlab.lib.pagesizes import A4
from PIL import Image
import os
import gc 
import torch
from module.doc_reader import extract_document_data, put_to_docx
from module.pdf_utils import (
    check_scanned_pdf, 
    get_pdf_pages_count, 
    get_pdf_page_size, 
    get_pdf_page_text_and_bboxes, 
    extract_all_pdf_pages_text_and_bboxes,
    create_pdf_from_text_and_bboxes
)
import fitz  # PyMuPDF for converting PDF pages to images

def main():
    data_path = '/home/ubuntu/alan/test_lm/data'
    layout = Layout()
    data_list = []
    
    # Process files in data directory
    for file in os.listdir(data_path):
        file_path = os.path.join(data_path, file)
        data_list.append(dict())
        data_list[-1]['file'] = file

        # Handle different file types
        if file.endswith('.pdf'):
            # Process PDF files
            is_scanned = check_scanned_pdf(file_path)
            
            if is_scanned:
                # Process scanned PDF as images
                print(f"Processing scanned PDF: {file}")
                
                # Create a list to store data for each page
                pdf_pages_data = []
                
                # Open PDF with PyMuPDF
                pdf_doc = fitz.open(file_path)
                num_pages = len(pdf_doc)
                
                for page_num in range(num_pages):
                    # Convert PDF page to image
                    page = pdf_doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Process image with layout detection
                    bboxes, labels = layout.detect_layout(img)
                    bboxes, labels = filter_contained_boxes(bboxes, labels)
                    
                    # Store page data
                    pdf_pages_data.append({
                        'page_num': page_num,
                        'img': img,
                        'bboxes': bboxes,
                        'labels': labels
                    })
                
                # Close PDF document
                pdf_doc.close()
                
                # Add all pages data to the main data list
                data_list[-1]['pdf_pages'] = pdf_pages_data
                data_list[-1]['is_scanned_pdf'] = True
                data_list[-1]['pdf_page_count'] = num_pages
                
            else:
                # Process regular PDF with text extraction
                print(f"Processing regular PDF with text extraction: {file}")
                
                # Get PDF information
                page_count = get_pdf_pages_count(file_path)
                page_size = get_pdf_page_size(file_path)
                
                # Extract text and bounding boxes from all pages
                all_texts, all_bboxes = extract_all_pdf_pages_text_and_bboxes(file_path)
                
                # Prepare text and bbox lists for all pages combined
                combined_texts = []
                combined_bboxes = []
                combined_labels = []
                
                # Process each page's data
                for page_num, (page_texts, page_bboxes) in enumerate(zip(all_texts, all_bboxes)):
                    # Skip empty pages
                    if not page_texts:
                        continue
                        
                    # Default label (assuming text paragraphs as default)
                    default_label = "1"  # Assuming "1" corresponds to regular text in your label system
                    page_labels = [default_label] * len(page_texts)
                    
                    # Add page data to combined lists
                    combined_texts.extend(page_texts)
                    combined_bboxes.extend(page_bboxes)
                    combined_labels.extend(page_labels)
                
                # Store extracted data
                data_list[-1]['texts'] = combined_texts
                data_list[-1]['bboxes'] = combined_bboxes
                data_list[-1]['labels'] = combined_labels
                data_list[-1]['is_scanned_pdf'] = False
                data_list[-1]['pdf_page_count'] = page_count
                data_list[-1]['pdf_page_size'] = page_size
                
                # Skip OCR for regular PDFs with text
                continue
                
        elif file.endswith('.docx') or file.endswith('.rtf'):
            # Skip DOCX/RTF processing here - will be handled below
            continue
        else:
            # Process image files
            img = Image.open(file_path).convert("RGB")
            bboxes, labels = layout.detect_layout(img)
            bboxes, labels = filter_contained_boxes(bboxes, labels)

            data_list[-1]['bboxes'] = bboxes
            data_list[-1]['labels'] = labels
            data_list[-1]['img'] = img
    
    # Release layout model resources
    layout.model.to("cpu")
    layout.model = None
    gc.collect()
    torch.cuda.empty_cache()

    # OCR processing
    ocr = OCR()
    for data in data_list:
        file = data['file']
        
        if file.endswith('.docx') or file.endswith('.rtf'):
            continue
            
        if file.endswith('.pdf') and not data.get('is_scanned_pdf', False):
            continue  # Skip OCR for non-scanned PDFs
            
        if file.endswith('.pdf') and data.get('is_scanned_pdf', True):
            # Process each page of scanned PDF with OCR
            pdf_pages = data['pdf_pages']
            
            all_texts = []
            all_bboxes = []
            all_labels = []
            
            for page_data in pdf_pages:
                img = page_data['img']
                bboxes = page_data['bboxes']
                labels = page_data['labels']
                
                # OCR for each text region
                page_texts = []
                for i in range(len(bboxes)):
                    page_texts.append(ocr.ocr(img.crop(bboxes[i])))
                
                # Add page data to combined lists
                all_texts.extend(page_texts)
                all_bboxes.extend(bboxes)
                all_labels.extend(labels)
            
            # Store combined data for all pages
            data['texts'] = all_texts
            data['bboxes'] = all_bboxes
            data['labels'] = all_labels
        else:
            # Regular image processing with OCR
            img = data['img']
            bboxes = data['bboxes']
            labels = data['labels']

            texts = []
            for i in range(len(bboxes)):   
                texts.append(ocr.ocr(img.crop(bboxes[i])))
            data['texts'] = texts
    
    # Release OCR model resources
    ocr.model.to("cpu")
    ocr.model = None
    gc.collect()
    torch.cuda.empty_cache()
    
    # Process DOCX/RTF files
    for data in data_list:
        file = data['file']
        if file.endswith('.docx') or file.endswith('.rtf'):
            data_doc = extract_document_data(os.path.join(data_path, file))
            data['texts'] = data_doc['texts']
            data['labels'] = data_doc['labels']
            data['bboxes'] = data_doc['bboxes']

    # Anonymize text
    for data in data_list:
        texts = data['texts']
        anonymized_texts = []
        for text in texts:  
            anonymized_texts.append(anonymize_text(text))
        data['anonymized_texts'] = anonymized_texts

    # Generate rephrased text using LLM
    llm = GENERATE_TEXT()
    for data in data_list:
        texts = data['texts']
        anonymized_texts = data['anonymized_texts']
        rephrased_texts = llm.generate_text(anonymized_texts)
        data['rephrased_texts'] = rephrased_texts
   
    # Create output directories
    try:
        os.makedirs("output")
    except:
        pass
    try:
        os.makedirs("tmp")
    except:
        pass    
    # Generate output files
    for data in data_list:
        file = data['file']
        bboxes = data['bboxes']
        labels = data['labels']
        rephrased_texts = data['rephrased_texts']
        
        # Determine page size
        if file.endswith('.pdf') and not data.get('is_scanned_pdf', False):
            size = data.get('pdf_page_size', A4)
        elif 'img' in data:
            size = data['img'].size
        else:
            size = A4
            
        # Handle DOCX files
        if file.endswith('.docx'):
            doc = put_to_docx(os.path.join(data_path, file), data)
            doc.save(os.path.join("output", f"nibba_{file}"))
            # doc.save(os.path.join("tmp", f"nibba_{file}"))
            # convert(os.path.join("tmp", f"nibba_{file}"), os.path.join("output", f"nibba_{file}.pdf"))
        else:    
            # Generate PDF with rephrased text
            generate_pdf_from_layout_data(
                texts_list=rephrased_texts,
                bboxes_list=bboxes,
                label_ids_list=labels,
                original_page_size=size,
                output_pdf_filename=os.path.join("output", f"nibba_{file}.pdf"),
                target_pdf_pagesize=A4,
                debug_draw_bbox_borders=True
            )

if __name__ == "__main__":
    main()