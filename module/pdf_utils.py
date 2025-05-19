from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
import os


def check_scanned_pdf(filepath):
    reader = PdfReader(filepath)
    if len(reader.pages) == 1 and reader.pages[0].extract_text() == "":
        return True
    return False

def get_pdf_pages_count(filepath):
    reader = PdfReader(filepath)
    return len(reader.pages)

def get_pdf_page_size(filepath):
    reader = PdfReader(filepath)
    return reader.pages[0].mediabox.width, reader.pages[0].mediabox.height  

def get_pdf_page_text_and_bboxes(filepath, page_num=0):
    """
    Extract text and bounding boxes from a PDF page.
    
    Args:
        filepath (str): Path to the PDF file
        page_num (int): Page number to extract from (0-indexed)
        
    Returns:
        tuple: (list of texts, list of bounding boxes)
    """
    reader = PdfReader(filepath)
    if page_num >= len(reader.pages):
        raise ValueError(f"Page {page_num} does not exist in PDF with {len(reader.pages)} pages")
        
    page = reader.pages[page_num]
    
    # Get page dimensions
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    
    # Extract text with layout information
    texts = []
    bboxes = []
    
    # Extract text from the page
    text_elements = page.extract_text(extraction_mode="layout")
    
    # Get text extraction objects with bbox information
    if hasattr(page, "/Resources") and "/Font" in page["/Resources"]:
        for obj in page.get_text_extraction_objects():
            if "text" in obj and len(obj["text"].strip()) > 0:
                text = obj["text"]
                
                # Get bounding box coordinates and normalize to page dimensions
                x0, y0, x1, y1 = obj.get("bbox", (0, 0, 0, 0))
                # Convert PDF coordinates (origin at bottom-left) to standard coordinates (origin at top-left)
                bbox = [x0, page_height - y1, x1, page_height - y0]
                
                texts.append(text)
                bboxes.append(bbox)
    
    return texts, bboxes

def extract_all_pdf_pages_text_and_bboxes(filepath):
    """
    Extract text and bounding boxes from all pages of a PDF.
    
    Args:
        filepath (str): Path to the PDF file
        
    Returns:
        tuple: (list of page texts, list of page bounding boxes)
    """
    reader = PdfReader(filepath)
    all_texts = []
    all_bboxes = []
    
    for page_num in range(len(reader.pages)):
        texts, bboxes = get_pdf_page_text_and_bboxes(filepath, page_num)
        all_texts.append(texts)
        all_bboxes.append(bboxes)
    
    return all_texts, all_bboxes

def create_pdf_from_text_and_bboxes(
    texts_list, 
    bboxes_list, 
    output_filepath, 
    page_size=A4, 
    font_name="Helvetica", 
    font_size=10,
    debug_draw_borders=False
):
    """
    Create a PDF file from lists of text elements and their bounding boxes.
    
    Args:
        texts_list (list): List of text strings
        bboxes_list (list): List of bounding boxes (each being [x0, y0, x1, y1])
        output_filepath (str): Path to save the output PDF
        page_size (tuple): Page size as (width, height) in points
        font_name (str): Font to use for text
        font_size (int): Base font size
        debug_draw_borders (bool): Whether to draw borders around text boxes
    """
    if len(texts_list) != len(bboxes_list):
        raise ValueError("The number of text elements and bounding boxes must be the same")
        
    # Create PDF canvas
    c = canvas.Canvas(output_filepath, pagesize=page_size)
    pdf_width, pdf_height = page_size
    
    # Create a basic paragraph style
    style = ParagraphStyle(
        'BasicStyle',
        fontName=font_name,
        fontSize=font_size,
        leading=font_size * 1.2  # Line spacing
    )
    
    for i, (text, bbox) in enumerate(zip(texts_list, bboxes_list)):
        if not text or text.isspace():
            continue
            
        x0, y0, x1, y1 = bbox
        box_width = x1 - x0
        box_height = y1 - y0
        
        # Skip too small boxes
        if box_width <= 1 or box_height <= 1:
            continue
            
        # Create paragraph object
        paragraph = Paragraph(text, style)
        
        # Create frame for the text
        padding = 2  # Padding around text
        frame = Frame(
            x0, 
            pdf_height - y1,  # Convert to PDF coordinates (origin at bottom-left)
            box_width, 
            box_height,
            leftPadding=padding,
            bottomPadding=padding,
            rightPadding=padding,
            topPadding=padding,
            showBoundary=1 if debug_draw_borders else 0
        )
        
        # Try to add text to the frame
        try:
            # Check if text fits
            w, h = paragraph.wrapOn(c, box_width - 2*padding, box_height - 2*padding)
            
            # Add text to frame
            frame.addFromList([paragraph], c)
                
        except Exception as e:
            print(f"Error adding text '{text[:20]}...' to frame: {e}")
            
            # Draw an empty frame to show the error location if debug is enabled
            if debug_draw_borders:
                c.saveState()
                c.setStrokeColorRGB(1, 0, 0)  # Red
                c.rect(x0, pdf_height - y1, box_width, box_height)
                c.restoreState()
    
    # Save the PDF
    c.save()
    return output_filepath
