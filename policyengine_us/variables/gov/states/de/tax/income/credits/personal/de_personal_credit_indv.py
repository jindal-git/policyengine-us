from policyengine_us.model_api import *


class de_personal_credit_indv(Variable):
    value_type = float
    entity = Person
    label = "Delaware personal credit per person for combined separate filing"
    unit = USD
    definition_period = YEAR
    reference = "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=9"
    defined_for = StateCode.DE

    def formula(person, period, parameters):
        # PIT-RES Line 27a: "split the total between Columns A and
        # B in increments of $110."  Taxpayers may choose how to
        # allocate; we assign greedily to the column with more
        # capacity (Line 26 tax minus aged + CDCC credits).
        p = parameters(period).gov.states.de.tax.income.credits
        is_head = person("is_tax_unit_head", period)
        is_spouse = person("is_tax_unit_spouse", period)

        # Line 26 tax per column.
        person_tax = person("de_income_tax_before_non_refundable_credits_indv", period)
        head_tax = person.tax_unit.sum(is_head * person_tax)
        spouse_tax = person.tax_unit.sum(is_spouse * person_tax)

        # Fixed credits per column (aged + CDCC).
        fixed = person("de_aged_personal_credit_indv", period) + person(
            "de_cdcc_indv", period
        )
        head_fixed = person.tax_unit.sum(is_head * fixed)
        spouse_fixed = person.tax_unit.sum(is_spouse * fixed)

        head_cap = max_(head_tax - head_fixed, 0)
        spouse_cap = max_(spouse_tax - spouse_fixed, 0)

        # Total personal credits to allocate.
        total = p.personal_credits.personal * person.tax_unit(
            "exemptions_count", period
        )

        # Greedy allocation to higher-capacity column first.
        head_more = head_cap >= spouse_cap
        best = where(head_more, head_cap, spouse_cap)
        worst = where(head_more, spouse_cap, head_cap)
        to_best = min_(best, total)
        to_worst = min_(worst, total - to_best)

        head_personal = where(head_more, to_best, to_worst)
        spouse_personal = where(head_more, to_worst, to_best)

        return is_head * head_personal + is_spouse * spouse_personal
