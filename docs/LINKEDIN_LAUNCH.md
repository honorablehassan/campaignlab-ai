# LinkedIn launch draft

I built CampaignLab because marketing teams do not need another dashboard that ends with “interesting.” They need help deciding what to do next, and they need to know when the evidence is too weak to support the confident answer everyone wants.

CampaignLab turns a strategy question or messy campaign dataset into a decision you can inspect and defend.

It includes:

- Strategy Lab for stress-testing a marketing decision
- Evidence Lab for selecting and running eligible statistical methods
- a guarded Marketing Mix Model Beta for contribution, response curves and budget scenarios
- Decision Memory for recording the prediction and checking what happened

The architecture is intentionally split: Python owns the calculations; AI reasons over bounded results and explains them. The system can say what the evidence supports, what it does not support and what would change the recommendation.

This is a portfolio pilot, not a claim that the hard parts of production analytics are finished. I documented the limitations, included reproducible synthetic scenarios and built a test suite around the analytical engines and product contracts.

I would love feedback on one question: does the product make the next decision clearer without hiding the uncertainty?

Live demo: [add URL]

GitHub: https://github.com/honorablehassan/campaignlab-ai

#AppliedAI #MarketingAnalytics #DataScience #ProductEngineering #Python #Streamlit
