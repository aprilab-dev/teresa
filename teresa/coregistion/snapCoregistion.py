import logging
from teresa.processor.snapProcessor import snapProcessor
from distutils.dir_util import copy_tree

class snapCoregistion(object):
    def __init__(self, params, slc_stack):
        """
        Initialize the snapCoregistion class.
        
        Parameters:
            parms (dict): A dictionary containing the parameters for coregistration.
            slc_stack (object): An object representing the stack of SLC images.
        """
        # Store input parameters
        self.params    = params
        self.slc_stack = slc_stack

        # Initialize SNAP processor
        self.snap      = snapProcessor(self.params)

        # Workspace directories
        self.work_dir = self.slc_stack.work_dir + os.sep + "workspace"
        self.temp_dir = self.work_dir + os.sep + "temp"

        # DEM creation flag
        self.create_dem = True

        # Supported IPF version for processing
        self.IPF_GOOD_VERSION = '002.43'

        # File pattern for master images
        self.master_file_glob = '[iq]_'+2*'[a-zA-Z]'+'_mst_'+2*'[0-9]'+ 3*'[a-zA-Z]'+4*'[0-9]'+'.img'
    
    
    def run(self):
        """
        Main workflow to perform SLC coregistration.

        Steps:
            1. Create working directory.
            2. Preprocess the master SLC image (EAP calibration).
            3. Coregister each slave SLC image to the master.
            4. Clean up temporary files.
        """
        # 1. Create working directory
        self.create_work_dir()

        # 2. Preprocess master SLC image (EAP calibration)
        master_date = self.slc_stack.master_date
        self.preprocess_slc_date(master_date)

        # 3. Coregister each slave SLC image
        for slave_date in self.slc_stack.slave_dates:
            # 3.1 Skip already coregistered slave dates
            merged_dim_path = os.path.join(self.work_dir, slave_date, 'merged.dim')
            if os.path.exists(merged_dim_path):
                logger.info('Slave date %s already coregistered, skipping...', slave_date)
                continue

            # 3.2 Preprocess slave SLC image (EAP calibration)
            self.preprocess_slc_date(slave_date)

            # 3.3 Coregister the slave image (subswaths + merge)
            self.coregister_single_image(slave_date)

        # 4. Clean up temporary directory
        if os.path.exists(self.temp_dir):
            logger.info('Cleaning up temporary coregistration data in %s', self.temp_dir)
            shutil.rmtree(self.temp_dir)
    
    def coregister_single_image(self, slave_date: str):
        """
        Perform coregistration of a single slave SLC image to the master SLC image.

        The method performs the following steps:
            1. Coregister each subswath of the slave image.
            2. Merge the coregistered subswaths.
            3. Copy the merged products to the working directory.
            4. Optionally, generate a DEM.
            5. Clean up temporary files.
        
        Args:
            slave_date (str): Date of the slave SLC image (format 'YYYYMMDD').
        """
        # 1. Coregister all subswaths
        merged_dim_path = os.path.join(self.temp_dir, slave_date, 'merged.dim')
        merge_kwargs = {'output_product': merged_dim_path}

        for subswath_idx in range(1, 4):
            # Coregister the current subswath
            self.coregister_subswath(slave_date, subswath_idx)
            subswath_output = os.path.join(
                self.temp_dir, slave_date, 'subswaths', f'{slave_date}_IW{subswath_idx}.dim'
            )
            merge_kwargs[f'input_product_subswath_{subswath_idx}'] = subswath_output

        # 2. Merge coregistered subswaths
        self.snap.merge_subswaths(**merge_kwargs)

        # 3. Copy merged products to work directory
        temp_data_path = os.path.join(self.temp_dir, slave_date, 'merged.data')
        out_data_path  = os.path.join(self.work_dir, slave_date, 'merged.data')
        copy_tree(temp_data_path, out_data_path)

        temp_dim_path  = os.path.join(self.temp_dir, slave_date, 'merged.dim')
        out_dim_path   = os.path.join(self.work_dir, slave_date, 'merged.dim')
        shutil.copyfile(temp_dim_path, out_dim_path)

        # 4. Generate DEM if requested 
        # TODO: 
        if self.create_dem:
            self._create_dem(dates_slv[create_dem_idx])
            self.create_dem = False

        # 5. Clean up temporary files
        temp_slave_dir = os.path.join(self.temp_dir, slave_date)
        if os.path.exists(temp_slave_dir):
            print('Cleaning up temporary coregistration data for slave date %s', slave_date)
            shutil.rmtree(temp_slave_dir)


    def coregister_subswath(self, slave_date: str, subswath: int):
        """
        Coregister a specific TOPS subswath for a given slave acquisition date.

        The coregistration strategy depends on whether the master and/or slave
        SLC products consist of single or multiple subswaths.
        
        Args:
            slave_date (str): Slave acquisition date (format: 'YYYYMMDD')
            subswath (int):   Subswath index (e.g. IW1, IW2, IW3 → 1, 2, 3)
        """

        # ------------------------------------------------------------------
        # Determine SLC structure: single-subswa​th vs multi-subswath
        # ------------------------------------------------------------------
        master_path = self.slc_stack.data_path_map[self.slc_stack.master_date]
        slave_path  = self.slc_stack.data_path_map[slave_date]

        has_multi_subswath_master = len(master_path) > 1
        has_multi_subswath_slave  = len(slave_path) > 1

        has_single_subswath_master = not has_multi_subswath_master
        has_single_subswath_slave  = not has_multi_subswath_slave

        # ------------------------------------------------------------------
        # Resolve input slave product
        #   - multi-subswa​th  → directory
        #   - single-subswa​th → .dim file if exists, otherwise raw product
        # ------------------------------------------------------------------
        slave_out_dir = os.path.join(self.temp_dir, slave_date)
        slave_slc_basename = os.path.basename(slave_path[0])

        input_slave_products = slave_out_dir
        if has_single_subswath_slave:
            input_slave_products = os.path.join(slave_out_dir, slave_slc_basename + '.dim')
            if not os.path.exists(input_slave_products):
                input_slave_products = os.path.join(slave_out_dir, slave_slc_basename)

        # ------------------------------------------------------------------
        # Resolve input master product (same logic as slave)
        # ------------------------------------------------------------------
        master_out_dir = os.path.join(self.temp_dir, self.slc_stack.master_date)
        master_slc_basename = os.path.basename(master_path[0])

        input_master_products = master_out_dir
        if has_single_subswath_master:
            input_master_products = os.path.join(master_out_dir, master_slc_basename + '.dim')
            if not os.path.exists(input_master_products):
                input_master_products = os.path.join(master_out_dir, master_slc_basename)

        # ------------------------------------------------------------------
        # Output product for current subswath
        # ------------------------------------------------------------------
        dem_name = 'SRTM 1Sec HGT'
        output_product = os.path.join(
            self.temp_dir,
            slave_date,
            'subswaths',
            f'{slave_date}_IW{subswath}.dim'
        )

        # ------------------------------------------------------------------
        # Select SNAP coregistration graph based on subswath structure
        # ------------------------------------------------------------------
        if has_multi_subswath_master and has_multi_subswath_slave:
            # Multi-subswa​th master  → Multi-subswa​th slave
            self.snap.coregister_subswath(
                subswath=subswath,
                pol=self.slc_stack.pol,
                input_slave_products=input_slave_products,
                input_master_products=input_master_products,
                output_product=output_product,
                dem_name=dem_name
            )

        if has_single_subswath_master and has_multi_subswath_slave:
            # Single-subswa​th master → Multi-subswa​th slave
            self.snap.coregister_subswath_single_slave_slice(
                subswath=subswath,
                pol=self.slc_stack.pol,
                input_slave_products=input_slave_products,
                input_master_products=input_master_products,
                output_product=output_product,
                dem_name=dem_name
            )

        if has_multi_subswath_master and has_single_subswath_slave:
            # Multi-subswa​th master  → Single-subswa​th slave
            self.snap.coregister_subswath_single_master_slice(
                subswath=subswath,
                pol=self.slc_stack.pol,
                input_slave_products=input_slave_products,
                input_master_products=input_master_products,
                output_product=output_product,
                dem_name=dem_name
            )

        if has_single_subswath_master and has_single_subswath_slave:
            # Single-subswa​th master → Single-subswa​th slave
            self.snap.coregister_subswath_single_slice(
                subswath=subswath,
                pol=self.slc_stack.pol,
                input_slave_products=input_slave_products,
                input_master_products=input_master_products,
                output_product=output_product,
                dem_name=dem_name
            )
        

    
    def preprocess_slc_date(self, date: str):
        """
        Preprocess all SLC images for a given date by applying EAP phase calibration if necessary.

        Args:
            date (str): The date of the SLC stack to preprocess (format 'YYYYMMDD').

        Steps:
            1. Iterate over all SLC image files for the specified date.
            2. Check if the calibrated output already exists.
            3. If not, check the IPF version:
                - If IPF version is outdated, run EAP phase calibration.
                - If IPF version is sufficient, create a symbolic link to the original image.
        """
        # Iterate over all SLC files for the given date
        slc_path_list = self.slc_stack.data_path_map.get(date, [])
        for idx, slc_file_path in enumerate(slc_path_list):
            slc_file_name = os.path.basename(slc_file_path)
            calibrated_output_path = os.path.join(self.temp_dir, date, slc_file_name)

            # Skip processing if output already exists
            if os.path.exists(calibrated_output_path):
                continue

            # Check IPF version to determine if EAP calibration is needed
            ipf_version = self.find_ipf_version(slc_file_path)
            if ipf_version < self.IPF_GOOD_VERSION:
                # Apply EAP phase calibration
                self.snap.apply_EAP_phase_calibration(
                    input_product=slc_file_path,
                    output_product=calibrated_output_path
                )
            else:
                # IPF version is sufficient, just create a symbolic link
                os.symlink(slc_file_path, calibrated_output_path)

            
    def create_work_dir(self):
        """
        Create the workspace directory structure for SNAP coregistration.

        This includes:
        1. The main workspace directory
        2. A DEM directory inside the workspace
        3. Individual directories for each SLC date under both workspace and temp directories
        """
        # 1. Create the main workspace directory
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        # 2. Create the DEM subdirectory
        dem_dir = os.path.join(self.work_dir, "dem")
        if not os.path.exists(dem_dir):
            os.makedirs(dem_dir)

        # 3. Create directories for each date
        for date in self.slc_stack.dates:
            # 3.1 Workspace directory for this date
            date_work_dir = os.path.join(self.work_dir, date)
            if not os.path.exists(date_work_dir):
                os.makedirs(date_work_dir)

            # 3.2 Temporary processing directory for this date
            date_temp_dir = os.path.join(self.temp_dir, date)
            if not os.path.exists(date_temp_dir):
                os.makedirs(date_temp_dir)