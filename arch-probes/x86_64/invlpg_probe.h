#ifndef LAB_X86_64_INVLPG_PROBE_H
#define LAB_X86_64_INVLPG_PROBE_H

/*
 * Educational wrapper only.
 *
 * This executes INVLPG directly and therefore only makes sense in
 * kernel mode on x86-class systems. Linux already provides the
 * architecture-aware TLB maintenance paths that real MM code should use.
 *
 * This header exists to support small lab probes and instrumentation
 * examples. It must not be used as a replacement for Linux MM helpers
 * or as a shortcut around existing kernel invalidation code.
 */
static inline void lab_invlpg(void *addr)
{
	asm volatile("invlpg (%0)" : : "r" (addr) : "memory");
}

#endif /* LAB_X86_64_INVLPG_PROBE_H */
