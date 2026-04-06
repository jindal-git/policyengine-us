from policyengine_us.model_api import *


class de_fs4_line33(Variable):
    value_type = float
    entity = Person
    label = (
        "Delaware FS4 per-column balance after non-refundable credits (PIT-RES Line 33)"
    )
    unit = USD
    definition_period = YEAR
    reference = "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=9"
    defined_for = StateCode.DE

    def formula(person, period, parameters):
        p = parameters(period).gov.states.de.tax.income.credits
        is_head = person("is_tax_unit_head", period)
        is_spouse = person("is_tax_unit_spouse", period)

        # Line 26: each column's tax from rate table.
        person_tax = person("de_income_tax_before_non_refundable_credits_indv", period)
        head_tax = person.tax_unit.sum(is_head * person_tax)
        spouse_tax = person.tax_unit.sum(is_spouse * person_tax)

        # Identify higher/lower-income column.
        person_taxable = person("de_taxable_income_indv", period)
        head_taxable = person.tax_unit.sum(is_head * person_taxable)
        spouse_taxable = person.tax_unit.sum(is_spouse * person_taxable)
        head_higher = head_taxable >= spouse_taxable

        # Line 27b: aged credits locked to person's column.
        head_aged = p.personal_credits.aged.calc(person.tax_unit("age_head", period))
        spouse_aged = p.personal_credits.aged.calc(
            person.tax_unit("age_spouse", period)
        )

        # Line 31: CDCC to LOWER-income column.
        cdcc = person.tax_unit("de_cdcc", period)
        head_cdcc = where(~head_higher, cdcc, 0)
        spouse_cdcc = where(head_higher, cdcc, 0)

        # Fixed credits per column (aged + CDCC).
        head_fixed = head_aged + head_cdcc
        spouse_fixed = spouse_aged + spouse_cdcc

        # Line 27a: personal credits optimally allocated.
        # Greedy: assign to column with more capacity first.
        total_personal = p.personal_credits.personal * person.tax_unit(
            "exemptions_count", period
        )
        head_cap = max_(head_tax - head_fixed, 0)
        spouse_cap = max_(spouse_tax - spouse_fixed, 0)

        head_more = head_cap >= spouse_cap
        best = where(head_more, head_cap, spouse_cap)
        worst = where(head_more, spouse_cap, head_cap)
        to_best = min_(best, total_personal)
        to_worst = min_(worst, total_personal - to_best)
        head_personal = where(head_more, to_best, to_worst)
        spouse_personal = where(head_more, to_worst, to_best)

        # Line 32: total credits capped at column's Line 26 tax.
        head_credits = min_(head_fixed + head_personal, head_tax)
        spouse_credits = min_(spouse_fixed + spouse_personal, spouse_tax)

        # Line 33: balance per column.
        head_line33 = head_tax - head_credits
        spouse_line33 = spouse_tax - spouse_credits

        return is_head * head_line33 + is_spouse * spouse_line33
