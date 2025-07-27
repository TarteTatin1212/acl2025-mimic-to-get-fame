import time
import random
import logging
import instructor

import re
from openai.types.chat import ChatCompletion

def process_deepseek_content(response):
    """Processes DeepSeek response content while maintaining ChatCompletion structure"""
    if not response.choices:
        return response
    
    # Process the content of the first choice
    original_content = response.choices[0].message.content or ""
    processed_content = re.sub(r'<think>.*?</think>', '', original_content, flags=re.DOTALL).strip()
    
    # Create updated objects using model_copy
    new_message = response.choices[0].message.model_copy(update={"content": processed_content})
    new_choices = [response.choices[0].model_copy(update={"message": new_message})]
    
    return response.model_copy(update={"choices": new_choices})

class ModelHandler():
    @staticmethod
    def call_model_with_retry(client, messages, model, max_tokens=1000, max_attempts=6, base_delay=3.0, response_model=None):
        for attempt in range(max_attempts):
            try:
                response = ModelHandler.call_model(client, model, messages, max_tokens, response_model=response_model)
                return response
            except Exception as e:
                if "429" in str(e):
                    sleep_time = (2 ** (attempt + 1)) + \
                        (random.randint(0, 1000) / 1000)
                    logging.warning(
                        f"Rate limit hit, backing off for {sleep_time} seconds.")
                    time.sleep(sleep_time)
                    attempt += 1
                else:
                    print(f"Error encountered: {str(e)}", flush=True)
                    break
            finally:
                time.sleep(base_delay)

    @staticmethod
    def call_model(cl, model, messages, max_tokens=1200, response_model=None):
        if response_model:
            patched_cl = instructor.patch(cl, ) # mode=instructor.Mode.MD_JSON 
            response = patched_cl.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                n=1,
                stop=None,
                temperature=0,
                top_p=0.95,
                frequency_penalty=0.5,
                presence_penalty=0.5,
                response_model=response_model  # Instructor will validate and convert.
            )
        else:
            response = cl.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                n=1,
                stop=None,
                temperature=0,
                top_p=0.95,
                frequency_penalty=0.5,
                presence_penalty=0.5,
            )

            if model == "deepseek-r1-distill-llama-70b":
                return process_deepseek_content(response)
                
    
        return response