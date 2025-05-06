# DeepVIS
Despite data visualization's power in uncovering patterns and sharing insights, crafting effective visuals demands knowledge of authoring tools and can disrupt the analysis process. Although large language models hold potential for auto-converting analysis intent into visualizations, current methods operate as black boxes lacking transparent reasoning, hindering users from grasping design rationales and improving subpar outputs.
![teaser](https://anonymous.4open.science/r/DeepVIS-9C33/img/teaser.png)

To address this issue, first, we propose a Chain-of-Thought (COT) data construction process. We design a comprehensive CoT reasoning process for Natural-Language-to-Visualization (NL2VIS) and develop an automated pipeline to endow existing datasets with structured reasoning steps. Second, we introduce **CoT-nvBench**, a specialized dataset that records detailed step-by-step reasoning from ambiguous natural language descriptions to final visualizations. Finally, we propose **DeepVIS**, an interactive visual interface that is deeply integrated with the CoT reasoning process. It enables users to inspect reasoning steps, correct errors, and optimize visualization results.
![overview](https://anonymous.4open.science/r/DeepVIS-9C33/img/overview.png)

# Demo Video
For a detailed demonstration of how DeepVIS system works, check out our [System Demo Video](https://anonymous.4open.science/r/DeepVIS-9C33/Demo%20Video.mp4).

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
