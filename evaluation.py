import json
import sqlite3
import re
import os
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut

def extract_last_vql_1(text):
    """
    Extract the last occurrence of Visualize and subsequent content as VQL from text
    """
    try:
        # Define regex to precisely match VQL statements starting with Visualize
        vql_pattern = re.compile(r'(Visualize\s+[A-Z]+\s+SELECT.*)', re.IGNORECASE | re.DOTALL)
        matches = vql_pattern.findall(text)
        if matches:
            last_vql = matches[-1].strip()
            # Remove possible extra quotes and newlines
            last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
            return last_vql
        return None
    except Exception as e:
        print(f"Error extracting VQL: {e}")
        return None

def extract_last_vql(text):
    """
    Extract the last occurrence of VQL statement from text
    """
    vql_pattern = re.compile(r'Final VQL:(.*)', re.IGNORECASE | re.DOTALL)
    matches = vql_pattern.findall(text)
    if matches:
        last_vql = matches[-1].strip()
        # Remove possible extra quotes and newlines
        last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
        return last_vql
    return None

def extract_vis(vql):
    """
    Extract VISUALIZE field from VQL
    """
    vql = vql.upper()
    parts = vql.split()
    if len(parts) > 1 and parts[0].upper() == 'VISUALIZE':
        return parts[1].upper()
    return None

def remove_space_before_comma(sql):
    result = ""
    for i, char in enumerate(sql):
        if char == ' ' and i > 0 and sql[i + 1] == ',':
            continue
        result += char
    return result

def extract_sql(vql):
    """
    Extract SQL part from VQL
    """
    # Remove VISUALIZE part
    vql = vql.upper()
    vis = extract_vis(vql)
    if vis:
        vql = vql.replace(f"VISUALIZE {vis}", "").strip()
    # Check if contains BIN BY
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[:bin_by_index].strip()
    return vql.strip()

def extract_bin(vql):
    """
    Extract BIN part from VQL
    """
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[bin_by_index:].strip()
    return None

def extract_select_columns(sql):
    """
    Extract column names from SELECT fields in SQL
    """
    if sql.startswith('SELECT'):
        select_part = sql[len('SELECT'):].strip()
        columns = select_part.split(',')
        columns = [col.strip().split(' ')[0].lower() for col in columns]  # Convert column names to lowercase
        return columns
    return []

def evaluate_accuracy(response_vql, groundtruth_vql):
    """
    Evaluate accuracy of response VQL against ground truth VQL for each part
    """
    # Extract VISUALIZE field
    response_vis = extract_vis(response_vql)
    groundtruth_vis = extract_vis(groundtruth_vql)
    vis_accuracy = response_vis == groundtruth_vis
    
    # Extract SQL part
    response_sql = extract_sql(response_vql)
    groundtruth_sql_1 = extract_sql(groundtruth_vql)
    groundtruth_sql = remove_space_before_comma(groundtruth_sql_1)
    
    # Case-insensitive comparison of SQL statements
    sql_accuracy = 1 if response_sql is not None and groundtruth_sql is not None and response_sql.lower() == groundtruth_sql.lower() else 0

    # Extract BIN part
    response_bin = extract_bin(response_vql)
    groundtruth_bin = extract_bin(groundtruth_vql)
    
    # Case-insensitive comparison of BIN part, check for None first
    if response_bin is None and groundtruth_bin is None:
        bin_accuracy = 1
    elif response_bin is None or groundtruth_bin is None:
        bin_accuracy = 0
    else:
        bin_accuracy = 1 if response_bin.lower() == groundtruth_bin.lower() else 0

    # Extract SELECT columns
    response_columns = extract_select_columns(response_sql)
    groundtruth_columns = extract_select_columns(groundtruth_sql)

    # Calculate SELECT field column name accuracy
    if len(groundtruth_columns) == 0:
        select_columns_accuracy = 1 if len(response_columns) == 0 else 0
    else:
        correct_count = sum(col in response_columns for col in groundtruth_columns)
        select_columns_accuracy = correct_count / len(groundtruth_columns)

    # Remove VISUALIZE part
    response_without_vis = response_vql.replace(f"Visualize {response_vis}", "").strip().lower() if response_vis else response_vql.strip().lower()
    groundtruth_without_vis_1 = groundtruth_vql.replace(f"Visualize {groundtruth_vis}", "").strip().lower() if groundtruth_vis else groundtruth_vql.strip().lower()
    groundtruth_without_vis = remove_space_before_comma(groundtruth_without_vis_1)
    
    # Case-insensitive comparison of part after removing VISUALIZE
    data_accuracy = 1 if response_without_vis == groundtruth_without_vis else 0

    # Overall accuracy: all_accuracy is 1 when both vis and data are correct
    all_accuracy = 1 if vis_accuracy and data_accuracy else 0

    return vis_accuracy, sql_accuracy, bin_accuracy, select_columns_accuracy, data_accuracy, all_accuracy

