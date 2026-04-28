#ifndef LAB_X86_64_INVPCID_PROBE_H
#define LAB_X86_64_INVPCID_PROBE_H

#include <linux/errno.h>
#include <linux/types.h>
#include <asm/cpufeature.h>

/*
 * INVPCID is more subtle than INVLPG because semantics depend on the
 * operation type and the PCID/context relationship in use.
 *
 * This header intentionally defaults to a disabled stub so that the
 * repository can document the instruction without encouraging blind use.
 * A real caller would need to verify CPU support, choose a correct type,
 * and reason carefully about the surrounding MM state.
 */
struct lab_invpcid_desc {
	u64 pcid;
	u64 addr;
};

static inline bool lab_invpcid_available(void)
{
#ifdef X86_FEATURE_INVPCID
	return boot_cpu_has(X86_FEATURE_INVPCID);
#else
	return false;
#endif
}

static inline int lab_invpcid_single_addr(const struct lab_invpcid_desc *desc,
					  u64 type)
{
#ifdef LAB_ENABLE_X86_INVPCID_DEMO
	if (!lab_invpcid_available())
		return -EOPNOTSUPP;

	/*
	 * AT&T syntax: invpcid src_reg, mem_operand
	 * %0: type (register)
	 * %1: descriptor (memory)
	 */
	asm volatile("invpcid %0, %1"
		     :
		     : "r" (type), "m" (*desc)
		     : "memory");
	return 0;
#else
	(void)desc;
	(void)type;
	return -EOPNOTSUPP;
#endif
}

#endif /* LAB_X86_64_INVPCID_PROBE_H */
