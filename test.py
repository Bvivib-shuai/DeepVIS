import json
from unsloth import FastLanguageModel, is_bfloat16_supported
from transformers import TextStreamer
from peft import PeftModel
from tqdm import tqdm
import pandas as pd
#SAVED_MODEL_FOLDER ="your model path"
#SAVED_ADAPTER_FOLDER="your checkpoint path"
def deep_dict_to_json(obj):
    if isinstance(obj, dict):
        return {key: deep_dict_to_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [deep_dict_to_json(item) for item in obj]
    else:
        return obj

def load_json_data(filename: str):
    data = []
    with open(filename, 'r') as file:
        test_data = json.load(file)
        for json_obj in test_data:
            json_obj = deep_dict_to_json(json_obj)
            json_obj = json.dumps(json_obj, ensure_ascii=False, indent=4)
            data.append(json.loads(json_obj))
    return data

def extract_content_1(data):
    return data.get('content_1', {})

def generate_input(content_1):
    return {"role": "user", "content": content_1}

def load_model(with_lora: bool = True):
    max_seq_length = 4048
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=SAVED_MODEL_FOLDER,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        dtype=None,
    )
    print("Pad token:", tokenizer.pad_token)  
    print("EOS token:", tokenizer.eos_token)  
    model = FastLanguageModel.for_inference(model)

    if with_lora:
        model = PeftModel.from_pretrained(model, SAVED_ADAPTER_FOLDER)

    return model, tokenizer

def generate_responses(model, tokenizer, prompt):
    inputs = tokenizer.apply_chat_template(
        [prompt],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    )
    device = next(model.parameters()).device
    inputs = inputs.to(device)

    response = model.generate(input_ids=inputs, max_new_tokens=4048, use_cache=True, temperature=0.1)
 
    response_txt = tokenizer.decode(response[0], skip_special_tokens=True)
    return response_txt

def main():
    # Load JSON data
    json_data = load_json_data("check_cot_test_format_1.json")

    model_lora, tokenizer_lora = load_model(with_lora=True)
    results = []
    for item in tqdm(json_data, desc="Processing items"):
        content_1 = extract_content_1(item)
        prompt = generate_input(content_1)

        # Load model with LoRA
        response_lora = generate_responses(model_lora, tokenizer_lora, prompt)

        # Load model without LoRA
        #model_no_lora, tokenizer_no_lora = load_model(with_lora=False)
        #response_no_lora = generate_responses(model_no_lora, tokenizer_no_lora, prompt)

        # Create a result dictionary for each item
        result = {
            "prompt": prompt,
            "response_finetuned_model": response_lora,
            #"response_non_finetuned_model": response_no_lora
        }
        results.append(result)

    # Save results to a JSON file
    now = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"test_{now}.json", 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print(f"Results saved to all_test_{now}.json")

if __name__ == "__main__":
    main()
