Cross-Border Anomaly Hunt: CasaMarket's Silent 18% Revenue Drain
The Situation
You're a data engineer at Yuno, and you've just received an urgent call from CasaMarket, a rapidly growing home goods e-commerce platform operating across Mexico, Colombia, Argentina, and Chile. They process roughly 45,000 transactions per month across multiple payment processors.

Their CFO noticed something alarming in last quarter's financial review: 18% of their approved transactions are settling for amounts different than what was authorized. Sometimes it's a few cents, sometimes it's dozens of dollars. The discrepancies seem random, but they're bleeding money — approximately $127,000 in unexplained differences last quarter alone.

CasaMarket's engineering team has been drowning in operational fires (a recent platform migration, new market launches) and hasn't had time to investigate. They've exported their transaction data from Yuno's dashboard and need someone to find the patterns, identify the root causes, and build a monitoring system they can use going forward.

Domain Background: Key Concepts
Before diving into the challenge, here's what you need to know about payment processing:

Authorization vs. Settlement
When a customer makes a purchase:

Authorization: The payment processor checks if the customer has sufficient funds and places a temporary hold for the purchase amount. This happens in real-time at checkout. If approved, the customer sees a pending charge.
Settlement: Usually 1-5 days later, the actual funds transfer from the customer's account to the merchant's account. This is the final amount the merchant receives.
The problem: The authorization amount and settlement amount should almost always match. When they don't, it's called a settlement discrepancy or clearing variance.

Common Causes of Discrepancies
Currency conversion timing: For cross-border transactions, exchange rates may differ between authorization time and settlement time
Partial captures: A merchant may authorize $100 but only capture/settle $80 (e.g., one item was out of stock)
Tip adjustments: Common in hospitality, where the tip is added after authorization
Processor fees or adjustments: Some processors apply unexpected fees or corrections at settlement
Fraud holds: Some transactions may have funds partially withheld due to risk assessments
Tax recalculations: In some countries, tax amounts may be adjusted between authorization and settlement based on final invoice details
Multi-Currency Transactions
CasaMarket operates in 4 countries with different currencies:

Mexico (MXN) - Mexican Peso
Colombia (COP) - Colombian Peso
Argentina (ARS) - Argentine Peso
Chile (CLP) - Chilean Peso
Some transactions involve currency conversion when customers pay in one currency but the merchant settles in another. Exchange rate fluctuations between authorization and settlement can cause legitimate small discrepancies (typically <2%).

Payment Processors (PSPs)
CasaMarket uses multiple Payment Service Providers (PSPs) to process transactions. Each PSP has different fee structures, settlement timing, and handling of edge cases. Understanding which PSP has the most discrepancies is crucial for diagnosis.

Your Mission
Build a transaction discrepancy analysis system that helps CasaMarket understand where their money is going. Your solution should ingest their transaction data, identify patterns in the discrepancies, surface the root causes, and provide an actionable way for them to monitor this issue going forward.

Functional Requirements
1. Data Pipeline & Discrepancy Detection (Core)
Build a data pipeline that:

