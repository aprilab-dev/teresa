import time
from datetime import datetime

class TeresaLog:
    def __init__(self, output_file="logs/teresa_run.log"):
        self.teresa_version = "v0.1.0"
        self.output_file = output_file
        self.radar_type = ""
        self.start_time = None
        self.task_index = 0
        self.task_count = 0
        self.success_count = 0
        self.logs = []
    
    def write(self, message=""):
        print(message)
        self.logs.append(message)
        if self.output_file:
            with open(self.output_file, "a") as f:
                f.write(message + "\n")

    def start_global(self, task_count=None):
        self.start_time = time.time()
        self.task_count = task_count or 0
        self.write("=" * 100)
        self.write(" " * 39 + "Teresa Processing Log")
        self.write("-" * 100)
        self.write(f" Script Version : {self.teresa_version}")
        self.write(f" Radar Type     : {self.radar_type}")
        if self.task_count:
            self.write(f" Total Tasks    : {self.task_count} stacks")
        self.write(f" Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write("=" * 100)
        self.write()

    def start_task(self, task):
        self.task_index += 1
        self.task_start_time = time.time()
        header = f"[{self.task_index} / {self.task_count}] Date: {task['processing_date']}"
        self.write()
        self.write(">" * 37 + f" {header} " + "<" * 37)
        self.write(f" Meta File      : {task['meta_file']}")
        self.write(f" Data File      : {task['data_file']}")
        self.write(f" Master Date    : {task['master']}")
        self.write(f" Slave Date     : {task['slave']}")
        self.write("-" * 100)
        self.write()

    def step_start(self, step):
        now = datetime.now().strftime("%H:%M:%S")
        self.write(f"[Step] {step:<15} | START @ {now}")

    def step_end(self, step, status):
        now = datetime.now().strftime("%H:%M:%S")
        self.write(f"[Step] {step:<15} | END   @ {now} | Status: {status}")
        self.write()

    def end_task(self, success=True):
        elapsed = int(time.time() - self.task_start_time)
        mm, ss = divmod(elapsed, 60)
        status = "Success" if success else "Failed"
        if success:
            self.success_count += 1
        self.write("-" * 100)
        self.write(f" Task Status: {status}")
        self.write(f" Task Time  : {mm:02}:{ss:02}")
        self.write("=" * 100)
        self.write()

    def end_global(self):
        elapsed = int(time.time() - self.start_time)
        mm, ss = divmod(elapsed, 60)
        self.write("=" * 100)
        self.write(" " * 39 + "All Processing Done.")
        self.write("-" * 100)
        self.write(f" Total Time : {mm:02}:{ss:02}")
        self.write(f" Success    : {self.success_count} / {self.task_count}")
        self.write(f" Failures   : {self.task_count - self.success_count}")
        self.write("=" * 100)

    def start_read(self, date):
        self.write(f"[File Load] Date: {date}")
    def read_meta(self, meta_file):
        self.write(f"    Meta File  : {meta_file}")   
    def read_data(self, data_file):
        self.write(f"    Data File  : {data_file}")
    def read_status(self, status):
        self.write(f"    Status     : {status}")
        self.write()

    
    def start_dem(self):
        self.write("Starting DEM-based coregistration...")

    def end_dem(self):  
        self.write("DEM-based coregistration completed.")
        self.write("=" * 100)

global_log = TeresaLog(output_file=None)