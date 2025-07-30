import os
import subprocess
from teresa.utils.TeresaLog import global_log

# DorisExpert
class dorisProcessor():
    def __init__(self, params):
        self.params = params   

    def _doris(self, arg):
        _DORIS = os.getenv('STACK_BUILDER_DORIS', '/home/junjun/doris/doris/src/doris') 
        with open("doris.log", 'w') as log_file:
            return subprocess.call([_DORIS, arg], stdout=log_file, stderr=log_file)

    def coarseorb(self, path):
        global_log.step_start("coarseorb")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'coarse_orbits:' in line][0].split()[1] == '1':
                    global_log.step_end("coarseorb", status="SKIPPED")
                    return
        
        self._doris('../dorisin/coarseorb.dorisin')

        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'coarse_orbits:' in line][0].split()[1] == '0':
                    global_log.step_end("coarseorb", status="FAIL")
                    raise ValueError(f"coarseorb error.")
        
        global_log.step_end("coarseorb", status="SUCCESS")

    def coarsecorr(self, path):
        global_log.step_start("coarsecorr")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'coarse_correl:' in line][0].split()[1] == '1':
                    global_log.step_end("coarsecorr", status="SKIPPED")
                    return
        
        self._doris('../dorisin/coarsecorr.dorisin')
        
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'coarse_correl:' in line][0].split()[1] == '0':
                    global_log.step_end("coarsecorr", status="FAIL")
                    raise ValueError(f"coarsecorr error.")
        
        global_log.step_end("coarsecorr", status="SUCCESS")

    def fine(self, path):
        global_log.step_start("fine")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'fine_coreg:' in line][0].split()[1] == '1':
                    global_log.step_end("fine", status="SKIPPED")
                    return

        self._doris('../dorisin/fine.dorisin')

        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'fine_coreg:' in line][0].split()[1] == '0':
                    global_log.step_end("fine", status="FAIL")
                    raise ValueError(f"fine error.")
        
        global_log.step_end("fine", status="SUCCESS")

    def coregpm(self, path):
        global_log.step_start("coregpm")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'comp_coregpm:' in line][0].split()[1] == '1':
                    global_log.step_end("coregpm", status="SKIPPED")
                    return
                
        self._doris('../dorisin/coregpm.dorisin')

        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'comp_coregpm:' in line][0].split()[1] == '0':
                    global_log.step_end("coregpm", status="FAIL")
                    raise ValueError(f"coregpm error.")
        
        global_log.step_end("coregpm", status="SUCCESS")

    def resample(self, path):
        global_log.step_start("resample")
        os.chdir(path)
        if os.path.exists('slave.res'):
            with open('slave.res') as coreg_out:
                if [line for line in coreg_out if 'resample:' in line][0].split()[1] == '1':
                    global_log.step_end("resample", status="SKIPPED")
                    return

        self._doris('../dorisin/resample.dorisin')
        
        if os.path.exists('slave.res'):
            with open('slave.res') as coreg_out:
                if [line for line in coreg_out if 'resample:' in line][0].split()[1] == '0':
                    global_log.step_end("resample", status="FAIL")
                    raise ValueError(f"resample error.")
        
        global_log.step_end("resample", status="SUCCESS")

    def interfero(self, path):
        global_log.step_start("interfero")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'interfero:' in line][0].split()[1] == '1':
                    global_log.step_end("interfero", status="SKIPPED")
                    return

        self._doris('../dorisin/interfero.dorisin')

        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'interfero:' in line][0].split()[1] == '0':
                    global_log.step_end("interfero", status="FAIL")
                    raise ValueError(f"interfero error.")
        
        global_log.step_end("interfero", status="SUCCESS")

    
    def dem(self, path):
        global_log.step_start("dem")
        os.chdir(path)
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'dem_assist:' in line][0].split()[1] == '1':
                    global_log.step_end("dem", status="SKIPPED")
                    return

        self._doris('../dorisin/dem.dorisin')
        
        if os.path.exists('coreg.out'):
            with open('coreg.out') as coreg_out:
                if [line for line in coreg_out if 'dem_assist:' in line][0].split()[1] == '0':
                    global_log.step_end("dem", status="FAIL")
                    raise ValueError(f"dem error.")
        