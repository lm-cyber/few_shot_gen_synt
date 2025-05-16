import re
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc
)

# Инициализация компонентов Natasha
segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)

def replace_ner_entities(text, replacement_map):
    """
    Заменяет извлеченные именованные сущности (PER, LOC) на заданные токены.

    Args:
        text (str): Входной текст.
        replacement_map (dict): Словарь, где ключи - типы сущностей ('PER', 'LOC'),
                                а значения - токены для замены.

    Returns:
        str: Текст с замененными сущностями.
    """
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    # Чтобы корректно заменять, не нарушая индексы,
    # собираем замены и применяем их в обратном порядке
    replacements = []
    for span in doc.spans:
        if span.type in replacement_map:
            replacements.append({
                "start": span.start,
                "stop": span.stop,
                "token": replacement_map[span.type]
            })

    # Сортируем замены по начальному индексу в обратном порядке
    replacements.sort(key=lambda x: x['start'], reverse=True)

    processed_text = list(text)
    for rep in replacements:
        # Заменяем исходный фрагмент текста на токен
        processed_text[rep['start']:rep['stop']] = list(rep['token'])

    return "".join(processed_text)

def replace_phone_numbers(text, token="[PHONE_NUMBER]"):
    """
    Заменяет номера телефонов на заданный токен.
    Это простое регулярное выражение, может потребовать доработки.
    """
    # Упрощенное регулярное выражение для номеров телефонов
    # Может потребоваться более сложное для покрытия всех форматов
    phone_pattern = re.compile(
        r"(\+7|8)?[\s\(-]*(\d{3})[\s\)-]*(\d{3})[\s-]*(\d{2})[\s-]*(\d{2})"
    )
    return phone_pattern.sub(token, text)

def replace_emails(text, token="[EMAIL_ADDRESS]"):
    """
    Заменяет email адреса на заданный токен.
    """
    email_pattern = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    return email_pattern.sub(token, text)

def replace_age(text, token="[AGE]"):
    """
    Заменяет упоминания возраста (число + "лет/год/года") на заданный токен.
    Это очень простое регулярное выражение и может требовать доработки.
    """
    # Пример: "30 лет", "25 год", "42 года"
    age_pattern = re.compile(r"\b(\d{1,3})\s+(лет|год|года)\b", re.IGNORECASE)

    # Чтобы избежать замены частей уже замененных токенов,
    # ищем совпадения и заменяем их, идя по тексту с конца
    matches = []
    for match in age_pattern.finditer(text):
        matches.append((match.start(), match.end()))

    processed_text = list(text)
    for start, end in sorted(matches, reverse=True):
        # Проверяем, не находится ли совпадение внутри уже замененного токена (например, [LOCATION])
        # Это очень упрощенная проверка. В более сложных случаях нужна другая логика.
        original_substring = "".join(processed_text[start:end])
        if "[" not in original_substring and "]" not in original_substring:
             processed_text[start:end] = list(token)

    return "".join(processed_text)


def anonymize_text(text):
    """
    Комплексная функция для анонимизации текста.
    """
    # Шаг 1: Замена NER-сущностей (Имена, Локации)
    # Важно: Сначала заменяем NER, так как регулярки могут сработать на частях имен или локаций,
    # которые выглядят как email или телефон (хотя это маловероятно для стандартных токенов).
    ner_replacement_map = {
        "PER": "[PERSON_NAME]",
        "LOC": "[LOCATION]"
    }
    processed_text = replace_ner_entities(text, ner_replacement_map)

    # Шаг 2: Замена возраста (после NER, чтобы не мешать, если имя содержит числа)
    processed_text = replace_age(processed_text, token="[AGE]")

    # Шаг 3: Замена email адресов
    processed_text = replace_emails(processed_text, token="[EMAIL_ADDRESS]")

    # Шаг 4: Замена номеров телефонов
    processed_text = replace_phone_numbers(processed_text, token="[PHONE_NUMBER]")

    return processed_text
