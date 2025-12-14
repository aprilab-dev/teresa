# import os
import subprocess
from teresa.utils.TeresaLog import global_log

# DorisExpert
class snapProcessor():
    def __init__(self, params):
        self.params = params   
        self.snap_processor = self.params['SNAP_parameters']['gptPath']
        self.cache_size = self.params['SNAP_parameters']['cache_size']
        self.nr_proc = self.params['SNAP_parameters']['nr_proc']
        self.graphs_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "graphs")

    def run_graph(self, graph_command, **kwargs):
        params = ['{} {} '.format(self.snap_processor, graph_command)]
        for name, value in kwargs.items():
            params.append('-P{}=\'{}\' '.format(name, value))
        params.append('-c {}G -q {} -e '.format(self.cache_size, self.nr_proc))

        gpt_call_str = ''.join(params)
        try:
            subprocess.run(gpt_call_str, shell=True, check=True, stderr=subprocess.PIPE)
            return
        except subprocess.CalledProcessError as e:
            raise RuntimeError("Snap command failed \n {} \n Stderr: {}"
                .format(gpt_call_str, e.stderr)) from e

    def apply_EAP_phase_calibration(self, input_product, output_product):
        # self.snap.apply_EAP_phase_calibration(input_product=img_file, output_product=output_product)
        pass
    
    def coregister_subswath(self):
        pass

    def coregister_subswath_single_slave_slice(self):
        pass
    
    def coregister_subswath_single_master_slice(self):
        pass
    
    def coregister_subswath_single_slice(self):
        pass

    def merge_subswaths(self):
        pass

    def add_elevation_band(self):
        pass