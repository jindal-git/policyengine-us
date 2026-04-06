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
        before_credits = tax_unit(
            "de_income_tax_before_non_refundable_credits_unit", period
        )
        non_refundable_credits = tax_unit("de_non_refundable_credits", period)

        # Joint/single path: pool credits at unit level.
        joint_result = max_(before_credits - non_refundable_credits, 0)

        # Filing Status 4 (combined separate): per-column credit
        # allocation.  PIT-RES Instructions p.5: "you must each report
        # your own income, personal credits, deductions."
        p = parameters(period).gov.states.de.tax.income.credits

        members = tax_unit.members
        is_head = members("is_tax_unit_head", period)
        is_spouse = members("is_tax_unit_spouse", period)
        person_tax = members("de_income_tax_before_non_refundable_credits_indv", period)
        head_tax = tax_unit.sum(is_head * person_tax)
        spouse_tax = tax_unit.sum(is_spouse * person_tax)

        # Line 27b: aged credits locked to each person's column.
        head_aged = p.personal_credits.aged.calc(tax_unit("age_head", period))
        spouse_aged = p.personal_credits.aged.calc(tax_unit("age_spouse", period))

        # Line 27a: personal credits optimally allocated between
        # columns.  The form lets taxpayers choose the split; we
        # assign greedily to the column with higher remaining tax.
        total_personal = p.personal_credits.personal * tax_unit(
            "exemptions_count", period
        )

        # Line 28: CDCC to higher-income column.
        cdcc = tax_unit("de_cdcc", period)

        # Determine higher-income column by individual taxable income.
        person_taxable = members("de_taxable_income_indv", period)
        head_taxable = tax_unit.sum(is_head * person_taxable)
        spouse_taxable = tax_unit.sum(is_spouse * person_taxable)
        head_higher_income = head_taxable >= spouse_taxable

        # Step 1: apply aged credits (locked to person's column).
        head_rem = max_(head_tax - head_aged, 0)
        spouse_rem = max_(spouse_tax - spouse_aged, 0)

        # Step 2: optimally allocate personal credits.
        higher_is_head = head_rem >= spouse_rem
        higher_rem = where(higher_is_head, head_rem, spouse_rem)
        lower_rem = where(higher_is_head, spouse_rem, head_rem)

        to_higher = min_(higher_rem, total_personal)
        to_lower = min_(lower_rem, total_personal - to_higher)

        head_personal = where(higher_is_head, to_higher, to_lower)
        spouse_personal = where(higher_is_head, to_lower, to_higher)

        head_rem = head_rem - head_personal
        spouse_rem = spouse_rem - spouse_personal

        # Step 3: CDCC to higher-income column.
        head_cdcc = where(head_higher_income, min_(cdcc, head_rem), 0)
        spouse_cdcc = where(~head_higher_income, min_(cdcc, spouse_rem), 0)
        head_rem = head_rem - head_cdcc
        spouse_rem = spouse_rem - spouse_cdcc

        # Line 29: net tax per column.
        head_net = max_(head_rem, 0)
        spouse_net = max_(spouse_rem, 0)

        # Line 30: non-refundable EITC to higher-income column.
        # PIT-RES p.10: "the credit may only be applied against the
        # tax imposed on the spouse with the higher taxable income."
        eitc = tax_unit("de_non_refundable_eitc", period)
        head_eitc = where(head_higher_income, min_(eitc, head_net), 0)
        spouse_eitc = where(~head_higher_income, min_(eitc, spouse_net), 0)
        head_final = max_(head_net - head_eitc, 0)
        spouse_final = max_(spouse_net - spouse_eitc, 0)

        separate_result = head_final + spouse_final

        return where(files_separately, separate_result, joint_result)
