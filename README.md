# DeepVIS
Despite data visualization's power in uncovering patterns and sharing insights, crafting effective visuals demands knowledge of authoring tools and can disrupt the analysis process. Although large language models hold potential for auto-converting analysis intent into visualizations, current methods operate as black boxes lacking transparent reasoning, hindering users from grasping design rationales and improving subpar outputs.
![teaser](https://anonymous.4open.science/r/DeepVIS-9C33/img/teaser.png)

To address this issue, first, we propose a Chain-of-Thought (COT) data construction process. We design a comprehensive CoT reasoning process for Natural-Language-to-Visualization (NL2VIS) and develop an automated pipeline to endow existing datasets with structured reasoning steps. Second, we introduce **CoT-nvBench**, a specialized dataset that records detailed step-by-step reasoning from ambiguous natural language descriptions to final visualizations. Finally, we propose **DeepVIS**, an interactive visual interface that is deeply integrated with the CoT reasoning process. It enables users to inspect reasoning steps, correct errors, and optimize visualization results.
![overview](https://anonymous.4open.science/r/DeepVIS-9C33/img/overview.png)

# Demo Video
For a detailed demonstration of how DeepVIS system works, check out our [System Demo Video](https://anonymous.4open.science/r/DeepVIS-9C33/Demo%20Video.mp4).

# Prompts for generating CoT steps
Please simulate a complete reasoning process to explain the Pre-entered Correct VQL, based on the provided Question and Database Schema below. Pretend that you are analyzing the Pre-entered Correct VQL for the first time and detail why each part of it is structured as such.

Question:   
{question}  
Database Schema:  
{db_schema}  
Pre-entered Correct VQL:  
[VQL]  
{additional_constraints}  

Now, please reason according to the following strict format:  
Step 1:  
Reasoning for Chart Type: [Explain why the chart type in the Pre-entered Correct VQL is chosen based on the question and the database schema]  
Chart Type: [Fill in the chart type from the Pre-entered Correct VQL here]  
Step 2:  
Reasoning for FROM: [Explain why the tables in the FROM clause of the Pre-entered Correct VQL are chosen based on the question and the database schema]  
FROM: [Table names for the FROM clause from the Pre-entered Correct VQL]  
Reasoning for SELECT: [Explain why the columns in the SELECT clause of the Pre-entered Correct VQL are chosen based on the question and the database schema]  
SELECT: [Columns for the SELECT clause from the Pre-entered Correct VQL]  
Reasoning for WHERE: [Explain why the conditions in the WHERE clause of the Pre-entered Correct VQL are set based on the question and the database schema]  
WHERE: [Conditions for the WHERE clause from the Pre-entered Correct VQL]  
Step 3:  
Reasoning for GROUP BY: [Explain why the columns in the GROUP BY clause of the Pre-entered Correct VQL are used for grouping based on the question and the database schema]  
GROUP BY: [Columns for the GROUP BY clause from the Pre-entered Correct VQL]  
Reasoning for BIN: [If applicable, explain why the BIN_COLUMN and BIN_TIME_UNIT in the Pre-entered Correct VQL are used based on the time - related grouping requirements and the database schema]  
BIN: [BIN_COLUMN from the Pre-entered Correct VQL]  
BY: [BIN_TIME_UNIT from the Pre-entered Correct VQL]  
Step 4:   
Reasoning for ORDER BY: [Explain why the columns in the ORDER BY clause of the Pre-entered Correct VQL are used for sorting based on the question and the database schema]  
ORDER BY: [Columns for the ORDER BY clause from the Pre-entered Correct VQL]  
Reasoning for SORT DIRECTION: [Based on the analysis of the question requirements and the database schema, explain why the ASC or DESC (or empty) in the Pre-entered Correct VQL is used for each column in the ORDER BY clause]  
SORT DIRECTION: [ASC|DESC|empty from the Pre-entered Correct VQL]  
Reasoning for LIMIT: [Explain why the LIMIT clause (if present) in the Pre-entered Correct VQL is set as such based on various factors]  
LIMIT: [Number of rows for the LIMIT clause from the Pre-entered Correct VQL]  
Step 5:  
Inspection: Check whether the reasoning results of the first four steps are reasonable.   
Final VQL: Combine the above content with the VQL template to obtain the final VQL result.   

# Comparative Analysis
We display vqls and generated charts between our model(**NL2VIS-CoT**) and seven representative NL2VIS models with different architectures.  
**Question:** 
Draw a chart showing the ten majors with the highest numbers of students whose city of residence is known, with the counts tallied for each major.  
**NL2VIS-CoT:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) DESC LIMIT 10  
**Seq2Vis:**
VISUALIZE BAR SELECT MAJOR, COUNT(*) FROM STUDENT GROUP BY MAJOR  
**Transformer:** 
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) DESC  
**ncNet:** 
VISUALIZE BAR SELECT MAJOR, COUNT(*) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY MAJOR DESC LIMIT 10  
**RGVisNet:** 
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) ASC LIMIT 10  
**Llama3.1-8B-SFT:**
VISUALIZE PIE SELECT MAJOR, COUNT() FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT() DESC LIMIT 10  
**ChartGPT:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR  
**GPT-4o-mini:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) ASC LIMIT 10  
![overview](https://anonymous.4open.science/r/DeepVIS-9C33/img/Comparative_analysis.png)

