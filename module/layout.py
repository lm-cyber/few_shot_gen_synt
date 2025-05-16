# Флоренс лучше но у меня не работает нормально флешатанешен, а без него просто не грузит !!!!!!!!!!!!!!!!!
# TODO ПРОЧИТАТЬ ЧТО ВЫШЕ 
from transformers import AutoImageProcessor
from transformers.models.detr import DetrForSegmentation
import os
from transformers import AutoProcessor, AutoModelForCausalLM
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import os
import torch
from PIL import Image, ImageDraw, ImageFont
load_dotenv()
 # можно пользовать для того чтобы генерация была более лучше 
from module.config import id2label
# "id2label": {
#     "0": "Caption",
#     "1": "Footnote",
#     "2": "Formula",
#     "3": "List-item",
#     "4": "Page-footer",
#     "5": "Page-header",
#     "6": "Picture",
#     "7": "Section-header",
#     "8": "Table",
#     "9": "Text",
#     "10": "Title"
#   },
class Layout:
    def __init__(self):
        self.img_proc = AutoImageProcessor.from_pretrained(
            "cmarkea/detr-layout-detection"
        )
        self.model = DetrForSegmentation.from_pretrained(
            "cmarkea/detr-layout-detection"
        ).to("cuda").eval()

    def detect_layout(self,img, threshold=0.5):
        with torch.inference_mode():
            input_ids = self.img_proc(img, return_tensors='pt').to("cuda")
            output = self.model(**input_ids)



        bbox_pred = self.img_proc.post_process_object_detection(
            output,
            threshold=threshold,
            target_sizes=[img.size[::-1]]
        )
        return list(map(lambda box: box.cpu().tolist(),bbox_pred[0]['boxes'])), list(map(lambda label: id2label[str(label.item())],bbox_pred[0]['labels']))

