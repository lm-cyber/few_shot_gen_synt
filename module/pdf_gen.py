#!/usr/bin/env python
#-*- coding: UTF-8 -*-

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, grey, blue, green, red, purple, orange
import os
from module.config import id2label
# --- Определение меток классов ---
ID2LABEL = {v:k for k,v in id2label.items()}
    
# --- Настройки шрифта ---
CYRILLIC_FONT_NAME = 'MyDejaVuSans'
CYRILLIC_FONT_PATH = '/home/ubuntu/alan/test_lm/DejaVuSans.ttf' # ОБЯЗАТЕЛЬНО ПРОВЕРЬТЕ ЭТОТ ПУТЬ!

font_registered_successfully = False
if os.path.exists(CYRILLIC_FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont(CYRILLIC_FONT_NAME, CYRILLIC_FONT_PATH))
        print(f"Шрифт '{CYRILLIC_FONT_NAME}' из файла '{CYRILLIC_FONT_PATH}' успешно зарегистрирован.")
        font_registered_successfully = True
    except Exception as e:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Не удалось загрузить шрифт '{CYRILLIC_FONT_NAME}' из '{CYRILLIC_FONT_PATH}'. Ошибка: {e}")
else:
    print(f"ОШИБКА: Файл шрифта '{CYRILLIC_FONT_PATH}' не найден!")
    print("Пожалуйста, убедитесь, что путь к файлу шрифта указан верно, и файл существует.")

effective_font_name = CYRILLIC_FONT_NAME if font_registered_successfully else 'Helvetica'
if not font_registered_successfully:
    print(f"Кириллица может не отображаться корректно, будет использован стандартный шрифт '{effective_font_name}'.")


def get_text_styles(current_font_name):
    styles = {}
    base_leading_multiplier = 1
    styles["Заголовок"] = ParagraphStyle('DocHeading', fontName=current_font_name, fontSize=9, leading=18 * base_leading_multiplier, textColor=black, spaceAfter=6, alignment=1)
    styles["Сноска"] = ParagraphStyle('Footnote', fontName=current_font_name, fontSize=4, leading=8 * base_leading_multiplier, textColor=grey)
    styles["Формула"] = ParagraphStyle('Formula', fontName=current_font_name, fontSize=5, leading=10 * base_leading_multiplier, alignment=1, textColor=blue)
    styles["Элемент списка"] = ParagraphStyle('ListItem', fontName=current_font_name, fontSize=5, leading=10 * base_leading_multiplier, leftIndent=20, bulletIndent=10, textColor=black)
    styles["Нижний колонтитул страницы"] = ParagraphStyle('PageFooter', fontName=current_font_name, fontSize=8, leading=8 * base_leading_multiplier, alignment=1, textColor=grey)
    styles["Верхний колонтитул страницы"] = ParagraphStyle('PageHeader', fontName=current_font_name, fontSize=8, leading=8 * base_leading_multiplier, alignment=1, textColor=grey)
    styles["Изображение"] = ParagraphStyle('ImageCaption', fontName=current_font_name, fontSize=4, leading=9 * base_leading_multiplier, alignment=1, textColor=green)
    styles["Заголовок раздела"] = ParagraphStyle('SectionHeading', fontName=current_font_name, fontSize=7, leading=14 * base_leading_multiplier, spaceBefore=12, spaceAfter=4, textColor=purple, alignment=0)
    styles["Таблица"] = ParagraphStyle('TableText', fontName=current_font_name, fontSize=5, leading=10 * base_leading_multiplier, textColor=orange)
    styles["Текст"] = ParagraphStyle('BodyText', fontName=current_font_name, fontSize=5, leading=10 * base_leading_multiplier, textColor=black, alignment=4)
    styles["_DEFAULT_"] = styles["Текст"]
    return styles


