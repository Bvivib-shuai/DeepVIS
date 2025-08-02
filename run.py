#!/usr/bin/env python3
"""
One-click pipeline script: Model Training -> Testing -> Evaluation
Integrates training, inference and evaluation in three steps
"""

import os
import json
import torch
import pandas as pd
import sqlite3
import re
import multiprocessing as mp
import requests
import zipfile
import shutil
from collections import OrderedDict
from tqdm import tqdm
from func_timeout import func_timeout, FunctionTimedOut

# Training related imports
from trl import SFTTrainer
from datasets import Dataset
from transformers import TrainingArguments, EarlyStoppingCallback, AutoTokenizer
from unsloth.chat_templates import get_chat_template
from unsloth import FastLanguageModel, is_bfloat16_supported
from sageattention import sageattn

# Testing related imports
from transformers import TextStreamer
from peft import PeftModel

# Set environment variables
os.environ['NCCL_P2P_DISABLE'] = '1'
os.environ['NCCL_IB_DISABLE'] = '1'
# Can modify GPU as needed
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

class IntegratedPipeline:
    def __init__(self, config=None):
        """
        Initialize configuration parameters
        """
        self.config = config or {
            'train_data_file': 'cot_train_format.json',
            'test_data_file': 'cot_test_format.json',
            'database_dir': 'database',
            'model_name': 'unsloth/Meta-Llama-3.1-8B-Instruct',
            'max_seq_length': 4048,
            'learning_rate': 4e-5,
            'per_device_train_batch_size': 4,
            'gradient_accumulation_steps': 8,
            'num_train_epochs': 4,
            'total_samples': 11260,
            'r': 16,
            'lora_alpha': 16,
            'target_modules': ["q_proj", "k_proj", "v_proj", "up_proj", "down_proj", "o_proj", "gate_proj"]
        }
        
        # Generate timestamp
        self.timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.model_folder = f"check_model_{self.timestamp}"
        self.adapter_folder = "output"
        self.test_results_file = f"cot_test_{self.timestamp}.json"

    def download_and_setup_data(self):
        """
        Download and setup training/testing data and databases from GitHub
        """
        print("=" * 60)
        print("Step 0/3: Downloading and setting up data...")
        print("=" * 60)
        
        # Check if files already exist
        data_files_exist = os.path.exists(self.config['train_data_file']) and os.path.exists(self.config['test_data_file'])
        database_exists = os.path.exists(self.config['database_dir']) and os.listdir(self.config['database_dir'])
        
        if data_files_exist and database_exists:
            print("Data files and databases already exist, skipping download.")
            return
        
        # Download training/testing data if needed
        if not data_files_exist:
            self.download_training_data()
        else:
            print("Training/testing data files already exist, skipping data download.")
        
        # Download databases if needed
        if not database_exists:
            self.download_databases()
        else:
            print("Database directory already exists and is not empty, skipping database download.")

    def download_training_data(self):
        """
        Download and setup training/testing data from DeepVIS repository
        """
        print("\n--- Downloading Training/Testing Data ---")
        
        # GitHub raw file URL for the zip
        zip_url = "https://github.com/Bvivib-shuai/DeepVIS/raw/main/nvBench-CoT.zip"
        zip_filename = "nvBench-CoT.zip"
        extract_dir = "nvBench-CoT"
        
        try:
            # Download the zip file
            print("Downloading nvBench-CoT.zip from GitHub...")
            self.download_file_with_progress(zip_url, zip_filename)
            print("Download completed!")
            
            # Extract the zip file
            print("Extracting zip file...")
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall()
            
            # Find the extracted directory (it might be nested)
            extracted_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file in ['train.json', 'test.json']:
                        extracted_files.append(os.path.join(root, file))
            
            # Locate train.json and test.json
            train_json_path = None
            test_json_path = None
            
            for file_path in extracted_files:
                if file_path.endswith('train.json'):
                    train_json_path = file_path
                elif file_path.endswith('test.json'):
                    test_json_path = file_path
            
            if not train_json_path or not test_json_path:
                raise FileNotFoundError("Could not find train.json or test.json in extracted files")
            
            # Copy files to target locations
            print("Setting up data files...")
            shutil.copy2(train_json_path, self.config['train_data_file'])
            shutil.copy2(test_json_path, self.config['test_data_file'])
            
            print(f"✓ {train_json_path} -> {self.config['train_data_file']}")
            print(f"✓ {test_json_path} -> {self.config['test_data_file']}")
            
            # Clean up
            print("Cleaning up temporary files...")
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            
            # Remove extracted directory if it exists
            for root, dirs, files in os.walk('.', topdown=False):
                for dirname in dirs:
                    if 'nvBench-CoT' in dirname or 'DeepVIS' in dirname:
                        dir_path = os.path.join(root, dirname)
                        try:
                            shutil.rmtree(dir_path)
                        except:
                            pass
            
            print("Training/testing data setup completed!")
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading file: {e}")
            print("Please manually download the file from:")
            print("https://github.com/Bvivib-shuai/DeepVIS/blob/main/nvBench-CoT.zip")
            raise
        except zipfile.BadZipFile:
            print("Error: Downloaded file is not a valid zip file")
            raise
        except Exception as e:
            print(f"Error setting up training data: {e}")
            raise

    def download_databases(self):
        """
        Download and setup databases from nvBench repository
        """
        print("\n--- Downloading Databases ---")
        
        # GitHub raw file URL for the databases zip
        zip_url = "https://github.com/TsinghuaDatabaseGroup/nvBench/raw/main/databases.zip"
        zip_filename = "databases.zip"
        temp_extract_dir = "temp_databases"
        
        try:
            # Download the zip file
            print("Downloading databases.zip from nvBench repository...")
            self.download_file_with_progress(zip_url, zip_filename)
            print("Database download completed!")
            
            # Create temporary extraction directory
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)
            
            # Extract the zip file to temporary directory
            print("Extracting database files...")
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # Create target database directory if it doesn't exist
            if os.path.exists(self.config['database_dir']):
                shutil.rmtree(self.config['database_dir'])
            os.makedirs(self.config['database_dir'])
            
            # Find and move all database-related files
            moved_files = 0
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    src_file = os.path.join(root, file)
                    
                    # Calculate relative path from the temp extraction directory
                    rel_path = os.path.relpath(src_file, temp_extract_dir)
                    
                    # Remove any leading 'databases' or similar directory from the path
                    path_parts = rel_path.split(os.sep)
                    if path_parts[0].lower() in ['databases', 'database', 'db']:
                        rel_path = os.sep.join(path_parts[1:]) if len(path_parts) > 1 else path_parts[0]
                    
                    # Create destination path
                    dst_file = os.path.join(self.config['database_dir'], rel_path)
                    dst_dir = os.path.dirname(dst_file)
                    
                    # Create destination directory if needed
                    if dst_dir and not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    
                    # Copy the file
                    shutil.copy2(src_file, dst_file)
                    moved_files += 1
            
            print(f"✓ Moved {moved_files} files to: {self.config['database_dir']}")
            
            # Count database files specifically
            db_count = 0
            sqlite_files = []
            for root, dirs, files in os.walk(self.config['database_dir']):
                for file in files:
                    if file.endswith('.sqlite'):
                        db_count += 1
                        sqlite_files.append(os.path.join(root, file))
            
            print(f"✓ Found {db_count} SQLite database files")
            
            # Show directory structure
            print(f"✓ Database directory structure:")
            for root, dirs, files in os.walk(self.config['database_dir']):
                level = root.replace(self.config['database_dir'], '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:3]:  # Show first 3 files in each directory
                    print(f"{subindent}{file}")
                if len(files) > 3:
                    print(f"{subindent}... and {len(files)-3} more files")
            
            # Clean up
            print("Cleaning up temporary files...")
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            
            print("Database setup completed!")
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading databases: {e}")
            print("Please manually download the file from:")
            print("https://github.com/TsinghuaDatabaseGroup/nvBench/blob/main/databases.zip")
            print(f"Then extract it to the '{self.config['database_dir']}' directory")
            raise
        except zipfile.BadZipFile:
            print("Error: Downloaded database file is not a valid zip file")
            raise
        except Exception as e:
            print(f"Error setting up databases: {e}")
            raise

    def download_file_with_progress(self, url, filename):
        """
        Download file with progress bar
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        with open(filename, 'wb') as file:
            if total_size == 0:
                file.write(response.content)
            else:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {filename}") as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            pbar.update(len(chunk))

    def deep_dict_to_json(self, obj):
        """Recursively convert dictionary to JSON format"""
        if isinstance(obj, dict):
            return {key: self.deep_dict_to_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.deep_dict_to_json(item) for item in obj]
        else:
            return obj

    def train_model(self):
        """
        Model training phase
        """
        print("=" * 60)
        print("Step 1/3: Starting model training...")
        print("=" * 60)
        
        # Load pretrained model
        print("Loading pretrained model...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.config['model_name'],
            max_seq_length=self.config['max_seq_length'],
            load_in_4bit=True,
            dtype=None,
        )
        
        # Configure LoRA
        print("Configuring LoRA parameters...")
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.config['r'],
            lora_alpha=self.config['lora_alpha'],
            lora_dropout=0,
            target_modules=self.config['target_modules'],
            use_rslora=True,
            use_gradient_checkpointing="unsloth",
        )

        # Load training data
        print("Loading training data...")
        data_train = []
        with open(self.config['train_data_file'], "r") as file:
            train_data = json.load(file)  
            for json_obj in train_data:
                json_obj = self.deep_dict_to_json(json_obj)
                json_obj = json.dumps(json_obj, ensure_ascii=False, indent=4)
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
                tokenizer.apply_chat_template(message, tokenize=False, add_generation_prompt=False) 
                for message in messages
            ]
            return {"text": text}
        
        dataset_train = Dataset.from_pandas(df_train) 
        dataset_train = dataset_train.map(apply_template, batched=True)
        print(f"Training data sample: {dataset_train[0]}")
        
        # Calculate training parameters
        effective_batch_size = self.config['per_device_train_batch_size'] * self.config['gradient_accumulation_steps']
        total_steps = (self.config['total_samples'] * self.config['num_train_epochs']) // effective_batch_size
        warmup_steps = int(0.1 * total_steps)
        
        print(f"Total training steps: {total_steps}, Warmup steps: {warmup_steps}")

        # Initialize trainer
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset_train,
            dataset_text_field="text",
            max_seq_length=self.config['max_seq_length'],
            dataset_num_proc=1,
            packing=True,
            args=TrainingArguments(
                learning_rate=self.config['learning_rate'],
                lr_scheduler_type="cosine",
                per_device_train_batch_size=self.config['per_device_train_batch_size'],
                gradient_accumulation_steps=self.config['gradient_accumulation_steps'],
                num_train_epochs=self.config['num_train_epochs'],
                fp16=not is_bfloat16_supported(),
                bf16=is_bfloat16_supported(),
                logging_steps=1,
                optim="adamw_hf",
                weight_decay=0.01,
                warmup_steps=warmup_steps,
                output_dir=self.adapter_folder, 
                seed=0,
            ),
        )

        # Start training
        print("Starting training...")
        trainer.train()

        # Save model
        print(f"Saving model to: {self.model_folder}")
        model.save_pretrained_merged(self.model_folder, tokenizer, save_method="merged_16bit")
        
        print("Training completed!")
        return self.model_folder, self.adapter_folder

    def test_model(self):
        """
        Model testing phase
        """
        print("=" * 60)
        print("Step 2/3: Starting model testing...")
        print("=" * 60)
        
        # Find latest checkpoint
        checkpoint_dirs = [d for d in os.listdir(self.adapter_folder) if d.startswith('checkpoint-')]
        if not checkpoint_dirs:
            raise FileNotFoundError("No training checkpoint found")
        
        # Sort by number and take the largest
        latest_checkpoint = max(checkpoint_dirs, key=lambda x: int(x.split('-')[1]))
        adapter_path = os.path.join(self.adapter_folder, latest_checkpoint)
        
        print(f"Using model: {self.model_folder}")
        print(f"Using adapter: {adapter_path}")

        # Load model
        print("Loading trained model...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.model_folder,
            max_seq_length=self.config['max_seq_length'],
            load_in_4bit=True,
            dtype=None,
        )
        
        print("Pad token:", tokenizer.pad_token)  
        print("EOS token:", tokenizer.eos_token)  
        model = FastLanguageModel.for_inference(model)
        model = PeftModel.from_pretrained(model, adapter_path)

        # Load test data
        print("Loading test data...")
        test_data = []
        with open(self.config['test_data_file'], 'r') as file:
            data = json.load(file)
            for json_obj in data:
                json_obj = self.deep_dict_to_json(json_obj)
                json_obj = json.dumps(json_obj, ensure_ascii=False, indent=4)
                test_data.append(json.loads(json_obj))

        # Generate inference results
        print("Starting inference...")
        results = []
        device = next(model.parameters()).device
        
        for item in tqdm(test_data, desc="Inference progress"):
            content_1 = item.get('content_1', {})
            prompt = {"role": "user", "content": content_1}

            # Generate response
            inputs = tokenizer.apply_chat_template(
                [prompt],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
            inputs = inputs.to(device)

            response = model.generate(
                input_ids=inputs, 
                max_new_tokens=4048, 
                use_cache=True, 
                temperature=0.1
            )
            response_txt = tokenizer.decode(response[0], skip_special_tokens=True)

            result = {
                "prompt": prompt,
                "response_finetuned_model": response_txt,
            }
            results.append(result)

        # Save results
        print(f"Saving test results to: {self.test_results_file}")
        with open(self.test_results_file, 'w') as json_file:
            json.dump(results, json_file, indent=4, ensure_ascii=False)

        print("Testing completed!")
        return self.test_results_file

    def evaluate_results(self):
        """
        Model evaluation phase
        """
        print("=" * 60)
        print("Step 3/3: Starting model evaluation...")
        print("=" * 60)

        # Load test results and ground truth labels
        print("Loading test results and ground truth labels...")
        try:
            with open(self.test_results_file, 'r') as f:
                test_data = json.load(f)
        except FileNotFoundError:
            print(f"Test results file not found: {self.test_results_file}")
            return

        try:
            with open(self.config['test_data_file'], 'r') as f:
                groundtruth_data = json.load(f)
        except FileNotFoundError:
            print(f"Ground truth file not found: {self.config['test_data_file']}")
            return

        # Evaluation function definitions
        def extract_last_vql_1(text):
            """Extract the last VQL statement from text"""
            try:
                vql_pattern = re.compile(r'(Visualize\s+[A-Z]+\s+SELECT.*)', re.IGNORECASE | re.DOTALL)
                matches = vql_pattern.findall(text)
                if matches:
                    last_vql = matches[-1].strip()
                    last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
                    return last_vql
                return None
            except Exception as e:
                print(f"Error extracting VQL: {e}")
                return None

        def extract_last_vql(text):
            """Extract Final VQL from text"""
            vql_pattern = re.compile(r'Final VQL:(.*)', re.IGNORECASE | re.DOTALL)
            matches = vql_pattern.findall(text)
            if matches:
                last_vql = matches[-1].strip()
                last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
                return last_vql
            return None

        def extract_vis(vql):
            """Extract VISUALIZE field from VQL"""
            vql = vql.upper()
            parts = vql.split()
            if len(parts) > 1 and parts[0].upper() == 'VISUALIZE':
                return parts[1].upper()
            return None

        def remove_space_before_comma(sql):
            """Remove spaces before commas"""
            result = ""
            for i, char in enumerate(sql):
                if char == ' ' and i > 0 and sql[i + 1] == ',':
                    continue
                result += char
            return result

        def extract_sql(vql):
            """Extract SQL part from VQL"""
            vql = vql.upper()
            vis = extract_vis(vql)
            if vis:
                vql = vql.replace(f"VISUALIZE {vis}", "").strip()
            bin_by_index = vql.find('BIN')
            if bin_by_index != -1:
                return vql[:bin_by_index].strip()
            return vql.strip()

        def extract_bin(vql):
            """Extract BIN part from VQL"""
            bin_by_index = vql.find('BIN')
            if bin_by_index != -1:
                return vql[bin_by_index:].strip()
            return None

        def extract_select_columns(sql):
            """Extract column names from SELECT fields in SQL"""
            if sql.startswith('SELECT'):
                select_part = sql[len('SELECT'):].strip()
                columns = select_part.split(',')
                columns = [col.strip().split(' ')[0].lower() for col in columns]
                return columns
            return []

        def evaluate_accuracy(response_vql, groundtruth_vql):
            """Evaluate accuracy of response VQL against ground truth VQL"""
            # Extract VISUALIZE field
            response_vis = extract_vis(response_vql)
            groundtruth_vis = extract_vis(groundtruth_vql)
            vis_accuracy = response_vis == groundtruth_vis
            
            # Extract SQL part
            response_sql = extract_sql(response_vql)
            groundtruth_sql_1 = extract_sql(groundtruth_vql)
            groundtruth_sql = remove_space_before_comma(groundtruth_sql_1)
            
            sql_accuracy = 1 if response_sql is not None and groundtruth_sql is not None and response_sql.lower() == groundtruth_sql.lower() else 0

            # Extract BIN part
            response_bin = extract_bin(response_vql)
            groundtruth_bin = extract_bin(groundtruth_vql)
            
            if response_bin is None and groundtruth_bin is None:
                bin_accuracy = 1
            elif response_bin is None or groundtruth_bin is None:
                bin_accuracy = 0
            else:
                bin_accuracy = 1 if response_bin.lower() == groundtruth_bin.lower() else 0

            # Extract SELECT columns
            response_columns = extract_select_columns(response_sql)
            groundtruth_columns = extract_select_columns(groundtruth_sql)

            if len(groundtruth_columns) == 0:
                select_columns_accuracy = 1 if len(response_columns) == 0 else 0
            else:
                correct_count = sum(col in response_columns for col in groundtruth_columns)
                select_columns_accuracy = correct_count / len(groundtruth_columns)

            # Compare after removing VISUALIZE part
            response_without_vis = response_vql.replace(f"Visualize {response_vis}", "").strip().lower() if response_vis else response_vql.strip().lower()
            groundtruth_without_vis_1 = groundtruth_vql.replace(f"Visualize {groundtruth_vis}", "").strip().lower() if groundtruth_vis else groundtruth_vql.strip().lower()
            groundtruth_without_vis = remove_space_before_comma(groundtruth_without_vis_1)
            
            data_accuracy = 1 if response_without_vis == groundtruth_without_vis else 0
            all_accuracy = 1 if vis_accuracy and data_accuracy else 0

            return vis_accuracy, sql_accuracy, bin_accuracy, select_columns_accuracy, data_accuracy, all_accuracy

        # Database execution functions
        def check_table_exists_and_has_data(conn, table_name):
            """Check if table exists and has data"""
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name)=?", (table_name.lower(),))
                table_exists = cursor.fetchone() is not None
                if table_exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    return row_count > 0
                return False
            except Exception as e:
                print(f"Error checking if table exists and has data: {e}")
                return False

        def get_table_and_column_names(conn):
            """Get all table and column names from database"""
            cursor = conn.cursor()
            table_names = []
            column_names = {}
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row[0] for row in cursor.fetchall()]
                for table_name in table_names:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    column_names[table_name] = [row[1] for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error getting table and column names: {e}")
            return table_names, column_names

        def standardize_sql(sql, table_names, column_names):
            """Standardize SQL with correct table and column names"""
            word_pattern = r'(["\']?[a-zA-Z_]+["\']?)'
            words = re.findall(word_pattern, sql)
            for word in words:
                stripped_word = word.strip('"\'')
                for table_name in table_names:
                    if stripped_word.lower() == table_name.lower():
                        replacement = word.replace(stripped_word, table_name)
                        sql = sql.replace(word, replacement)
                for columns in column_names.values():
                    for column in columns:
                        if stripped_word.lower() == column.lower():
                            replacement = word.replace(stripped_word, column)
                            sql = sql.replace(word, replacement)
            return sql

        def execute_sql(predicted_sql, ground_truth, db_path, db_id):
            """Execute SQL queries and compare results"""
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            empty_db_ids = []
            skipped = False
            skipped_info = {}
            try:
                table_names, column_names = get_table_and_column_names(conn)
                predicted_sql = standardize_sql(predicted_sql, table_names, column_names)
                ground_truth = standardize_sql(ground_truth, table_names, column_names)

                table_name_match = re.search(r'\bFROM\s+(["\']?[a-zA-Z_]+["\']?)(?:\s+AS\s+["\']?[a-zA-Z_]+["\']?)?',
                                             predicted_sql, re.IGNORECASE)
                if table_name_match:
                    table_name = table_name_match.group(1).strip('"\'')
                    if not check_table_exists_and_has_data(conn, table_name):
                        empty_db_ids.append(db_id)
                        skipped = True
                        skipped_info = {
                            "db_id": db_id,
                            "predicted_sql": predicted_sql,
                            "ground_truth": ground_truth,
                            "reason": f"Table {table_name} does not exist or is empty"
                        }
                        return 0, empty_db_ids, skipped, skipped_info

                cursor.execute(predicted_sql)
                predicted_res = cursor.fetchall()
                cursor.execute(ground_truth)
                ground_truth_res = cursor.fetchall()

                predicted_res = sorted(predicted_res)
                ground_truth_res = sorted(ground_truth_res)

                return 1 if predicted_res == ground_truth_res else 0, empty_db_ids, skipped, skipped_info
            except Exception as e:
                skipped_info = {
                    "db_id": db_id,
                    "predicted_sql": predicted_sql,
                    "ground_truth": ground_truth,
                    "reason": f"Error executing SQL: {e}"
                }
                return 0, empty_db_ids, skipped, skipped_info
            finally:
                conn.close()

        def find_sqlite_file(db_id):
            """Find SQLite database file for given db_id"""
            db_dir = f"{self.config['database_dir']}/{db_id}/"
            if os.path.exists(db_dir):
                for root, dirs, files in os.walk(db_dir):
                    for file in files:
                        if file.endswith('.sqlite'):
                            db_path = os.path.join(root, file)
                            return db_path
            return None

        # Text-based evaluation
        print("Performing text-based evaluation...")
        total_samples = len(test_data)
        valid_samples = 0
        vis_accuracies = []
        sql_accuracies = []
        bin_accuracies = []
        select_columns_accuracies = []
        data_accuracies = []
        all_accuracies = []

        # For database execution
        sql_pairs = []
        vis_pairs = []
        bin_by_pairs = []
        db_paths = []
        db_ids = []

        for i in range(total_samples):
            # Extract response VQL
            response_text = test_data[i]['response_finetuned_model']
            response_vql = extract_last_vql_1(response_text)
            if not response_vql:
                continue

            # Extract ground truth VQL
            groundtruth_text = groundtruth_data[i]['content_2']
            groundtruth_vql = extract_last_vql(groundtruth_text)
            if not groundtruth_vql:
                continue

            valid_samples += 1
            
            # Text-based evaluation
            vis_acc, sql_acc, bin_acc, select_columns_acc, data_acc, all_acc = evaluate_accuracy(response_vql, groundtruth_vql)
            vis_accuracies.append(vis_acc)
            sql_accuracies.append(sql_acc)
            bin_accuracies.append(bin_acc)
            select_columns_accuracies.append(select_columns_acc)
            data_accuracies.append(data_acc)
            all_accuracies.append(all_acc)

            # Prepare for database execution
            response_sql = extract_sql(response_vql)
            groundtruth_sql = extract_sql(groundtruth_vql)
            response_vis = extract_vis(response_vql)
            groundtruth_vis = extract_vis(groundtruth_vql)
            response_bin_by = extract_bin(response_vql)
            groundtruth_bin_by = extract_bin(groundtruth_vql)

            # Get db_id and find database file
            db_id = groundtruth_data[i]['db_id']
            db_path = find_sqlite_file(db_id)
            if db_path:
                sql_pairs.append((response_sql, groundtruth_sql))
                vis_pairs.append((response_vis, groundtruth_vis))
                bin_by_pairs.append((response_bin_by, groundtruth_bin_by))
                db_paths.append(db_path)
                db_ids.append(db_id)

        # Calculate text-based accuracies
        if valid_samples > 0:
            avg_vis_accuracy = sum(vis_accuracies) / valid_samples
            avg_sql_accuracy = sum(sql_accuracies) / valid_samples
            avg_select_columns_accuracy = sum(select_columns_accuracies) / valid_samples
        else:
            avg_vis_accuracy = avg_sql_accuracy = avg_select_columns_accuracy = 0

        # Database execution evaluation
        avg_sql_execution_accuracy = 0
        avg_all_execution_accuracy = 0
        
        if sql_pairs and os.path.exists(self.config['database_dir']):
            print("Performing database execution evaluation...")
            
            # Execute SQL queries in parallel (simplified version)
            correct_sql_count = 0
            correct_all_count = 0
            executed_count = 0
            
            for i, (sql_pair, vis_pair, bin_by_pair) in enumerate(zip(sql_pairs, vis_pairs, bin_by_pairs)):
                try:
                    predicted_sql, ground_truth = sql_pair
                    predicted_vis, ground_truth_vis = vis_pair
                    predicted_bin_by, ground_truth_bin_by = bin_by_pair
                    
                    # Execute SQL
                    sql_result, _, _, _ = execute_sql(predicted_sql, ground_truth, db_paths[i], db_ids[i])
                    
                    # Calculate vis and bin results
                    vis_result = 1 if predicted_vis == ground_truth_vis else 0
                    bin_result = 1 if predicted_bin_by == ground_truth_bin_by else 0
                    
                    # Accumulate results
                    correct_sql_count += sql_result
                    if sql_result == 1 and vis_result == 1 and bin_result == 1:
                        correct_all_count += 1
                    executed_count += 1
                    
                except Exception as e:
                    print(f"Error executing SQL for sample {i}: {e}")
                    continue
            
            if executed_count > 0:
                avg_sql_execution_accuracy = (correct_sql_count / executed_count) * 100
                avg_all_execution_accuracy = (correct_all_count / executed_count) * 100
        else:
            print("Skipping database execution evaluation (database directory not found or no valid SQL pairs)")

        # Output final results
        print("\n" + "=" * 60)
        print("EVALUATION RESULTS SUMMARY")
        print("=" * 60)
        print(f"Chart Acc: {avg_vis_accuracy:.4f}")
        print(f"Axis Acc: {avg_select_columns_accuracy:.4f}")
        print(f"SQL Acc: {avg_sql_accuracy:.4f}")
        print(f"Data Acc: {avg_sql_execution_accuracy:.2f}%")
        print(f"All Acc: {avg_all_execution_accuracy:.2f}%")
        
        # Save evaluation results
        evaluation_results = {
            'timestamp': self.timestamp,
            'total_samples': total_samples,
            'valid_samples': valid_samples,
            'chart_accuracy': avg_vis_accuracy,
            'axis_accuracy': avg_select_columns_accuracy,
            'sql_accuracy': avg_sql_accuracy,
            'data_accuracy': avg_sql_execution_accuracy / 100,  # Convert back to 0-1 scale
            'all_accuracy': avg_all_execution_accuracy / 100,   # Convert back to 0-1 scale
            'model_folder': self.model_folder,
            'test_results_file': self.test_results_file
        }
        
        results_file = f"evaluation_results_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
        
        print(f"\nEvaluation results saved to: {results_file}")
        print("Evaluation completed!")

    def run_full_pipeline(self):
        """
        Run complete pipeline: Data/Database Download -> Training -> Testing -> Evaluation
        """
        print("Starting complete training-testing-evaluation pipeline...")
        print(f"Timestamp: {self.timestamp}")
        
        try:
            # Step 0: Download and setup data and databases
            self.download_and_setup_data()
            
            # Step 1: Train model
            model_folder, adapter_folder = self.train_model()
            
            # Step 2: Test model
            test_results_file = self.test_model()
            
            # Step 3: Evaluate results
            self.evaluate_results()
            
            print("\n" + "=" * 60)
            print("COMPLETE PIPELINE EXECUTED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Data files and databases downloaded and set up")
            print(f"Trained model saved in: {model_folder}")
            print(f"Test results saved in: {test_results_file}")
            print(f"Evaluation results saved in: evaluation_results_{self.timestamp}.json")
            
        except Exception as e:
            print(f"Pipeline execution error: {str(e)}")
            raise

def main():
    """Main function"""
    # Custom configuration (can be modified here)
    config = {
        'train_data_file': 'cot_train_format.json',
        'test_data_file': 'cot_test_format.json',
        'database_dir': 'database',
        'model_name': 'unsloth/Meta-Llama-3.1-8B-Instruct',
        'max_seq_length': 4048,
        'learning_rate': 4e-5,
        'per_device_train_batch_size': 4,
        'gradient_accumulation_steps': 8,
        'num_train_epochs': 4,
        'total_samples': 11260,
        'r': 16,
        'lora_alpha': 16,
        'target_modules': ["q_proj", "k_proj", "v_proj", "up_proj", "down_proj", "o_proj", "gate_proj"]
    }
    
    # Create pipeline instance and run
    pipeline = IntegratedPipeline(config)
    pipeline.run_full_pipeline()

if __name__ == "__main__":
    main()
