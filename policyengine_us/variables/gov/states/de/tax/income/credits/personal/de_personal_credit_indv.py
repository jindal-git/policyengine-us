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
        # B in increments of $110."  The form lets the taxpayer
        # choose any split; we assign the full total to whichever
        # column has more remaining capacity (Line 26 minus aged
        # plus CDCC credits), staying in $110 increments.
        p = parameters(period).gov.states.de.tax.income.credits
        is_head = person("is_tax_unit_head", period)
        is_spouse = person("is_tax_unit_spouse", period)

        person_tax = person("de_income_tax_before_non_refundable_credits_indv", period)
        head_tax = person.tax_unit.sum(is_head * person_tax)
        spouse_tax = person.tax_unit.sum(is_spouse * person_tax)

        fixed = person("de_aged_personal_credit_indv", period) + person(
            "de_cdcc_indv", period
        )
        head_fixed = person.tax_unit.sum(is_head * fixed)
        spouse_fixed = person.tax_unit.sum(is_spouse * fixed)

        head_capacity = max_(head_tax - head_fixed, 0)
        spouse_capacity = max_(spouse_tax - spouse_fixed, 0)

        total = p.personal_credits.personal * person.tax_unit(
            "exemptions_count", period
        )
        head_more = head_capacity >= spouse_capacity

        return where((is_head & head_more) | (is_spouse & ~head_more), total, 0)