# Database execution functions
def check_table_exists_and_has_data(conn, table_name):
    cursor = conn.cursor()
    try:
        # Check if table exists, convert table name to lowercase
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name)=?", (table_name.lower(),))
        table_exists = cursor.fetchone() is not None
        if table_exists:
            # Check if table has data
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            return row_count > 0
        return False
    except Exception as e:
        print(f"Error checking if table exists and has data: {e}")
        return False

def get_table_and_column_names(conn):
    cursor = conn.cursor()
    table_names = []
    column_names = {}
    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row[0] for row in cursor.fetchall()]
        # Get column names for each table
        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name})")
            column_names[table_name] = [row[1] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting table and column names: {e}")
    return table_names, column_names

def standardize_sql(sql, table_names, column_names):
    # Match letter plus underscore combinations that might be wrapped in quotes
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    empty_db_ids = []
    skipped = False
    skipped_info = {}
    try:
        # Get table and column names
        table_names, column_names = get_table_and_column_names(conn)
        # Standardize SQL statements
        predicted_sql = standardize_sql(predicted_sql, table_names, column_names)
        ground_truth = standardize_sql(ground_truth, table_names, column_names)

        # Try to extract table name (considering quotes), optimize regex
        table_name_match = re.search(r'\bFROM\s+(["\']?[a-zA-Z_]+["\']?)(?:\s+AS\s+["\']?[a-zA-Z_]+["\']?)?',
                                     predicted_sql, re.IGNORECASE)
        if table_name_match:
            table_name = table_name_match.group(1).strip('"\'')
            if not check_table_exists_and_has_data(conn, table_name):
                print(f"------------------------------")
                print(f"Table {table_name} does not exist or is empty, skipping execution.")
                print(f"db_id: {db_id}")
                print(f"Predicted SQL: {predicted_sql}")
                print(f"Ground truth SQL: {ground_truth}")
                print(f"------------------------------")
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

        # Sort result sets
        predicted_res = sorted(predicted_res)
        ground_truth_res = sorted(ground_truth_res)

        return 1 if predicted_res == ground_truth_res else 0, empty_db_ids, skipped, skipped_info
    except Exception as e:
        print(f"------------------------------")
        print(f"Error executing SQL:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground truth SQL: {ground_truth}")
        print(f"Error message: {e}")
        print(f"------------------------------")
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": f"Error executing SQL: {e}"
        }
        return 0, empty_db_ids, skipped, skipped_info
    finally:
        conn.close()

def execute_model(predicted_sql, ground_truth, predicted_vis, ground_truth_vis, predicted_bin_by, ground_truth_bin_by, db_place, idx, meta_time_out, db_id):
    try:
        sql_res, empty_db_ids, skipped, skipped_info = func_timeout(meta_time_out, execute_sql,
                                                                args=(predicted_sql, ground_truth, db_place, db_id))
        vis_res = 1 if predicted_vis == ground_truth_vis else 0
        bin_res = 1 if predicted_bin_by == ground_truth_bin_by else 0
        all_res = 1 if sql_res == 1 and vis_res == 1 and bin_res == 1 else 0
        bin_sql_res = 1 if sql_res == 1 and bin_res == 1 else 0
    except KeyboardInterrupt:
        import sys
        sys.exit(0)
    except FunctionTimedOut:
        print(f"------------------------------")
        print(f"SQL execution timeout:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground truth SQL: {ground_truth}")
        print(f"------------------------------")
        sql_res = 0
        vis_res = 0
        bin_res = 0
        all_res = 0
        bin_sql_res = 0
        empty_db_ids = []
        skipped = False
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": "SQL execution timeout"
        }
    except Exception as e:
        print(f"------------------------------")
        print(f"Unknown error occurred during SQL execution:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground truth SQL: {ground_truth}")
        print(f"Error message: {e}")
        print(f"------------------------------")
        sql_res = 0
        vis_res = 0
        bin_res = 0
        all_res = 0
        bin_sql_res = 0
        empty_db_ids = []
        skipped = False
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": f"Unknown error occurred during SQL execution: {e}"
        }
    return {'sql_idx': idx, 'sql_res': sql_res, 'vis_res': vis_res, 'bin_res': bin_res, 'all_res': all_res, 'bin_sql_res': bin_sql_res, 'empty_db_ids': empty_db_ids, 'skipped': skipped, 'skipped_info': skipped_info}

