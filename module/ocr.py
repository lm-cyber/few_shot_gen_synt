from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import os 

def ocr(img,model,processor, ):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": img,
                },
                # {"type": "text", "text": "Please perform OCR on this image. The text is in Russian. Return the recognized text exactly as it appears in the image, without translation."}, # RU !!!!!!!!!!!!!!!!
                {"type": "text", "text": "Please perform OCR on this image. Return the recognized text exactly as it appears in the image, without translation."},
            ],
        }
    ]

    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")

    generated_ids = model.generate(**inputs, max_new_tokens=128)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text
    

class OCR:
    def __init__(self):
        ocr_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct", torch_dtype="auto", device_map="auto"
        )

        # We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
        # model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        #     "Qwen/Qwen2.5-VL-7B-Instruct",
        #     torch_dtype=torch.bfloat16,
        #     attn_implementation="flash_attention_2", # а вот сука не работает, на моем железе!!!!!!!!!!!!!!!!!
        #     device_map="auto",
        # )

        # processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

        # The default range for the number of visual tokens per image in the model is 4-16384.
        # You can set min_pixels and max_pixels according to your needs, such as a token range of 256-1280, to balance performance and cost.
        min_pixels = 256*28*28
        max_pixels = 1280*28*28
        ocr_processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct", min_pixels=min_pixels, max_pixels=max_pixels)
        self.model = ocr_model
        self.processor = ocr_processor

    def ocr(self, img):
        return ocr(img, self.model, self.processor)[0]