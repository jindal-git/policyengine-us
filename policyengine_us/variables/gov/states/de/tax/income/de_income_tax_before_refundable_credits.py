from policyengine_us.model_api import *


class de_income_tax_before_refundable_credits(Variable):
    value_type = float
    entity = TaxUnit
    label = "Delaware personal income tax before refundable credits"
    unit = USD
    definition_period = YEAR
    reference = (
        "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=5",
        "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=10",
    )
    defined_for = StateCode.DE

    def formula(tax_unit, period, parameters):
        files_separately = tax_unit("de_files_separately", period)

        # Joint/single path: pool credits at unit level.
        before_credits = tax_unit(
            "de_income_tax_before_non_refundable_credits_unit", period
        )
        non_refundable_credits = tax_unit("de_non_refundable_credits", period)
        joint_result = max_(before_credits - non_refundable_credits, 0)

        # Combined separate path: per-column credits already
        # applied in de_income_tax_after_non_refundable_credits_indv.
        # This step applies Line 34 (non-refundable EITC) to the
        # higher-income spouse's column.
        members = tax_unit.members
        is_head = members("is_tax_unit_head", period)
        is_spouse = members("is_tax_unit_spouse", period)

        line33 = members("de_income_tax_after_non_refundable_credits_indv", period)
        head_line33 = tax_unit.sum(is_head * line33)
        spouse_line33 = tax_unit.sum(is_spouse * line33)

        # Tie-break: when taxable incomes are equal, head is treated
        # as the higher-income spouse, so EITC routes to head.
        person_taxable = members("de_taxable_income_indv", period)
        head_taxable = tax_unit.sum(is_head * person_taxable)
        spouse_taxable = tax_unit.sum(is_spouse * person_taxable)
        head_higher = head_taxable >= spouse_taxable

        eitc = tax_unit("de_non_refundable_eitc", period)
        head_eitc = where(head_higher, min_(eitc, head_line33), 0)
        spouse_eitc = where(~head_higher, min_(eitc, spouse_line33), 0)

        separate_result = max_(head_line33 - head_eitc, 0) + max_(
            spouse_line33 - spouse_eitc, 0
        )

        return where(files_separately, separate_result, joint_result)