def run_sqls_parallel(sqls, vis_pairs, bin_by_pairs, db_places, db_ids, num_cpus=1, meta_time_out=30.0):
    exec_result = []
    pool = mp.Pool(processes=num_cpus)
    for i, (sql_pair, vis_pair, bin_by_pair) in enumerate(zip(sqls, vis_pairs, bin_by_pairs)):
        predicted_sql, ground_truth = sql_pair
        predicted_vis, ground_truth_vis = vis_pair
        predicted_bin_by, ground_truth_bin_by = bin_by_pair
        result = pool.apply_async(execute_model,
                                  args=(predicted_sql, ground_truth, predicted_vis, ground_truth_vis, predicted_bin_by, ground_truth_bin_by, db_places[i], i, meta_time_out, db_ids[i]))
        exec_result.append(result)
    pool.close()
    pool.join()
    all_empty_db_ids = []
    final_results = []
    skipped_count = 0
    skipped_infos = []
    for res in exec_result:
        result = res.get()
        final_results.append(result)
        all_empty_db_ids.extend(result['empty_db_ids'])
        if result['skipped']:
            skipped_count += 1
            skipped_infos.append(result['skipped_info'])
    return final_results, set(all_empty_db_ids), skipped_count, skipped_infos

def find_sqlite_file(db_id):
    db_dir = f"database/{db_id}/"
    if os.path.exists(db_dir):
        for root, dirs, files in os.walk(db_dir):
            for file in files:
                if file.endswith('.sqlite'):
                    db_path = os.path.join(root, file)
                    print(f"Found database file for {db_id}: {db_path}")
                    return db_path
    print(f"Could not find .sqlite database file for {db_id}")
    return None

# Main execution
try:
    with open('reponse.json', 'r') as f:
        test_data = json.load(f)
except FileNotFoundError:
    print("Could not find response.json file, please check file path.")
    exit(1)

try:
    with open('test.json', 'r') as f:
        groundtruth_data = json.load(f)
except FileNotFoundError:
    print("Could not find test.json file, please check file path.")
    exit(1)

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

print("Processing samples for text-based evaluation...")

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
avg_vis_accuracy = sum(vis_accuracies) / valid_samples if valid_samples > 0 else 0
avg_sql_accuracy = sum(sql_accuracies) / valid_samples if valid_samples > 0 else 0
avg_select_columns_accuracy = sum(select_columns_accuracies) / valid_samples if valid_samples > 0 else 0

print(f"\n=== Text-based Evaluation Results ===")
print(f"Chart Acc: {avg_vis_accuracy:.4f}")
print(f"Axis Acc: {avg_select_columns_accuracy:.4f}")
print(f"SQL Acc: {avg_sql_accuracy:.4f}")

# Database execution evaluation
if sql_pairs:
    print("\nProcessing samples for database execution evaluation...")
    exec_results, empty_db_ids, skipped_count, skipped_infos = run_sqls_parallel(
        sql_pairs, vis_pairs, bin_by_pairs, db_paths, db_ids, 
        num_cpus=mp.cpu_count(), meta_time_out=30.0
    )
    
    correct_sql_count = sum([res['sql_res'] for res in exec_results])
    correct_all_count = sum([res['all_res'] for res in exec_results])
    
    avg_sql_execution_accuracy = (correct_sql_count / len(exec_results)) * 100 if exec_results else 0
    avg_all_execution_accuracy = (correct_all_count / len(exec_results)) * 100 if exec_results else 0
    
    print(f"\n=== Database Execution Evaluation Results ===")
    print(f"Data Acc: {avg_sql_execution_accuracy:.2f}%")
    print(f"All Acc: {avg_all_execution_accuracy:.2f}%")
    
    if empty_db_ids:
        print(f"Empty db_ids: {empty_db_ids}")
    if skipped_count > 0:
        print(f"Skipped SQL executions: {skipped_count}")
else:
    print("\nNo valid SQL pairs found for database execution evaluation.")

print(f"\n=== Summary ===")
print(f"Chart Acc: {avg_vis_accuracy:.4f}")
print(f"Axis Acc: {avg_select_columns_accuracy:.4f}")
print(f"SQL Acc: {avg_sql_accuracy:.4f}")
if sql_pairs:
    print(f"Data Acc: {avg_sql_execution_accuracy:.2f}%")
    print(f"All Acc: {avg_all_execution_accuracy:.2f}%")
