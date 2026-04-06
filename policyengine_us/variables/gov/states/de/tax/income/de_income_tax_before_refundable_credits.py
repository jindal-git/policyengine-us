from policyengine_us.model_api import *


class de_income_tax_before_refundable_credits(Variable):
    value_type = float
    entity = TaxUnit
    label = "Delaware personal income tax before refundable credits"
    unit = USD
    definition_period = YEAR
    reference = (
        "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=5",
        "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=9",
    )
    defined_for = StateCode.DE

    def formula(tax_unit, period, parameters):
        files_separately = tax_unit("de_files_separately", period)

        # Joint/single: pool credits at unit level.
        before_credits = tax_unit(
            "de_income_tax_before_non_refundable_credits_unit", period
        )
        non_refundable_credits = tax_unit("de_non_refundable_credits", period)
        joint_result = max_(before_credits - non_refundable_credits, 0)

        # FS4 (combined separate): per-column credit allocation.
        fs4_result = tax_unit("de_income_tax_before_refundable_credits_fs4", period)

        return where(files_separately, fs4_result, joint_result)