Ingests transaction records containing authorization and settlement information
Calculates discrepancies between authorized and settled amounts
Flags transactions with meaningful discrepancies (you'll need to define what "meaningful" means — hint: 2 cents on a $500 transaction is probably noise, but $20 is not)
Enriches the data with computed fields that will help with analysis (e.g., discrepancy percentage, discrepancy amount, time between auth and settlement)
Acceptance criteria: A reviewer should be able to run your pipeline on the test dataset and get a clean, enriched dataset with discrepancy metrics calculated for each transaction.

2. Root Cause Analysis (Core)
Identify patterns and segment the discrepancies by potential root causes:

Which countries/currencies have the highest discrepancy rates?
Which payment processors (PSPs) are most problematic?
Do transaction sizes correlate with discrepancy likelihood or magnitude?
Are there time-based patterns (e.g., certain days of the week, or settlement delays)?
Can you identify clusters of similar discrepancies that might point to systematic issues vs. random errors?
Your analysis should produce clear, data-driven insights that CasaMarket can act on. Examples:

"87% of large discrepancies (>5%) occur on PSP_B transactions in Argentina"
"Currency-conversion transactions have 3.2x higher discrepancy rates than domestic transactions"
"Transactions settling after 4+ days have 61% higher average discrepancy amounts"
Acceptance criteria: A reviewer should be able to see your analysis outputs (tables, charts, summary statistics, or a report) and immediately understand which factors are driving the discrepancies.

3. Monitoring Dashboard or Alert System (Stretch Goal)
Build an interactive dashboard or automated alert system that CasaMarket's operations team can use to:

Visualize discrepancy trends over time
Drill down into specific segments (by country, PSP, transaction size, etc.)
Identify outlier transactions that need immediate investigation
Monitor whether the situation is improving or getting worse week-over-week
This could be a web-based dashboard, a Jupyter notebook with interactive widgets, a Streamlit/Dash app, or even a command-line tool that generates reports. Choose whatever format lets you deliver the most value in the time available.

Acceptance criteria: A reviewer should be able to interact with your monitoring solution and answer questions like "Which PSP had the worst week last month?" or "Show me all transactions with discrepancies over $50."

4. Actionable Recommendations (Stretch Goal)
Based on your analysis, provide CasaMarket with a prioritized list of 3-5 concrete actions they should take to reduce discrepancies. Each recommendation should:

Reference specific data findings from your analysis
Estimate the potential financial impact if addressed
Suggest an implementation approach (e.g., "Renegotiate settlement terms with PSP_B" or "Implement real-time exchange rate locking for cross-border transactions")
Acceptance criteria: A written document (Markdown, PDF, or included in your dashboard) with clear, evidence-based recommendations.

Test Data Specification
You'll need to generate or simulate transaction data for development and demonstration. Your test dataset should include:

At least 500 transactions spanning 3-4 months
All four countries (Mexico, Colombia, Argentina, Chile) with realistic currency codes (MXN, COP, ARS, CLP)
3-5 different payment processors (you can name them PSP_A, PSP_B, etc., or invent realistic names)
A realistic mix of transaction statuses: mostly approved/settled, but include some failed authorizations and pending settlements
Authorization and settlement amounts that:
Match exactly for ~60-70% of transactions (the "healthy" baseline)
Have small discrepancies (0.1%-2%) for ~15-20% (possibly currency conversion noise)
Have meaningful discrepancies (>2%) for ~10-18% (the problem transactions)
Have large discrepancies (>5% or >$20) for ~3-5% (the outliers CasaMarket needs to investigate)
Timestamps for both authorization and settlement (settlement should be 1-7 days after authorization, with some outliers)
Transaction metadata like customer ID, product category, transaction amount tiers ($10-$50, $50-$200, $200+), and whether it's a cross-border transaction
Pattern suggestions: Introduce deliberate patterns that your analysis should uncover, such as:

One PSP consistently has 3-4% higher discrepancy rates in Argentina
Large transactions (>$300) in Colombia have settlement timing issues
Weekend authorizations have higher discrepancy rates
One specific PSP has a systematic rounding issue for certain currency pairs
You can generate this data using Python (Faker, NumPy, Pandas), AI tools, or any method you prefer.

Deliverables
You must submit:

Working code for your data pipeline and analysis (with clear README/instructions on how to run it)
Generated test dataset (or script to generate it) so the reviewer can reproduce your analysis
Analysis outputs: Tables, visualizations, summary statistics, or a report showing your findings
Documentation: Brief explanation of your approach, key findings, and any assumptions you made
(Stretch) Dashboard/monitoring tool or actionable recommendations document
What "Done" Looks Like
A successful submission will:

Process transaction data and accurately calculate discrepancies
Surface at least 3-4 clear patterns or root causes backed by data
Be well-documented so CasaMarket's team can understand and use it
Demonstrate thoughtful data engineering practices (clean code, reproducibility, clear outputs)
(Stretch) Provide an interactive way to explore the data or concrete next steps for the client
Partial completion of stretch goals is expected and welcomed. Focus on delivering a solid pipeline and insightful analysis first; if time permits, add monitoring or recommendations.

Technical Constraints
Your solution must be runnable locally by the reviewer (assume they have Python, Node.js, or Docker available)
Include clear setup/run instructions in your README
If you build a dashboard or web app, it should run on localhost
You have complete freedom to choose:

Programming language and frameworks
Database or data storage approach (files, SQLite, Postgres, DuckDB, etc.)
Visualization libraries or dashboard frameworks
Analysis techniques (statistical analysis, clustering, ML-based anomaly detection, etc.)
Notes on Scope
This challenge is intentionally scoped for 2 hours with AI assistance. You should:

Use AI tools (Claude, ChatGPT, Copilot, Cursor, etc.) to accelerate data generation, boilerplate code, and visualization
Focus on delivering insights and a working prototype, not a production-grade system
Prioritize the core requirements (pipeline + analysis); stretch goals are optional
Keep your architecture simple — this is a focused analytical tool, not an enterprise data warehouse
Time budget guidance:

Data generation/setup: 15-20 minutes
Pipeline development: 25-35 minutes
Analysis and visualization: 30-40 minutes
Documentation and polish: 15-20 minutes
Stretch goals (if time): 20-30 minutes
Good luck! CasaMarket is counting on your data expertise to solve their mystery.

Deliverables
–
Working code for data pipeline and analysis with clear README and run instructions
–
Generated test dataset (or script to generate it) containing at least 500 transactions across 4 countries with realistic discrepancy patterns
–
Analysis outputs: tables, visualizations, summary statistics, or report showing key findings and root cause patterns
–
Documentation explaining your approach, key findings, assumptions made, and how to interpret the results
–
(Stretch) Interactive dashboard/monitoring tool OR actionable recommendations document with 3-5 prioritized actions for the client
Evaluation Criteria
Data Pipeline Quality: Clean, well-structured code that accurately calculates discrepancies and enriches data with relevant metrics
20pts
Test Data Realism: Generated dataset includes realistic patterns, appropriate distributions, and deliberate anomalies that reflect the scenario
10pts
Root Cause Analysis Depth: Identifies multiple meaningful patterns across dimensions (PSP, country, transaction size, timing) with statistical evidence
25pts
Insight Quality & Clarity: Findings are specific, actionable, and clearly communicated with supporting visualizations or summary statistics
20pts
Technical Execution: Code is runnable, well-documented, follows good data engineering practices, and demonstrates thoughtful architectural choices
15pts
Stretch Goals & Polish: Includes monitoring dashboard/tool OR actionable recommendations, plus overall completeness and presentation quality
10pts
Total
100pts