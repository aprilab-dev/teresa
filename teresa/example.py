import stack

slc_dir = "/data/slc/cn_xian_s1_asc_iw"
coregistered_dir = "/data/stack/cn_xian_s1_asc_iw"
master = "20210401"

output = (
    stack
    .Sentinel1SlcStack(sourcedir=slc_dir)
    .load()
    .coregister(output=coregistered_dir, master=master)
)
