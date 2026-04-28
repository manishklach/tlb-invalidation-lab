#ifndef LAB_ARM64_TLBI_PROBE_H
#define LAB_ARM64_TLBI_PROBE_H

/*
 * Educational notes for arm64 TLBI sequencing.
 *
 * Typical invalidation sequences require barriers around TLBI:
 *
 *   dsb ishst
 *   tlbi ...
 *   dsb ish
 *   isb
 *
 * The exact TLBI operation depends on scope, translation regime, and
 * whether invalidation is local, inner-shareable, or wider in effect.
 * Real kernel code should continue to use the established Linux arm64
 * TLB helpers rather than issuing ad hoc TLBI from random call sites.
 */
#ifdef LAB_ENABLE_ARM64_TLBI_DEMO
static inline void lab_arm64_tlbi_demo_all_inner_shareable(void)
{
	asm volatile(
		"dsb ishst\n"
		"tlbi vmalle1is\n"
		"dsb ish\n"
		"isb\n"
		:
		:
		: "memory");
}
#endif

#endif /* LAB_ARM64_TLBI_PROBE_H */
