from policyengine_us.model_api import *


class de_income_tax_before_refundable_credits_fs4(Variable):
    value_type = float
    entity = TaxUnit
    label = "Delaware tax after per-column non-refundable credits for Filing Status 4"
    unit = USD
    definition_period = YEAR
    reference = "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf#page=10"
    defined_for = StateCode.DE

    def formula(tax_unit, period, parameters):
        members = tax_unit.members
        is_head = members("is_tax_unit_head", period)
        is_spouse = members("is_tax_unit_spouse", period)

        # Line 33 per column (from de_fs4_line33).
        line33 = members("de_fs4_line33", period)
        head_line33 = tax_unit.sum(is_head * line33)
        spouse_line33 = tax_unit.sum(is_spouse * line33)

        # Line 34: non-refundable EITC to higher-income column.
        # "the credit may only be applied against the tax imposed
        # on the spouse with the higher taxable income on Line 23."
        person_taxable = members("de_taxable_income_indv", period)
        head_taxable = tax_unit.sum(is_head * person_taxable)
        spouse_taxable = tax_unit.sum(is_spouse * person_taxable)
        head_higher = head_taxable >= spouse_taxable

        eitc = tax_unit("de_non_refundable_eitc", period)
        head_eitc = where(head_higher, min_(eitc, head_line33), 0)
        spouse_eitc = where(~head_higher, min_(eitc, spouse_line33), 0)

        return max_(head_line33 - head_eitc, 0) + max_(spouse_line33 - spouse_eitc, 0)
