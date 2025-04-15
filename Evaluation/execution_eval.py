import json
import sqlite3
import re
import os
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut


def extract_last_vql_1(text):
    """
    Extract the last occurrence of the Visualize word and the subsequent content as VQL from the text.
    """
    try:
        # Define a regular expression to precisely match VQL statements starting with Visualize.
        vql_pattern = re.compile(r'(Visualize\s+[A-Z]+\s+SELECT.*)', re.IGNORECASE | re.DOTALL)
        matches = vql_pattern.findall(text)
        if matches:
            last_vql = matches[-1].strip()
            # Remove any possible extra quotes and line breaks.
            last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
            return last_vql
        return None
    except Exception as e:
        print(f"Error occurred while extracting VQL: {e}")
        return None


def extract_last_vql(text):
    """
    Extract the last occurrence of the VQL statement from the text.
    """
    vql_pattern = re.compile(r'Final VQL:(.*)', re.IGNORECASE | re.DOTALL)
    matches = vql_pattern.findall(text)
    if matches:
        last_vql = matches[-1].strip()
        # Remove any possible extra quotes and line breaks.
        last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
        return last_vql
    return None


def extract_sql(vql):
    """
    Extract the SQL part from the VQL.
    """
    # Remove the VISUALIZE part.
    vql = vql.upper()
    parts = vql.split()
    if len(parts) > 1 and parts[0].upper() == 'VISUALIZE':
        vql = vql.replace(f"VISUALIZE {parts[1].upper()}", "").strip()
    # Check if it contains BIN BY.
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[:bin_by_index].strip()
    return vql.strip()


def extract_vis(vql):
    """
    Extract the visualization part from the VQL.
    """
    vql = vql.upper()
    parts = vql.split()
    if len(parts) > 1 and parts[0].upper() == 'VISUALIZE':
        return parts[1].upper()
    return None


def extract_bin_by(vql):
    """
    Extract the BIN BY part from the VQL.
    """
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[bin_by_index:].strip()
    return None


def check_table_exists_and_has_data(conn, table_name):
    cursor = conn.cursor()
    try:
        # Check if the table exists, convert the table name to lowercase.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name)=?", (table_name.lower(),))
        table_exists = cursor.fetchone() is not None
        if table_exists:
            # Check if there is data in the table.
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            return row_count > 0
        return False
    except Exception as e:
        print(f"Error occurred while checking if the table exists and has data: {e}")
        return False


def get_table_and_column_names(conn):
    cursor = conn.cursor()
    table_names = []
    column_names = {}
    try:
        # Get all table names.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row[0] for row in cursor.fetchall()]
        # Get the column names of each table.
        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name})")
            column_names[table_name] = [row[1] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error occurred while getting table and column names: {e}")
    return table_names, column_names


def standardize_sql(sql, table_names, column_names):
    # Match letter and underscore combinations that may be enclosed in quotes.
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
        # Get table and column names.
        table_names, column_names = get_table_and_column_names(conn)
        # Standardize the SQL statements.
        predicted_sql = standardize_sql(predicted_sql, table_names, column_names)
        ground_truth = standardize_sql(ground_truth, table_names, column_names)

        # Try to extract the table name (considering the quote situation), optimize the regular expression.
        table_name_match = re.search(r'\bFROM\s+(["\']?[a-zA-Z_]+["\']?)(?:\s+AS\s+["\']?[a-zA-Z_]+["\']?)?',
                                     predicted_sql, re.IGNORECASE)
        if table_name_match:
            table_name = table_name_match.group(1).strip('"\'')
            if not check_table_exists_and_has_data(conn, table_name):
                print(f"------------------------------")
                print(f"Table {table_name} does not exist or is empty, skipping execution.")
                print(f"db_id: {db_id}")
                print(f"Predicted SQL: {predicted_sql}")
                print(f"Ground Truth SQL: {ground_truth}")
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

        # Sort the result sets.
        predicted_res = sorted(predicted_res)
        ground_truth_res = sorted(ground_truth_res)

        return 1 if predicted_res == ground_truth_res else 0, empty_db_ids, skipped, skipped_info
    except Exception as e:
        print(f"------------------------------")
        print(f"Error occurred while executing SQL:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground Truth SQL: {ground_truth}")
        print(f"Error message: {e}")
        print(f"------------------------------")
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": f"Error occurred while executing SQL: {e}"
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
        bin_sql_res = 1 if sql_res == 1 and bin_res == 1 else 0  # New: Calculate the execution result of bin+sql
    except KeyboardInterrupt:
        import sys
        sys.exit(0)
    except FunctionTimedOut:
        print(f"------------------------------")
        print(f"SQL execution timed out:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground Truth SQL: {ground_truth}")
        print(f"------------------------------")
        sql_res = 0
        vis_res = 0
        bin_res = 0
        all_res = 0
        bin_sql_res = 0  # New: The execution result of bin+sql is 0 in case of timeout
        empty_db_ids = []
        skipped = False
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": "SQL execution timed out"
        }
    except Exception as e:
        print(f"------------------------------")
        print(f"An unknown error occurred while executing SQL:")
        print(f"db_id: {db_id}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Ground Truth SQL: {ground_truth}")
        print(f"Error message: {e}")
        print(f"------------------------------")
        sql_res = 0
        vis_res = 0
        bin_res = 0
        all_res = 0
        bin_sql_res = 0  # New: The execution result of bin+sql is 0 in case of unknown error
        empty_db_ids = []
        skipped = False
        skipped_info = {
            "db_id": db_id,
            "predicted_sql": predicted_sql,
            "ground_truth": ground_truth,
            "reason": f"An unknown error occurred while executing SQL: {e}"
        }
    return {'sql_idx': idx, 'sql_res': sql_res, 'vis_res': vis_res, 'bin_res': bin_res, 'all_res': all_res,
            'bin_sql_res': bin_sql_res, 'empty_db_ids': empty_db_ids, 'skipped': skipped, 'skipped_info': skipped_info}


