import stack, coregistration

SLC_PATH = "/data/slc/cn_xian_s1_asc_iw"

# create a SlcPair object
slc_pair = stack.SlcPair(
    stack.Image("20210401", SLC_PATH),
    stack.Image("20210519", SLC_PATH)
)

# create a coregistration object
s1_coreg = coregistration.Sentinel1Coregistration(
    slc_pair=slc_pair,
    output_path="/data/stacks/cn_xian_s1_asc_iw",
    dry_run=True)

s1_coreg.coregister()