def generate_pdf_from_layout_data(
    texts_list: list[str],
    bboxes_list: list[list[float]],
    label_ids_list: list[str],
    original_page_size: tuple[float, float],
    output_pdf_filename: str = "generated_document_from_layout.pdf",
    target_pdf_pagesize: tuple[float, float] = A4,
    debug_draw_bbox_borders: bool = False
):
    if not (len(texts_list) == len(bboxes_list) == len(label_ids_list)):
        raise ValueError("Списки текстов, bbox и ID меток должны быть одинаковой длины.")

    doc_canvas = canvas.Canvas(output_pdf_filename, pagesize=target_pdf_pagesize)
    pdf_width, pdf_height = target_pdf_pagesize

    original_w, original_h = original_page_size
    if original_w <= 0 or original_h <= 0:
        raise ValueError("Размеры оригинальной страницы (original_page_size) должны быть положительными.")

    scale_x = pdf_width / original_w
    scale_y = pdf_height / original_h

    available_styles = get_text_styles(effective_font_name)

    for i in range(len(texts_list)):
        text_content = texts_list[i]
        if not text_content or text_content.isspace(): # Пропускаем пустые строки
            print(f"1 Предупреждение: Элемент {i} содержит пустой текст. Пропуск.")
            continue
        
        bbox_coords = bboxes_list[i]
        label_id_str = str(label_ids_list[i])

        label_description = ID2LABEL.get(label_id_str)
        current_style_obj = available_styles.get(label_description, available_styles["_DEFAULT_"])

        if not label_description:
            print(f"2 Предупреждение: Метка ID '{label_id_str}' не найдена в ID2LABEL. "
                  f"Используется стиль по умолчанию для текста: '{text_content[:50]}...'")

        # Clone the style so we can modify it for this specific text block
        text_style = ParagraphStyle(
            f'Style_{i}', 
            parent=current_style_obj,
            fontSize=current_style_obj.fontSize
        )

        orig_x_min, orig_y_min, orig_x_max, orig_y_max = bbox_coords

        scaled_bbox_width = (orig_x_max - orig_x_min) * scale_x
        scaled_bbox_height = (orig_y_max - orig_y_min) * scale_y
        frame_x_pdf = orig_x_min * scale_x
        frame_y_pdf = pdf_height - (orig_y_max * scale_y)

        if scaled_bbox_width <= 1 or scaled_bbox_height <= 1:
            print(f"3 Предупреждение: Элемент {i} ('{text_content[:50]}...') имеет очень маленькую "
                  f"ширину/высоту ({scaled_bbox_width:.2f} x {scaled_bbox_height:.2f} точек) "
                  f"после масштабирования. Пропуск, если <=0.")
            if scaled_bbox_width <= 0 or scaled_bbox_height <= 0:
                if debug_draw_bbox_borders: # Нарисуем рамку даже для пропущенного элемента
                    doc_canvas.saveState()
                    doc_canvas.setStrokeColor(red)
                    doc_canvas.setDash(3,3)
                    doc_canvas.rect(frame_x_pdf, frame_y_pdf, max(1,scaled_bbox_width), max(1,scaled_bbox_height)) # рисуем хотя бы точку
                    doc_canvas.restoreState()
                continue
        
        # Define padding (internal margins for the frame)
        frame_left_padding = 1
        frame_bottom_padding = 1
        frame_right_padding = 1
        frame_top_padding = 1
        
        # Calculate available space for text within the frame
        available_width_for_text = scaled_bbox_width - (frame_left_padding + frame_right_padding)
        available_height_for_text = scaled_bbox_height - (frame_top_padding + frame_bottom_padding)

        if available_width_for_text < 1: available_width_for_text = 1
        if available_height_for_text < 1: available_height_for_text = 1

        # Prepare text for fitting
        # If text is too long, add line breaks to help with wrapping
        if len(text_content) > 50 and " " in text_content:
            # Add more line breaks for long text to help with wrapping
            words = text_content.split()
            text_content = ""
            line_length = 0
            max_line_chars = max(10, min(40, int(available_width_for_text / 3)))
            
            for word in words:
                if line_length + len(word) > max_line_chars:
                    text_content += " " + word + "\n"
                    line_length = 0
                else:
                    text_content += " " + word
                    line_length += len(word) + 1
            
            text_content = text_content.strip()
        
        # Create frame for the text
        text_frame = Frame(
            x1=frame_x_pdf, y1=frame_y_pdf,
            width=scaled_bbox_width, height=scaled_bbox_height,
            leftPadding=frame_left_padding, bottomPadding=frame_bottom_padding,
            rightPadding=frame_right_padding, topPadding=frame_top_padding,
            showBoundary=1 if debug_draw_bbox_borders else 0,
            id=f'frame_{i}'
        )
        
        # Try to fit text with automatic font size adaptation
        success = False
        min_font_size = 4  # Don't go smaller than this
        max_attempts = 5   # Limit font size reduction attempts
        current_attempt = 0
        
        while not success and current_attempt < max_attempts:
            try:
                # Create paragraph with current style
                paragraph_obj = Paragraph(text_content, text_style)
                
                # Check if text fits with current font size
                required_w, required_h = paragraph_obj.wrapOn(doc_canvas, available_width_for_text, available_height_for_text)
                
                problem_drawing = False
                if required_w > available_width_for_text + 0.01 or required_h > available_height_for_text + 0.01:
                    problem_drawing = True
                    
                    # If text doesn't fit, reduce font size for next attempt
                    if text_style.fontSize > min_font_size:
                        # Reduce font size by 10% or at least 0.5 points
                        new_font_size = max(min_font_size, text_style.fontSize * 0.9)
                        new_font_size = max(new_font_size, text_style.fontSize - 0.5)
                        
                        if current_attempt == 0:
                            print(f"Адаптация размера шрифта для элемента {i}, исходный размер: {text_style.fontSize}, "
                                  f"требуемые размеры: {required_w:.1f}x{required_h:.1f}, "
                                  f"доступные размеры: {available_width_for_text:.1f}x{available_height_for_text:.1f}")
                        
                        text_style.fontSize = new_font_size
                        # Adjust leading (line height) accordingly
                        text_style.leading = new_font_size * 1.2
                        
                        current_attempt += 1
                        continue
                
                # Try to add the paragraph to the frame
                success = text_frame._add(paragraph_obj, doc_canvas, trySplit=1)
                
                if not success:
                    # If adding to frame failed despite good size calculation
                    if text_style.fontSize > min_font_size and current_attempt < max_attempts - 1:
                        # Try with even smaller font
                        text_style.fontSize = max(min_font_size, text_style.fontSize * 0.9)
                        text_style.leading = text_style.fontSize * 1.2
                        current_attempt += 1
                    else:
                        # We've reached minimum font size or max attempts, force placement
                        doc_canvas.saveState()
                        doc_canvas.setFont(text_style.fontName, text_style.fontSize)
                        # Calculate how many lines we can fit
                        line_height = text_style.leading
                        max_lines = int(available_height_for_text / line_height)
                        
                        # Draw text directly with clipping
                        text_lines = text_content.split('\n')[:max_lines]
                        for line_idx, line in enumerate(text_lines):
                            y_pos = frame_y_pdf + scaled_bbox_height - (line_idx + 1) * line_height
                            # Only draw if visible on page
                            if y_pos > frame_y_pdf:
                                # Truncate line if too long
                                drawn_text = line
                                if doc_canvas.stringWidth(drawn_text, text_style.fontName, text_style.fontSize) > available_width_for_text:
                                    # Find where to cut the text
                                    char_limit = int(len(drawn_text) * available_width_for_text / 
                                                    doc_canvas.stringWidth(drawn_text, text_style.fontName, text_style.fontSize))
                                    if char_limit > 3:  # Only truncate if we can show something meaningful
                                        drawn_text = drawn_text[:char_limit-3] + "..."
                                
                                doc_canvas.drawString(frame_x_pdf + frame_left_padding, y_pos + frame_bottom_padding, drawn_text)
                        
                        doc_canvas.restoreState()
                        success = True  # Mark as success since we've done our best
                        
                        if current_attempt == max_attempts - 1:
                            print(f"Размещен текст для элемента {i} с минимальным размером шрифта {text_style.fontSize}")
                
            except Exception as frame_error:
                # Final attempt failed
                print(f"ОШИБКА при размещении текста для элемента {i}: {frame_error}")
                if debug_draw_bbox_borders:
                    doc_canvas.saveState()
                    doc_canvas.setStrokeColor(red)
                    doc_canvas.setFillColor(red)
                    doc_canvas.setStrokeAlpha(0.7)
                    doc_canvas.setFillAlpha(0.1)
                    doc_canvas.rect(frame_x_pdf, frame_y_pdf, scaled_bbox_width, scaled_bbox_height, fill=1, stroke=1)
                    doc_canvas.restoreState()
                break
                
        # If no success after all attempts and debug is enabled, draw error indicator
        if not success and debug_draw_bbox_borders:
            doc_canvas.saveState()
            doc_canvas.setStrokeColor(purple)  # Используем фиолетовый для обозначения полного провала размещения
            doc_canvas.setDash(2, 4)
            doc_canvas.rect(frame_x_pdf, frame_y_pdf, scaled_bbox_width, scaled_bbox_height)
            doc_canvas.restoreState()

    doc_canvas.save()
    print(f"PDF файл '{output_pdf_filename}' успешно сгенерирован.")
