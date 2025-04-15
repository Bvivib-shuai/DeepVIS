import torch
import pandas as pd
import json
from collections import OrderedDict
from trl import SFTTrainer
from datasets import Dataset
from transformers import TrainingArguments
from unsloth.chat_templates import get_chat_template
from unsloth import FastLanguageModel, is_bfloat16_supported
from transformers import EarlyStoppingCallback
from sageattention import sageattn
from transformers import AutoTokenizer

def main():
    max_seq_length = 4048
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Meta-Llama-3.1-8B-Instruct",
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        dtype=None,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=16,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "up_proj", "down_proj", "o_proj", "gate_proj"],
        use_rslora=True,
        use_gradient_checkpointing="unsloth",
    )


    def deep_dict_to_json(obj):
        if isinstance(obj, dict):
            return {key: deep_dict_to_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [deep_dict_to_json(item) for item in obj]
        else:
            return obj
          
    data_train = []
    with open("CoT-nvBench/train.json", "r") as file:
        train_data = json.load(file)  
        for json_obj in train_data:
            json_obj=deep_dict_to_json(json_obj)
            json_obj = json.dumps(json_obj, ensure_ascii=False, indent=4)
            #print(json_obj)
            data_train.append(json.loads(json_obj))
   
    df_train = pd.DataFrame(data_train)
    
    def apply_template(examples):
        messages = []
        for role_1, content_1, role_2, content_2 in zip(
                examples["role_1"], examples["content_1"], examples["role_2"], examples["content_2"]):
            content_1_str = json.dumps(content_1, ensure_ascii=False)
            content_2_str = json.dumps(content_2, ensure_ascii=False)
            messages.append([
                {"role": role_1, "content": content_1_str},
                {"role": role_2, "content": content_2_str}
            ])

        text = [
            tokenizer.apply_chat_template(message, tokenize=False, add_generation_prompt=False) for message in messages
        ]
        return {"text": text}
    dataset_train = Dataset.from_pandas(df_train) 
    #dataset_train = dataset_train.shuffle(seed=42)
    dataset_train = dataset_train.map(apply_template, batched=True)
    print(dataset_train[0])
    
    total_samples = 11260
    per_device_train_batch_size =4
    gradient_accumulation_steps=8
    num_train_epochs=4
    effective_batch_size = per_device_train_batch_size * gradient_accumulation_steps
    total_steps = (total_samples*num_train_epochs) // effective_batch_size

    warmup_steps = int(0.1 * total_steps)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset_train,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=1,
        packing=True,
        args=TrainingArguments(
            learning_rate=3e-4,
            lr_scheduler_type="cosine",
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            num_train_epochs=num_train_epochs,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=1,
            optim="adamw_hf",
            weight_decay=0.01,
            warmup_steps=warmup_steps,
            output_dir="output", 
            seed=0,
        ),
    )

    print("Training...")
    trainer.train()

    now = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    model.save_pretrained_merged(f"model_{now}", tokenizer, save_method="merged_16bit")

if __name__ == "__main__":
    main()
