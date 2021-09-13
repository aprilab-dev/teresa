import stack

slc_dir = "/data/slc/cn_xian_s1_asc_iw"
coregistered_dir = "/data/stack/cn_xian_s1_asc_iw"

output = (
    stack
    .SlcStack(input=slc_dir, output=coregistered_dir, master="20000101")
    .coregister(update=False)
)