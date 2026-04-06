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
        # allocation per PIT-RES Instructions p.5: "you must each
        # report your own income, personal credits, deductions."
        p = parameters(period).gov.states.de.tax.income.credits

        members = tax_unit.members
        is_head = members("is_tax_unit_head", period)
        is_spouse = members("is_tax_unit_spouse", period)
        person_tax = members("de_income_tax_before_non_refundable_credits_indv", period)

        # Line 26: each column's tax from rate table.
        head_tax = tax_unit.sum(is_head * person_tax)
        spouse_tax = tax_unit.sum(is_spouse * person_tax)

        # Identify higher/lower-income column by taxable income.
        person_taxable = members("de_taxable_income_indv", period)
        head_taxable = tax_unit.sum(is_head * person_taxable)
        spouse_taxable = tax_unit.sum(is_spouse * person_taxable)
        head_higher_income = head_taxable >= spouse_taxable

        # --- Fixed credits per column ---

        # Line 27b: aged credits locked to person's column.
        # "enter $110 in the column(s) that correspond to the
        # checked box(es)."
        head_aged = p.personal_credits.aged.calc(tax_unit("age_head", period))
        spouse_aged = p.personal_credits.aged.calc(tax_unit("age_spouse", period))

        # Line 31: CDCC to LOWER-income column.
        # "the credit may only be applied against the tax imposed
        # on the spouse with the lower taxable income on Line 23."
        cdcc = tax_unit("de_cdcc", period)
        head_cdcc = where(~head_higher_income, cdcc, 0)
        spouse_cdcc = where(head_higher_income, cdcc, 0)

        # Fixed credits per column (aged + CDCC).
        head_fixed = head_aged + head_cdcc
        spouse_fixed = spouse_aged + spouse_cdcc

        # --- Optimize personal credit allocation (Line 27a) ---
        # "split the total between Columns A and B in increments
        # of $110."  We assign greedily to the column with more
        # remaining capacity (tax minus fixed credits).
        total_personal = p.personal_credits.personal * tax_unit(
            "exemptions_count", period
        )

        head_capacity = max_(head_tax - head_fixed, 0)
        spouse_capacity = max_(spouse_tax - spouse_fixed, 0)

        head_has_more_capacity = head_capacity >= spouse_capacity
        best_capacity = where(head_has_more_capacity, head_capacity, spouse_capacity)
        worst_capacity = where(head_has_more_capacity, spouse_capacity, head_capacity)

        to_best = min_(best_capacity, total_personal)
        to_worst = min_(worst_capacity, total_personal - to_best)

        head_personal = where(head_has_more_capacity, to_best, to_worst)
        spouse_personal = where(head_has_more_capacity, to_worst, to_best)

        # --- Line 32: total non-refundable credits, capped at
        # each column's Line 26 tax. ---
        head_total_credits = min_(head_fixed + head_personal, head_tax)
        spouse_total_credits = min_(spouse_fixed + spouse_personal, spouse_tax)

        # Line 33: balance per column.
        head_line33 = head_tax - head_total_credits
        spouse_line33 = spouse_tax - spouse_total_credits

        # --- Line 34: non-refundable EITC to higher-income column.
        # "the credit may only be applied against the tax imposed
        # on the spouse with the higher taxable income on Line 23."
        eitc = tax_unit("de_non_refundable_eitc", period)
        head_eitc = where(head_higher_income, min_(eitc, head_line33), 0)
        spouse_eitc = where(~head_higher_income, min_(eitc, spouse_line33), 0)

        separate_result = max_(head_line33 - head_eitc, 0) + max_(
            spouse_line33 - spouse_eitc, 0
        )

        return where(files_separately, separate_result, joint_result)
