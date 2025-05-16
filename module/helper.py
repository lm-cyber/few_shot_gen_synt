def calculate_area(box):
    """Рассчитывает площадь bbox.
    box: [xmin, ymin, xmax, ymax]
    """
    if box[0] >= box[2] or box[1] >= box[3]:
        return 0.0
    return (box[2] - box[0]) * (box[3] - box[1])

def calculate_iou(box1, box2):
    """
    Рассчитывает Intersection over Union (IoU) для двух bbox.
    box1, box2: [xmin, ymin, xmax, ymax]
    """
    # Координаты пересечения
    xmin_inter = max(box1[0], box2[0])
    ymin_inter = max(box1[1], box2[1])
    xmax_inter = min(box1[2], box2[2])
    ymax_inter = min(box1[3], box2[3])

    # Площадь пересечения
    intersection_area = max(0, xmax_inter - xmin_inter) * max(0, ymax_inter - ymin_inter)

    # Площади каждого bbox
    area1 = calculate_area(box1)
    area2 = calculate_area(box2)

    # Площадь объединения
    union_area = area1 + area2 - intersection_area

    if union_area == 0:
        return 0.0  # Избегаем деления на ноль

    iou = intersection_area / union_area
    return iou

def is_inside(inner_box, outer_box, tolerance=0.0):
    """
    Проверяет, находится ли inner_box полностью внутри outer_box.
    tolerance: небольшое допущение, чтобы учесть возможные погрешности float.
               Если inner_box почти касается границы outer_box, но из-за
               погрешности выходит на epsilon, tolerance может это скомпенсировать.
               Для строгой вложенности используйте tolerance = 0.0.
    """
    return (outer_box[0] - tolerance <= inner_box[0] and
            outer_box[1] - tolerance <= inner_box[1] and
            outer_box[2] + tolerance >= inner_box[2] and
            outer_box[3] + tolerance >= inner_box[3])

def filter_contained_boxes(boxes,labels):
    """
    Фильтрует список bbox, удаляя те, которые полностью содержатся в других.
    boxes: список bbox, где каждый bbox это [xmin, ymin, xmax, ymax]
    """
    if not boxes:
        return []

    n = len(boxes)
    # Изначально считаем, что все bbox нужно сохранить
    keep_mask = [True] * n

    for i in range(n):
        # Если i-й bbox уже помечен на удаление, пропускаем его
        if not keep_mask[i]:
            continue

        for j in range(n):
            if i == j:  # Не сравниваем bbox сам с собой
                continue
            
            # Если j-й bbox (потенциальный контейнер) уже помечен на удаление,
            # он не может содержать i-й. Это необязательная оптимизация, т.к.
            # если j удален, он не будет в итоговом списке.
            # if not keep_mask[j]:
            #     continue

            box_i = boxes[i]
            box_j = boxes[j] # Потенциальный контейнер для box_i

            # Если box_i находится внутри box_j
            if is_inside(box_i, box_j):
                # Тогда box_i нужно удалить
                keep_mask[i] = False
                break # box_i уже содержится в box_j, нет смысла проверять другие контейнеры для box_i
    
    filtered_boxes = [boxes[i] for i in range(n) if keep_mask[i]]
    filtered_labels = [labels[i] for i in range(n) if keep_mask[i]]
    return filtered_boxes,filtered_labels
