import coregistration


class SlcImage:
    def __init__(self, date: str, folder: str):
        self.date = date
        self.folder = folder


class SlcPair:
    def __init__(self, master: SlcImage, slave: SlcImage):
        self.master = master
        self.slave = slave

    def coregister(
        self, 
        output_path: str = "/data/stacks/cn_xian_s1_asc_iw", 
        dry_run: bool = True
    ):
        s1_coreg = coregistration.Sentinel1Coregistration(
            slc_pair=self, 
            output_path=output_path, 
            dry_run=dry_run
        )

        s1_coreg.coregister()

class SlcStack:
    def __init__(self, input, output, master):
        pass

    def coregister(self, update: bool = False) -> None:   
        master = image_list[0]
        for slave in image_list[1:]: 
            SlcPair(master=master, slave=slave).coregister()