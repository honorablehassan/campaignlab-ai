# Outcome Learning V1

CampaignLab can now preserve a structured prediction with every Decision Object and compare it with an observed numeric outcome.

For each observation it records:

- predicted direction and point estimate
- prediction interval when one existed
- actual measured change in the same unit
- directional correctness
- signed prediction error
- whether reality landed inside the stated interval
- user notes and observation time

Decision Memory summarizes direction accuracy, mean error, mean absolute error and interval coverage. Fewer than ten observations are explicitly labeled as history rather than a stable calibration estimate.

Outcome learning never rewrites the original decision. It appends reality to the historical record so later calibration can distinguish good direction from exaggerated magnitude.
