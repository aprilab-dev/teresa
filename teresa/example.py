import stack

source_dir = "/data/slc/cn_xian_s1_asc_iw"
destination = "/data/stack/cn_xian_s1_asc_iw"
master = "20210401"

output = (
    stack
    .Sentinel1SlcStack(sourcedir=source_dir)
    .load()
    .coregister(output=destination, master=master, dry_run=False)
)
