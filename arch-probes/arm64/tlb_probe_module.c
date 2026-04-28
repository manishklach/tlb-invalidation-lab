#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>

#include "tlbi_probe.h"

static int __init lab_tlb_probe_init(void)
{
	pr_info("lab_tlb_probe_arm64: educational module loaded; default build does not execute TLBI\n");
	pr_info("lab_tlb_probe_arm64: lab note sequence is dsb ishst -> tlbi ... -> dsb ish -> isb\n");
#ifdef LAB_ENABLE_ARM64_TLBI_DEMO
	pr_info("lab_tlb_probe_arm64: LAB_ENABLE_ARM64_TLBI_DEMO is enabled in this build\n");
#endif
	return 0;
}

static void __exit lab_tlb_probe_exit(void)
{
	pr_info("lab_tlb_probe_arm64: unloaded\n");
}

module_init(lab_tlb_probe_init);
module_exit(lab_tlb_probe_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Educational arm64 TLB probe module for lab use");
MODULE_AUTHOR("tlb-invalidation-lab");
