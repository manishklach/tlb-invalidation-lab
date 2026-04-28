#include <linux/gfp.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mm.h>

#include "invlpg_probe.h"
#include "invpcid_probe.h"

static unsigned long lab_probe_page;

static int __init lab_tlb_probe_init(void)
{
	char *ptr;

	/*
	 * Single educational execution only: one page allocation, one write,
	 * one INVLPG, then stop. This is intentionally not a stress path.
	 */
	lab_probe_page = __get_free_page(GFP_KERNEL);
	if (!lab_probe_page)
		return -ENOMEM;

	ptr = (char *)lab_probe_page;
	ptr[0] = 0x5a;

	lab_invlpg(ptr);

	pr_info("lab_tlb_probe_x86_64: touched one page at %px and executed one INVLPG; invpcid_available=%d\n",
		ptr, lab_invpcid_available());
	return 0;
}

static void __exit lab_tlb_probe_exit(void)
{
	if (lab_probe_page)
		free_page(lab_probe_page);

	pr_info("lab_tlb_probe_x86_64: unloaded\n");
}

module_init(lab_tlb_probe_init);
module_exit(lab_tlb_probe_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Educational x86-64 TLB probe module for lab use");
MODULE_AUTHOR("tlb-invalidation-lab");
