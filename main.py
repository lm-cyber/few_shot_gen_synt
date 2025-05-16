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
from module.doc_reader import extract_document_data

def main():
    data_path = '/home/ubuntu/alan/test_lm/data'
    layout = Layout()
    data_list = []
    for file in os.listdir(data_path):
        data_list.append(dict())

        data_list[-1]['file'] = file

        if file.endswith('.docx') or file.endswith('.rtf'):
            continue
        img = Image.open(os.path.join(data_path, file)).convert("RGB")
        bboxes, labels  = layout.detect_layout(img)
        bboxes, labels = filter_contained_boxes(bboxes, labels)

        data_list[-1]['bboxes'] = bboxes
        data_list[-1]['labels'] = labels
        data_list[-1]['img'] = img
    layout.model.to("cpu")
    layout.model = None
    gc.collect()
    torch.cuda.empty_cache()

    ocr = OCR()
    for data in data_list:
        file = data['file']
        if file.endswith('.docx') or file.endswith('.rtf'):
                continue
        img = data['img']
        bboxes = data['bboxes']
        labels = data['labels']

        texts = []
        for i in range(len(bboxes)):   
            texts.append(ocr.ocr(img.crop(bboxes[i])))
        data['texts'] = texts
    ocr.model.to("cpu")
    ocr.model = None
    gc.collect()
    torch.cuda.empty_cache()
    for data in data_list:
        file = data['file']
        if file.endswith('.docx') or file.endswith('.rtf'):
            data_doc = extract_document_data(os.path.join(data_path, file))
            data['texts'] = data_doc['texts']
            data['labels'] = data_doc['labels']
            data['bboxes'] = data_doc['bboxes']


    for data in data_list:
        texts = data['texts']
        anonymized_texts = []
        for text in texts:  
            anonymized_texts.append(anonymize_text(text))
        data['anonymized_texts'] = anonymized_texts

   
    llm = GENERATE_TEXT()
    for data in data_list:
        texts = data['texts']
        anonymized_texts = data['anonymized_texts']
        rephrased_texts = llm.generate_text(anonymized_texts)
        data['rephrased_texts'] = rephrased_texts
   
    try:
        os.makedirs("output")
    except:
        pass
    for data in data_list:
        size = A4
        if 'img' in data:
            size = data['img'].size
        bboxes = data['bboxes']
        labels = data['labels']
        rephrased_texts = data['rephrased_texts']
        file = data['file']
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