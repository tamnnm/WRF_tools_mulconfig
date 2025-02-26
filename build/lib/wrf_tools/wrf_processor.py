import os
import shutil
import subprocess
import glob
import re
from datetime import datetime, timedelta
import numpy as np
import xarray as xr
from collections import OrderedDict
import pandas as pd

class WRFProcessor:
    def __init__(self, run_period, domain_center, domain, paths, run_dir):
        self.run_period = run_period
        self.domain_center = domain_center
        self.domain = domain
        self.paths = paths
        self.run_dir = run_dir

    def setup_directories(self):
        wpsdir = self.paths['wpsdir']
        os.makedirs(self.run_dir, exist_ok=True)
        for idir in ['geogrid', 'ungrib', 'metgrid']:
            shutil.copytree(os.path.join(wpsdir, idir), os.path.join(self.run_dir, idir), dirs_exist_ok=True)
            shutil.copy2(os.path.join(wpsdir, f'{idir}.exe'), os.path.join(self.run_dir, f'{idir}.exe'))
        shutil.copy2(os.path.join(wpsdir, 'link_grib.csh'), self.run_dir)
        return self.run_dir

    def copy_wrf_run_files(self):
        source_dir = os.path.join(self.paths['wrfdir'], 'run')
        destination_dir = self.run_dir
        
        for file_name in os.listdir(source_dir):
            if file_name == 'namelist.input':
                continue
            full_file_name = os.path.join(source_dir, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_dir)
                
    def modify_namelist(self, namelist_path_in, namelist_path_out, replacements):
        with open(namelist_path_in, 'r') as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            for key, value in replacements.items():
                if re.match(rf'^\s*{key}\s*=', line):
                    lines[i] = f' {key} = {value},\n'
        with open(namelist_path_out, 'w') as file:
            file.writelines(lines)

    def generate_date_range(self):
        start_date = self.run_period['start_date']
        end_date = self.run_period['end_date']
        return [(datetime.strptime(start_date, '%Y-%m-%d %H') + timedelta(days=i)).strftime('%Y%m%d') 
                for i in range((datetime.strptime(end_date, '%Y-%m-%d %H') - datetime.strptime(start_date, '%Y-%m-%d %H')).days + 1)]


    def set_domains(self):
        max_dom = self.domain['max_dom']
        parent_grid_ratio = self.domain['parent_grid_ratio']
        e_we_ini = self.domain['e_we_ini']
        e_sn_ini = self.domain['e_sn_ini']

        e_we = [] 
        e_sn = []
        e_we.append(e_we_ini[0])
        e_sn.append(e_sn_ini[0])
        ips = [1]
        jps = [1]

        for i in range(1, max_dom):
            ii = np.arange(1, e_we[i-1]//2) - 1
            jj = np.arange(1, e_sn[i-1]//2) - 1
            nx2 = (e_we[i-1] - ii*2 - 1) * parent_grid_ratio[i]
            ny2 = (e_sn[i-1] - jj*2 - 1) * parent_grid_ratio[i]
            is2 = np.argmin(abs(nx2 - e_we_ini[i]))
            js2 = np.argmin(abs(ny2 - e_sn_ini[i]))
            e_we.append(nx2[is2] + 1)
            e_sn.append(ny2[js2] + 1)
            ips.append(ii[is2] + 1)
            jps.append(jj[js2] + 1)
        
        return (', '.join(np.asarray(ips).astype('int').astype('str')),
                ', '.join(np.asarray(jps).astype('int').astype('str')),
                ', '.join(np.asarray(e_we).astype('int').astype('str')),
                ', '.join(np.asarray(e_sn).astype('int').astype('str')))

    def generate_namelist_parameters(self):
        max_dom = self.domain['max_dom']
        lat = self.domain_center['lat']
        lon = self.domain_center['lon']
        start_date = self.run_period['start_date']
        end_date = self.run_period['end_date']
        parent_grid_ratio = self.domain['parent_grid_ratio']
        dx = self.domain['dx']
        dy = self.domain['dy']
        #e_we_ini = self.domain['e_we_ini']
        #e_sn_ini = self.domain['e_sn_ini']

        vd = {}
        vd['max_dom'] = str(max_dom)
        vd['start_date'] = ','.join([f'"{start_date.replace(" ", "_")}:00:00"']*max_dom)
        vd['end_date'] = ','.join([f'"{end_date.replace(" ", "_")}:00:00"']*max_dom)
        vd['geog_data_res'] = '"modis_landuse_20class_30s_with_lakes", ' * max_dom
        vd['parent_id'] = '1,1,2'  
        vd['parent_grid_ratio'] = ','.join(map(str, parent_grid_ratio))
        vd['dx'] = str(dx)
        vd['dy'] = str(dy)
        vd['i_parent_start'], vd['j_parent_start'], vd['e_we'], vd['e_sn'] = self.set_domains()
        
        vd['ref_lat'], vd['ref_lon'] = str(lat), str(lon)

        if float(vd['ref_lat']) > 30. or float(vd['ref_lat']) < -30.: 
            print('---high latitude: ', vd['ref_lat'])
            vd['map_proj']  = '"lambert"'
            vd['truelat1'], vd['truelat2']  = vd['ref_lat'], vd['ref_lat']
            vd['stand_lon'] = vd['ref_lon']
        else:
            print('---low latitude: ', vd['ref_lat'])
            vd['map_proj'] = '"mercator"'
            vd['truelat1'], vd['truelat2']  = vd['ref_lat'], vd['ref_lat']
            vd['stand_lon'] = vd['ref_lon']  
        
        return vd

    def update_namelist_time_domain_from_wps(self):
        wps = open(os.path.join(self.run_dir, 'namelist.wps')).readlines()
        win = open(os.path.join(self.run_dir, 'namelist.input')).readlines()

        vdinput = OrderedDict([(l.split('=')[0].strip(), l.split('=')[1].strip()) for l in win if len(l.split('=')) > 1])
        vdwps = OrderedDict([(l.split('=')[0].strip(), l.split('=')[1].strip()) for l in wps if len(l.split('=')) > 1])

        max_dom = int(vdwps['max_dom'][0])
        dx = int(vdwps['dx'].split(',')[0])
        dy = int(vdwps['dy'].split(',')[0])
        parent_grid_ratio = [int(x) for x in vdwps['parent_grid_ratio'].split(',') if x.strip().lower() != '']

        st, en = [pd.to_datetime(vdwps[a].split(',')[0].strip().replace('"', '').replace("'", ""), format='%Y-%m-%d_%H:%M:%S') 
              for a in ['start_date', 'end_date']]

        vd = {
            'run_days': str((en - st).days),
            'run_hours': str((en - st).seconds // 3600),
            'start_year': (str(st.year) + ', ') * max_dom,
            'start_month': (str(st.month) + ', ') * max_dom,
            'start_day': (str(st.day) + ', ') * max_dom,
            'start_hour': (str(st.hour) + ', ') * max_dom,
            'end_year': (str(en.year) + ', ') * max_dom,
            'end_month': (str(en.month) + ', ') * max_dom,
            'end_day': (str(en.day) + ', ') * max_dom,
            'end_hour': (str(en.hour) + ', ') * max_dom,
        }

        for k in ['max_dom', 'e_we', 'e_sn', 'start_date', 'end_date', 'dx', 'dy',
                  'parent_grid_ratio', 'i_parent_start', 'j_parent_start', 'fg_name']:
            vd[k] = vdwps[k]

        dxs, dys = np.array([dx]), np.array([dy])
        for idom in range(1, max_dom):
            dxs = np.append(dxs, dxs[idom - 1] / parent_grid_ratio[idom])
            dys = np.append(dys, dys[idom - 1] / parent_grid_ratio[idom])

        parent_id = np.arange(max_dom)
        parent_id[0] = 1
        vd['parent_id'] = ','.join(parent_id.astype('str'))
        vd['grid_id'] = ','.join(np.arange(1, max_dom + 1).astype('str'))
        
        vd['dx'] = ', '.join(dxs.astype('str'))
        vd['dy'] = ', '.join(dys.astype('str'))

        print(vd['dx'] )
        
        e_vert = vdinput['e_vert'].split(',')[0]
        vd['e_vert'] = ', '.join([e_vert] * max_dom)
        vd['parent_time_step_ratio'] = ', '.join(map(str, parent_grid_ratio))
        vd['time_step'] = str( int(dxs[0] * 6 / 1000))
        
        vd['feedback'] = '0'
        vd['input_from_file'] = ', '.join(['.true.']*max_dom)

        for k, v in zip(['history_interval', 'frames_per_outfile'], ['60', '24']):
            vd[k] = (v+',')*max_dom
        
        for il, l in enumerate(win):
            k = l.split('=')[0].strip()
            if k in vd.keys():
                win[il] = k+'='+vd[k]+'\n'
        
        open(os.path.join(self.run_dir, 'namelist.input'), 'w').write(''.join(win))

    def get_met_em_info(self):
        try:
            namelist = {}
            ds = xr.open_dataset(sorted(glob.glob(os.path.join(self.run_dir, 'met_em*.nc')))[0])
            namelist['num_metgrid_levels'] = str(ds.dims['num_metgrid_levels'])
            namelist['num_land_cat'] = str(ds.LANDUSEF.shape[1])
            namelist['num_metgrid_soil_levels'] = str(ds.dims['num_st_layers'])
            return namelist
        except:
            print('Errors: No met_em files')
            

    def run_ungrib_era5(self, date_range):
        source_file = os.path.join(self.run_dir, 'ungrib/Variable_Tables/Vtable.ECMWF')
        target_link = os.path.join(self.run_dir, 'Vtable')
        original_dir = os.getcwd()
        os.chdir(self.run_dir)
        if os.path.islink(target_link) or os.path.exists(target_link): os.remove(target_link)
        os.symlink(source_file, target_link)
        os.chdir(original_dir)
        
        prefixes = ['ERA5A', 'ERA5S']
        levels = ['pressure', 'surface']
        
        for i in range(2):
            prefix = prefixes[i]
            level = levels[i]
            subprocess.run(['rm', '-f'] + glob.glob(os.path.join(self.run_dir,   'GRIB*')), check=True)
            reanal_files = [os.path.join(self.paths['renaldir'], f'era5_ungrib_{level}_levels_{date}.grib')
                            for date in date_range  ]
            subprocess.run(['./link_grib.csh'] + reanal_files, cwd=self.run_dir, check=True)
            subprocess.run(['rm', '-f'] + glob.glob(os.path.join(self.run_dir, prefix + '*')), check=True)
            self.modify_namelist(os.path.join(self.run_dir, 'namelist.wps'), os.path.join(self.run_dir, 'namelist.wps'), {'prefix': f'"{prefix}"'})
            subprocess.run(['./ungrib.exe'], cwd=self.run_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['rm', '-f'] + glob.glob(os.path.join(self.run_dir,   'GRIB*')), check=True)

        fg_name = ', '.join([f'"{prefix}"' for prefix in prefixes])

        replacements = {'fg_name' : f'{fg_name}'}

        self.modify_namelist(os.path.join(self.run_dir, 'namelist.wps'), os.path.join(self.run_dir, 'namelist.wps'), replacements) 


    def run_wrf_process(self, executable, mpi=False, num_cores=4):
        cmd = ['mpirun', '-np', str(num_cores), executable] if mpi else [executable]
        subprocess.run(cmd, cwd=self.run_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    def run_wrf(self):
        #start_date = self.run_period['start_date']
        #end_date = self.run_period['end_date']
        #max_dom = self.domain['max_dom']
        #parent_grid_ratio = self.domain['parent_grid_ratio']
        #dx = self.domain['dx']
        #dy = self.domain['dy']
        #e_we_ini = self.domain['e_we_ini']
        #e_sn_ini = self.domain['e_sn_ini']
        #lat = self.domain_center['lat']
        #lon = self.domain_center['lon']
        
        namelist_wps_out = os.path.join(self.run_dir, 'namelist.wps')
        namelist_input_out = os.path.join(self.run_dir, 'namelist.input')
        
        date_range = self.generate_date_range()

        self.setup_directories()
        self.copy_wrf_run_files()

        self.modify_namelist(self.paths['namelist_wps'], namelist_wps_out, {}) 
        self.modify_namelist(self.paths['namelist_input'], namelist_input_out, {}) 
        
        replacements = self.generate_namelist_parameters()
        replacements.update({'geog_data_path' : f'"{self.paths["geogdir"]}"'})

        self.modify_namelist(namelist_wps_out, namelist_wps_out, replacements) 
        self.run_wrf_process('./geogrid.exe')
        
        self.run_ungrib_era5(date_range)
        
        self.run_wrf_process('./metgrid.exe')
        
        self.update_namelist_time_domain_from_wps()
        
        replacements = self.get_met_em_info()
        self.modify_namelist(namelist_input_out, namelist_input_out, replacements) 
        
        self.run_wrf_process('./real.exe')
        self.run_wrf_process('./wrf.exe', mpi=True, num_cores=4)



if __name__ == "__main__":
    run_period = { 'start_date' : "2024-01-01 00", 'end_date' : "2024-01-02 12" }
    domain_center = { 'id': 'Mogadishu', 'lat': 2.05, 'lon': 45.32 }
    domain = { 'max_dom': 2, 'parent_grid_ratio' : (1,3,3), 'dx' : 6000, 'dy' : 6000, 'e_we_ini' : (50, 50, 50), 'e_sn_ini' : (50, 50, 50) }
    paths = {
        'wpsdir': "/Volumes/work/WRF_program/WRF_install/WPS/",
        'wrfdir': "/Volumes/work/WRF_program/WRF_install/WRF_mpi/",
        'geogdir': "/Volumes/work/WRF_program/WPS_GEOG",
        'renaldir': "/Volumes/work/WRF_program/era5/"+domain_center['id']+'/',
        'namelist_wps' : "namelist/namelist.wps",
        'namelist_input': "namelist/namelist.input"
    }
    base_dir = '/Volumes/work/share_data/2025/WRF'
    run_dir = os.path.join(base_dir, 'Run_WRF', domain_center['id'])

    wrf_processor = WRFProcessor(run_period, domain_center, domain, paths, run_dir)
    wrf_processor.run_wrf()
    
    
    
    
    
    
    