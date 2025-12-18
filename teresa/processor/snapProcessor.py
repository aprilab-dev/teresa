import os
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

    def apply_EAP_phase_calibration(self, **kwargs):
        graph_command = os.path.join(self.graphs_dir, "apply_EAP_phase_calibration.xml")

        self.run_graph(graph_command,
            input_product=input_product,
            output_product=output_product)  

    
    def coregister_subswath(self, subswath, pol, input_slave_products, input_master_products, output_product, dem_name):
        graph_command = os.path.join(self.graphs_dir, "coregister_subswath_single_slice.xml")

        self.run_graph(graph_command,
            subswath=subswath,
            pol=pol,
            input_slave_products=input_slave_products,
            input_master_products=input_master_products,
            output_product=output_product,
            dem_name=dem_name)

    def coregister_subswath_single_slave_slice(self, subswath, pol, input_slave_products, input_master_products, output_product, dem_name):
        graph_command = os.path.join(self.graphs_dir, "coregister_subswath_single_slice.xml")

        self.run_graph(graph_command,
            subswath=subswath,
            pol=pol,
            input_slave_products=input_slave_products,
            input_master_products=input_master_products,
            output_product=output_product,
            dem_name=dem_name)
    
    def coregister_subswath_single_master_slice(self, subswath, pol, input_slave_products, input_master_products, output_product, dem_name):
        graph_command = os.path.join(self.graphs_dir, "coregister_subswath_single_slice.xml")

        self.run_graph(graph_command,
            subswath=subswath,
            pol=pol,
            input_slave_products=input_slave_products,
            input_master_products=input_master_products,
            output_product=output_product,
            dem_name=dem_name)
    
    def coregister_subswath_single_slice(self, subswath, pol, input_slave_products, input_master_products, output_product, dem_name):
        graph_command = os.path.join(self.graphs_dir, "coregister_subswath_single_slice.xml")

        self.run_graph(graph_command,
            subswath=subswath,
            pol=pol,
            input_slave_products=input_slave_products,
            input_master_products=input_master_products,
            output_product=output_product,
            dem_name=dem_name)

    def merge_subswaths(self, **merge_kwargs):
        graph_command = os.path.join(self.graphs_dir, "merge_subswaths.xml")
        self.run_graph(graph_command, **merge_kwargs)

    def add_elevation_band(self, input_product, output_product, dem_name):
        graph_command = os.path.join(self.graphs_dir, "add_elevation_band.xml")
        self.run_graph(graph_command,
            input_product=input_product,
            output_product=output_product,
            dem_name=dem_name)

    def run_graph(self, graph, **kwargs):
        '''Processes GPT graph.

        Args:
            graph (str): abs path to graph file.
            **kwargs: key-value pairs of GPT parameters.

        '''
        params = ['{} {} '.format(self.snap_processor, graph)]
        for name, value in kwargs.items():
            params.append('-P{}=\'{}\' '.format(name, value))
        params.append('-c {}G -q {} -e '.format(self.cache_size, self.nr_proc))
        
        gpt_call_str = ''.join(params)
        print("Running snap command: \n {}".format(gpt_call_str))
        try:
            subprocess.run(gpt_call_str, shell=True, check=True, stderr=subprocess.PIPE)
            return
        except subprocess.CalledProcessError as e:
            raise RuntimeError("Snap command failed \n {} \n Stderr: {}"
                .format(gpt_call_str, e.stderr)) from e