def run_sqls_parallel(sqls, vis_pairs, bin_by_pairs, db_places, db_ids, num_cpus=1, meta_time_out=30.0):
    exec_result = []
    pool = mp.Pool(processes=num_cpus)
    for i, (sql_pair, vis_pair, bin_by_pair) in enumerate(zip(sqls, vis_pairs, bin_by_pairs)):
        predicted_sql, ground_truth = sql_pair
        predicted_vis, ground_truth_vis = vis_pair
        predicted_bin_by, ground_truth_bin_by = bin_by_pair
        result = pool.apply_async(execute_model,
                                  args=(predicted_sql, ground_truth, predicted_vis, ground_truth_vis, predicted_bin_by,
                                        ground_truth_bin_by, db_places[i], i, meta_time_out, db_ids[i]))
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
                    print(f"Found the database file for {db_id}: {db_path}")
                    return db_path
    print(f"Did not find the .sqlite database file for {db_id}")
    return None


try:
    with open('test_result_{now}.json', 'r') as f:
        test_data = json.load(f)
except FileNotFoundError:
    print("The result file was not found. Please check the file path.")
    exit(1)

try:
    with open('test.json', 'r') as f:
        groundtruth_data = json.load(f)
except FileNotFoundError:
    print("The file test.json was not found. Please check the file path.")
    exit(1)

total_samples = len(test_data)
sql_pairs = []
vis_pairs = []
bin_by_pairs = []
db_paths = []
db_ids = []

for i in range(total_samples):
    # Extract the last VQL from the response.
    response_text = test_data[i]['response_finetuned_model']
    response_vql = extract_last_vql_1(response_text)
    if not response_vql:
        continue

    # Extract the ground truth VQL.
    groundtruth_text = groundtruth_data[i]['content_2']
    groundtruth_vql = extract_last_vql(groundtruth_text)
    if not groundtruth_vql:
        continue

    # Extract the SQL part.
    response_sql = extract_sql(response_vql)
    groundtruth_sql = extract_sql(groundtruth_vql)

    # Extract the visualization part.
    response_vis = extract_vis(response_vql)
    groundtruth_vis = extract_vis(groundtruth_vql)

    # Extract the BIN BY part.
    response_bin_by = extract_bin_by(response_vql)
    groundtruth_bin_by = extract_bin_by(groundtruth_vql)

    # Get the db_id.
    db_id = groundtruth_data[i]['db_id']
    db_path = find_sqlite_file(db_id)
    if db_path:
        sql_pairs.append((response_sql, groundtruth_sql))
        vis_pairs.append((response_vis, groundtruth_vis))
        bin_by_pairs.append((response_bin_by, groundtruth_bin_by))
        db_paths.append(db_path)
        db_ids.append(db_id)

if not sql_pairs:
    print("There are no valid SQL pairs for execution.")
    exit(1)

exec_results, empty_db_ids, skipped_count, skipped_infos = run_sqls_parallel(sql_pairs, vis_pairs, bin_by_pairs, db_paths, db_ids, num_cpus=mp.cpu_count(), meta_time_out=30.0)
correct_sql_count = sum([res['sql_res'] for res in exec_results])
correct_vis_count = sum([res['vis_res'] for res in exec_results])
correct_bin_count = sum([res['bin_res'] for res in exec_results])
correct_all_count = sum([res['all_res'] for res in exec_results])
correct_bin_sql_count = sum([res['bin_sql_res'] for res in exec_results])  # New: Calculate the number of correct bin+sql executions

avg_sql_execution_accuracy = (correct_sql_count / len(exec_results)) * 100 if exec_results else 0
avg_vis_accuracy = (correct_vis_count / len(exec_results)) * 100 if exec_results else 0
avg_bin_accuracy = (correct_bin_count / len(exec_results)) * 100 if exec_results else 0
avg_all_accuracy = (correct_all_count / len(exec_results)) * 100 if exec_results else 0
avg_bin_sql_accuracy = (correct_bin_sql_count / len(exec_results)) * 100 if exec_results else 0  # New: Calculate the overall accuracy of bin+sql execution
for info in skipped_infos:
    print(f"db_id: {info['db_id']}")
    print(f"Predicted SQL: {info['predicted_sql']}")
    print(f"Ground Truth SQL: {info['ground_truth']}")
    print(f"Reason: {info['reason']}")
    print("------------------------------")

print(f"Average SQL execution accuracy: {avg_sql_execution_accuracy}%")
print(f"Average visualization accuracy: {avg_vis_accuracy}%")
print(f"Average BIN accuracy: {avg_bin_accuracy}%")
print(f"Overall average accuracy (SQL + Visualization + BIN): {avg_all_accuracy}%")
print(f"Overall accuracy of bin+sql execution: {avg_bin_sql_accuracy}%")  # New: Output the overall accuracy of bin+sql execution
print("db_ids that are empty:", empty_db)
print("skipped sql count:", skipped_count)
