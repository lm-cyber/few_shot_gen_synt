from vllm import LLM, SamplingParams
MODEL_NAME = "RefalMachine/RuadaptQwen2.5-14B-Instruct-1M"
SAMPLING_PARAMS = SamplingParams(temperature=0.7, top_p=0.9, max_tokens=500)
import os
from .config import anonymize_text_tokens

PROMPT_TEMPLATE = f"""Перефразируй следующий текст, сохраняя его первоначальный смысл. Важно: следующие плейсхолдеры должны остаться в тексте БЕЗ ИЗМЕНЕНИЙ:
{anonymize_text_tokens}

Текст для перефразирования:
"{{text_to_rephrase}}"

Перефразированный текст:
"""

class GENERATE_TEXT:
    def __init__(self):
        os.environ["CUDA_VISIBLE_DEVICES"] = "1"

        self.llm = LLM(
            model=MODEL_NAME,
            trust_remote_code=True,
        tensor_parallel_size=1,
        gpu_memory_utilization=0.7,
        max_model_len=1200,
        dtype="bfloat16"
      )



    def generate_text(self, texts):
        full_prompts = []
        for text in texts:
            full_prompts.append(PROMPT_TEMPLATE.format(text_to_rephrase=text))

        outputs = self.llm.generate(full_prompts, SAMPLING_PARAMS)
        rephrased_texts = []
        for i, output in enumerate(outputs):
            generated_text = output.outputs[0].text.strip() # Берем первый сгенерированный вариант
            rephrased_texts.append(generated_text)
        return rephrased_texts